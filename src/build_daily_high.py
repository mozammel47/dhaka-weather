"""Daily high temperature in Dhaka, current year against the record.

The hottest part of the day. In Dhaka this peaks before the monsoon
arrives, in April, rather than at midsummer.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import ribbon

OUT_DEFAULT = "graphs/DailyHighTemp_Dhaka.png"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/dhaka_daily.csv")
    parser.add_argument("--out", default=OUT_DEFAULT)
    parser.add_argument("--smooth", type=int, default=5,
                        help="centred smoothing window for the ribbons in days, 1 disables it")
    parser.add_argument("--palette", default="heat", choices=["heat", "night", "humid", "rain", "burst"])
    args = parser.parse_args()

    written = ribbon.build(
        data_path=Path(args.data),
        out_path=Path(args.out),
        value="tmax_c",
        title="Daily High Temperature in Dhaka",
        variable_note="Daily maximum 2 m air temperature",
        palette_name=args.palette,
        smooth=args.smooth,
    )
    print(f"Wrote {written}")


if __name__ == "__main__":
    main()
