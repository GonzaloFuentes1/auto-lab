---
name: log-finding
description: Append a properly-schematized entry to this project's research/state.jsonl (hypothesis, result, insight, hypothesis_status, session, decision_log, paper_track, citation). Use whenever a hypothesis is proposed, an experiment finishes, a pattern crystallizes across experiments, or a research session starts/ends — enforces hypothesis-driven methodology instead of ad hoc notes.
---

# Log a research finding

`research/state.jsonl` is the append-only lab notebook for this project — always relative to repo
root, run from wherever, don't hardcode an absolute path. It is the source of truth — don't keep
parallel bookkeeping in chat, memory, or hardcoded lists inside agent prompts. Append one JSON
object per line, matching the existing schema below.

## Core rule: define the discovery criterion BEFORE you see the result

When registering a new hypothesis, write the falsifiable prediction first:
```json
{"type":"hypothesis","id":"H_N","prediction":"+5..10pp at <metric>, because <mechanism>"}
```
Only after the experiment finishes, compare the actual result against *that* prediction — not
against what would have been a nice story. This is what separates hypothesis-testing from
post-hoc narrative.

## Schema — use the existing `type` values, don't invent new ones without reason

```json
{"type":"session","timestamp":"ISO8601","note":"focus of this session"}
{"type":"hypothesis","id":"H_N","prediction":"quantitative, falsifiable","prior_art":"optional — close prior work found via web search before registering, if any"}
{"type":"experiment","id":"...","name":"...","ckpt":"...","epoch":N,"status":"running|done","results":{"<offset_or_metric>":value,...}}
{"type":"result","exp_id":"...","env":"...","results":{...},"deltas_vs_baseline":{...},"note":"interpretation"}
{"type":"hypothesis_status","id":"H_N","verdict":"pending|confirmed|rejected","prediction":"restate it"}
{"type":"insight","id":"...","text":"mechanistic explanation once a pattern is clear across experiments","date":"YYYY-MM-DD"}
{"type":"decision_log","entry":"ISO8601","decision":"...","reason":"..."}
{"type":"watcher","exp_id":"...","watcher_pid":N,"gpu":N,"note":"what it's waiting for and ETA"}
{"type":"paper_track","id":"H_N","status":"candidate|promoted|blocked","checklist":{"math":bool,"prediction":bool,"validation":bool,"claim":bool},"claim":"one-line paper claim","blocked_on":"what's missing, if blocked","date":"YYYY-MM-DD"}
{"type":"citation","key":"author2022shortname","bibtex":"@inproceedings{author2022shortname, ...}","found_for":"H_N","date":"YYYY-MM-DD"}
```

`paper_track` is a **separate, higher bar** than `hypothesis_status:confirmed` — see
`research/PAPER_STANDARD.md`. Only log it when deliberately evaluating a confirmed hypothesis for
inclusion in the paper, not automatically on every confirmation. Most hypotheses never need one.

`citation` is logged whenever web search (at hypothesis-registration time, per the autonomous
research agent's literature-grounding step — see `.claude/agents/`) turns up prior art worth
citing. `key` must be a valid BibTeX citekey (author+year+shortname, no spaces/special chars) —
it's what gets referenced in the hypothesis's `prior_art` field and later in `paper/main.tex` as
`\citep{key}`. Run `research/sync_citations.py` to materialize all logged `citation` entries into
`paper/references.bib` (dedups by key, idempotent, safe to run repeatedly).

## Appending

```bash
echo '{"type":"result","exp_id":"...","env":"...","results":{...},"note":"..."}' \
  >> research/state.jsonl
```

Validate it's well-formed JSON before appending (a broken line breaks every future `tail`/`grep -c`
pass over the file):
```bash
python3 -c "import json,sys; json.loads(sys.argv[1])" '<the line>'
```

## Keep the cheap summary in sync — do this every time you log `hypothesis_status`

`research/HYPOTHESES_SUMMARY.md` (create it the first time you have ≥3-4 hypotheses worth
tracking — see `research/HYPOTHESES_SUMMARY_HOWTO.md` for the format) is the maintained,
low-token digest of every hypothesis, grouped by a taxonomy you define for your own project (see
the HOWTO). It exists so future sessions/subagents read one short file instead of grepping the
whole `state.jsonl`. Whenever you append a `hypothesis_status` entry:
1. Update that hypothesis's row in `HYPOTHESES_SUMMARY.md` (verdict + one-line result).
2. If it's a genuinely new ID, add a row under the closest taxonomy category.
Skipping this is what makes the summary drift and forces the next session back into a full jsonl
parse — the whole point of the table is to avoid that.

## When a finding is big enough to matter beyond this session

If a `hypothesis_status` flips to `confirmed`/`rejected` in a way that changes the paper's
direction (not just another data point), also update your persistent Claude memory (a
`project_<name>.md` memory file) — `state.jsonl` is append-only and grows past what's cheap to
re-read every session; memory should carry forward only the conclusions that survived, not the
full trail.

## Starting/ending a session

At the start, append a `session` entry stating what this session is focusing on. This is cheap
and lets a future session or an autonomous research agent pick up context without re-deriving it
from potentially hundreds of lines of history.
