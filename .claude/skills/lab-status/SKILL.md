---
name: lab-status
description: Cheap, token-minimal snapshot of everything running in this research setup — cluster jobs, local GPU processes, and recent experiment results. Use instead of manually chaining job-queue/GPU/log commands when the user asks "what's running" or at the start of a research session.
---

# Lab status

Goal: answer "what's the state of my experiments right now" using the **fewest tokens possible** —
condensed commands only, never full log dumps.

**Customize the commands in this file for your actual compute environment** (SLURM/PBS/local
GPUs/cloud) — the structure below is the pattern, not literal commands to copy-paste. Fill in your
cluster's queue command, partition name, and username once, then this file stays correct.

## Do this, in order, and summarize — don't paste raw output verbatim unless asked

### 1. Cluster/scheduler jobs (if applicable)
```bash
squeue -u <your-username> --format="%.7i %.8j %.2t %.10M %R"   # SLURM example — swap for your scheduler
```
Jobs may run both via the scheduler **and** directly on local GPUs — the scheduler alone doesn't
tell the whole story if you also launch things with `nohup`/`disown` directly.

### 2. Local GPU processes (not managed by the scheduler)
```bash
nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader
pgrep -af "python.*(train|eval|finetune)" 2>/dev/null
```

### 3. Progress markers (nohup'd background scripts write these)
```bash
tail -n 3 /tmp/*_progress.txt 2>/dev/null
```

### 4. Last known state from the research log — tail, never full read
```bash
tail -n 20 research/state.jsonl
```
For a **complete verdict table across all hypotheses**, read `research/HYPOTHESES_SUMMARY.md`
instead of parsing the whole jsonl — it's a maintained, ordered digest kept in sync at write-time
(see the `log-finding` skill). Only fall back to reading the full `state.jsonl` if the user needs
the raw trail behind a specific entry, or the summary looks stale relative to the last `tail`.

### 5. New results not yet logged (only if step 4 looks stale)
Grep the metric, never cat the log:
```bash
grep -l "success_rate" logs/*.log 2>/dev/null | \
  xargs -I{} sh -c 'echo {}; grep -o "success_rate.: [0-9.]*" {} | tail -1'
```

## Report format

Give a compact summary: running/pending jobs (name + state + elapsed), free vs busy GPUs, and
the most recent 1-3 `hypothesis_status`/`insight` entries from `state.jsonl`. Flag anything that
looks like a discovery criterion being met (see thresholds logged as `hypothesis` predictions).
Skip sections with nothing to report instead of printing empty output.
