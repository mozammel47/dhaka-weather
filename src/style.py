"""Shared matplotlib styling for the Dhaka weather graphs.

Mirrors the publication defaults used elsewhere in this workflow:
300 dpi, Arial/Helvetica, TrueType-embedded fonts, 170 mm canvas width.
Figures are saved without bbox_inches='tight' so the canvas size is exact.
"""

import matplotlib as mpl
import matplotlib.pyplot as plt

MM = 1.0 / 25.4

PAPER = "linen"
RECORD_HIGH = "#d7191c"
RECORD_LOW = "#2c7bb6"

# One palette per chart, so the three graphs are told apart at a glance.
# Each runs light to dark, outermost band first, and each is a ColorBrewer
# sequential ramp, which keeps them legible in greyscale and safe for the
# common forms of colour vision deficiency.
PALETTES = {
    # Daytime heat. The lightest step is kept darker than the linen paper,
    # so the record-range band stays visible against the background.
    "heat": {
        "outer": "#fcbba1",
        "mid": "#fc9272",
        "inner": "#ef3b2c",
        "core": "#a50f15",
        "accent": "#67000d",
    },
    # Overnight warmth
    "night": {
        "outer": "#dadaeb",
        "mid": "#bcbddc",
        "inner": "#9e9ac8",
        "core": "#6a51a3",
        "accent": "#3f007d",
    },
    # Rainfall
    "rain": {
        "outer": "#bdc9e1",
        "mid": "#74a9cf",
        "inner": "#2b8cbe",
        "core": "#045a8d",
        "accent": "#023858",
    },
    # Rainfall intensity, kept clearly apart from the rainfall blues
    "burst": {
        "outer": "#b2e2e2",
        "mid": "#66c2a4",
        "inner": "#2ca25f",
        "core": "#006d2c",
        "accent": "#00441b",
    },
}


def palette(name):
    """Look up a named palette, falling back to the rainfall blues."""
    return PALETTES.get(name, PALETTES["rain"])


# Backwards-compatible names, pointing at the rainfall blues
BAND_OUTER = PALETTES["rain"]["outer"]
BAND_MID = PALETTES["rain"]["mid"]
BAND_INNER = PALETTES["rain"]["inner"]
BAND_CORE = PALETTES["rain"]["core"]


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


PANEL_LABEL_SIZE = 14


def apply_panel_style():
    """Publication defaults for the multi-panel indicator figure.

    Larger type than the single web graphs, since this figure is meant to
    survive being dropped into a slide or a manuscript at 170 mm wide.
    """
    apply_style()
    mpl.rcParams.update({
        "font.size": 12,
        "axes.titlesize": 13,
        "axes.labelsize": 12,
        "xtick.labelsize": 12,
        "ytick.labelsize": 12,
        "legend.fontsize": 12,
    })


def figure(width_mm=170.0, height_mm=95.0):
    """Create a figure at an exact millimetre canvas size."""
    return plt.figure(figsize=(width_mm * MM, height_mm * MM))


def save(fig, path):
    """Save without bbox_inches so the declared canvas size is preserved."""
    fig.savefig(path, dpi=300, facecolor=fig.get_facecolor())
    plt.close(fig)
