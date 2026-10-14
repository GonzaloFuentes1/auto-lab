"""Board and move encoding.

Everything is expressed from the side-to-move's perspective: when black is to move the board is
mirrored (colors swapped, ranks flipped), so the network only ever sees "my pieces moving up the
board". This halves what the model has to learn and is what Lc0 / searchless_chess do too.

Board -> 64 square tokens (piece id per square) + 2 global features (castling, rule-50 bucket).
Move  -> one of 1858 indices (1792 queen/knight-line from->to pairs + 66 underpromotions), the
         same action space size as Lc0. Queen promotions are the plain from->to move.
"""
from __future__ import annotations

import math

import chess
import numpy as np

# --- square tokens -------------------------------------------------------------------------
# 0 = empty, 1..6 = own P N B R Q K, 7..12 = opponent P N B R Q K, 13 = en-passant target square
EMPTY, EP_TOKEN = 0, 13
N_SQUARE_TOKENS = 14
N_CASTLING = 16      # 4 bits: own K-side, own Q-side, opp K-side, opp Q-side
N_RULE50 = 10        # halfmove clock bucketed by 10


def _orient(board: chess.Board) -> chess.Board:
    """Return a board where the side to move is white."""
    return board if board.turn == chess.WHITE else board.mirror()


def encode_board(board: chess.Board) -> tuple[np.ndarray, np.ndarray]:
    """Return (squares uint8[64], glob int64[2]) from the side-to-move perspective."""
    b = _orient(board)
    squares = np.zeros(64, dtype=np.uint8)
    for sq, piece in b.piece_map().items():
        squares[sq] = piece.piece_type + (0 if piece.color == chess.WHITE else 6)
    if b.ep_square is not None and b.has_legal_en_passant():
        squares[b.ep_square] = EP_TOKEN
    castling = (
        int(b.has_kingside_castling_rights(chess.WHITE))
        | int(b.has_queenside_castling_rights(chess.WHITE)) << 1
        | int(b.has_kingside_castling_rights(chess.BLACK)) << 2
        | int(b.has_queenside_castling_rights(chess.BLACK)) << 3
    )
    rule50 = min(b.halfmove_clock, 99) // 10
    return squares, np.array([castling, rule50], dtype=np.int64)


# --- move vocabulary -----------------------------------------------------------------------
UNDERPROMOS = (chess.KNIGHT, chess.BISHOP, chess.ROOK)


def _build_vocab() -> list[tuple[int, int, int | None]]:
    moves: list[tuple[int, int, int | None]] = []
    for frm in range(64):
        fr, ff = divmod(frm, 8)
        for to in range(64):
            if to == frm:
                continue
            tr, tf = divmod(to, 8)
            dr, df = tr - fr, tf - ff
            line = dr == 0 or df == 0 or abs(dr) == abs(df)
            knight = (abs(dr), abs(df)) in ((1, 2), (2, 1))
            if line or knight:
                moves.append((frm, to, None))
    for ff in range(8):
        frm = chess.square(ff, 6)
        for df in (-1, 0, 1):
            if 0 <= ff + df < 8:
                to = chess.square(ff + df, 7)
                for p in UNDERPROMOS:
                    moves.append((frm, to, p))
    return moves


MOVE_VOCAB = _build_vocab()
N_MOVES = len(MOVE_VOCAB)  # 1858
_MOVE_TO_IDX = {m: i for i, m in enumerate(MOVE_VOCAB)}

# Index tensors used by the policy head to turn a 64x64 from->to logit map (+ per-destination
# underpromotion biases) into the 1858-way action space.
FT_FLAT_INDEX = np.array([f * 64 + t for f, t, _ in MOVE_VOCAB], dtype=np.int64)
PROMO_INDEX = np.array(
    [-1 if p is None else t * 3 + UNDERPROMOS.index(p) for _, t, p in MOVE_VOCAB], dtype=np.int64
)


def move_to_index(board: chess.Board, move: chess.Move) -> int:
    """Index of a (real-board) move in the side-to-move-oriented vocabulary."""
    frm, to = move.from_square, move.to_square
    if board.turn == chess.BLACK:
        frm, to = chess.square_mirror(frm), chess.square_mirror(to)
    promo = None if move.promotion in (None, chess.QUEEN) else move.promotion
    return _MOVE_TO_IDX[(frm, to, promo)]


def index_to_move(board: chess.Board, idx: int) -> chess.Move:
    """Inverse of move_to_index; adds queen promotion for pawn moves to the last rank."""
    frm, to, promo = MOVE_VOCAB[idx]
    if board.turn == chess.BLACK:
        frm, to = chess.square_mirror(frm), chess.square_mirror(to)
    if promo is None and board.piece_type_at(frm) == chess.PAWN and chess.square_rank(to) in (0, 7):
        promo = chess.QUEEN
    return chess.Move(frm, to, promo)


def legal_move_indices(board: chess.Board) -> tuple[list[chess.Move], np.ndarray]:
    moves = list(board.legal_moves)
    return moves, np.array([move_to_index(board, m) for m in moves], dtype=np.int64)


# --- value targets -------------------------------------------------------------------------
# Lichess' centipawn -> win-probability curve (https://lichess.org/page/accuracy).
_CP_SCALE = 0.00368208


def cp_to_score(cp: float) -> float:
    """Expected score in [0, 1] for the side the centipawn value is relative to."""
    return 1.0 / (1.0 + math.exp(-_CP_SCALE * cp))


def mate_to_score(mate: int) -> float:
    return 1.0 if mate > 0 else 0.0
