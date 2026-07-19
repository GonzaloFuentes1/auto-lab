#!/usr/bin/env python3
"""
Example figure demonstrating the paper/FIGURE_STANDARD.md pattern end-to-end.

Runs out of the box with synthetic demo data (clearly marked below) so you can
see the pipeline work before wiring it to your own research/state.jsonl.
Copy this file's structure for your first real figure -- swap the demo data
block for a call to `significance.load_results(...)`.

Usage:
    python3 paper/figures/example_fig.py
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "research"))
sys.path.insert(0, str(Path(__file__).parent))

from significance import wilson_ci, DEFAULT_N  # noqa: E402
from style import apply, PALETTE_2, GRIDLINE, INK_MUTED, save_pdf  # noqa: E402

# --- DEMO DATA -- replace this block with significance.load_results(state_path, "H_N") ---
x = [1, 2, 3, 4, 5]
baseline_sr = [50, 52, 48, 55, 51]
treatment_sr = [58, 64, 62, 70, 74]
n = DEFAULT_N
# --- end demo data ---


def main():
    apply()

    base_lo, base_hi = zip(*[wilson_ci(sr, n) for sr in baseline_sr])
    treat_lo, treat_hi = zip(*[wilson_ci(sr, n) for sr in treatment_sr])

    fig, ax = plt.subplots(figsize=(3.3, 2.4))

    ax.fill_between(x, base_lo, base_hi, color=PALETTE_2["baseline"], alpha=0.15, linewidth=0)
    ax.plot(x, baseline_sr, color=PALETTE_2["baseline"], marker="o")

    ax.fill_between(x, treat_lo, treat_hi, color=PALETTE_2["treatment"], alpha=0.15, linewidth=0)
    ax.plot(x, treatment_sr, color=PALETTE_2["treatment"], marker="o")

    ax.annotate("treatment", xy=(x[-1], treatment_sr[-1]), xytext=(4, 4), textcoords="offset points",
                color=PALETTE_2["treatment"], fontsize=8, va="bottom")
    ax.annotate("baseline", xy=(x[-1], baseline_sr[-1]), xytext=(4, -10), textcoords="offset points",
                color=PALETTE_2["baseline"], fontsize=8, va="top")

    ax.set_xlabel("Condition")
    ax.set_ylabel("Metric (%)")
    ax.set_ylim(0, 100)
    ax.grid(True, axis="y", color=GRIDLINE, linewidth=0.6)
    ax.tick_params(colors=INK_MUTED)

    save_pdf(fig, "example_fig")


if __name__ == "__main__":
    main()
