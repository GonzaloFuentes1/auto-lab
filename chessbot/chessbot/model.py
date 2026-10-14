"""Square-token transformer with policy + value heads.

Design follows what currently works best for neural chess (see notes/sota_chess_review.md):
  * one token per square (+1 global token), encoder-only, pre-LayerNorm   [Chessformer / Lc0 BT4]
  * optional learned per-head 65x65 attention bias, a cheap static stand-in for Lc0's
    smolgen / Chessformer's geometric attention bias                       [ARCH hypotheses]
  * policy head = source->destination attention logits over 64x64 squares, gathered into the
    1858-move vocabulary, plus per-destination underpromotion biases
  * value head = classification over K bins of the expected score with HL-Gauss targets, which
    beat MSE regression in searchless_chess (Ruoss et al. 2024; Farebrother et al. 2024)
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F

from .encoding import FT_FLAT_INDEX, N_CASTLING, N_RULE50, N_SQUARE_TOKENS, PROMO_INDEX


@dataclass
class ModelConfig:
    d_model: int = 256
    n_layers: int = 8
    n_heads: int = 8
    ffn_mult: int = 4
    value_bins: int = 64
    attn_bias: bool = True
    dropout: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class Block(nn.Module):
    def __init__(self, cfg: ModelConfig, seq_len: int):
        super().__init__()
        d, h = cfg.d_model, cfg.n_heads
        self.n_heads = h
        self.ln1 = nn.LayerNorm(d)
        self.qkv = nn.Linear(d, 3 * d)
        self.proj = nn.Linear(d, d)
        self.ln2 = nn.LayerNorm(d)
        self.ffn = nn.Sequential(nn.Linear(d, cfg.ffn_mult * d), nn.GELU(), nn.Linear(cfg.ffn_mult * d, d))
        self.drop = nn.Dropout(cfg.dropout)
        self.bias = nn.Parameter(torch.zeros(h, seq_len, seq_len)) if cfg.attn_bias else None

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, D = x.shape
        q, k, v = self.qkv(self.ln1(x)).view(B, T, 3, self.n_heads, D // self.n_heads).unbind(2)
        q, k, v = (t.transpose(1, 2) for t in (q, k, v))
        mask = None if self.bias is None else self.bias.to(q.dtype)
        a = F.scaled_dot_product_attention(q, k, v, attn_mask=mask)
        x = x + self.drop(self.proj(a.transpose(1, 2).reshape(B, T, D)))
        return x + self.drop(self.ffn(self.ln2(x)))


class ChessTransformer(nn.Module):
    SEQ = 65  # global token + 64 squares

    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.cfg = cfg
        d = cfg.d_model
        self.piece_emb = nn.Embedding(N_SQUARE_TOKENS, d)
        self.castle_emb = nn.Embedding(N_CASTLING, d)
        self.rule50_emb = nn.Embedding(N_RULE50, d)
        self.pos_emb = nn.Parameter(torch.randn(self.SEQ, d) * 0.02)
        self.blocks = nn.ModuleList(Block(cfg, self.SEQ) for _ in range(cfg.n_layers))
        self.ln_f = nn.LayerNorm(d)
        self.pol_q = nn.Linear(d, d)
        self.pol_k = nn.Linear(d, d)
        self.pol_promo = nn.Linear(d, 3)
        self.val_head = nn.Sequential(nn.Linear(d, d), nn.GELU(), nn.Linear(d, cfg.value_bins))
        self.register_buffer("ft_index", torch.from_numpy(FT_FLAT_INDEX), persistent=False)
        self.register_buffer("promo_index", torch.from_numpy(PROMO_INDEX.clip(min=0)), persistent=False)
        self.register_buffer("promo_mask", torch.from_numpy(PROMO_INDEX >= 0), persistent=False)
        self.register_buffer("bin_centers", (torch.arange(cfg.value_bins) + 0.5) / cfg.value_bins, persistent=False)

    def forward(self, squares: torch.Tensor, glob: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """squares: long[B,64], glob: long[B,2] -> (policy_logits[B,1858], value_logits[B,K])."""
        g = self.castle_emb(glob[:, 0]) + self.rule50_emb(glob[:, 1])
        x = torch.cat([g[:, None], self.piece_emb(squares)], dim=1) + self.pos_emb
        for blk in self.blocks:
            x = blk(x)
        x = self.ln_f(x)
        sq = x[:, 1:]
        ft = self.pol_q(sq) @ self.pol_k(sq).transpose(1, 2) / math.sqrt(self.cfg.d_model)
        promo = self.pol_promo(sq).flatten(1)  # [B, 64*3], indexed by to_square*3 + piece
        policy = ft.flatten(1)[:, self.ft_index]
        policy = policy + torch.where(self.promo_mask, promo[:, self.promo_index], 0.0)
        return policy, self.val_head(x[:, 0])

    def expected_score(self, value_logits: torch.Tensor) -> torch.Tensor:
        return (value_logits.float().softmax(-1) * self.bin_centers).sum(-1)


def hl_gauss_targets(y: torch.Tensor, n_bins: int, sigma_ratio: float = 0.75) -> torch.Tensor:
    """Histogram-loss Gaussian targets for scalars y in [0,1] (Imani & White 2018)."""
    edges = torch.linspace(0.0, 1.0, n_bins + 1, device=y.device)
    sigma = sigma_ratio / n_bins
    cdf = torch.special.ndtr((edges[None, :] - y[:, None]) / sigma)
    probs = cdf[:, 1:] - cdf[:, :-1]
    return probs / probs.sum(-1, keepdim=True).clamp_min(1e-8)


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())
