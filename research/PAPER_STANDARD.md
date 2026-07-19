# Paper-track standard

A separate, deliberately **higher bar** than the normal hypothesis loop (see root `CLAUDE.md`
methodology and the `log-finding` skill). Most tracked hypotheses never need this — they're fast
falsifiable checks and most get rejected, which is fine and expected. This checklist only applies
to the small subset that will actually appear as a claim/table/figure in the paper. Promoting
something here is a deliberate act, not automatic on `verdict:confirmed`.

## Why a separate gate

Requiring math + full validation on every hypothesis kills the iteration speed that makes this
whole system worth using. The fast loop stays fast. This gate exists so that by the time you sit
down to write the paper, the handful of headline results already have everything a reviewer will
ask for, instead of discovering the gap at write-up time.

## Checklist to promote a hypothesis to paper-track

All four required before `status: promoted`:

1. **Mechanistic/mathematical formulation** — not necessarily a formal theorem, but a precise,
   falsifiable statement of *why* the effect should happen, written down somewhere durable (e.g.
   a `math_notes.md`) under a heading matching the current hypothesis ID. If your project has
   renumbered or reorganized hypothesis IDs at some point, verify an existing section is actually
   about the hypothesis you think it is before trusting it — don't assume a matching heading means
   matching content.
2. **Falsifiable prediction, logged before results** — already required by the base methodology
   (`{"type":"hypothesis","id":"H_N","prediction":"..."}`), just confirm it's actually there and
   was quantitative, not vague.
3. **Empirical validation beyond the first result** — multi-seed and/or cross-condition, per
   what's appropriate for the claim. A single-run, single-condition result is not paper-track
   regardless of effect size. Run `python3 research/significance.py --id H_N` and attach the
   verdict — a delta the script flags "within noise" doesn't clear this bar no matter how good the
   headline number looks.
4. **One-line paper claim** — the exact sentence/number that would go in a table or abstract,
   stated precisely enough that it's falsifiable by a reviewer re-running the eval.

## Schema — `state.jsonl` entry type

```json
{"type":"paper_track","id":"H_N","status":"candidate|promoted|blocked","checklist":{"math":true,"prediction":true,"validation":false,"claim":true},"claim":"one-line paper claim","blocked_on":"what's missing, if status=blocked","date":"YYYY-MM-DD"}
```

Log this via the `log-finding` skill's conventions (validate JSON before appending). Update
`research/HYPOTHESES_SUMMARY.md`'s row for that hypothesis with a 📄 marker when `status` becomes
`promoted`.

## A lesson learned building this pattern the first time (le-wm project)

Two of that project's most-cited headline numbers turned out to only exist as narrative asides
inside *other* hypotheses' comparison entries — not as their own standalone `result` entry in
`state.jsonl`. Nobody noticed until this checklist forced someone to go looking for the source.
**Log a standalone `result` entry for a hypothesis's own baseline case even if it feels redundant
with a comparison entry that already mentions the number** — future-you (or future-agent) will go
looking for exactly that entry and not find it otherwise.
