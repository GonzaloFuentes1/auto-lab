"""Play matches and report score + Elo difference with a 95% CI.

Calibrated opponent ladder (main Elo yardstick, cheap and reproducible):
    python -m chessbot.arena --ckpt runs/X/ckpt.pt --nodes 1 \
        --stockfish /path/to/stockfish --sf-elo 2000 --games 200 --movetime-ms 100
Stockfish's UCI_LimitStrength/UCI_Elo is calibrated to CCRL 40/4 Elo (range ~1320-3190).

Checkpoint vs checkpoint (A/B for hypotheses):
    python -m chessbot.arena --ckpt runs/A/ckpt.pt --opp-ckpt runs/B/ckpt.pt --games 400

Games use paired openings (each opening played with both colors) to cancel opening bias.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import chess
import chess.engine
import chess.pgn

from .search import Engine, load_engine

# Short, balanced, commonly played opening lines (UCI). Paired: each one is played twice.
OPENINGS = [
    "e2e4 e7e5 g1f3 b8c6", "e2e4 c7c5 g1f3 d7d6", "e2e4 c7c5 g1f3 b8c6", "e2e4 e7e6 d2d4 d7d5",
    "e2e4 c7c6 d2d4 d7d5", "d2d4 d7d5 c2c4 e7e6", "d2d4 d7d5 c2c4 c7c6", "d2d4 g8f6 c2c4 e7e6",
    "d2d4 g8f6 c2c4 g7g6", "c2c4 e7e5 b1c3 g8f6", "g1f3 d7d5 g2g3 g8f6", "e2e4 d7d6 d2d4 g8f6",
    "e2e4 g7g6 d2d4 f8g7", "d2d4 f7f5 g2g3 g8f6", "e2e4 e7e5 f1c4 g8f6", "c2c4 c7c5 g1f3 g8f6",
    "e2e4 c7c5 b1c3 b8c6", "d2d4 g8f6 g1f3 e7e6", "e2e4 d7d5 e4d5 d8d5", "d2d4 d7d5 g1f3 g8f6",
]


class Player:
    def __init__(self, name: str, engine: Engine | None = None, uci: chess.engine.SimpleEngine | None = None,
                 limit: chess.engine.Limit | None = None):
        self.name, self.engine, self.uci, self.limit = name, engine, uci, limit

    def move(self, board: chess.Board) -> chess.Move:
        if self.engine is not None:
            return self.engine.play(board)[0]
        return self.uci.play(board, self.limit).move


def play_game(white: Player, black: Player, opening: str, max_plies: int = 400) -> chess.pgn.Game:
    board = chess.Board()
    for uci in opening.split():
        board.push_uci(uci)
    while not board.is_game_over(claim_draw=True) and board.ply() < max_plies:
        board.push((white if board.turn == chess.WHITE else black).move(board))
    game = chess.pgn.Game.from_board(board)
    game.headers.update({"White": white.name, "Black": black.name})
    if not board.is_game_over(claim_draw=True):
        game.headers["Result"] = "1/2-1/2"  # adjudicated at max_plies
    else:
        game.headers["Result"] = board.result(claim_draw=True)
    return game


def elo_with_ci(wins: int, draws: int, losses: int) -> dict:
    n = wins + draws + losses
    s = (wins + 0.5 * draws) / n
    var = (wins * (1 - s) ** 2 + draws * (0.5 - s) ** 2 + losses * s ** 2) / n
    se = math.sqrt(var / n)

    def to_elo(x: float) -> float:
        x = min(max(x, 1e-4), 1 - 1e-4)
        return -400 * math.log10(1 / x - 1)

    return {"games": n, "w": wins, "d": draws, "l": losses, "score": round(s, 4),
            "elo_diff": round(to_elo(s), 1), "elo_ci95": [round(to_elo(s - 1.96 * se), 1), round(to_elo(s + 1.96 * se), 1)]}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--nodes", type=int, default=1)
    ap.add_argument("--opp-ckpt")
    ap.add_argument("--opp-nodes", type=int, default=1)
    ap.add_argument("--stockfish")
    ap.add_argument("--sf-elo", type=int, help="UCI_Elo for a strength-limited Stockfish opponent")
    ap.add_argument("--movetime-ms", type=int, default=100, help="Stockfish think time per move")
    ap.add_argument("--games", type=int, default=100)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--pgn-out")
    args = ap.parse_args(argv)

    me = Player(f"chessbot@{args.nodes}", engine=load_engine(args.ckpt, args.device, args.nodes))
    sf = None
    if args.opp_ckpt:
        opp = Player(f"opp@{args.opp_nodes}", engine=load_engine(args.opp_ckpt, args.device, args.opp_nodes))
    elif args.stockfish:
        sf = chess.engine.SimpleEngine.popen_uci(args.stockfish)
        name = "stockfish"
        if args.sf_elo:
            sf.configure({"UCI_LimitStrength": True, "UCI_Elo": args.sf_elo})
            name += f"@{args.sf_elo}"
        opp = Player(name, uci=sf, limit=chess.engine.Limit(time=args.movetime_ms / 1000))
    else:
        ap.error("need --opp-ckpt or --stockfish")

    w = d = l = 0
    pgn = open(args.pgn_out, "a") if args.pgn_out else None
    try:
        for g in range(args.games):
            opening = OPENINGS[(g // 2) % len(OPENINGS)]
            me_white = g % 2 == 0
            game = play_game(me, opp, opening) if me_white else play_game(opp, me, opening)
            r = game.headers["Result"]
            if r == "1/2-1/2":
                d += 1
            elif (r == "1-0") == me_white:
                w += 1
            else:
                l += 1
            if pgn:
                print(game, file=pgn, end="\n\n")
            print(f"game {g + 1}/{args.games}: {r} ({'W' if me_white else 'B'})  +{w} ={d} -{l}", flush=True)
    finally:
        if sf is not None:
            sf.quit()
    summary = {"me": me.name, "opp": opp.name, **elo_with_ci(w, d, l)}
    print(json.dumps(summary))
    if args.pgn_out:
        Path(args.pgn_out).with_suffix(".summary.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
