import json
import random
import subprocess
import sys

import chess
import numpy as np
import torch

from chessbot.data import ShardData, parse_eval_record, write_shards
from chessbot.encoding import N_MOVES, encode_board, index_to_move, legal_move_indices, move_to_index
from chessbot.model import ChessTransformer, ModelConfig, hl_gauss_targets
from chessbot.search import MCTS, Engine, Evaluator, terminal_value

TINY = ModelConfig(d_model=32, n_layers=2, n_heads=4, value_bins=16)


def random_positions(n, seed=0):
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        b = chess.Board()
        for _ in range(rng.randint(0, 120)):
            moves = list(b.legal_moves)
            if not moves:
                break
            b.push(rng.choice(moves))
        if not b.is_game_over():
            out.append(b)
    return out


def test_vocab_size_matches_lc0():
    assert N_MOVES == 1858


def test_every_legal_move_round_trips():
    boards = random_positions(300) + [chess.Board("8/P6k/8/8/8/8/6Kp/8 w - - 0 1"),
                                      chess.Board("8/P6k/8/8/8/8/6Kp/8 b - - 0 1")]
    for b in boards:
        moves, idx = legal_move_indices(b)
        assert len(set(idx.tolist())) == len(moves)  # injective on legal moves
        for m, i in zip(moves, idx):
            assert index_to_move(b, int(i)) == m


def test_encoding_is_color_symmetric():
    b = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
    sq_w, g_w = encode_board(b)
    sq_b, g_b = encode_board(b.mirror())
    assert np.array_equal(sq_w, sq_b) and np.array_equal(g_w, g_b)


def test_model_shapes_and_hlgauss():
    model = ChessTransformer(TINY)
    boards = random_positions(4)
    enc = [encode_board(b) for b in boards]
    sq = torch.from_numpy(np.stack([e[0] for e in enc]).astype(np.int64))
    g = torch.from_numpy(np.stack([e[1] for e in enc]))
    pol, val = model(sq, g)
    assert pol.shape == (4, N_MOVES) and val.shape == (4, TINY.value_bins)
    t = hl_gauss_targets(torch.tensor([0.0, 0.5, 1.0]), 16)
    assert torch.allclose(t.sum(-1), torch.ones(3))
    centers = (torch.arange(16) + 0.5) / 16
    assert abs((t[1] * centers).sum().item() - 0.5) < 1e-4


def test_parse_eval_record_black_to_move_flips_score():
    line = json.dumps({"fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq -",
                       "evals": [{"pvs": [{"cp": 300, "line": "e7e5 g1f3"}], "knodes": 10, "depth": 20}]})
    board, move, score = parse_eval_record(line)
    assert move == chess.Move.from_uci("e7e5") and score < 0.5


def test_shards_roundtrip(tmp_path):
    recs = [(b, next(iter(b.legal_moves)), 0.5) for b in random_positions(50)]
    assert write_shards(iter(recs), tmp_path, shard_size=20) == 50
    data = ShardData(tmp_path)
    assert len(data) == 50
    batch = data.sample(8, np.random.default_rng(0), torch.device("cpu"))
    assert batch["squares"].shape == (8, 64)


def test_mcts_finds_mate_in_one_and_returns_legal_moves():
    torch.manual_seed(0)
    ev = Evaluator(ChessTransformer(TINY))
    b = chess.Board("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1")  # Ra8#
    move, visits, _ = MCTS(ev).search(b, 400)
    assert move == chess.Move.from_uci("a1a8")
    for b in random_positions(5, seed=1):
        assert Engine(ChessTransformer(TINY), nodes=16).play(b)[0] in b.legal_moves
    assert terminal_value(chess.Board("7k/5QQ1/8/8/8/8/8/K7 b - - 0 1")) == -1.0


def test_uci_smoke(tmp_path):
    ckpt = tmp_path / "ckpt.pt"
    torch.save({"model": ChessTransformer(TINY).state_dict(), "config": TINY.to_dict()}, ckpt)
    cmds = "uci\nisready\nposition startpos moves e2e4 e7e5\ngo nodes 8\nquit\n"
    out = subprocess.run([sys.executable, "-m", "chessbot.uci", "--ckpt", str(ckpt)], input=cmds,
                         capture_output=True, text=True, timeout=120).stdout
    assert "uciok" in out and "readyok" in out
    best = out.split("bestmove ")[1].split()[0]
    b = chess.Board()
    b.push_uci("e2e4"); b.push_uci("e7e5")
    assert chess.Move.from_uci(best) in b.legal_moves
