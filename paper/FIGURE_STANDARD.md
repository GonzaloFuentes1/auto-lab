# Figure standard

Same idea as `research/PAPER_STANDARD.md` — a checklist a figure must pass before it goes into
`main.tex`, so "looks fine to me" isn't the bar. Uses the `dataviz` skill's method (form → color →
validate → marks) as the base, plus academic-print-specific rules that skill doesn't cover (it's
written for interactive web charts, not static LaTeX figures).

## Checklist

1. **Vector, not raster.** Save as PDF via `paper/figures/style.py::save_pdf()`, never PNG for a
   line/bar/scatter figure — PNG blurs on zoom and in print, bloats the file, and can't be
   selected/searched if it has text. PNG is fine only for a screenshot-style figure that has no
   real vector content of its own.
2. **Consistent style across every figure.** Call `style.apply()` once at the top of every figure
   script — same font, same line weights, same colors everywhere. A paper where one figure uses a
   different font than another reads as unfinished.
3. **Colorblind-safe, validated, not eyeballed.** Use `PALETTE_2`/`PALETTE_3` from `style.py`
   (already validated against a white print surface with the `dataviz` skill's
   `validate_palette.js`). If you need a different hue set, re-run the validator — don't pick new
   colors by eye.
4. **One axis. Zero-baseline for anything encoded as bar length.** No dual-y-axis charts — the
   alignment between two scales is arbitrary and invents a correlation that isn't there (see the
   `dataviz` skill's anti-patterns). A bar chart's y-axis must start at 0 — truncating it to
   exaggerate a small difference is exactly the visual equivalent of the eyeballed-significance
   mistake `research/significance.py` exists to prevent numerically. A *line* chart zoomed to the
   relevant range (not starting at 0) is fine and often necessary — the zero-baseline rule is
   specifically about bar length encoding magnitude.
5. **Error bars/bands come from `research/significance.py`, not eyeballed.** If a figure shows a
   proportion metric, show the Wilson CI (import `wilson_ci` directly — don't recompute it
   differently in the figure script). For multi-run results, show the actual spread, not just
   the mean.
6. **Caption states N and the stats method.** A reviewer should be able to tell if a difference is
   real from the caption alone, without cross-referencing the text.
7. **Direct labels over a legend when there are ≤3 series** — put labels directly on the lines
   near their endpoints rather than a separate legend box, if it fits without collision. Falls
   back to a legend past 3 series.
8. **Run it past the `dataviz` skill's `anti-patterns.md`** before calling a figure done — dual
   axes, rainbow sequential ramps, a number crammed onto every point, thick saturated blocks with
   heavy gridlines are all explicitly called out there and apply here unchanged.

## Where scripts live

`paper/figures/*.py` — one script per figure (or per closely-related figure group), reading
directly from `research/state.jsonl` via the same loader `research/significance.py` uses
(`load_results`) — import it, don't reimplement jsonl parsing in every figure script. Never
hand-transcribe a number from a jsonl entry into a plotting script.

## Setup

Figure scripts need `matplotlib`, which doesn't belong in your main training/eval venv. Use a
dedicated lightweight venv:
```bash
python3 -m venv paper/.venv-figs && source paper/.venv-figs/bin/activate
pip install -r paper/requirements.txt
```

## Example

`paper/figures/example_fig.py` — a working, runnable example with synthetic data demonstrating
the pattern: validated palette, Wilson CI bands, direct labels, vector PDF output. Copy its
structure for your first real figure rather than starting from a blank matplotlib script.
