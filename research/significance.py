#!/usr/bin/env python3
"""
Wilson-score significance helper over research/state.jsonl `result` entries.

Deterministic, stdlib-only, no LLM call needed -- this is exactly the kind of
report that should be computed once and read, not re-derived by eyeballing
deltas in a jsonl note by hand (easy to make exactly the kind of copy-paste
mistake this script exists to catch).

Assumes a binary success-rate metric (successes/N trials) per data point --
the common case for eval-episode success rates. If your metric isn't a
proportion, this Wilson-CI approach doesn't directly apply; adapt or replace
`wilson_ci()`.

Usage:
    python3 research/significance.py --id H12
    python3 research/significance.py --id H12 --env <env>
    python3 research/significance.py --id H12 --n 50   # override trial count per data point

Handles both result shapes:
  (a) flat:   {"results": {"<offset_or_metric>": SR, ...}, "deltas_vs_baseline": {...}}
  (b) seeded: {"results": {"seed1": {"<offset>": SR, ...}, ...}, "means": {...}}
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

DEFAULT_STATE = Path(__file__).parent / "state.jsonl"
DEFAULT_N = 50  # trials per data point -- SET THIS to your actual eval protocol's N


def wilson_ci(successes_pct, n, z=1.96):
    """95% Wilson score interval for a success rate given as a percentage."""
    p = successes_pct / 100.0
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return max(0.0, (center - half) * 100), min(100.0, (center + half) * 100)


def load_results(state_path, hyp_id, env=None):
    entries = []
    with open(state_path) as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                print(f"warning: skipping malformed line {lineno}", file=sys.stderr)
                continue
            if obj.get("type") != "result":
                continue
            exp_id = str(obj.get("exp_id", ""))
            # word-boundary match on exp_id -- a naive substring check would let "H27" match
            # inside "H7H27_combo" (a DIFFERENT hypothesis), silently mixing in the wrong data.
            exp_id_matches = re.search(rf"(?<![A-Za-z0-9]){re.escape(hyp_id)}(?![A-Za-z0-9])", exp_id)
            if obj.get("hypothesis") != hyp_id and not exp_id_matches:
                continue
            if env and obj.get("env") and obj.get("env") != env:
                continue
            entries.append(obj)
    return entries


def is_seeded(results):
    return bool(results) and all(
        isinstance(v, dict) for v in results.values()
    ) and all(k.startswith("seed") for k in results.keys())


def report_flat(entry, n):
    results = entry.get("results", {})
    deltas = entry.get("deltas_vs_baseline", {})
    print(f"  exp_id={entry.get('exp_id', '?')}  env={entry.get('env', '?')}  N={n}/offset")
    print(f"  {'offset':>6}  {'SR%':>6}  {'95% CI':>15}  {'Δ vs baseline':>14}  verdict")
    for offset, sr in sorted(results.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0):
        lo, hi = wilson_ci(sr, n)
        delta = deltas.get(offset)
        se_delta = math.sqrt(2) * math.sqrt((sr / 100) * (1 - sr / 100) / n) * 100
        if delta is not None:
            verdict = "likely real" if abs(delta) > 2 * se_delta else "within noise (~2SE)"
            delta_str = f"{delta:+.1f}pp"
        else:
            verdict = "-"
            delta_str = "-"
        print(f"  {offset:>6}  {sr:>6.1f}  [{lo:5.1f}, {hi:5.1f}]  {delta_str:>14}  {verdict}")


def report_seeded(entry, n):
    results = entry.get("results", {})
    means = entry.get("means", {})
    print(f"  exp_id={entry.get('exp_id', '?')}  env={entry.get('env', '?')}  N={n}/offset/seed")
    print(f"  Per-seed means: " + ", ".join(f"{k}={v:.1f}" for k, v in means.items()))
    baseline_mean = means.get("baseline")
    seed_means = [v for k, v in means.items() if k != "baseline"]
    if baseline_mean is not None and seed_means:
        lo_of_seeds, hi_of_seeds = min(seed_means), max(seed_means)
        # crude but honest: does baseline fall inside the spread the seeds actually produced?
        if lo_of_seeds <= baseline_mean <= hi_of_seeds:
            print(f"  -> baseline ({baseline_mean:.1f}) falls INSIDE the seed range "
                  f"[{lo_of_seeds:.1f}, {hi_of_seeds:.1f}] -- effect is NOT robust across seeds.")
        else:
            print(f"  -> baseline ({baseline_mean:.1f}) falls OUTSIDE the seed range "
                  f"[{lo_of_seeds:.1f}, {hi_of_seeds:.1f}] -- effect looks robust across seeds.")
    print()
    for seed, offsets in results.items():
        print(f"  [{seed}]")
        for offset, sr in sorted(offsets.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0):
            lo, hi = wilson_ci(sr, n)
            print(f"    {offset:>6}  {sr:>6.1f}  [{lo:5.1f}, {hi:5.1f}]")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True, help="hypothesis ID, e.g. H37")
    ap.add_argument("--env", default=None, help="restrict to one env (tworoom/pusht/reacher/cube)")
    ap.add_argument("--n", type=int, default=DEFAULT_N, help=f"episodes per offset (default {DEFAULT_N})")
    ap.add_argument("--state", default=str(DEFAULT_STATE), help="path to state.jsonl")
    args = ap.parse_args()

    entries = load_results(args.state, args.id, args.env)
    if not entries:
        print(f"No 'result' entries found for {args.id}" + (f" (env={args.env})" if args.env else ""))
        sys.exit(1)

    print(f"=== {args.id}: {len(entries)} result entr{'y' if len(entries)==1 else 'ies'} found ===\n")
    for entry in entries:
        results = entry.get("results", {})
        if is_seeded(results):
            report_seeded(entry, args.n)
        else:
            report_flat(entry, args.n)
        print()


if __name__ == "__main__":
    main()
