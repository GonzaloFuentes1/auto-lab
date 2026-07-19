---
name: weekly-journal
description: Close out the research week in notes/journal/<year>/wNN.md using the existing template, pulling experiment/result entries from research/state.jsonl instead of re-deriving them from memory. Use when the user asks to "close the week", write a weekly update, or when you notice the journal has fallen behind actual research activity.
---

# Weekly journal

`notes/journal/_template.md` defines the format — customize it once for your workflow (this
template ships with: What I did / Blockers / Next week / Experiments table / Papers read). Fill a
new `notes/journal/<year>/wNN.md` (ISO week number, Monday–Sunday dates) rather than editing past
entries.

## Gather the week's material cheaply

Don't re-read the whole codebase. Pull from what already tracks activity:

```bash
# Experiment/result/insight entries from the last 7 days
git log --since="7 days ago" --oneline 2>/dev/null
grep -E '"type":"(result|experiment|insight|hypothesis_status)"' research/state.jsonl | tail -50
squeue -u <your-username> --format="%.7i %.8j %.2t %.10M %R"   # or your scheduler's equivalent
```

Cross-reference dates in the JSONL entries (most carry a `date`/`timestamp` field) against the week
window — don't include older entries just because they're near the tail of the file.

## Filling the table

One row per notable experiment, not per job — collapse a training+eval pair into one row.
`Result` should be the headline number/delta, `Run path` the checkpoint or exp_id, so it's
traceable back to the matching `state.jsonl` entry later.

## Before finishing

Check `notes/meetings/` for any meeting since the last journal entry — if there's one without a
corresponding journal entry, surface it so decisions from that meeting aren't lost.

If the last journal entry is more than 2 weeks old, say so explicitly rather than silently writing
one entry that skips the gap — the user may want a condensed multi-week catch-up instead of
pretending only this week happened.
