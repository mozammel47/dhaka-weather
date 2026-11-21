"""Shared builder for the Tufte-style temperature ribbon charts.

Nested ribbons show the historical distribution of a daily temperature for
every calendar day. A black line traces the current year against that
backdrop, and dots mark days that broke the all-time record for that
calendar day.

Three things are built from this module. The standalone daily-high and
overnight-low graphs call `build`, which makes its own figure and adds the
vertical key. The four-panel year figure calls `draw` directly, with
`compact=True`, to render onto an axis it already owns.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime
from pathlib import Path

import matplotlib.dates as mdates
import numpy as np
import pandas as pd

import style

BAND_COLUMNS = ["lo", "p5", "p20", "p40", "p60", "p80", "p95", "hi"]

BAND_PAIRS = [("lo", "hi", "outer"), ("p5", "p95", "mid"),
              ("p20", "p80", "inner"), ("p40", "p60", "core")]

KEY_LEVELS = {"lo": 0.00, "p5": 0.17, "p20": 0.33, "p40": 0.46,
              "p60": 0.54, "p80": 0.67, "p95": 0.83, "hi": 1.00}


def load(path: Path, value: str) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["date"])
    frame = frame[frame[value].notna()].copy()
    frame["year"] = frame["date"].dt.year
    frame["month"] = frame["date"].dt.month
    frame["day"] = frame["date"].dt.day
    return frame


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
    out["lo"] = np.minimum(out["lo"], out["p5"])
    out["hi"] = np.maximum(out["hi"], out["p95"])
    return out


def daily_distribution(history: pd.DataFrame, value: str, plot_year: int) -> pd.DataFrame:
    """Percentiles of the historical record for each calendar day."""
    grouped = history.groupby(["month", "day"])[value]
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


def records_this_year(current: pd.DataFrame, value: str, stats: pd.DataFrame) -> pd.DataFrame:
    """Days where the current year beat the historical high or low."""
    merged = current.merge(stats[["month", "day", "lo", "hi"]],
                           on=["month", "day"], how="inner")
    merged["kind"] = np.where(
        merged[value] > merged["hi"], "high",
        np.where(merged[value] < merged["lo"], "low", "none"),
    )
    return merged[merged["kind"] != "none"]


def draw_key(fig, rect, colours: dict) -> None:
    """A vertical cross-section of the ribbon, used as the chart key."""
    axis = fig.add_axes(rect)
    axis.set_facecolor(style.PAPER)
    for spine in axis.spines.values():
        spine.set_visible(False)
    axis.set_xticks([])
    axis.set_yticks([])
    axis.set_xlim(0, 1)
    axis.set_ylim(-0.02, 1.02)

    for low, high, slot in BAND_PAIRS:
        axis.fill_between([0, 1], KEY_LEVELS[low], KEY_LEVELS[high],
                          color=colours[slot], lw=0)

    labels = [("hi", "record high"), ("p95", "95th"), ("p80", "80th"),
              ("p60", "60th"), ("p40", "40th"), ("p20", "20th"),
              ("p5", "5th"), ("lo", "record low")]
    for key, text in labels:
        axis.annotate(
            text, xy=(1.0, KEY_LEVELS[key]), xytext=(1.55, KEY_LEVELS[key]),
            fontsize=6.4, va="center", ha="left", color="#333333",
            annotation_clip=False,
            arrowprops=dict(arrowstyle="-", lw=0.4, color="#999999",
                            shrinkA=0, shrinkB=0),
        )
    axis.text(0.0, 1.075, "spread of\npast years", fontsize=6.2, ha="left",
              va="bottom", color="#555555", linespacing=1.4)


def month_axis(axis, plot_year: int, compact: bool) -> None:
    """Dotted guide at the start of each month, labels at mid month."""
    for month in range(1, 13):
        axis.axvline(datetime(plot_year, month, 1), color="#999999", lw=0.3,
                     ls=(0, (1, 2)), zorder=4)
    if compact:
        months = [1, 3, 5, 7, 9, 11]
        axis.set_xticks([datetime(plot_year, m, 15) for m in months])
    else:
        axis.set_xticks([datetime(plot_year, m, 15) for m in range(1, 13)])
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    axis.tick_params(axis="x", length=0, labelsize=8 if not compact else 7.6)


def draw(axis, frame: pd.DataFrame, value: str, plot_year: int, colours: dict,
         smooth: int = 5, tick_step: float = 5.0, compact: bool = False,
         headroom: int = 0) -> dict:
    """Render the ribbons, this year's line and record dots onto an axis.

    `headroom` adds that many tick steps of empty space above the data, so a
    caller can park a label up there without it landing on a ribbon.
    """
    current = frame[frame["year"] == plot_year].copy()
    history = frame[frame["year"] != plot_year]
    if history.empty:
        raise SystemExit("Need at least one complete prior year of data.")

    raw_stats = daily_distribution(history, value, plot_year)
    # Records are judged against the true daily extremes, never the smoothed ones
    hits = records_this_year(current, value, raw_stats)
    stats = smooth_bands(raw_stats, smooth)

    axis.set_facecolor(style.PAPER)
    x = stats["date"].to_numpy()
    for low, high, slot in BAND_PAIRS:
        axis.fill_between(x, stats[low], stats[high], color=colours[slot], lw=0, zorder=2)

    lowest = min(float(np.nanmin(stats["lo"])), float(current[value].min()))
    highest = max(float(np.nanmax(stats["hi"])), float(current[value].max()))
    y_lo = tick_step * np.floor(lowest / tick_step)
    y_hi = tick_step * np.ceil(highest / tick_step) + tick_step * headroom
    ticks = np.arange(y_lo, y_hi + 0.1, tick_step)

    # White reference lines drawn over the ribbons, as in the original
    for level in ticks:
        axis.axhline(level, color="white", lw=0.35, zorder=3)

    axis.plot(current["date"], current[value], color="black",
              lw=0.8 if compact else 1.0, zorder=5, solid_capstyle="round")

    for kind, dot in [("high", style.RECORD_HIGH), ("low", style.RECORD_LOW)]:
        subset = hits[hits["kind"] == kind]
        if not subset.empty:
            axis.scatter(subset["date"], subset[value], s=8 if compact else 11,
                         color=dot, zorder=6, linewidths=0.4, edgecolors="white")

    axis.set_ylim(y_lo, y_hi)
    axis.set_yticks(ticks)
    axis.set_yticklabels([f"{int(t)}°" for t in ticks],
                         fontsize=8 if not compact else 7.6)
    axis.set_xlim(stats["date"].iloc[0], stats["date"].iloc[-1])
    month_axis(axis, plot_year, compact)
    axis.tick_params(axis="y", length=0)
    for spine in axis.spines.values():
        spine.set_visible(False)

    return {
        "stats": stats,
        "hits": hits,
        "history": history,
        "current": current,
        "y_lo": y_lo,
        "y_hi": y_hi,
        "ticks": ticks,
    }


def build(
    data_path: Path,
    out_path: Path,
    value: str,
    title: str,
    variable_note: str,
    palette_name: str,
    smooth: int = 5,
    tick_step: float = 5.0,
) -> Path:
    """Draw one standalone ribbon chart and write it to disk."""
    style.apply_style()
    colours = style.palette(palette_name)

    frame = load(data_path, value)
    plot_year = int(frame["year"].max())
    last_date = frame["date"].max()

    fig = style.figure(width_mm=170.0, height_mm=108.0)
    axis = fig.add_axes([0.068, 0.215, 0.660, 0.520])
    info = draw(axis, frame, value, plot_year, colours, smooth, tick_step)

    mirror = axis.twinx()
    mirror.set_ylim(info["y_lo"], info["y_hi"])
    mirror.set_yticks(info["ticks"])
    mirror.set_yticklabels([f"{int(t)}°" for t in info["ticks"]], fontsize=8)
    mirror.tick_params(axis="y", length=0)
    mirror.set_facecolor("none")
    for spine in mirror.spines.values():
        spine.set_visible(False)

    draw_key(fig, [0.790, 0.250, 0.020, 0.430], colours)

    hits = info["hits"]
    record_start = frame["date"].min()
    n_years = plot_year - int(frame["year"].min())

    fig.text(0.068, 0.955, title, fontsize=13, fontweight="bold", va="top")
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
        f"{variable_note}, ERA5 reanalysis via Open-Meteo. "
        f"Built {date.today().strftime('%d %B %Y')}.",
        fontsize=6.4, va="bottom", color="#555555", linespacing=1.5,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    style.save(fig, out_path)
    return out_path
