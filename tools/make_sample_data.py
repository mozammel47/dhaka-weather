"""Generate a synthetic Dhaka-like daily series for offline testing.

This exists so the plotting code can be exercised on a machine with no
outbound network access. It is NOT real weather data. Use
`src/fetch_dhaka.py` for the real record.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd


def make(start_year: int, end: date, seed: int = 11) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range(f"{start_year}-01-01", end, freq="D")
    doy = dates.dayofyear.to_numpy()
    year = dates.year.to_numpy()
    warming = (year - start_year) * 0.018

    # Two seasonal humps, a pre-monsoon April peak and a monsoon plateau
    pre_monsoon = 5.2 * np.exp(-0.5 * ((doy - 108) / 26.0) ** 2)
    monsoon_damp = 1.9 * np.exp(-0.5 * ((doy - 210) / 42.0) ** 2)
    tmax = 29.0 - 4.2 * np.cos(2 * np.pi * (doy - 15) / 365.25) + pre_monsoon - monsoon_damp
    tmax = tmax + warming + rng.normal(0, 1.5, len(dates))
    tmax = tmax + pd.Series(rng.normal(0, 0.9, len(dates))).rolling(5, min_periods=1).mean().to_numpy()

    tmin = tmax - (11.5 - 5.0 * np.exp(-0.5 * ((doy - 200) / 55.0) ** 2))
    tmin = tmin + rng.normal(0, 1.0, len(dates))

    # Monsoon dominated rainfall, dry winter
    wet_season = np.exp(-0.5 * ((doy - 196) / 48.0) ** 2)
    rain_odds = 0.04 + 0.66 * wet_season
    rains = rng.random(len(dates)) < rain_odds
    amount = rng.gamma(shape=0.85, scale=16.0 + 20.0 * wet_season)
    prcp = np.where(rains, amount, 0.0)

    frame = pd.DataFrame({
        "date": dates.date,
        "year": year,
        "month": dates.month,
        "day": dates.day,
        "day_of_year": doy,
        "tmax_c": np.round(tmax, 1),
        "tmin_c": np.round(tmin, 1),
        "prcp_mm": np.round(prcp, 1),
    })
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/sample_dhaka_daily.csv")
    parser.add_argument("--start-year", type=int, default=1960)
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    frame = make(args.start_year, date.today())
    frame.to_csv(out, index=False)
    print(f"Wrote {len(frame):,} synthetic rows to {out}")


if __name__ == "__main__":
    main()
