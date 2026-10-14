"""Puzzle accuracy on Lichess-format puzzle CSVs (lichess puzzle DB or searchless_chess puzzles.csv).

    python -m chessbot.puzzles --ckpt runs/X/ckpt.pt --csv data/puzzles.csv --limit 10000 --nodes 1

CSV columns used: FEN (position *before* the opponent's setup move), Moves (space-separated UCI;
Moves[0] is the opponent's move, then ours/theirs alternate), Rating. A puzzle counts as solved
only if every one of our moves matches the solution, or delivers mate (lichess accepts any mate).
Puzzle accuracy is a cheap proxy — Miłosz et al. 2026 show it can dissociate from playing Elo, so
never use it as the only metric for a hypothesis.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict

import chess

from .search import Engine, load_engine


def solve(engine: Engine, fen: str, moves: list[str]) -> bool:
    board = chess.Board(fen)
    board.push_uci(moves[0])
    for i in range(1, len(moves), 2):
        mine = engine.play(board)[0]
        board.push(mine)
        if board.is_checkmate():
            return True
        board.pop()
        if mine.uci() != moves[i]:
            return False
        board.push(mine)
        if i + 1 < len(moves):
            board.push_uci(moves[i + 1])
    return True


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--limit", type=int, default=10_000)
    ap.add_argument("--nodes", type=int, default=1)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args(argv)

    engine = load_engine(args.ckpt, args.device, args.nodes)
    by_bucket: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    with open(args.csv, newline="") as fh:
        for i, row in enumerate(csv.DictReader(fh)):
            if i >= args.limit:
                break
            ok = solve(engine, row["FEN"], row["Moves"].split())
            bucket = int(row["Rating"]) // 400 * 400
            by_bucket[bucket][0] += ok
            by_bucket[bucket][1] += 1
    solved = sum(v[0] for v in by_bucket.values())
    total = sum(v[1] for v in by_bucket.values())
    print(json.dumps({"puzzles": total, "accuracy": round(solved / max(total, 1), 4),
                      "by_rating": {f"{k}-{k + 399}": round(v[0] / v[1], 4) for k, v in sorted(by_bucket.items())}}))


if __name__ == "__main__":
    main()
