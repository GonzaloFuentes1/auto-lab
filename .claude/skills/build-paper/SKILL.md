---
name: build-paper
description: Compile the paper draft (paper/) to PDF with tectonic, and generate/update figures from research/state.jsonl data. Use when the user asks to build/compile the paper, check what it looks like, or regenerate a figure/table from current results.
---

# Build the paper

Source lives in `paper/`. Ships with an ICLR template by default (swap for your target venue's
`.sty`/`.bst` — most conferences publish an official LaTeX template on GitHub or their site).

## One-time setup: install tectonic (user-space, no sudo)

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh
mv tectonic ~/.local/bin/   # or wherever's on your $PATH
```
No system LaTeX install needed or wanted — tectonic downloads and caches the packages it needs on
first run (few minutes, needs internet), then works offline.

## Compile

```bash
python3 research/sync_citations.py   # materialize any new `citation` entries into references.bib first
cd paper && tectonic main.tex
```

Output: `main.pdf` in `paper/` — gitignore this (build artifact), regenerate on demand rather than
committing it.

## Adding figures

Put figure-generation scripts in `paper/figures/`, reading directly from `research/state.jsonl`
`result` entries — never hand-transcribe numbers from memory into a plot, always regenerate from
source so a stale number can't silently persist after a re-run changes the underlying result.
Output PNGs/PDFs into `paper/figures/`, reference with `\includegraphics{figures/<name>}`.

## Keeping content honest

`paper/main.tex` should be a **skeleton with TODO markers**, not a draft to fill in freely. Before
writing real prose for a section:
1. Check `research/PAPER_STANDARD.md` — only hypotheses with `paper_track` status
   `candidate`/`promoted` should anchor a claim. If nothing is `promoted` yet, say so in the text
   rather than overclaiming.
2. Pull numbers from `research/state.jsonl` `result` entries or `research/HYPOTHESES_SUMMARY.md`,
   never from a prior draft or from memory of what the number was.
3. Before writing "X beats Y by Zpp" anywhere, run `python3 research/significance.py --id H_N` —
   it computes a Wilson-score CI per data point and flags "likely real" vs "within noise", and for
   multi-seed entries whether the baseline falls inside or outside the seeds' own range. Don't
   eyeball a delta and call it significant.

## Swapping the venue template

When your actual target venue's style files are published, replace the `.sty`/`.bst` in `paper/`,
update the `\usepackage{...}`/`\bibliographystyle{...}` lines in `main.tex`, recompile, and diff
the output against the old version to catch formatting-rule changes (margins, page limit,
anonymity rules do shift between years/venues).
