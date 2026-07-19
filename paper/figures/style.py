"""
Shared matplotlib style for every figure in paper/. Import and call `apply()`
once at the top of a figure script, then use PALETTE/save_pdf for everything
else -- this is what keeps every figure in the paper looking like the same
paper, not eight different plotting sessions stapled together.

Colors are the validated categorical slots from the dataviz skill's reference
palette (references/palette.md), re-checked against a pure-white print
surface (#ffffff, not the #fcfcfb web-chart surface) with
scripts/validate_palette.js -- both sets below PASS every check (CVD
separation, normal-vision floor, contrast) at that surface.
"""
import matplotlib.pyplot as plt
from pathlib import Path

FIGURES_DIR = Path(__file__).parent

# 2-series set (e.g. baseline vs treatment) -- ΔE 24.7 CVD / 33.6 normal-vision, both well above the ≥8 / ≥15 targets.
PALETTE_2 = {"baseline": "#2a78d6", "treatment": "#eb6834"}

# 3-series set -- validated under --pairs all (every pair, not just adjacent), all PASS.
PALETTE_3 = ["#2a78d6", "#eb6834", "#4a3aa7"]

# Chart chrome (from the same reference palette, light-mode column)
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE_AXIS = "#c3c2b7"


def apply():
    """Call once per script, before creating any figure."""
    plt.rcParams.update({
        # Serif to match the paper body (Times, via the ICLR/iclr2026_conference.sty \usepackage{times})
        # -- not matplotlib's default DejaVu Sans, which visibly clashes with LaTeX body text.
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "Nimbus Roman", "Liberation Serif", "DejaVu Serif"],
        "font.size": 9,          # close to \small in a two-column ICLR figure
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "legend.fontsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        # Thin marks, recessive grid -- see dataviz skill, marks-and-anatomy.md
        "axes.linewidth": 0.8,
        "lines.linewidth": 1.6,
        "lines.markersize": 5,
        "grid.color": GRIDLINE,
        "grid.linewidth": 0.6,
        "axes.edgecolor": BASELINE_AXIS,
        "axes.labelcolor": INK_PRIMARY,
        "xtick.color": INK_MUTED,
        "ytick.color": INK_MUTED,
        "text.color": INK_PRIMARY,
        # Vector-friendly: embed fonts as outlines (Type 3->42) so the PDF is
        # portable and text stays selectable/searchable, not rasterized.
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 150,       # for on-screen preview only -- saved PDFs are vector, DPI doesn't apply
    })


def save_pdf(fig, name, tight=True):
    """Save as vector PDF into paper/figures/ -- never PNG for a line/bar figure
    going into the paper (PNG rasterizes, blurs on zoom/print, bloats the PDF).
    A PNG export is fine for a quick Slack preview, never for \\includegraphics."""
    if tight:
        fig.tight_layout()
    out = FIGURES_DIR / f"{name}.pdf"
    fig.savefig(out, format="pdf", bbox_inches="tight" if tight else None)
    print(f"wrote {out}")
    return out
