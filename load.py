"""
Week 2: load the raw files into a DuckDB database and build clean tables.

Layers (the same idea dbt uses later):
  raw_*   the files as they are, plus which file each row came from
  stg_*   cleaned: proper types, UTC timestamps, duplicates removed
  fct_hourly   one row per hour: demand joined with temperature

Usage:
    python load.py
"""

import csv
import json
from pathlib import Path

import duckdb

RAW_DIR = Path("data/raw")
STAGING_DIR = Path("data/staging")
DB_PATH = Path("data/warehouse.duckdb")


# ---- Step 1: flatten the raw files into simple CSVs DuckDB can read ------

def stage_demand() -> Path:
    """Copy every IESO demand file into one CSV, skipping the comment lines."""
    out = STAGING_DIR / "demand.csv"
    with out.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "hour_ending", "market_demand_mw",
                         "ontario_demand_mw", "source_file"])
        for path in sorted((RAW_DIR / "demand").glob("PUB_Demand_*.csv")):
            for line in path.read_text().splitlines():
                if not line or line.startswith("\\") or line.startswith("Date,"):
                    continue
                date, hour, market, ontario = line.split(",")[:4]
                writer.writerow([date, hour, market, ontario, path.name])
    return out


def stage_weather() -> Path:
    """Flatten the yearly history files and the daily files into one CSV."""
    out = STAGING_DIR / "weather.csv"
    files = sorted((RAW_DIR / "weather_history").glob("*.json")) + \
            sorted((RAW_DIR / "weather").glob("*.json"))
    with out.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_utc", "temperature_c", "source_file"])
        for path in files:
            hourly = json.loads(path.read_text()).get("hourly", {})
            for t, temp in zip(hourly.get("time", []),
                               hourly.get("temperature_2m", [])):
                # "2025-01-01T05:00" -> "2025-01-01 05:00:00", a format any SQL reads
                timestamp = t.replace("T", " ") + (":00" if len(t) == 16 else "")
                writer.writerow([timestamp, "" if temp is None else temp, path.name])
    return out


# ---- Step 2: SQL models ----------------------------------------------------

SQL_MODELS = """
-- raw layer: exactly what the files contain
CREATE OR REPLACE TABLE raw_demand AS
SELECT * FROM read_csv('{demand_csv}', header = true,
    columns = {{'date': 'DATE', 'hour_ending': 'INTEGER',
               'market_demand_mw': 'INTEGER', 'ontario_demand_mw': 'INTEGER',
               'source_file': 'VARCHAR'}});

CREATE OR REPLACE TABLE raw_weather AS
SELECT * FROM read_csv('{weather_csv}', header = true,
    columns = {{'time_utc': 'TIMESTAMP', 'temperature_c': 'DOUBLE',
               'source_file': 'VARCHAR'}});

-- staging: IESO "hour ending 1" = 00:00-01:00 Eastern Standard Time
-- (no daylight saving) = 05:00-06:00 UTC, so hour start in UTC = date + (hour + 4)
CREATE OR REPLACE TABLE stg_demand AS
SELECT
    date                                              AS date_est,
    hour_ending,
    CAST(date AS TIMESTAMP) + to_hours(hour_ending + 4) AS hour_start_utc,
    ontario_demand_mw,
    market_demand_mw
FROM raw_demand
WHERE hour_ending BETWEEN 1 AND 24
QUALIFY row_number() OVER (
    PARTITION BY date, hour_ending ORDER BY source_file DESC) = 1;

CREATE OR REPLACE TABLE stg_weather AS
SELECT time_utc, temperature_c
FROM raw_weather
WHERE temperature_c IS NOT NULL
QUALIFY row_number() OVER (PARTITION BY time_utc ORDER BY source_file) = 1;

-- fact table: one row per hour, demand + temperature
CREATE OR REPLACE TABLE fct_hourly AS
SELECT
    d.hour_start_utc,
    d.date_est,
    d.hour_ending,
    dayname(d.date_est)              AS day_of_week,
    month(d.date_est)                AS month,
    d.ontario_demand_mw,
    d.market_demand_mw,
    w.temperature_c
FROM stg_demand d
LEFT JOIN stg_weather w ON w.time_utc = d.hour_start_utc;
"""

QUALITY_CHECKS = {
    "Raw demand rows":
        "SELECT count(*) FROM raw_demand",
    "Duplicate hours removed":
        "SELECT (SELECT count(*) FROM raw_demand) - (SELECT count(*) FROM stg_demand)",
    "Days without 24 hours":
        "SELECT count(*) FROM (SELECT date_est FROM stg_demand "
        "GROUP BY 1 HAVING count(*) <> 24)",
    "Hours with no temperature":
        "SELECT count(*) FROM fct_hourly WHERE temperature_c IS NULL",
    "Hours in fct_hourly":
        "SELECT count(*) FROM fct_hourly",
}

FIRST_QUESTION = """
SELECT
    CAST(floor(temperature_c / 5) * 5 AS INTEGER)     AS temp_from_c,
    CAST(round(avg(ontario_demand_mw)) AS INTEGER)    AS avg_demand_mw,
    count(*)                                          AS hours
FROM fct_hourly
WHERE temperature_c IS NOT NULL
GROUP BY 1
ORDER BY 1
"""


def main() -> None:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    demand_csv = stage_demand().as_posix()
    weather_csv = stage_weather().as_posix()

    con = duckdb.connect(str(DB_PATH))
    con.execute(SQL_MODELS.format(demand_csv=demand_csv, weather_csv=weather_csv))

    print("Data quality")
    for name, sql in QUALITY_CHECKS.items():
        print(f"  {name:<28}{con.execute(sql).fetchone()[0]:>8,}")

    print("\nAverage Ontario demand by temperature (5 degree bands)")
    print(f"  {'Temp (C)':<12}{'Avg MW':>8}{'Hours':>8}")
    for temp, mw, hours in con.execute(FIRST_QUESTION).fetchall():
        print(f"  {temp:>3} to {temp + 5:<4}  {mw:>8,}{hours:>8,}")

    con.close()
    print(f"\nDatabase saved to {DB_PATH}")


if __name__ == "__main__":
    main()
