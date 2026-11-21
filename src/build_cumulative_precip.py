"""Cumulative annual rainfall in Dhaka, current year against the record.

A thin wrapper. The drawing and the statistics live in `cumulative.py`, so
the four-panel year figure can render the same picture at panel size.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cumulative

OUT_DEFAULT = "graphs/CumulativeRainfall_Dhaka.png"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/dhaka_daily.csv")
    parser.add_argument("--out", default=OUT_DEFAULT)
    parser.add_argument("--palette", default="rain",
                        choices=["heat", "night", "humid", "rain", "burst"])
    args = parser.parse_args()

    written = cumulative.build(Path(args.data), Path(args.out), palette_name=args.palette)
    print(f"Wrote {written}")


if __name__ == "__main__":
    main()
