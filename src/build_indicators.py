"""Four-panel climate indicator figure for Dhaka.

Each panel answers a question a weather app does not. One colour ramp per
panel, so the four are told apart at a glance and none of them is mistaken
for another. Every panel carries a marker for the current year, which is the
only part of the figure that changes from day to day and the reason to look
again.

Panel A   Hot nights per year, purples
Panel B   Humid heat days per year, reds
Panel C   Monsoon onset and withdrawal, blues
Panel D   Share of the year's rain on its wettest days, greens

The current year is incomplete by definition, so it is drawn in a lighter
accent, labelled "to date", and excluded from every trend line.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import indicators
import style

OUT_DEFAULT = "graphs/ClimateIndicators_Dhaka.png"
TREND_WINDOW = 11

PANEL_PALETTES = {"A": "night", "B": "heat", "C": "rain", "D": "burst"}

# Day of year for the first of each month, non-leap, used on the monsoon axis
MONTH_STARTS = {"May": 121, "Jun": 152, "Jul": 182, "Aug": 213,
                "Sep": 244, "Oct": 274, "Nov": 305}


def trend(series: pd.Series) -> pd.Series:
    return series.rolling(TREND_WINDOW, center=True, min_periods=6).mean()


def label_panel(axis, letter: str) -> None:
    axis.text(-0.20, 1.14, letter, transform=axis.transAxes,
              fontsize=style.PANEL_LABEL_SIZE, fontweight="bold",
              va="top", ha="left")


def tidy(axis) -> None:
    axis.set_facecolor(style.PAPER)
    for side in ("top", "right"):
        axis.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axis.spines[side].set_color("#999999")
        axis.spines[side].set_linewidth(0.6)
    axis.tick_params(length=2.5, width=0.6, color="#999999", labelsize=10)
    axis.grid(axis="y", color="white", lw=0.8, zorder=0)
    axis.set_axisbelow(True)


def note(axis, text: str) -> None:
    axis.text(0.0, 1.025, text, transform=axis.transAxes, fontsize=7.4,
              va="bottom", ha="left", color="#555555")


# Headroom above the tallest bar, so the current-year label has somewhere to
# sit without a background patch painting over the data behind it
HEADROOM = 1.20


def draw_count_panel(axis, table, column, colours, title, ylabel, note_text,
                     current_year, suffix="") -> None:
    """Bar per year, trend line over complete years, current year flagged."""
    complete = table[table["complete_year"] & (table.index != current_year)]
    values = complete[column].dropna()

    axis.bar(values.index, values.to_numpy(), width=0.86,
             color=colours["mid"], lw=0, zorder=2)
    axis.plot(values.index, trend(values).to_numpy(), color=colours["accent"],
              lw=1.6, zorder=4)

    if current_year in table.index and pd.notna(table.loc[current_year, column]):
        latest = float(table.loc[current_year, column])
        axis.bar([current_year], [latest], width=0.86, color=colours["core"],
                 lw=0.5, edgecolor="black", zorder=3)
        # Parked in the headroom at the top right, where nothing else sits,
        # so it never lands on a bar or on the trend line
        axis.text(0.995, 0.99, f"{current_year}\n{latest:,.0f}{suffix} to date",
                  transform=axis.transAxes, fontsize=7.4, ha="right", va="top",
                  color="black", linespacing=1.35, zorder=6)

    axis.set_title(title, fontsize=11, fontweight="bold", pad=14, loc="left")
    axis.set_ylabel(ylabel, fontsize=9)
    note(axis, note_text)
    axis.set_xlim(values.index.min() - 1.5, current_year + 2.5)
    axis.set_ylim(0, float(table[column].max()) * HEADROOM)
    tidy(axis)


def draw_monsoon_panel(axis, table, colours, current_year) -> None:
    """A vertical bar per year running from onset to withdrawal."""
    usable = table[table["onset_doy"].notna() & table["withdrawal_doy"].notna()]
    past = usable[usable.index != current_year]

    axis.vlines(past.index, past["onset_doy"], past["withdrawal_doy"],
                color=colours["mid"], lw=1.4, zorder=2)
    axis.plot(past.index, trend(past["onset_doy"]).to_numpy(),
              color=colours["accent"], lw=1.6, zorder=4)
    axis.plot(past.index, trend(past["withdrawal_doy"]).to_numpy(),
              color=colours["accent"], lw=1.6, zorder=4)

    if current_year in usable.index:
        row = usable.loc[current_year]
        axis.vlines([current_year], row["onset_doy"], row["withdrawal_doy"],
                    color="black", lw=1.8, zorder=5)

    # Labels anchored on the left, where the panel is least crowded
    anchor = past.index.min() + 5
    axis.annotate("withdrawal", xy=(anchor, trend(past["withdrawal_doy"]).loc[anchor]),
                  xytext=(0, 7), textcoords="offset points", fontsize=7.4,
                  ha="left", va="bottom", color=colours["accent"], zorder=6)
    axis.annotate("onset", xy=(anchor, trend(past["onset_doy"]).loc[anchor]),
                  xytext=(0, -7), textcoords="offset points", fontsize=7.4,
                  ha="left", va="top", color=colours["accent"], zorder=6)

    axis.set_title("Monsoon season", fontsize=11, fontweight="bold", pad=14, loc="left")
    note(axis, "onset to withdrawal, rule in the README")
    axis.set_yticks(list(MONTH_STARTS.values()))
    axis.set_yticklabels(list(MONTH_STARTS.keys()))
    axis.set_ylim(min(MONTH_STARTS.values()) - 18, max(MONTH_STARTS.values()) + 10)
    axis.set_xlim(past.index.min() - 1.5, current_year + 2.5)
    tidy(axis)
    axis.grid(axis="y", color="white", lw=0.8, zorder=0)


def build(data_path: Path, out_path: Path) -> tuple[Path, str]:
    style.apply_panel_style()

    table, meta = indicators.build(data_path)
    current_year = meta["current_year"]

    fig = style.figure(width_mm=170.0, height_mm=178.0)
    axes = fig.subplots(2, 2)
    for axis in axes.flat:
        axis.set_facecolor(style.PAPER)

    draw_count_panel(
        axes[0, 0], table, "hot_nights", style.palette(PANEL_PALETTES["A"]),
        "Hot nights", "nights per year",
        f"minimum at or above {meta['tmin_threshold']:.1f} °C",
        current_year,
    )
    draw_count_panel(
        axes[0, 1], table, "heat_days", style.palette(PANEL_PALETTES["B"]),
        "Humid heat days", "days per year",
        f"apparent maximum at or above {meta['app_threshold']:.1f} °C",
        current_year,
    )
    draw_monsoon_panel(axes[1, 0], table, style.palette(PANEL_PALETTES["C"]), current_year)
    draw_count_panel(
        axes[1, 1], table, "rain_concentration_pct", style.palette(PANEL_PALETTES["D"]),
        "Rain concentration", "per cent of annual total",
        f"share falling on the {indicators.TOP_RAIN_DAYS} wettest days",
        current_year, suffix="%",
    )

    for letter, axis in zip("ABCD", axes.flat):
        label_panel(axis, letter)

    # Written as plain figure text rather than suptitle, since tight_layout
    # reserves space for a suptitle on top of the rect and leaves a gap
    fig.text(0.012, 0.992, "Dhaka Climate Indicators", fontsize=15,
             fontweight="bold", va="top", ha="left")
    fig.text(
        0.012, 0.952,
        f"Thresholds are Dhaka's own {meta['baseline_quantile']:.0%} percentile for "
        f"{meta['baseline_start']} to {meta['baseline_end']}, not imported constants.\n"
        f"Heavy lines are {TREND_WINDOW}-year running means. The dark bar is "
        f"{current_year} to {meta['last_date'].strftime('%d %B')}, excluded from every trend.",
        fontsize=7.6, va="top", ha="left", color="#333333", linespacing=1.5,
    )
    fig.text(
        0.012, 0.012,
        "Daily ERA5 reanalysis via Open-Meteo. Monsoon dates follow one stated rule, "
        "not an official declaration. "
        f"Built {date.today().strftime('%d %B %Y')}.",
        fontsize=6.8, va="bottom", ha="left", color="#555555",
    )

    # tight_layout reserves room for the panel titles inside this rect.
    # Do not follow it with subplots_adjust(top=...), which moves the axes up
    # and pushes the titles back under the header.
    fig.tight_layout(rect=[0.012, 0.030, 0.995, 0.900], h_pad=1.2, w_pad=2.6)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    style.save(fig, out_path)
    return out_path, indicators.headline(table, meta)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/dhaka_daily.csv")
    parser.add_argument("--out", default=OUT_DEFAULT)
    args = parser.parse_args()
    written, line = build(Path(args.data), Path(args.out))
    print(f"Wrote {written}")
    print(line)


if __name__ == "__main__":
    main()
