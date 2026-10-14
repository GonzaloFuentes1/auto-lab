# chessbot (auto-lab side project)

A neural chess engine built as engine distillation (supervised on Stockfish-labelled positions)
→ MCTS search → bounded RL fine-tuning (Gumbel expert iteration + KL anchor). The research angle
is **Elo per FLOP** and **whether cheap RL can beat its teacher**, not out-muscling Stockfish.
Target venue: TBD (arXiv / games-and-search workshop; decide once phase-2 numbers exist).
Compute: **TODO — not decided yet** (CPU is only good for smoke tests; phase 1 needs a GPU).

Background and rationale for every design choice: `notes/sota_chess_review.md` (read this
before proposing a new direction; it is the literature grounding for H1–H7).

## Orientation — what's what

| Directory | Status | Notes |
|---|---|---|
| `chessbot/` | **ACTIVE** | Python package + tests. `chessbot/chessbot/{encoding,model,data,train,search,uci,arena,puzzles,prepare}.py`. Data/checkpoints go in `chessbot/data/`, `chessbot/runs/` (git-ignored). |
| `research/` | active | `state.jsonl` (append-only lab notebook), `HYPOTHESES_SUMMARY.md` (ordered digest), `PAPER_STANDARD.md` (rigor gate for paper claims), `significance.py`/`sync_citations.py` (deterministic helpers). |
| `paper/` | active | LaTeX source, compiled with `tectonic` (see `build-paper` skill). |
| `notes/` | active | `journal/` (weekly log), `meetings/`. |

<!-- Add rows here for any deprecated/legacy directories as your project accumulates them, with an
explicit instruction not to explore them without being asked — this saved real token budget in
practice (see the auto-lab README for why). -->

## Research methodology

This project uses an **append-only lab-notebook pattern** in `research/state.jsonl`. Don't invent
a different bookkeeping scheme — this one is deliberately chosen to keep hypothesis-testing
honest and cheap to resume across sessions.

**The cycle:**
1. **Hypothesis** — formulate a quantitative, falsifiable prediction BEFORE running the
   experiment. Log: `{"type":"hypothesis","id":"H_N","prediction":"..."}`. Define the
   success/failure criterion before seeing results — this is what prevents post-hoc narrative.
2. **Experiment** — run it, always logging enough to reconstruct what was actually varied.
3. **Result** — `{"type":"result","exp_id":...,"results":{...},"deltas_vs_baseline":{...},"note":"..."}`.
4. **Verdict** — `{"type":"hypothesis_status","id":"H_N","verdict":"confirmed|rejected|pending",...}`,
   compared against the criterion from step 1, not against what would have been a nicer finding.
   Before calling a close call "confirmed", run `python3 research/significance.py --id H_N`.
5. **Insight** — when a pattern crystallizes across ≥2 experiments, log
   `{"type":"insight",...}` with the mechanistic explanation. This is what becomes a paper section.
6. **Be reactive** — the next experiment's priority comes from what's `pending` in the most recent
   `hypothesis_status` entries, not from a fixed list written a week ago. Don't hardcode "next
   steps" anywhere except `state.jsonl` — it goes stale immediately.

**Start of session**: log `{"type":"session","timestamp":...,"note":"this session's focus"}` — cheap,
and lets a future session (or an autonomous agent) resume without re-reading everything.

**Big findings** (a verdict that redirects the project's direction) should also land in your
persistent Claude memory (`project_<name>.md`), not just `state.jsonl` — the log is append-only
and grows past what's cheap to re-read every session.

**Paper-track**: hypotheses that will actually appear in the paper go through a separate, higher
bar — see `research/PAPER_STANDARD.md`. Most hypotheses never need this; it exists so the fast
loop above stays fast.

**Weekly journal**: use the `weekly-journal` skill to close out `notes/journal/wNN.md` from
`state.jsonl` instead of writing it from memory.

## Rules for minimizing token consumption

- **Never** `cat` a full log. Use `tail -n 50` or `grep` for the specific metric.
- **Never** do an unfiltered recursive `ls`/`find`/glob inside a deprecated/legacy directory once
  you have one — point at the exact file you need.
- To check experiment status, read `research/state.jsonl` with `tail -N`/`grep '"type":"X"'`, not
  the whole file. For the full hypothesis verdict table, read `research/HYPOTHESES_SUMMARY.md`
  instead of parsing the jsonl.
- For open-ended codebase exploration, delegate to a read-only search subagent rather than
  chaining `find`/`grep` manually in the main session.
- Before re-deriving something ("what's already been tried?"), check `state.jsonl` and persistent
  memory first — cheaper than reconstructing it from raw logs.
- Use the `lab-status` skill for a condensed compute+progress snapshot instead of manually
  chaining scheduler/GPU/log commands.

## Compute cheatsheet

```bash
cd chessbot && pip install -r requirements.txt && python -m pytest -q   # 8 tests, ~10s on CPU

# data (lichess, CC0) -> shards. Use disjoint slices for train/val (--skip).
python -m chessbot.prepare evaldb lichess_db_eval.jsonl.zst data/shards/evaldb --limit 50000000
# train / evaluate / play
python -m chessbot.train --data data/shards/evaldb --val-data data/shards/evaldb_val --out runs/<exp_id>
python -m chessbot.puzzles --ckpt runs/<exp_id>/ckpt.pt --csv data/lichess_db_puzzle.csv --limit 10000
python -m chessbot.arena --ckpt runs/<exp_id>/ckpt.pt --nodes 1 --stockfish $(which stockfish) --sf-elo 2000 --games 200
python -m chessbot.uci --ckpt runs/<exp_id>/ckpt.pt --nodes 400        # for cutechess / lichess-bot

# TODO compute: queue status / GPU check commands once the compute environment is decided
nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader
```

**Evaluation protocol (don't deviate without a decision_log entry):** playing strength is
measured with `chessbot.arena` (paired openings, Elo diff with 95% CI) — vs the Stockfish
`UCI_Elo` ladder for absolute numbers, checkpoint-vs-checkpoint for A/B hypotheses. Puzzle accuracy
is a secondary, cheap metric only: it can dissociate from Elo (Miłosz et al. 2026). Never confirm
a hypothesis on puzzles alone, and never compare Elo numbers across different ladders (engine
ladder vs Lichess-human ratings). `research/significance.py` assumes binary success rates; for
match results use the Elo CI printed by `arena.py`.

## Skills installed (`.claude/skills/`)

- **lab-status** — cheap snapshot of compute + experiment progress, no full log dumps.
- **log-finding** — schema templates for `state.jsonl` so you don't reinvent the format.
- **weekly-journal** — closes the week from `state.jsonl` instead of memory.
- **build-paper** — compiles `paper/` with `tectonic`, figure-generation convention.
- **paper-vs-code** — cross-checks a paper's claims against its released implementation before you
  build on it or cite it.

## Paper writing

`paper/` — LaTeX source (ships with an ICLR template as a placeholder, swap for your actual
venue). Compile with `tectonic` (user-space, no sudo — see `build-paper` skill). Section skeleton
in `main.tex` has TODO markers pointing at the exact source for each piece
(`research/HYPOTHESES_SUMMARY.md`, `PAPER_STANDARD.md`, `state.jsonl`) — not prose to fill freely.

## Autonomous research agent

`.claude/agents/autoresearch-template.md` is a template for an autonomous agent that reads
`research/state.jsonl`, checks compute availability, launches the next highest-priority
experiment, logs results, grounds new hypotheses against prior literature via web search, and
self-paces with a wakeup schedule. Copy it to `~/.claude/agents/autoresearch-chessbot.md`
and fill in its placeholders (compute paths are still TODO) before use.
