"""Policy-only play and PUCT Monte-Carlo tree search on top of the network.

Values inside the tree are in [-1, 1] from the perspective noted on each field. Phase-2
hypotheses (SEARCH category) measure how much Elo this adds over the raw policy.

Known simplifications to revisit when they become the bottleneck:
  * one network call per simulation (no batching / virtual loss)
  * no tree reuse between moves
  * root-only Gumbel / sequential halving is not implemented yet (needed for cheap self-play, RL phase)
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import chess
import numpy as np
import torch

from .encoding import encode_board, legal_move_indices
from .model import ChessTransformer


class Evaluator:
    def __init__(self, model: ChessTransformer, device: torch.device | str = "cpu"):
        self.model = model.eval()
        self.device = torch.device(device)

    @torch.no_grad()
    def __call__(self, board: chess.Board) -> tuple[list[chess.Move], np.ndarray, float]:
        """Return (legal moves, prior probabilities, value in [-1,1] for the side to move)."""
        sq, g = encode_board(board)
        squares = torch.from_numpy(sq.astype(np.int64))[None].to(self.device)
        glob = torch.from_numpy(g)[None].to(self.device)
        logits, vlogits = self.model(squares, glob)
        moves, idx = legal_move_indices(board)
        priors = logits[0, torch.from_numpy(idx).to(self.device)].float().softmax(-1).cpu().numpy()
        value = 2.0 * self.model.expected_score(vlogits)[0].item() - 1.0
        return moves, priors, value


def terminal_value(board: chess.Board) -> float | None:
    """Value for the side to move if the game is over (treating a single repetition as a draw)."""
    if board.is_checkmate():
        return -1.0
    if (board.is_stalemate() or board.is_insufficient_material() or board.halfmove_clock >= 100
            or board.is_repetition(2)):
        return 0.0
    return None


@dataclass
class Node:
    prior: float
    visits: int = 0
    value_sum: float = 0.0  # from the perspective of the player who made the move into this node
    children: dict[chess.Move, "Node"] = field(default_factory=dict)

    def q(self) -> float:
        return self.value_sum / self.visits if self.visits else 0.0


class MCTS:
    def __init__(self, evaluator: Evaluator, c_puct: float = 1.75, fpu_reduction: float = 0.3):
        self.evaluator = evaluator
        self.c_puct = c_puct
        self.fpu_reduction = fpu_reduction

    def _expand(self, node: Node, board: chess.Board) -> float:
        moves, priors, value = self.evaluator(board)
        node.children = {m: Node(float(p)) for m, p in zip(moves, priors)}
        return value

    def _select(self, node: Node) -> tuple[chess.Move, Node]:
        sqrt_n = math.sqrt(max(node.visits, 1))
        visited_prior = sum(c.prior for c in node.children.values() if c.visits)
        fpu = node.q() * -1.0 - self.fpu_reduction * math.sqrt(visited_prior)  # parent-perspective
        best, best_score = None, -math.inf
        for move, child in node.children.items():
            q = child.q() if child.visits else fpu
            score = q + self.c_puct * child.prior * sqrt_n / (1 + child.visits)
            if score > best_score:
                best, best_score = (move, child), score
        return best

    def search(self, board: chess.Board, n_sims: int,
               time_limit: float | None = None) -> tuple[chess.Move, dict[chess.Move, int], float]:
        deadline = None if time_limit is None else time.monotonic() + time_limit
        root = Node(prior=1.0)
        root_value = self._expand(root, board)
        root.visits, root.value_sum = 1, -root_value
        for _ in range(n_sims):
            if deadline is not None and time.monotonic() > deadline:
                break
            node, b, path = root, board.copy(), [root]
            while node.children:
                move, node = self._select(node)
                b.push(move)
                path.append(node)
            v = terminal_value(b)
            if v is None:
                v = self._expand(node, b)
            # v is for the side to move at the leaf; the leaf's stored value is for the mover.
            for n in reversed(path):
                v = -v
                n.visits += 1
                n.value_sum += v
        visits = {m: c.visits for m, c in root.children.items()}
        best = max(visits, key=visits.get)
        return best, visits, root.children[best].q()


class Engine:
    """Picks a move with the raw policy (nodes <= 1) or with MCTS."""

    def __init__(self, model: ChessTransformer, device: torch.device | str = "cpu", nodes: int = 1):
        self.evaluator = Evaluator(model, device)
        self.mcts = MCTS(self.evaluator)
        self.nodes = nodes

    def play(self, board: chess.Board, nodes: int | None = None,
             time_limit: float | None = None) -> tuple[chess.Move, float]:
        """Return (move, value in [-1,1] for the side to move)."""
        nodes = self.nodes if nodes is None else nodes
        if nodes <= 1:
            moves, priors, value = self.evaluator(board)
            return moves[int(priors.argmax())], value
        move, _, q = self.mcts.search(board, nodes, time_limit)
        return move, q


def load_engine(ckpt_path: str, device: str = "cpu", nodes: int = 1) -> Engine:
    from .model import ModelConfig

    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    model = ChessTransformer(ModelConfig(**ckpt["config"])).to(device)
    model.load_state_dict(ckpt["model"])
    return Engine(model, device, nodes)
