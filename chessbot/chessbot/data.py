"""Training data: raw sources -> compact .npz shards -> random minibatches.

Sources (all public):
  * lichess eval DB  (database.lichess.org, CC0): ~395M positions with Stockfish evals + PVs.
    Gives a value target (eval -> expected score) and a policy target (first move of best PV).
    This is the phase-1 "distill the engine" source.
  * lichess games PGN (database.lichess.org, CC0): human moves + game result. Only used as the
    human-imitation baseline for the DATA hypotheses — expected to cap at human strength.

Shard layout (one .npz per shard):
  squares uint8[N,64], glob uint8[N,2], move int16[N], score float16[N]  (score: side to move)
"""
from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Iterator

import chess
import chess.pgn
import numpy as np
import torch

from .encoding import cp_to_score, encode_board, mate_to_score, move_to_index


def open_text(path: str | Path) -> io.TextIOBase:
    path = str(path)
    if path.endswith(".zst"):
        import zstandard

        fh = open(path, "rb")
        return io.TextIOWrapper(zstandard.ZstdDecompressor().stream_reader(fh), encoding="utf-8")
    return open(path, encoding="utf-8")


# --- record parsers: each yields (board, best_move, score_for_side_to_move) -----------------
def parse_eval_record(line: str) -> tuple[chess.Board, chess.Move, float] | None:
    rec = json.loads(line)
    if not rec.get("evals"):
        return None
    ev = max(rec["evals"], key=lambda e: (e.get("depth", 0), e.get("knodes", 0)))
    pv = ev["pvs"][0]
    if not pv.get("line"):
        return None
    board = chess.Board(rec["fen"])
    move = chess.Move.from_uci(pv["line"].split()[0])
    if move not in board.legal_moves:
        return None
    # lichess evals are from white's point of view
    white_score = mate_to_score(pv["mate"]) if "mate" in pv else cp_to_score(pv["cp"])
    score = white_score if board.turn == chess.WHITE else 1.0 - white_score
    return board, move, score


def iter_eval_db(path: str | Path) -> Iterator[tuple[chess.Board, chess.Move, float]]:
    with open_text(path) as fh:
        for line in fh:
            out = parse_eval_record(line)
            if out is not None:
                yield out


def iter_pgn_games(path: str | Path, min_elo: int = 2000) -> Iterator[tuple[chess.Board, chess.Move, float]]:
    """Human moves from games where both players are >= min_elo; value = final game result."""
    result_score = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}
    with open_text(path) as fh:
        while (game := chess.pgn.read_game(fh)) is not None:
            h = game.headers
            try:
                if min(int(h.get("WhiteElo", 0)), int(h.get("BlackElo", 0))) < min_elo:
                    continue
            except ValueError:
                continue
            if h.get("Result") not in result_score:
                continue
            white_score = result_score[h["Result"]]
            board = game.board()
            for move in game.mainline_moves():
                yield board.copy(stack=False), move, white_score if board.turn == chess.WHITE else 1.0 - white_score
                board.push(move)


# --- shard writing ----------------------------------------------------------------------------
def write_shards(records: Iterator[tuple[chess.Board, chess.Move, float]], out_dir: str | Path,
                 shard_size: int = 1_000_000, limit: int | None = None) -> int:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    buf_sq, buf_g, buf_m, buf_s = [], [], [], []
    n_total, shard_id = 0, 0

    def flush():
        nonlocal shard_id
        if not buf_sq:
            return
        np.savez(out_dir / f"shard_{shard_id:05d}.npz", squares=np.stack(buf_sq),
                 glob=np.stack(buf_g).astype(np.uint8), move=np.array(buf_m, dtype=np.int16),
                 score=np.array(buf_s, dtype=np.float16))
        shard_id += 1
        for b in (buf_sq, buf_g, buf_m, buf_s):
            b.clear()

    for board, move, score in records:
        sq, g = encode_board(board)
        buf_sq.append(sq)
        buf_g.append(g)
        buf_m.append(move_to_index(board, move))
        buf_s.append(score)
        n_total += 1
        if len(buf_sq) >= shard_size:
            flush()
        if limit is not None and n_total >= limit:
            break
    flush()
    return n_total


# --- loading ----------------------------------------------------------------------------------
class ShardData:
    """Loads all shards in a directory into memory and samples random minibatches."""

    def __init__(self, shard_dir: str | Path):
        files = sorted(Path(shard_dir).glob("shard_*.npz"))
        if not files:
            raise FileNotFoundError(f"no shard_*.npz in {shard_dir}")
        parts = [np.load(f) for f in files]
        self.squares = np.concatenate([p["squares"] for p in parts])
        self.glob = np.concatenate([p["glob"] for p in parts])
        self.move = np.concatenate([p["move"] for p in parts])
        self.score = np.concatenate([p["score"] for p in parts])

    def __len__(self) -> int:
        return len(self.move)

    def batch(self, idx: np.ndarray, device: torch.device) -> dict[str, torch.Tensor]:
        return {
            "squares": torch.from_numpy(self.squares[idx].astype(np.int64)).to(device),
            "glob": torch.from_numpy(self.glob[idx].astype(np.int64)).to(device),
            "move": torch.from_numpy(self.move[idx].astype(np.int64)).to(device),
            "score": torch.from_numpy(self.score[idx].astype(np.float32)).to(device),
        }

    def sample(self, batch_size: int, rng: np.random.Generator, device: torch.device) -> dict[str, torch.Tensor]:
        return self.batch(rng.integers(0, len(self), batch_size), device)
