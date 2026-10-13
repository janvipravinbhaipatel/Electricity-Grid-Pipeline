"""
Step 1 ingestion (Ontario, Canada): pull hourly electricity demand from the
IESO public reports site and hourly weather for Toronto, and save the raw
responses untouched. No API key is needed for either source.

Usage:
    python ingest.py              # latest complete day in the IESO file
    python ingest.py 2026-10-09   # a specific date
"""

import csv
import io
import json
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

import requests

# ---- Settings you can change -------------------------------------------

LATITUDE = 43.65          # Toronto, used for the weather pull
LONGITUDE = -79.38

# One file per year, refreshed by IESO every morning with the previous day.
IESO_URL = "https://reports-public.ieso.ca/public/Demand/PUB_Demand_{year}.csv"
WEATHER_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
WEATHER_RECENT_URL = "https://api.open-meteo.com/v1/forecast"

RAW_DIR = Path("data/raw")

# -------------------------------------------------------------------------


def fetch_demand_file(year: int) -> str:
    """Download the whole hourly demand file for one year, as text."""
    response = requests.get(IESO_URL.format(year=year), timeout=60)
    response.raise_for_status()                 # stop loudly on HTTP errors
    return response.text


def hours_per_day(demand_text: str) -> Counter:
    """Count how many hourly rows each date has.

    The file starts with comment lines that begin with a backslash, then a
    header: Date,Hour,Market Demand,Ontario Demand. Hours run 1 to 24.
    """
    data_lines = [line for line in demand_text.splitlines()
                  if line and not line.startswith("\\")]
    reader = csv.DictReader(io.StringIO("\n".join(data_lines)))
    return Counter(row["Date"] for row in reader)


def fetch_weather(day: date) -> dict:
    """Hourly temperature for one UTC day from Open-Meteo."""
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "temperature_2m",
        "start_date": str(day),
        "end_date": str(day),
        "timezone": "UTC",
    }
    # The archive lags a few days, so recent dates use the forecast endpoint.
    today = datetime.now(timezone.utc).date()
    url = WEATHER_RECENT_URL if (today - day).days <= 7 else WEATHER_ARCHIVE_URL
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def main() -> None:
    requested = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None
    year = requested.year if requested else datetime.now(timezone.utc).year

    # --- Demand: save the raw file exactly as IESO published it ----------
    demand_text = fetch_demand_file(year)
    demand_dir = RAW_DIR / "demand"
    demand_dir.mkdir(parents=True, exist_ok=True)
    demand_path = demand_dir / f"PUB_Demand_{year}.csv"
    demand_path.write_text(demand_text)         # same name, so reruns overwrite

    counts = hours_per_day(demand_text)
    complete_days = sorted(d for d, n in counts.items() if n == 24)
    if not complete_days:
        sys.exit("No complete days found in the demand file. Open it and check.")

    day = requested or date.fromisoformat(complete_days[-1])
    demand_rows = counts.get(str(day), 0)
    print(f"Demand:  {len(counts)} days in file -> {demand_path}")
    print(f"         {day} has {demand_rows} hourly records")

    # --- Weather: one JSON file per day -----------------------------------
    weather = fetch_weather(day)
    weather_rows = len(weather.get("hourly", {}).get("time", []))
    weather_dir = RAW_DIR / "weather"
    weather_dir.mkdir(parents=True, exist_ok=True)
    weather_path = weather_dir / f"{day}.json"
    weather_path.write_text(json.dumps(weather, indent=2))
    print(f"Weather: {weather_rows} hourly records -> {weather_path}")

    if demand_rows != 24 or weather_rows != 24:
        print("Warning: expected 24 records from each source. Check the files.")

    # Note for Week 2: IESO hours are "hour ending" in Eastern Standard Time
    # all year (no daylight saving), while the weather is in UTC. Lining the
    # two up is a transform step, not an ingestion step.


if __name__ == "__main__":
    main()
