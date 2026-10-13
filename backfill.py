"""
Backfill: download full years of history in one go.

ingest.py fetches one day at a time, which is right for daily runs.
For history, this script pulls whole years instead:
  - Ontario demand: one IESO file per year (same file ingest.py uses)
  - Toronto weather: one Open-Meteo archive request per year

Usage:
    python backfill.py              # 2024, 2025 and 2026 so far
    python backfill.py 2023 2024    # specific years
"""

import json
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

from ingest import LATITUDE, LONGITUDE, RAW_DIR, fetch_demand_file, hours_per_day

WEATHER_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
ARCHIVE_LAG_DAYS = 6          # the weather archive runs a few days behind today


def backfill_demand(year: int) -> None:
    text = fetch_demand_file(year)
    folder = RAW_DIR / "demand"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"PUB_Demand_{year}.csv"
    path.write_text(text)                       # same name, so reruns overwrite

    counts = hours_per_day(text)
    incomplete = sorted(d for d, n in counts.items() if n != 24)
    print(f"Demand  {year}: {len(counts)} days -> {path}")
    if incomplete:
        print(f"  Warning: {len(incomplete)} days without 24 hours, "
              f"e.g. {incomplete[:3]}")


def backfill_weather(year: int) -> None:
    start = date(year, 1, 1)
    last_available = datetime.now(timezone.utc).date() - timedelta(days=ARCHIVE_LAG_DAYS)
    end = min(date(year, 12, 31), last_available)
    if end < start:
        print(f"Weather {year}: nothing in the archive yet, skipped")
        return

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "temperature_2m",
        "start_date": str(start),
        "end_date": str(end),
        "timezone": "UTC",
    }
    response = requests.get(WEATHER_ARCHIVE_URL, params=params, timeout=120)
    response.raise_for_status()
    payload = response.json()

    folder = RAW_DIR / "weather_history"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{year}.json"
    path.write_text(json.dumps(payload))

    hours = len(payload.get("hourly", {}).get("time", []))
    expected = ((end - start).days + 1) * 24
    print(f"Weather {year}: {hours} hours ({start} to {end}) -> {path}")
    if hours != expected:
        print(f"  Warning: expected {expected} hours")


def main() -> None:
    this_year = datetime.now(timezone.utc).year
    years = [int(y) for y in sys.argv[1:]] or [this_year - 2, this_year - 1, this_year]

    for year in years:
        backfill_demand(year)
        backfill_weather(year)
        time.sleep(1)                           # be polite to free services

    print("Done.")


if __name__ == "__main__":
    main()
