"""Cumulative annual rainfall, current year against the record.

Dhaka receives most of its rain in a few monsoon months, so a running
annual total says far more than daily bars. Bands cover the full historical
range plus the 10th to 90th and 25th to 75th percentiles.

As with the temperature ribbons, `build` makes a standalone figure and
`draw` renders onto an axis the caller already owns.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime
from pathlib import Path

import matplotlib.dates as mdates
import numpy as np
import pandas as pd

import style

VALUE = "prcp_mm"


def load(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["date"])
    frame = frame[frame[VALUE].notna()].copy()
    frame["year"] = frame["date"].dt.year
    frame["month"] = frame["date"].dt.month
    frame["day"] = frame["date"].dt.day
    frame["md"] = frame["month"] * 100 + frame["day"]
    return frame.sort_values("date")


def cumulative_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Wide table of running yearly totals, rows are calendar days."""
    work = frame.copy()
    work["cumulative"] = work.groupby("year")[VALUE].cumsum()
    table = work.pivot_table(index="md", columns="year", values="cumulative", aggfunc="last")
    return table.sort_index()


def complete_years(frame: pd.DataFrame, plot_year: int) -> list[int]:
    counts = frame[frame["year"] < plot_year].groupby("year").size()
    return sorted(counts[counts >= 360].index.tolist())


def draw(axis, frame: pd.DataFrame, plot_year: int, colours: dict,
         compact: bool = False) -> dict:
    """Render the rainfall envelope and this year's running total."""
    table = cumulative_table(frame)
    past_years = complete_years(frame, plot_year)
    if not past_years:
        raise SystemExit("Need at least one complete prior year of data.")

    plot_days = frame.loc[frame["year"] == plot_year, "md"].tolist()
    axis_days = sorted(set(table.index.tolist()))
    if not calendar.isleap(plot_year):
        axis_days = [d for d in axis_days if d != 229]

    past = table.loc[axis_days, past_years].ffill()
    dates = [datetime(plot_year, d // 100, d % 100) for d in axis_days]

    envelope = pd.DataFrame({
        "lo": past.min(axis=1),
        "p10": past.quantile(0.10, axis=1),
        "p25": past.quantile(0.25, axis=1),
        "median": past.median(axis=1),
        "p75": past.quantile(0.75, axis=1),
        "p90": past.quantile(0.90, axis=1),
        "hi": past.max(axis=1),
    })

    totals = past.iloc[-1]
    wettest_year = int(totals.idxmax())
    driest_year = int(totals.idxmin())

    current = table.loc[[d for d in plot_days if d in table.index], plot_year].dropna()
    current_dates = [datetime(plot_year, d // 100, d % 100) for d in current.index]

    axis.set_facecolor(style.PAPER)
    axis.fill_between(dates, envelope["lo"], envelope["hi"],
                      color=colours["outer"], lw=0, zorder=2)
    axis.fill_between(dates, envelope["p10"], envelope["p90"],
                      color=colours["mid"], lw=0, zorder=2)
    axis.fill_between(dates, envelope["p25"], envelope["p75"],
                      color=colours["inner"], lw=0, zorder=2)
    axis.plot(dates, envelope["median"], color=colours["core"], lw=0.9, zorder=4)

    if not compact:
        for year, colour in [(wettest_year, "#7b3294"), (driest_year, "#a6611a")]:
            series = past[year]
            axis.plot(dates, series, color=colour, lw=0.7, ls=(0, (3, 1.6)), zorder=5)
            axis.annotate(f"{year}  {series.iloc[-1]:,.0f} mm",
                          xy=(dates[-1], series.iloc[-1]), xytext=(4, 0),
                          textcoords="offset points", fontsize=6.4, va="center",
                          color=colour, annotation_clip=False)

    axis.plot(current_dates, current.to_numpy(), color="black",
              lw=1.0 if compact else 1.2, zorder=6, solid_capstyle="round")
    axis.scatter([current_dates[-1]], [current.iloc[-1]],
                 s=8 if compact else 10, color="black", zorder=7)

    top = float(envelope["hi"].max())
    step = 500 if top > 2500 else 250
    ticks = np.arange(0, top + step, step)
    for level in ticks:
        axis.axhline(level, color="white", lw=0.35, zorder=3)

    axis.set_ylim(0, top * 1.02)
    axis.set_yticks(ticks)
    axis.set_yticklabels([f"{int(t):,}" for t in ticks],
                         fontsize=7.6 if compact else 8)
    axis.set_xlim(dates[0], dates[-1])

    for month in range(1, 13):
        axis.axvline(datetime(plot_year, month, 1), color="#999999", lw=0.3,
                     ls=(0, (1, 2)), zorder=3)
    months = [1, 3, 5, 7, 9, 11] if compact else list(range(1, 13))
    axis.set_xticks([datetime(plot_year, m, 15) for m in months])
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    axis.tick_params(axis="x", length=0, labelsize=7.6 if compact else 8)
    axis.tick_params(axis="y", length=0)
    for spine in axis.spines.values():
        spine.set_visible(False)

    return {
        "dates": dates,
        "envelope": envelope,
        "current": current,
        "current_dates": current_dates,
        "past_years": past_years,
        "wettest_year": wettest_year,
        "driest_year": driest_year,
        "median_to_date": float(envelope["median"].loc[current.index[-1]]),
        "top": top,
    }


def build(data_path: Path, out_path: Path, palette_name: str = "rain") -> Path:
    style.apply_style()
    colours = style.palette(palette_name)

    frame = load(data_path)
    plot_year = int(frame["year"].max())
    last_date = frame["date"].max()

    fig = style.figure(width_mm=170.0, height_mm=108.0)
    axis = fig.add_axes([0.090, 0.215, 0.700, 0.520])
    info = draw(axis, frame, plot_year, colours)

    current = info["current"]
    current_dates = info["current_dates"]
    normal_to_date = info["median_to_date"]
    top = info["top"]

    # Keep the two end labels from colliding when this year sits near normal
    axis_height_pts = 0.520 * fig.get_figheight() * 72.0
    separation_pts = abs(float(current.iloc[-1]) - normal_to_date) / (top * 1.02) * axis_height_pts
    extra = max(0.0, 13.0 - separation_pts)
    above = float(current.iloc[-1]) >= normal_to_date

    axis.annotate(f"{plot_year}  {current.iloc[-1]:,.0f} mm",
                  xy=(current_dates[-1], current.iloc[-1]),
                  xytext=(6, (2 + extra / 2) * (1 if above else -1)),
                  textcoords="offset points", fontsize=7.2, fontweight="bold",
                  va="bottom" if above else "top", color="black", annotation_clip=False)
    axis.annotate(f"median by this date  {normal_to_date:,.0f} mm",
                  xy=(current_dates[-1], normal_to_date),
                  xytext=(6, (-2 - extra / 2) * (1 if above else -1)),
                  textcoords="offset points", fontsize=6.4,
                  va="top" if above else "bottom",
                  color=colours["core"], annotation_clip=False)

    axis.set_ylabel("millimetres since 1 January", fontsize=8)

    record_start = frame["date"].min()
    fig.text(0.090, 0.955, "Cumulative Rainfall in Dhaka", fontsize=13,
             fontweight="bold", va="top")
    fig.text(
        0.090, 0.885,
        f"The black line is the running total for {plot_year}, through "
        f"{last_date.strftime('%d %B %Y')}.\nBands cover the full range, the 10th to 90th "
        f"and the 25th to 75th percentiles of {len(info['past_years'])} past years.",
        fontsize=8, va="top", color="#333333", linespacing=1.45,
    )
    fig.text(
        0.090, 0.030,
        f"Solid blue line is the median year. Dashed lines are the wettest and driest years "
        f"on record.\nRecord begins {record_start.strftime('%d %B %Y')}. "
        f"Daily precipitation, ERA5 reanalysis via Open-Meteo. "
        f"Built {date.today().strftime('%d %B %Y')}.",
        fontsize=6.4, va="bottom", color="#555555", linespacing=1.5,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    style.save(fig, out_path)
    return out_path
