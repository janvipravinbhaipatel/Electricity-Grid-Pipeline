"""
Exports the final table to a small Parquet file the dashboard can read.

Usage:
    python export.py
"""

from pathlib import Path

import duckdb

DB_PATH = "data/warehouse.duckdb"
OUT = Path("dashboard/fct_hourly.parquet")


def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    con = duckdb.connect(DB_PATH, read_only=True)
    con.execute(f"""
        COPY (SELECT * FROM analytics.fct_hourly ORDER BY hour_start_utc)
        TO '{OUT.as_posix()}' (FORMAT parquet)
    """)
    rows = con.execute(f"SELECT count(*) FROM '{OUT.as_posix()}'").fetchone()[0]
    con.close()
    print(f"Exported {rows:,} rows to {OUT}")


if __name__ == "__main__":
    main()