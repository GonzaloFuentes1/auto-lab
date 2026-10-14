"""Minimal UCI front-end so the engine runs in cutechess-cli / fastchess / lichess-bot.

    python -m chessbot.uci --ckpt runs/X/ckpt.pt --nodes 400

Supports: uci, isready, ucinewgame, setoption name Nodes, position [startpos|fen ...] moves ...,
go [nodes N | movetime MS | wtime/btime/winc/binc], stop (no-op, search is synchronous), quit.
"""
from __future__ import annotations

import argparse
import sys

import chess

from .search import load_engine


def _time_budget(tokens: list[str], turn: chess.Color) -> float | None:
    opts = {tokens[i]: int(tokens[i + 1]) for i in range(len(tokens) - 1) if tokens[i + 1].lstrip("-").isdigit()}
    if "movetime" in opts:
        return opts["movetime"] / 1000.0
    t = opts.get("wtime" if turn == chess.WHITE else "btime")
    if t is None:
        return None
    inc = opts.get("winc" if turn == chess.WHITE else "binc", 0)
    return max(0.05, (t / 30 + inc * 0.8) / 1000.0)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--nodes", type=int, default=400)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args(argv)

    engine = load_engine(args.ckpt, args.device, args.nodes)
    board = chess.Board()
    out = sys.stdout
    for line in sys.stdin:
        tokens = line.split()
        if not tokens:
            continue
        cmd = tokens[0]
        if cmd == "uci":
            out.write("id name chessbot\nid author auto-lab\n")
            out.write(f"option name Nodes type spin default {args.nodes} min 1 max 10000000\nuciok\n")
        elif cmd == "isready":
            out.write("readyok\n")
        elif cmd == "ucinewgame":
            board = chess.Board()
        elif cmd == "setoption" and len(tokens) >= 5 and tokens[2].lower() == "nodes":
            engine.nodes = int(tokens[4])
        elif cmd == "position":
            if len(tokens) > 1 and tokens[1] == "startpos":
                board, rest = chess.Board(), tokens[2:]
            else:
                end = tokens.index("moves") if "moves" in tokens else len(tokens)
                board, rest = chess.Board(" ".join(tokens[2:end])), tokens[end:]
            if rest and rest[0] == "moves":
                for uci in rest[1:]:
                    board.push_uci(uci)
        elif cmd == "go":
            nodes = int(tokens[tokens.index("nodes") + 1]) if "nodes" in tokens else None
            move, q = engine.play(board, nodes=nodes, time_limit=_time_budget(tokens, board.turn))
            cp = int(round(q * 1000))  # crude display only; q in [-1, 1]
            out.write(f"info score cp {cp}\nbestmove {move.uci()}\n")
        elif cmd == "quit":
            break
        out.flush()


if __name__ == "__main__":
    main()
