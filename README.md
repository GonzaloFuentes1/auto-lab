# auto-lab

**A hypothesis-driven research operating system for Claude Code.** Drop it into any empirical
research project — ML, systems, anything with a run→measure→conclude loop — and get an
append-only lab notebook, an autonomous experiment-running agent, statistical-significance
checking, a citation pipeline, and a paper-writing setup that all talk to each other, out of the
box.

Extracted and generalized from a real ML research project (world models for RL) after ~two weeks
of actual daily use — 31+ hypotheses tracked, several rounds of "wait, was that actually
significant?" caught before they became embarrassing paper claims. This isn't a designed-in-a-
vacuum template; every piece exists because something went wrong once without it.

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
| `research/state.jsonl` | Append-only lab notebook. One JSON line per hypothesis, result, verdict, insight, or decision. Never edited, only appended — the whole system is built around this being cheap to trust. |
| `research/HYPOTHESES_SUMMARY.md` | The ordered, human-and-agent-readable digest of every hypothesis's current status — read this instead of re-parsing the whole log. |
| `research/PAPER_STANDARD.md` | A **separate, higher** rigor bar for the handful of hypotheses that will actually become paper claims (math formulation, pre-registered prediction, multi-seed/cross-condition validation, one-line claim) — without slowing down the fast loop for everything else. |
| `research/significance.py` | Wilson-score confidence intervals over your results, zero LLM calls. Flags "likely real" vs "within noise" before anyone calls a delta a discovery. |
| `research/sync_citations.py` | Turns `citation` log entries (found during literature-grounding search) into a clean `references.bib`, automatically, deduplicated. |
| `paper/` | LaTeX paper source (ships with an ICLR template as a placeholder — swap for your venue), compiled with [tectonic](https://tectonic-typesetting.github.io/) — no system LaTeX install, no sudo. |
| `.claude/agents/autoresearch-template.md` | An autonomous agent that reads the log, checks your compute, launches the next experiment, logs results, grounds new hypotheses against prior literature via web search, and self-paces on a wakeup schedule. Copy, fill in the placeholders, go. |
| `.claude/skills/lab-status` | One command, a compact answer to "what's running and what's the latest result" — never a raw log dump. |
| `.claude/skills/log-finding` | The `state.jsonl` schema, so you (or the agent) never reinvent the format mid-project. |
| `.claude/skills/build-paper` | Compiles the paper, syncs citations first, reminds you to run the significance check before writing a claim. |
| `.claude/skills/weekly-journal` | Closes out a weekly log from the state log instead of from memory. |
| `.claude/skills/paper-vs-code` | Cross-checks a paper's claimed method against its actual released code — catches the gap between what's described and what's implemented, with numerical verification where it's cheap. |

## Quickstart

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
