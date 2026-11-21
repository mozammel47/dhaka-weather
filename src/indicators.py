"""Long-run climate indicators for Dhaka, derived from the daily record.

These are the numbers a weather app cannot give you. Each one is a single
value per year, so eighty-odd years fit in one panel and a trend is either
there or it is not.

Every threshold is defined against Dhaka's own 1961 to 1990 baseline rather
than an imported constant. The European "tropical night" threshold of 20 °C,
for instance, is useless here, because almost every Dhaka summer night clears
it. A baseline percentile asks the locally meaningful question, which is how
often today's weather would have counted as unusual within living memory.

Indicators
    hot_nights          nights at or above the baseline 90th percentile of
                        the daily minimum temperature
    heat_days           days at or above the baseline 90th percentile of the
                        daily maximum apparent temperature, so humidity counts
    monsoon             onset date, withdrawal date and season length
    concentration       share of the year's rain falling on its 10 wettest days

Caveat on the monsoon. There is no single agreed definition of onset, and the
Bangladesh Meteorological Department, the India Meteorological Department and
the research literature all use different criteria. The rule applied here is
stated explicitly in the constants below and in the README. Treat the dates as
one defensible definition, not as official declarations.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

BASELINE_START = 1961
BASELINE_END = 1990
BASELINE_QUANTILE = 0.90

# A year needs this many daily records before it is treated as complete
MIN_YEAR_DAYS = 360

# Monsoon onset. The first day from 1 May onward that is wet enough over the
# following week, and is followed by a sustained wet spell rather than an
# isolated pre-monsoon thunderstorm.
ONSET_EARLIEST = (5, 1)
ONSET_LATEST = (9, 30)
ONSET_WINDOW_DAYS = 7
ONSET_WINDOW_MM = 40.0
ONSET_SUSTAIN_DAYS = 20
ONSET_SUSTAIN_MM = 100.0

# Monsoon withdrawal. The first day from 1 September onward whose following
# fortnight is dry. Withdrawal is taken as the day before that dry spell.
WITHDRAWAL_EARLIEST = (9, 1)
WITHDRAWAL_LATEST = (12, 15)
WITHDRAWAL_WINDOW_DAYS = 14
WITHDRAWAL_WINDOW_MM = 20.0

TOP_RAIN_DAYS = 10


def load(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["date"]).sort_values("date")
    frame["year"] = frame["date"].dt.year
    frame["day_of_year"] = frame["date"].dt.dayofyear
    return frame.reset_index(drop=True)


def year_lengths(frame: pd.DataFrame) -> pd.Series:
    return frame.groupby("year").size()


def baseline_years(frame: pd.DataFrame) -> list[int]:
    """Complete years making up the reference period.

    Falls back to the first thirty complete years on record when the data do
    not reach back far enough to cover 1961 to 1990.
    """
    lengths = year_lengths(frame)
    complete = lengths[lengths >= MIN_YEAR_DAYS].index.tolist()
    window = [y for y in complete if BASELINE_START <= y <= BASELINE_END]
    if len(window) < 20:
        window = complete[:30]
    if not window:
        raise SystemExit("Not enough complete years to define a baseline.")
    return window


def recent_years(frame: pd.DataFrame, span: int = 30) -> list[int]:
    """The most recent complete years, for comparison against the baseline."""
    lengths = year_lengths(frame)
    complete = lengths[lengths >= MIN_YEAR_DAYS].index.tolist()
    return complete[-span:]


def baseline_threshold(frame: pd.DataFrame, column: str) -> tuple[float, int, int]:
    """Percentile of a column over the baseline period."""
    window = baseline_years(frame)
    values = frame.loc[frame["year"].isin(window), column].dropna()
    return float(values.quantile(BASELINE_QUANTILE)), min(window), max(window)


def count_through(frame: pd.DataFrame, column: str, threshold: float,
                  through_doy: int, years: list[int]) -> float:
    """Mean count, across the given years, of qualifying days up to a date.

    This is what makes a part-year number comparable. Counting the whole of
    1975 against eleven months of this year would flatter the past.
    """
    subset = frame[frame["year"].isin(years) & (frame["day_of_year"] <= through_doy)]
    if subset.empty:
        return float("nan")
    per_year = (subset[column] >= threshold).groupby(subset["year"]).sum()
    return float(per_year.mean())


def rain_through(frame: pd.DataFrame, through_doy: int, years: list[int]) -> float:
    """Mean rainfall total, across the given years, up to a date."""
    subset = frame[frame["year"].isin(years) & (frame["day_of_year"] <= through_doy)]
    if subset.empty:
        return float("nan")
    return float(subset.groupby("year")["prcp_mm"].sum().mean())


def annual_day_counts(frame: pd.DataFrame, column: str, threshold: float) -> pd.Series:
    hits = frame[column] >= threshold
    return hits.groupby(frame["year"]).sum().astype(float)


def forward_sum(series: pd.Series, window: int, min_periods: int | None = None) -> pd.Series:
    """Total over the current day and the next window minus one days."""
    reversed_series = series.iloc[::-1]
    rolled = reversed_series.rolling(window, min_periods=min_periods or window).sum()
    return rolled.iloc[::-1]


def monsoon_table(frame: pd.DataFrame) -> pd.DataFrame:
    rain = frame.set_index("date")["prcp_mm"]
    onset_window = forward_sum(rain, ONSET_WINDOW_DAYS)
    onset_sustain = forward_sum(rain, ONSET_SUSTAIN_DAYS, min_periods=ONSET_SUSTAIN_DAYS - 4)
    dry_window = forward_sum(rain, WITHDRAWAL_WINDOW_DAYS,
                             min_periods=WITHDRAWAL_WINDOW_DAYS - 4)

    rows = []
    for year, group in frame.groupby("year"):
        dates = group["date"]
        onset_from = pd.Timestamp(year=year, month=ONSET_EARLIEST[0], day=ONSET_EARLIEST[1])
        onset_to = pd.Timestamp(year=year, month=ONSET_LATEST[0], day=ONSET_LATEST[1])
        window = dates[(dates >= onset_from) & (dates <= onset_to)]

        onset = pd.NaT
        for stamp in window:
            if (onset_window.get(stamp, np.nan) >= ONSET_WINDOW_MM
                    and onset_sustain.get(stamp, np.nan) >= ONSET_SUSTAIN_MM):
                onset = stamp
                break

        withdrawal = pd.NaT
        if pd.notna(onset):
            dry_from = max(onset + pd.Timedelta(days=ONSET_SUSTAIN_DAYS),
                           pd.Timestamp(year=year, month=WITHDRAWAL_EARLIEST[0],
                                        day=WITHDRAWAL_EARLIEST[1]))
            dry_to = pd.Timestamp(year=year, month=WITHDRAWAL_LATEST[0],
                                  day=WITHDRAWAL_LATEST[1])
            tail = dates[(dates >= dry_from) & (dates <= dry_to)]
            for stamp in tail:
                value = dry_window.get(stamp, np.nan)
                if pd.notna(value) and value < WITHDRAWAL_WINDOW_MM:
                    withdrawal = stamp - pd.Timedelta(days=1)
                    break

        rows.append({
            "year": year,
            "onset_doy": onset.dayofyear if pd.notna(onset) else np.nan,
            "withdrawal_doy": withdrawal.dayofyear if pd.notna(withdrawal) else np.nan,
            "monsoon_days": ((withdrawal - onset).days
                             if pd.notna(onset) and pd.notna(withdrawal) else np.nan),
        })

    return pd.DataFrame(rows).set_index("year")


def concentration(frame: pd.DataFrame, top_n: int = TOP_RAIN_DAYS) -> pd.Series:
    """Share of each year's rainfall that fell on its wettest days."""
    def share(values: pd.Series) -> float:
        total = values.sum()
        if total <= 0:
            return np.nan
        return float(values.nlargest(top_n).sum() / total * 100.0)

    return frame.groupby("year")["prcp_mm"].apply(share)


def build(path: Path) -> tuple[pd.DataFrame, dict]:
    frame = load(path)

    tmin_threshold, base_lo, base_hi = baseline_threshold(frame, "tmin_c")
    app_threshold, _, _ = baseline_threshold(frame, "app_tmax_c")

    table = pd.DataFrame({
        "days_recorded": year_lengths(frame),
        "hot_nights": annual_day_counts(frame, "tmin_c", tmin_threshold),
        "heat_days": annual_day_counts(frame, "app_tmax_c", app_threshold),
        "rain_total_mm": frame.groupby("year")["prcp_mm"].sum(),
        "rain_concentration_pct": concentration(frame),
    })
    table = table.join(monsoon_table(frame))
    table["complete_year"] = table["days_recorded"] >= MIN_YEAR_DAYS

    meta = {
        "tmin_threshold": tmin_threshold,
        "app_threshold": app_threshold,
        "baseline_start": base_lo,
        "baseline_end": base_hi,
        "baseline_quantile": BASELINE_QUANTILE,
        "baseline_years": baseline_years(frame),
        "recent_years": recent_years(frame),
        "last_date": frame["date"].max(),
        "current_year": int(frame["year"].max()),
    }
    return table, meta


def headline(table: pd.DataFrame, meta: dict) -> str:
    """One sentence of plain arithmetic, for the top of the README."""
    complete = table[table["complete_year"]]
    if complete.empty:
        return "Not enough complete years yet for a headline comparison."

    early = complete.head(10)
    late = complete.tail(10)
    return (
        f"Dhaka averaged {late['hot_nights'].mean():.0f} hot nights a year over the "
        f"last ten complete years, against {early['hot_nights'].mean():.0f} a year in "
        f"{int(early.index.min())} to {int(early.index.max())}. A hot night here means "
        f"a minimum at or above {meta['tmin_threshold']:.1f} °C, the warmest ten "
        f"per cent of nights in {meta['baseline_start']} to {meta['baseline_end']}."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute Dhaka climate indicators.")
    parser.add_argument("--data", default="data/dhaka_daily.csv")
    parser.add_argument("--out", default="data/indicators.csv")
    args = parser.parse_args()

    table, meta = build(Path(args.data))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out_path)

    print(f"Baseline {meta['baseline_start']} to {meta['baseline_end']}, "
          f"{meta['baseline_quantile']:.0%} percentile")
    print(f"  hot night at or above {meta['tmin_threshold']:.1f} C")
    print(f"  heat day at or above {meta['app_threshold']:.1f} C apparent")
    print(f"Wrote {len(table)} years to {out_path}")
    print()
    print(headline(table, meta))


if __name__ == "__main__":
    main()
