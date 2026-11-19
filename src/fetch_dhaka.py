"""Retrieve the daily weather record for Dhaka, Bangladesh.

Source
    Open-Meteo Historical Weather API, which serves ERA5 / ERA5-Land
    reanalysis. Daily values are available from 1940 to roughly five days
    before today. The remaining few days are patched from Open-Meteo's
    forecast endpoint using its `past_days` window, so the series always
    runs up to yesterday.

Both endpoints are free for non-commercial use and need no API key.

The script is incremental. On a first run it pulls the full record. On
later runs it refetches only a trailing window and merges, because ERA5
values for recent days are revised as the reanalysis settles.

Output
    data/dhaka_daily.csv with one row per calendar day.
"""

from __future__ import annotations

import argparse
import io
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

# Dhaka, Bangladesh
LATITUDE = 23.8103
LONGITUDE = 90.4125
TIMEZONE = "Asia/Dhaka"
LOCATION_NAME = "Dhaka"

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

RECORD_START = date(1940, 1, 1)
DAILY_VARS = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"]

COLUMN_MAP = {
    "time": "date",
    "temperature_2m_max": "tmax_c",
    "temperature_2m_min": "tmin_c",
    "precipitation_sum": "prcp_mm",
}

# Trailing days refetched on every incremental run
REFRESH_WINDOW_DAYS = 45
# Chunk size for the first full pull, keeps each request modest
CHUNK_YEARS = 20


def _get_json(url: str, params: dict, attempts: int = 5) -> dict:
    """GET with a simple exponential backoff, since the API rate limits."""
    delay = 2.0
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, params=params, timeout=180)
            if response.status_code == 200:
                return response.json()
            if response.status_code in (429, 500, 502, 503, 504):
                last_error = f"HTTP {response.status_code}"
            else:
                response.raise_for_status()
        except requests.RequestException as exc:
            last_error = str(exc)
        if attempt < attempts:
            print(f"    retry {attempt} after {last_error}", file=sys.stderr)
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"request to {url} failed after {attempts} attempts, {last_error}")


def _daily_frame(payload: dict) -> pd.DataFrame:
    daily = payload.get("daily")
    if not daily:
        return pd.DataFrame(columns=list(COLUMN_MAP.values()))
    frame = pd.DataFrame(daily).rename(columns=COLUMN_MAP)
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    keep = [c for c in COLUMN_MAP.values() if c in frame.columns]
    return frame[keep]


def fetch_archive(start: date, end: date) -> pd.DataFrame:
    """Pull ERA5 daily values between two dates, in multi-year chunks."""
    if start > end:
        return pd.DataFrame(columns=list(COLUMN_MAP.values()))

    pieces = []
    cursor = start
    while cursor <= end:
        chunk_end = min(date(cursor.year + CHUNK_YEARS, 1, 1) - timedelta(days=1), end)
        print(f"  archive {cursor} to {chunk_end}")
        payload = _get_json(ARCHIVE_URL, {
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "start_date": cursor.isoformat(),
            "end_date": chunk_end.isoformat(),
            "daily": ",".join(DAILY_VARS),
            "timezone": TIMEZONE,
        })
        pieces.append(_daily_frame(payload))
        cursor = chunk_end + timedelta(days=1)

    return pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame()


def fetch_recent(past_days: int = 14) -> pd.DataFrame:
    """Patch the ERA5 lag with the forecast endpoint's recent-past window."""
    print(f"  recent window, past {past_days} days")
    payload = _get_json(FORECAST_URL, {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "daily": ",".join(DAILY_VARS),
        "past_days": past_days,
        "forecast_days": 1,
        "timezone": TIMEZONE,
    })
    return _daily_frame(payload)


def add_calendar_columns(frame: pd.DataFrame) -> pd.DataFrame:
    stamps = pd.to_datetime(frame["date"])
    frame = frame.copy()
    frame["year"] = stamps.dt.year
    frame["month"] = stamps.dt.month
    frame["day"] = stamps.dt.day
    frame["day_of_year"] = stamps.dt.dayofyear
    ordered = ["date", "year", "month", "day", "day_of_year", "tmax_c", "tmin_c", "prcp_mm"]
    return frame[[c for c in ordered if c in frame.columns]]


def merge(existing: pd.DataFrame, fresh: pd.DataFrame) -> pd.DataFrame:
    """Combine, letting freshly fetched rows win on any shared date."""
    if existing.empty:
        combined = fresh
    else:
        combined = pd.concat([existing, fresh], ignore_index=True)
        combined = combined.drop_duplicates(subset="date", keep="last")
    combined = combined.sort_values("date").reset_index(drop=True)
    return combined


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch daily weather data for Dhaka.")
    parser.add_argument("--out", default="data/dhaka_daily.csv", help="output CSV path")
    parser.add_argument("--full", action="store_true",
                        help="ignore any cached file and refetch the whole record")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    yesterday = date.today() - timedelta(days=1)

    existing = pd.DataFrame()
    if out_path.exists() and not args.full:
        existing = pd.read_csv(out_path, parse_dates=["date"])
        existing["date"] = existing["date"].dt.date

    if existing.empty:
        print(f"Full pull for {LOCATION_NAME}, {RECORD_START} to {yesterday}")
        archive_start = RECORD_START
    else:
        last_seen = max(existing["date"])
        archive_start = last_seen - timedelta(days=REFRESH_WINDOW_DAYS)
        print(f"Incremental pull for {LOCATION_NAME}, from {archive_start}")

    fresh = fetch_archive(archive_start, yesterday)
    recent = fetch_recent(past_days=14)

    combined = merge(existing, fresh)
    combined = merge(combined, recent)

    # Drop any trailing rows that came back without a temperature reading
    combined = combined[combined["tmax_c"].notna() | combined["prcp_mm"].notna()]

    combined = add_calendar_columns(combined)
    combined.to_csv(out_path, index=False)

    span_start = combined["date"].min()
    span_end = combined["date"].max()
    print(f"Wrote {len(combined):,} rows to {out_path} covering {span_start} to {span_end}")


if __name__ == "__main__":
    main()
