"""
Backfill: download full years of history.

  - Ontario demand: one IESO file per year
  - Toronto weather: Open-Meteo archive, fetched ONE MONTH AT A TIME with
    automatic retries, so one slow response can't fail the whole run

Usage:
    python backfill.py              # last 2 years + this year
    python backfill.py 2023 2024    # specific years
"""

import calendar
import json
import sys
import time
from datetime import date, datetime, timedelta, timezone

import requests

from ingest import IESO_URL, LATITUDE, LONGITUDE, RAW_DIR, hours_per_day

WEATHER_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
ARCHIVE_LAG_DAYS = 6       # the weather archive runs a few days behind today
ATTEMPTS = 5               # tries per request before giving up
TIMEOUT = 60               # seconds to wait for each response


def get_with_retries(url: str, params: dict | None = None) -> requests.Response:
    """GET a URL, retrying on timeouts, connection errors, rate limits and 5xx."""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            response = requests.get(url, params=params, timeout=TIMEOUT)
            if response.status_code == 429 or response.status_code >= 500:
                raise requests.HTTPError(f"HTTP {response.status_code}")
            response.raise_for_status()      # other 4xx errors: fail at once
            return response
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as error:
            is_client_error = (isinstance(error, requests.HTTPError)
                               and error.response is not None
                               and 400 <= error.response.status_code < 500
                               and error.response.status_code != 429)
            if is_client_error or attempt == ATTEMPTS:
                raise
            wait = 10 * attempt
            print(f"  Attempt {attempt} failed ({error}). Retrying in {wait}s...")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def backfill_demand(year: int) -> None:
    text = get_with_retries(IESO_URL.format(year=year)).text
    folder = RAW_DIR / "demand"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"PUB_Demand_{year}.csv"
    path.write_text(text)                    # same name, so reruns overwrite

    counts = hours_per_day(text)
    incomplete = sorted(d for d, n in counts.items() if n != 24)
    print(f"Demand  {year}: {len(counts)} days -> {path}")
    if incomplete:
        print(f"  Warning: {len(incomplete)} days without 24 hours, e.g. {incomplete[:3]}")


def backfill_weather(year: int) -> None:
    last_available = datetime.now(timezone.utc).date() - timedelta(days=ARCHIVE_LAG_DAYS)
    year_end = min(date(year, 12, 31), last_available)
    folder = RAW_DIR / "weather_history"
    path = folder / f"{year}.json"
    times: list[str] = []
    temps: list[float | None] = []
    first_month = 1

    # Reuse what was downloaded before (restored from the cache on GitHub Actions)
    if path.exists():
        saved = json.loads(path.read_text()).get("hourly", {})
        old_times = saved.get("time", [])
        old_temps = saved.get("temperature_2m", [])
        if old_times and old_times[-1][:10] >= str(year_end):
            print(f"Weather {year}: already complete ({len(old_times)} hours), skipped")
            return
        if old_times:
            # Keep whole months already saved; re-fetch from the last saved month on
            first_month = int(old_times[-1][5:7])
            for t, v in zip(old_times, old_temps):
                if int(t[5:7]) < first_month:
                    times.append(t)
                    temps.append(v)

    for month in range(first_month, 13):
        start = date(year, month, 1)
        end = min(date(year, month, calendar.monthrange(year, month)[1]), last_available)
        if end < start:
            break                            # this month isn't in the archive yet

        params = {
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "hourly": "temperature_2m",
            "start_date": str(start),
            "end_date": str(end),
            "timezone": "UTC",
        }
        hourly = get_with_retries(WEATHER_ARCHIVE_URL, params).json().get("hourly", {})
        times += hourly.get("time", [])
        temps += hourly.get("temperature_2m", [])
        time.sleep(1)                        # be polite to a free service

    if not times:
        print(f"Weather {year}: nothing in the archive yet, skipped")
        return

    folder.mkdir(parents=True, exist_ok=True)
    # Same structure as a single Open-Meteo response, so load.py needs no change
    path.write_text(json.dumps({"hourly": {"time": times, "temperature_2m": temps}}))
    print(f"Weather {year}: {len(times)} hours ({times[0][:10]} to {times[-1][:10]}) -> {path}")


def main() -> None:
    this_year = datetime.now(timezone.utc).year
    years = [int(y) for y in sys.argv[1:]] or [this_year - 2, this_year - 1, this_year]

    for year in years:
        backfill_demand(year)
        backfill_weather(year)

    print("Done.")


if __name__ == "__main__":
    main()