# How to build research/HYPOTHESES_SUMMARY.md

This file doesn't exist yet in a fresh project — create it once you have roughly 3-4 hypotheses
worth tracking (before that, `state.jsonl` alone is cheap enough to read directly). Delete this
HOWTO once you've made the real file, or keep it for reference — up to you.

## What it's for

A single, ordered, low-token digest of every hypothesis's current status — so a future session or
subagent reads one short file instead of grepping a growing `state.jsonl`. It's a **derived view**,
not a second source of truth: `state.jsonl` is authoritative, this file is a maintained cache of
its conclusions. See the `log-finding` skill's "keep the cheap summary in sync" section for the
write-time discipline that keeps it from going stale.

## Design your own taxonomy — don't skip this step

The historical hypothesis IDs (`H1`, `H2`, ...) should stay put once assigned — they get baked into
config filenames, checkpoint names, and `state.jsonl` entries, so renumbering breaks traceability.
But raw sequential IDs don't tell you *what kind* of change each hypothesis tests, which makes the
table hard to scan once you have 20+ entries. Add a **second axis**: a small set of categories
specific to your project's actual axes of variation.

Example from the le-wm project (a world-model RL project) — **don't copy this literally, design
your own**, this is just to show the shape:

| Code | Category | What it tested |
|---|---|---|
| DIST | Distance/cost function | Alternative planning costs |
| REG | Predictor regularization | Loss/architecture constraints on one component |
| REP | Representation structure | Questions about the learned embedding itself |
| SWEEP | Hyperparameter sweep | Systematic parameter variation, same architecture |
| DIAG | Diagnostic/analysis | No training — measures a property of existing artifacts |
| LEGACY | Closed phases | Earlier project phases, archived, kept for the historical record |

For a different kind of project (say, a systems/networking paper, or a vision model), your
categories would be entirely different — e.g. `ARCH` (architecture changes), `DATA` (data/training
distribution changes), `ABLATION`, `BASELINE-COMPARISON`, `SCALE` (model/data scaling). Pick 4-7
categories that actually partition how your hypotheses vary, not a generic list.

## Table format

```markdown
| ID | Cat | Name | Verdict | Result |
|---|---|---|---|---|
| H1 | CATX1 | Short name | CONFIRMED / REJECTED / PENDING | One-line result with the key number(s) |
```

Group by category (one section per taxonomy code), each with its own small table. Add a taxonomy
legend near the top (see the example table above) so a reader who's never seen this project can
still parse the categories in 10 seconds.

Mark paper-track candidates with 📄 (see `research/PAPER_STANDARD.md`) directly in the ID column.

## Keep it honest

When you build this the first time, cross-check every "confirmed" claim against
`research/significance.py` and the actual `result` entries — don't transcribe verdicts from memory
or from old chat summaries. It's common to find a headline number that turns out to only exist as
a narrative aside in a different entry (see the lesson documented in `PAPER_STANDARD.md`) — that's
worth fixing (log a proper standalone `result` entry) rather than perpetuating.
