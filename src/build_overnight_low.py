"""Overnight low temperature in Dhaka, current year against the record.

The coolest point of each 24 hours, usually just before dawn. This is the
quieter half of the temperature story and often the more consequential one.
A hot day is survivable if the night lets the body shed heat. When the
overnight low stays high, it does not, which is why warm nights track heat
mortality more closely than daytime peaks do. Overnight minima also tend to
rise faster than daytime maxima under warming, so the upward drift shows
earlier here than in the daytime chart.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import ribbon

OUT_DEFAULT = "graphs/OvernightLowTemp_Dhaka.png"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/dhaka_daily.csv")
    parser.add_argument("--out", default=OUT_DEFAULT)
    parser.add_argument("--smooth", type=int, default=5,
                        help="centred smoothing window for the ribbons in days, 1 disables it")
    parser.add_argument("--palette", default="night", choices=["heat", "night", "rain"])
    args = parser.parse_args()

    written = ribbon.build(
        data_path=Path(args.data),
        out_path=Path(args.out),
        value="tmin_c",
        title="Overnight Low Temperature in Dhaka",
        variable_note="Daily minimum 2 m air temperature",
        palette_name=args.palette,
        smooth=args.smooth,
    )
    print(f"Wrote {written}")


if __name__ == "__main__":
    main()
