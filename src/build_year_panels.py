"""The current year against the whole record, in four panels.

Every panel is the same picture the parent repository draws, a day-of-year
axis with nested percentile ribbons behind a black line for this year. The
four are chosen so that no two say the same thing, and each carries its own
colour ramp.

Panel A   Daily high temperature, reds
Panel B   Humid heat, apparent maximum, yellow through brown
Panel C   Overnight low temperature, purples
Panel D   Cumulative rainfall, blues

The long-run comparison that a day-of-year axis cannot show is carried in
words instead. Each panel states how many qualifying days this year has had
so far against the 1961 to 1990 average by the same date, which is the only
honest way to compare a part year with a full one.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd

import cumulative
import indicators
import ribbon
import style

OUT_DEFAULT = "graphs/YearAgainstRecord_Dhaka.png"


def panel_header(axis, title: str, note_text: str) -> None:
    axis.set_title(title, fontsize=10.5, fontweight="bold", pad=13, loc="left")
    axis.text(0.0, 1.025, note_text, transform=axis.transAxes, fontsize=7.2,
              va="bottom", ha="left", color="#555555")


def corner_stat(axis, lines: list[str]) -> None:
    """Short comparison parked in the quiet top-left corner of a panel."""
    axis.text(0.015, 0.965, "\n".join(lines), transform=axis.transAxes,
              fontsize=6.8, va="top", ha="left", color="black",
              linespacing=1.45, zorder=7)


def label_panel(axis, letter: str) -> None:
    axis.text(-0.155, 1.20, letter, transform=axis.transAxes,
              fontsize=style.PANEL_LABEL_SIZE, fontweight="bold",
              va="top", ha="left")


def temperature_panel(axis, frame, value, plot_year, palette_name, title,
                      note_text, threshold, through_doy, base_years, smooth) -> dict:
    colours = style.palette(palette_name)
    info = ribbon.draw(axis, frame, value, plot_year, colours,
                       smooth=smooth, compact=True, headroom=1)

    so_far = int((info["current"][value] >= threshold).sum())
    baseline = indicators.count_through(frame, value, threshold, through_doy, base_years)
    unit = "nights" if value == "tmin_c" else "days"
    corner_stat(axis, [
        f"{so_far} {unit} at or above {threshold:.1f}°",
        f"baseline {baseline:.0f} by this date",
    ])
    panel_header(axis, title, note_text)
    return info


def build(data_path: Path, out_path: Path, smooth: int = 5) -> Path:
    style.apply_panel_style()

    frame = ribbon.load(data_path, "tmax_c")
    frame["day_of_year"] = frame["date"].dt.dayofyear
    plot_year = int(frame["year"].max())
    last_date = frame["date"].max()
    through_doy = int(frame.loc[frame["year"] == plot_year, "day_of_year"].max())

    base_years = indicators.baseline_years(frame)
    tmax_threshold, base_lo, base_hi = indicators.baseline_threshold(frame, "tmax_c")
    app_threshold, _, _ = indicators.baseline_threshold(frame, "app_tmax_c")
    tmin_threshold, _, _ = indicators.baseline_threshold(frame, "tmin_c")

    fig = style.figure(width_mm=170.0, height_mm=172.0)
    axes = fig.subplots(2, 2)

    temperature_panel(
        axes[0, 0], frame, "tmax_c", plot_year, "heat", "Daily high",
        "maximum air temperature", tmax_threshold, through_doy, base_years, smooth,
    )
    temperature_panel(
        axes[0, 1], frame, "app_tmax_c", plot_year, "humid", "Humid heat",
        "apparent maximum, humidity included", app_threshold, through_doy,
        base_years, smooth,
    )
    temperature_panel(
        axes[1, 0], frame, "tmin_c", plot_year, "night", "Overnight low",
        "minimum air temperature", tmin_threshold, through_doy, base_years, smooth,
    )

    rain_frame = cumulative.load(data_path)
    rain_info = cumulative.draw(axes[1, 1], rain_frame, plot_year,
                                style.palette("rain"), compact=True)
    rain_so_far = float(rain_info["current"].iloc[-1])
    rain_baseline = indicators.rain_through(frame, through_doy, base_years)
    corner_stat(axes[1, 1], [
        f"{rain_so_far:,.0f} mm so far",
        f"baseline {rain_baseline:,.0f} mm by this date",
    ])
    panel_header(axes[1, 1], "Cumulative rain", "millimetres since 1 January")

    for letter, axis in zip("ABCD", axes.flat):
        label_panel(axis, letter)

    n_years = plot_year - int(frame["year"].min())
    fig.text(0.012, 0.992, f"Dhaka {plot_year} Against the Record", fontsize=15,
             fontweight="bold", va="top", ha="left")
    fig.text(
        0.012, 0.952,
        f"The black line is {plot_year} through {last_date.strftime('%d %B')}. Ribbons show "
        f"the spread of the previous {n_years} years, from the\nfull record range outside "
        f"to the 40th to 60th percentile core, in each panel's own colour.\nRed and blue "
        f"dots mark record-breaking days. Counts compare part year with part year.",
        fontsize=7.4, va="top", ha="left", color="#333333", linespacing=1.5,
    )
    fig.text(
        0.012, 0.010,
        f"Daily ERA5 reanalysis via Open-Meteo. Baseline {base_lo} to {base_hi}, "
        f"{indicators.BASELINE_QUANTILE:.0%} percentile.\nBands smoothed over {smooth} "
        f"days. Built {date.today().strftime('%d %B %Y')}.",
        fontsize=6.6, va="bottom", ha="left", color="#555555", linespacing=1.5,
    )

    fig.tight_layout(rect=[0.012, 0.045, 0.995, 0.885], h_pad=1.4, w_pad=2.8)

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
