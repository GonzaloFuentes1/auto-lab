# auto-lab

**A hypothesis-driven research operating system for Claude Code.** Drop it into any empirical
research project — ML, systems, anything with a run→measure→conclude loop — and get an
append-only lab notebook, an autonomous experiment-running agent, statistical-significance
checking, a citation pipeline, and a paper-writing setup that all talk to each other, out of the
box.

Extracted and generalized from a real ML research project (world models for RL). Background on
that origin project, for context only: after about two weeks of daily use its own log held more
than 31 hypotheses, and several "was that actually significant?" moments were caught before they
became paper claims. None of that data is in this repository, which ships an empty log (see
[What ships empty](#what-ships-empty-researchstatejsonl)). Every piece exists because something
went wrong once without it.

## Why

Doing research with an LLM agent in the loop has a token-cost problem: every session either
re-reads your entire experiment history to figure out what's going on, or the agent (and you)
lose track of what's already been tried. `auto-lab` solves this with one rule — **state.jsonl is
the only source of truth, everything else is a cheap, maintained view over it** — plus enough
structure that "confirmed" actually means confirmed, and your related-work section doesn't get
written from memory.

## What's inside

| Piece | What it does |
|---|---|
| `research/state.jsonl` | Append-only lab notebook. One JSON line per hypothesis, result, verdict, insight, or decision. Never edited, only appended — the whole system is built around this being cheap to trust. **Ships as an empty file** (0 bytes); see [below](#what-ships-empty-researchstatejsonl). |
| `research/HYPOTHESES_SUMMARY.md` | The ordered, human-and-agent-readable digest of every hypothesis's current status — read this instead of re-parsing the whole log. **Not shipped**: you create it once you have a few hypotheses, following `research/HYPOTHESES_SUMMARY_HOWTO.md`. |
| `research/PAPER_STANDARD.md` | A **separate, higher** rigor bar for the handful of hypotheses that will actually become paper claims (math formulation, pre-registered prediction, multi-seed/cross-condition validation, one-line claim) — without slowing down the fast loop for everything else. |
| `research/significance.py` | Wilson-score confidence intervals over your results, zero LLM calls. Flags "likely real" vs "within noise" before anyone calls a delta a discovery. |
| `research/sync_citations.py` | Turns `citation` log entries (found during literature-grounding search) into a clean `references.bib`, automatically, deduplicated. |
| `paper/` | LaTeX paper source (ships with an ICLR template as a placeholder — swap for your venue), compiled with [tectonic](https://tectonic-typesetting.github.io/) — no system LaTeX install, no sudo. |
| `paper/FIGURE_STANDARD.md` + `paper/figures/style.py` | A checklist and a shared matplotlib style so figures don't get eyeballed together: vector PDF, a colorblind-safe palette validated (not guessed) against a white print surface, Wilson CI bands instead of bare point estimates, zero-baseline bars. Ships a working example figure. |
| `.claude/agents/autoresearch-template.md` | An autonomous agent that reads the log, checks your compute, launches the next experiment, logs results, grounds new hypotheses against prior literature via web search, and self-paces on a wakeup schedule. Copy, fill in the placeholders, go. |
| `.claude/skills/lab-status` | One command, a compact answer to "what's running and what's the latest result" — never a raw log dump. |
| `.claude/skills/log-finding` | The `state.jsonl` schema, so you (or the agent) never reinvent the format mid-project. |
| `.claude/skills/build-paper` | Compiles the paper, syncs citations first, reminds you to run the significance check before writing a claim. |
| `.claude/skills/weekly-journal` | Closes out a weekly log from the state log instead of from memory. |
| `.claude/skills/paper-vs-code` | Cross-checks a paper's claimed method against its actual released code — catches the gap between what's described and what's implemented, with numerical verification where it's cheap. |

## What ships empty: `research/state.jsonl`

`research/state.jsonl` is committed as a zero-byte file on purpose. It is a template for **your**
lab notebook, not a record of past work: this repository contains no hypotheses, results, or
verdicts, and `research/significance.py` will report "No 'result' entries found" until you append
some. The schema is defined in `.claude/skills/log-finding/SKILL.md`.

The three lines below are **illustrative examples of the format only**. They are invented, they
do not come from any experiment, and they are not in the shipped file.

```jsonl
{"type":"hypothesis","id":"H1","prediction":"+5..10pp success rate at offset 10, because the new cost term penalizes drift"}
{"type":"result","exp_id":"H1_example","env":"example-env","results":{"0":62,"10":58},"deltas_vs_baseline":{"0":2,"10":8},"note":"EXAMPLE ONLY, invented numbers"}
{"type":"hypothesis_status","id":"H1","verdict":"pending","prediction":"+5..10pp success rate at offset 10, because the new cost term penalizes drift"}
```

Here `results` maps an offset (or metric name) to a success rate in percent, and
`deltas_vs_baseline` gives the change in percentage points. Running the significance helper on
those three lines (saved to a scratch file, with the default of 50 trials per offset) prints:

```text
$ python research/significance.py --id H1 --state scratch.jsonl
=== H1: 1 result entry found ===

  exp_id=H1_example  env=example-env  N=50/offset
  offset     SR%           95% CI   Δ vs baseline  verdict
       0    62.0  [ 48.2,  74.1]          +2.0pp  within noise (~2SE)
      10    58.0  [ 44.2,  70.6]          +8.0pp  within noise (~2SE)
```

That output was produced with Python 3.12 on Windows 11 (x86-64) and describes only the invented
numbers above. Note how a +8pp delta at 50 trials still falls within noise, which is the kind of
claim the helper exists to catch. Set `DEFAULT_N` in `significance.py` (or pass `--n`) to match
your real evaluation protocol. On Windows consoles that default to a legacy code page, set
`PYTHONUTF8=1` so the table header prints.

## Install — the easy way

Open Claude Code in your project's directory (new or existing) and paste this:

> Set up [auto-lab](https://github.com/GonzaloFuentes1/auto-lab) in this project. Clone
> `https://github.com/GonzaloFuentes1/auto-lab.git` into a temp directory, then copy its
> `.claude/`, `research/`, `paper/`, `notes/`, `CLAUDE.md.template`, `.gitignore`, and `LICENSE`
> into this project — don't overwrite anything that already exists here, merge instead. Rename
> `CLAUDE.md.template` to `CLAUDE.md` and ask me what to put in each `{{PLACEHOLDER}}` (project
> name, target venue, compute environment — cluster/scheduler or local GPU, etc.) rather than
> guessing. Do the same for `.claude/agents/autoresearch-template.md` — rename it to something
> project-specific and fill in its placeholders from my answers too. Install `tectonic` (for
> compiling `paper/`) if it isn't already on my `$PATH` — no sudo, user-space install. Read
> `research/HYPOTHESES_SUMMARY_HOWTO.md` and help me design a hypothesis taxonomy for my actual
> project instead of copying the example one literally. Finish by appending a `session` entry to
> `research/state.jsonl` describing this setup.

Claude Code will clone it, ask you the placeholder questions instead of guessing, and leave you
with a working setup — no manual file surgery required.

## Manual install

```bash
git clone https://github.com/GonzaloFuentes1/auto-lab.git my-project
cd my-project
rm -rf .git && git init   # start your own history

# 1. Fill in the project-level config
mv CLAUDE.md.template CLAUDE.md
# edit CLAUDE.md: fill in every {{PLACEHOLDER}} — project name, venue, compute setup

# 2. Point Claude Code at the skills and agent
#    (Claude Code auto-discovers .claude/skills/ in the repo; for the agent,
#    copy it to your global agents directory and fill in its placeholders too)
cp .claude/agents/autoresearch-template.md ~/.claude/agents/autoresearch-my-project.md
# edit that file: fill in every {{PLACEHOLDER}}

# 3. Design your own hypothesis taxonomy (don't skip this — see the HOWTO)
cat research/HYPOTHESES_SUMMARY_HOWTO.md

# 4. Set up the paper toolchain (one-time, no sudo)
curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh
mv tectonic ~/.local/bin/

# 5. Start logging
echo '{"type":"session","timestamp":"'$(date -Iseconds)'","note":"kickoff"}' >> research/state.jsonl
```

Then just work with Claude Code normally — invoke `/lab-status`, `/log-finding`, `/build-paper`,
`/paper-vs-code`, or launch your copied autonomous agent to run in the background.

## Design principles

1. **One source of truth.** Everything else — summaries, memory, the paper draft — is a view over
   `state.jsonl`, regenerated or kept in sync, never a second place to maintain by hand.
2. **Register the prediction before you see the result.** The schema makes this the path of least
   resistance, not an afterthought.
3. **A fast loop stays fast.** The paper-track rigor gate is opt-in and separate, precisely so that
   testing 30 hypotheses in two weeks stays possible.
4. **No unverified deltas.** `significance.py` exists because "eyeballing a table" produced a real
   false rejection in the project this was extracted from — corrected minutes later, but only by
   luck of someone double-checking.
5. **IDs are permanent, categories are a second axis.** Renumbering breaks traceability across
   logs, configs, and checkpoints — so hypothesis IDs never change once assigned. A taxonomy you
   design for your own project (see `research/HYPOTHESES_SUMMARY_HOWTO.md`) gives you the
   "what kind of thing is this" view without touching the IDs.

## License

MIT — see `LICENSE`. Take it, fork it, rip pieces out.
