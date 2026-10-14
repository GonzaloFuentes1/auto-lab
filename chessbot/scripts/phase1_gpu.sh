#!/usr/bin/env bash
# Phase 1 (SL distillation) on a single GPU. Run from chessbot/.
#   bash scripts/phase1_gpu.sh            # prepare data (once) + train H1 engine-label baseline
# Env overrides: N_TRAIN (positions), STEPS, D_MODEL, N_LAYERS, RUN.
set -euo pipefail
N_TRAIN=${N_TRAIN:-100000000}
STEPS=${STEPS:-300000}
D_MODEL=${D_MODEL:-512}
N_LAYERS=${N_LAYERS:-8}
RUN=${RUN:-runs/H1_evaldb_d${D_MODEL}l${N_LAYERS}_s0}
mkdir -p data

[ -f data/lichess_db_eval.jsonl.zst ] || curl -L -o data/lichess_db_eval.jsonl.zst https://database.lichess.org/lichess_db_eval.jsonl.zst
[ -f data/lichess_db_puzzle.csv ] || { curl -L -o data/lichess_db_puzzle.csv.zst https://database.lichess.org/lichess_db_puzzle.csv.zst && unzstd -f data/lichess_db_puzzle.csv.zst; }

# Data prep is single-process (~6k pos/s/core): split the source into disjoint slices in parallel.
if [ ! -d data/shards/evaldb ]; then
  NPROC=${NPROC:-$(nproc)}
  PER=$(( N_TRAIN / NPROC ))
  for i in $(seq 0 $((NPROC - 1))); do
    python -m chessbot.prepare evaldb data/lichess_db_eval.jsonl.zst data/shards/evaldb_part$i \
      --skip $(( i * PER )) --limit $PER &
  done
  wait
  mkdir -p data/shards/evaldb
  for i in $(seq 0 $((NPROC - 1))); do
    for f in data/shards/evaldb_part$i/shard_*.npz; do mv "$f" "data/shards/evaldb/p${i}_$(basename "$f")"; done
    rmdir data/shards/evaldb_part$i
  done
fi
[ -d data/shards/evaldb_val ] || python -m chessbot.prepare evaldb data/lichess_db_eval.jsonl.zst \
  data/shards/evaldb_val --skip "$N_TRAIN" --limit 200000

python -m chessbot.train --data data/shards/evaldb --val-data data/shards/evaldb_val --out "$RUN" \
  --steps "$STEPS" --batch-size 1024 --lr 3e-4 --d-model "$D_MODEL" --n-layers "$N_LAYERS" --n-heads 8
