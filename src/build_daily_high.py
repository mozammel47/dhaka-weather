"""Tufte-style daily high temperature graph for Dhaka.

Nested ribbons show the historical distribution of the daily maximum
temperature for every calendar day. A black line traces the current year
against that backdrop, and dots mark days that broke the all-time record
for that calendar day.

Inspired by Edward Tufte's annual weather graphic and by the Milwaukee
version at github.com/jdjohn215/milwaukee-weather.
"""

from __future__ import annotations

import argparse
import calendar
from datetime import date, datetime
from pathlib import Path

import matplotlib.dates as mdates
import numpy as np
import pandas as pd

import style

VALUE = "tmax_c"
TITLE = "Daily High Temperature in Dhaka"
OUT_DEFAULT = "graphs/DailyHighTemp_Dhaka.png"


def load(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["date"])
    frame = frame[frame[VALUE].notna()].copy()
    frame["year"] = frame["date"].dt.year
    frame["month"] = frame["date"].dt.month
    frame["day"] = frame["date"].dt.day
    return frame


BAND_COLUMNS = ["lo", "p5", "p20", "p40", "p60", "p80", "p95", "hi"]


def smooth_bands(stats: pd.DataFrame, window: int) -> pd.DataFrame:
    """Circular rolling mean over the percentile columns.

    Day-of-year percentiles are inherently ragged, since each calendar day
    is estimated from only as many values as there are years on record.
    A short centred window keeps the seasonal shape and removes sampling
    noise. Set window to 1 to leave the raw percentiles untouched.
    """
    if window <= 1:
        return stats
    out = stats.copy()
    pad = window
    for column in BAND_COLUMNS:
        series = out[column].to_numpy(dtype=float)
        wrapped = np.concatenate([series[-pad:], series, series[:pad]])
        smoothed = pd.Series(wrapped).rolling(window, center=True, min_periods=1).mean()
        out[column] = smoothed.to_numpy()[pad:pad + len(series)]
    # Keep the nesting intact after smoothing
    out["lo"] = np.minimum(out["lo"], out["p5"])
    out["hi"] = np.maximum(out["hi"], out["p95"])
    return out


def daily_distribution(history: pd.DataFrame, plot_year: int) -> pd.DataFrame:
    """Percentiles of the historical record for each calendar day."""
    grouped = history.groupby(["month", "day"])[VALUE]
    stats = grouped.agg(
        lo="min",
        hi="max",
        p5=lambda s: np.nanpercentile(s, 5),
        p20=lambda s: np.nanpercentile(s, 20),
        p40=lambda s: np.nanpercentile(s, 40),
        p60=lambda s: np.nanpercentile(s, 60),
        p80=lambda s: np.nanpercentile(s, 80),
        p95=lambda s: np.nanpercentile(s, 95),
        n="count",
    ).reset_index()

    # Drop February 29th unless the plotted year actually has one
    if not calendar.isleap(plot_year):
        stats = stats[~((stats["month"] == 2) & (stats["day"] == 29))]

    stats["date"] = pd.to_datetime(dict(
        year=plot_year, month=stats["month"], day=stats["day"]
    ))
    return stats.sort_values("date").reset_index(drop=True)


def records_this_year(current: pd.DataFrame, stats: pd.DataFrame) -> pd.DataFrame:
    """Days where the current year beat the historical high or low."""
    merged = current.merge(stats[["month", "day", "lo", "hi"]], on=["month", "day"], how="inner")
    merged["kind"] = np.where(
        merged[VALUE] > merged["hi"], "high",
        np.where(merged[VALUE] < merged["lo"], "low", "none"),
    )
    return merged[merged["kind"] != "none"]


def draw_key(fig, rect, stats: pd.DataFrame) -> None:
    """A vertical cross-section of the ribbon, used as the chart key."""
    axis = fig.add_axes(rect)
    axis.set_facecolor(style.PAPER)
    for spine in axis.spines.values():
        spine.set_visible(False)
    axis.set_xticks([])
    axis.set_yticks([])
    axis.set_xlim(0, 1)
    axis.set_ylim(-0.08, 1.02)

    levels = {"lo": 0.00, "p5": 0.17, "p20": 0.33, "p40": 0.46,
              "p60": 0.54, "p80": 0.67, "p95": 0.83, "hi": 1.00}
    span = [0, 1]
    pairs = [
        ("lo", "hi", style.BAND_OUTER),
        ("p5", "p95", style.BAND_MID),
        ("p20", "p80", style.BAND_INNER),
        ("p40", "p60", style.BAND_CORE),
    ]
    for low, high, colour in pairs:
        axis.fill_between(span, levels[low], levels[high], color=colour, lw=0)

    labels = [
        ("hi", "record high"),
        ("p95", "95th"),
        ("p80", "80th"),
        ("p60", "60th"),
        ("p40", "40th"),
        ("p20", "20th"),
        ("p5", "5th"),
        ("lo", "record low"),
    ]
    for key, text in labels:
        y = levels[key]
        axis.annotate(
            text, xy=(1.0, y), xytext=(1.55, y),
            fontsize=6.4, va="center", ha="left", color="#333333",
            annotation_clip=False,
            arrowprops=dict(arrowstyle="-", lw=0.4, color="#999999",
                            shrinkA=0, shrinkB=0),
        )
    axis.text(0.0, 1.075, "spread of\npast years",
              fontsize=6.2, ha="left", va="bottom", color="#555555", linespacing=1.4)


def build(data_path: Path, out_path: Path, smooth: int = 5) -> Path:
    style.apply_style()

    frame = load(data_path)
    plot_year = int(frame["year"].max())
    last_date = frame["date"].max()

    current = frame[frame["year"] == plot_year].copy()
    history = frame[frame["year"] != plot_year]
    if history.empty:
        raise SystemExit("Need at least one complete prior year of data.")

    raw_stats = daily_distribution(history, plot_year)
    # Records are judged against the true daily extremes, never the smoothed ones
    hits = records_this_year(current, raw_stats)
    stats = smooth_bands(raw_stats, smooth)

    fig = style.figure(width_mm=170.0, height_mm=108.0)
    axis = fig.add_axes([0.068, 0.215, 0.660, 0.520])
    axis.set_facecolor(style.PAPER)

    x = stats["date"].to_numpy()
    bands = [
        ("lo", "hi", style.BAND_OUTER),
        ("p5", "p95", style.BAND_MID),
        ("p20", "p80", style.BAND_INNER),
        ("p40", "p60", style.BAND_CORE),
    ]
    for low, high, colour in bands:
        axis.fill_between(x, stats[low], stats[high], color=colour, lw=0, zorder=2)

    # Y limits and breaks, rounded outward to whole 5 degree steps
    lowest = float(np.nanmin(stats["lo"]))
    highest = float(np.nanmax(stats["hi"]))
    y_lo = 5 * np.floor(min(lowest, float(current[VALUE].min())) / 5)
    y_hi = 5 * np.ceil(max(highest, float(current[VALUE].max())) / 5)
    ticks = np.arange(y_lo, y_hi + 0.1, 5)

    # White reference lines drawn over the ribbons, as in the original
    for level in ticks:
        axis.axhline(level, color="white", lw=0.35, zorder=3)

    axis.plot(current["date"], current[VALUE], color="black", lw=1.0, zorder=5,
              solid_capstyle="round")

    for kind, colour, label in [("high", style.RECORD_HIGH, "record high set this year"),
                                ("low", style.RECORD_LOW, "record low set this year")]:
        subset = hits[hits["kind"] == kind]
        if not subset.empty:
            axis.scatter(subset["date"], subset[VALUE], s=7, color=colour,
                         zorder=6, linewidths=0, label=label)

    axis.set_ylim(y_lo, y_hi)
    axis.set_yticks(ticks)
    axis.set_yticklabels([f"{int(t)}°" for t in ticks], fontsize=8)
    axis.set_xlim(stats["date"].iloc[0], stats["date"].iloc[-1])

    # Dotted guide at the start of each month, labels at mid month
    month_starts = [datetime(plot_year, m, 1) for m in range(1, 13)]
    month_mids = [datetime(plot_year, m, 15) for m in range(1, 13)]
    for start in month_starts:
        axis.axvline(start, color="#999999", lw=0.3, ls=(0, (1, 2)), zorder=4)
    axis.set_xticks(month_mids)
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    axis.tick_params(axis="x", length=0, labelsize=8)
    axis.tick_params(axis="y", length=0)

    mirror = axis.twinx()
    mirror.set_ylim(y_lo, y_hi)
    mirror.set_yticks(ticks)
    mirror.set_yticklabels([f"{int(t)}°" for t in ticks], fontsize=8)
    mirror.tick_params(axis="y", length=0)
    mirror.set_facecolor("none")
    for spine in list(axis.spines.values()) + list(mirror.spines.values()):
        spine.set_visible(False)

    draw_key(fig, [0.790, 0.250, 0.020, 0.430], stats)

    record_start = frame["date"].min()
    n_years = plot_year - int(frame["year"].min())

    fig.text(0.068, 0.955, TITLE, fontsize=13, fontweight="bold", va="top")
    fig.text(
        0.068, 0.885,
        f"The black line is {plot_year}. Ribbons cover the spread of the previous "
        f"{n_years} years.\nLast day shown is {last_date.strftime('%d %B %Y')}.",
        fontsize=8, va="top", color="#333333", linespacing=1.45,
    )

    marks = []
    if (hits["kind"] == "high").any():
        marks.append("red dots mark record highs")
    if (hits["kind"] == "low").any():
        marks.append("blue dots mark record lows")
    marks_text = ", ".join(marks)
    if marks_text:
        marks_text = marks_text[0].upper() + marks_text[1:] + ". "

    band_note = f"Bands smoothed over {smooth} days. " if smooth > 1 else ""
    fig.text(
        0.068, 0.030,
        f"{marks_text}{band_note}Record begins {record_start.strftime('%d %B %Y')}.\n"
        f"Daily maximum 2 m air temperature, ERA5 reanalysis via Open-Meteo. "
        f"Built {date.today().strftime('%d %B %Y')}.",
        fontsize=6.4, va="bottom", color="#555555", linespacing=1.5,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    style.save(fig, out_path)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/dhaka_daily.csv")
    parser.add_argument("--out", default=OUT_DEFAULT)
    parser.add_argument("--smooth", type=int, default=5,
                        help="centred smoothing window for the ribbons in days, 1 disables it")
    args = parser.parse_args()
    written = build(Path(args.data), Path(args.out), smooth=args.smooth)
    print(f"Wrote {written}")


if __name__ == "__main__":
    main()
