# chessbot

Motor de ajedrez neuronal, side-project de auto-lab. El pipeline es **destilación de motor (SL)
→ búsqueda MCTS → RL de fine-tuning**. Las razones de cada decisión están en
[`../notes/sota_chess_review.md`](../notes/sota_chess_review.md), y las hipótesis en
[`../research/HYPOTHESES_SUMMARY.md`](../research/HYPOTHESES_SUMMARY.md).

## Instalación

```bash
pip install -r requirements.txt
python -m pytest -q
```

## Flujo

```bash
# 1. Datos (Lichess, CC0). La eval DB trae ~395M posiciones con evaluación de Stockfish.
mkdir -p data && cd data
curl -LO https://database.lichess.org/lichess_db_eval.jsonl.zst
curl -LO https://database.lichess.org/lichess_db_puzzle.csv.zst && unzstd lichess_db_puzzle.csv.zst
cd ..
python -m chessbot.prepare evaldb data/lichess_db_eval.jsonl.zst data/shards/evaldb --limit 50000000
python -m chessbot.prepare evaldb data/lichess_db_eval.jsonl.zst data/shards/evaldb_val --skip 50000000 --limit 200000

# 2. Entrenamiento supervisado (GPU recomendada; CPU solo para smoke tests)
python -m chessbot.train --data data/shards/evaldb --val-data data/shards/evaldb_val \
    --out runs/H1_evaldb_s0 --steps 200000 --batch-size 1024

# 3. Evaluación
python -m chessbot.puzzles --ckpt runs/H1_evaldb_s0/ckpt.pt --csv data/lichess_db_puzzle.csv --limit 10000
python -m chessbot.arena --ckpt runs/H1_evaldb_s0/ckpt.pt --nodes 1 \
    --stockfish $(which stockfish) --sf-elo 2000 --games 200 --pgn-out runs/H1_evaldb_s0/vs_sf2000.pgn

# 4. Motor UCI (cutechess-cli, fastchess, lichess-bot)
python -m chessbot.uci --ckpt runs/H1_evaldb_s0/ckpt.pt --nodes 400
```

## Módulos

| Archivo | Qué hace |
|---|---|
| `encoding.py` | Tablero → 64 tokens (desde la perspectiva de quien mueve) + castling/regla de 50. Jugadas → vocabulario de 1858 (igual que Lc0). Conversión cp → score. |
| `model.py` | Transformer con un token por casilla y sesgo de atención aprendido. Policy head origen→destino (64×64 → 1858) y value head HL-Gauss. |
| `data.py` / `prepare.py` | Lichess eval DB o PGN → shards `.npz` compactos → minibatches. |
| `train.py` | SL: CE de política + pérdida de valor (HL-Gauss o MSE), AdamW con coseno y bf16 en GPU. |
| `search.py` | Política cruda o PUCT MCTS. Sin batching ni Gumbel todavía (ver TODO). |
| `arena.py` | Partidas con aperturas pareadas vs Stockfish (`UCI_Elo`) u otro checkpoint. Reporta Elo con IC95. |
| `puzzles.py` | Accuracy en puzzles de Lichess por tramo de rating. |
| `uci.py` | Front-end UCI. |

## TODO por fase

- **Fase 1:** preparar datos en paralelo (hoy ~6k pos/s por núcleo); targets de política soft
  desde las multi-PV de la eval DB; loader de ChessBench (action-values).
- **Fase 2:** MCTS batcheado con virtual loss, reutilización de árbol y gestión de tiempo.
- **Fase 3:** Gumbel root search (sequential halving), generador de self-play, liga
  (self + checkpoints anteriores + SF@Elo), ancla KL y re-etiquetado con SF (H5–H7).
