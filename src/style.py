"""Shared matplotlib styling for the Dhaka weather graphs.

Mirrors the publication defaults used elsewhere in this workflow:
300 dpi, Arial/Helvetica, TrueType-embedded fonts, 170 mm canvas width.
Figures are saved without bbox_inches='tight' so the canvas size is exact.
"""

import matplotlib as mpl
import matplotlib.pyplot as plt

MM = 1.0 / 25.4

# Tufte-style ribbon palette, light to dark
BAND_OUTER = "#bdc9e1"   # min to max
BAND_MID = "#74a9cf"     # 5th to 95th
BAND_INNER = "#2b8cbe"   # 20th to 80th
BAND_CORE = "#045a8d"    # 40th to 60th
PAPER = "linen"
RECORD_HIGH = "#d7191c"
RECORD_LOW = "#2c7bb6"


def apply_style():
    """Apply the shared rcParams. Call once before building a figure."""
    mpl.rcParams.update({
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "font.size": 12,
        "axes.titlesize": 13,
        "axes.labelsize": 12,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "legend.fontsize": 12,
        "axes.facecolor": PAPER,
        "figure.facecolor": PAPER,
        "savefig.facecolor": PAPER,
        "axes.edgecolor": "#444444",
        "axes.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def figure(width_mm=170.0, height_mm=95.0):
    """Create a figure at an exact millimetre canvas size."""
    return plt.figure(figsize=(width_mm * MM, height_mm * MM))


def save(fig, path):
    """Save without bbox_inches so the declared canvas size is preserved."""
    fig.savefig(path, dpi=300, facecolor=fig.get_facecolor())
    plt.close(fig)
