"""Supervised training (phase 1): policy CE on the teacher's best move + value loss.

    python -m chessbot.train --data data/shards/evaldb --out runs/H1_evaldb_s0 --steps 200000

Writes runs/<name>/metrics.jsonl (one line per log interval) and ckpt.pt. Log the final numbers to
research/state.jsonl as a `result` entry (see the log-finding skill) — metrics.jsonl is a raw
artifact, not the lab notebook.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from .data import ShardData
from .model import ChessTransformer, ModelConfig, count_params, hl_gauss_targets


def losses(model: ChessTransformer, batch: dict, value_loss: str) -> dict[str, torch.Tensor]:
    policy, vlogits = model(batch["squares"], batch["glob"])
    pol = F.cross_entropy(policy.float(), batch["move"])
    if value_loss == "hlgauss":
        val = -(hl_gauss_targets(batch["score"], model.cfg.value_bins) * vlogits.float().log_softmax(-1)).sum(-1).mean()
    else:
        val = F.mse_loss(model.expected_score(vlogits), batch["score"])
    with torch.no_grad():
        acc = (policy.argmax(-1) == batch["move"]).float().mean()
        mae = (model.expected_score(vlogits) - batch["score"]).abs().mean()
    return {"loss": pol + val, "policy_ce": pol, "value_loss": val, "top1": acc, "value_mae": mae}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="shard dir for training")
    ap.add_argument("--val-data", help="held-out shard dir for validation metrics (optional)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, default=100_000)
    ap.add_argument("--batch-size", type=int, default=1024)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--wd", type=float, default=0.01)
    ap.add_argument("--warmup", type=int, default=2000)
    ap.add_argument("--value-loss", choices=["hlgauss", "mse"], default="hlgauss")
    ap.add_argument("--d-model", type=int, default=256)
    ap.add_argument("--n-layers", type=int, default=8)
    ap.add_argument("--n-heads", type=int, default=8)
    ap.add_argument("--no-attn-bias", action="store_true")
    ap.add_argument("--log-every", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args(argv)

    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    device = torch.device(args.device)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    train = ShardData(args.data)
    val = ShardData(args.val_data) if args.val_data else None
    cfg = ModelConfig(d_model=args.d_model, n_layers=args.n_layers, n_heads=args.n_heads,
                      attn_bias=not args.no_attn_bias)
    model = ChessTransformer(cfg).to(device)
    print(f"params={count_params(model):,} train_positions={len(train):,}")
    (out / "args.json").write_text(json.dumps({**vars(args), "params": count_params(model)}, indent=1))

    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.wd, betas=(0.9, 0.95))
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / args.warmup)
                                              * 0.5 * (1 + math.cos(math.pi * min(s / args.steps, 1.0))))
    amp = torch.autocast(device.type, dtype=torch.bfloat16, enabled=device.type == "cuda")
    log = open(out / "metrics.jsonl", "a")
    t0, running = time.time(), {}
    for step in range(1, args.steps + 1):
        model.train()
        with amp:
            m = losses(model, train.sample(args.batch_size, rng, device), args.value_loss)
        opt.zero_grad(set_to_none=True)
        m["loss"].backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        sched.step()
        for k, v in m.items():
            running[k] = running.get(k, 0.0) + v.item()
        if step % args.log_every == 0 or step == args.steps:
            rec = {"step": step, **{f"train_{k}": v / args.log_every for k, v in running.items()},
                   "lr": sched.get_last_lr()[0], "elapsed_s": round(time.time() - t0, 1)}
            running = {}
            if val is not None:
                model.eval()
                vm: dict[str, float] = {}
                vidx = np.arange(min(len(val), 50_000))
                with torch.no_grad(), amp:
                    for i in range(0, len(vidx), args.batch_size):
                        b = val.batch(vidx[i:i + args.batch_size], device)
                        for k, v in losses(model, b, args.value_loss).items():
                            vm[k] = vm.get(k, 0.0) + v.item() * len(b["move"])
                rec.update({f"val_{k}": v / len(vidx) for k, v in vm.items()})
            print(json.dumps(rec))
            log.write(json.dumps(rec) + "\n")
            log.flush()
            torch.save({"model": model.state_dict(), "config": cfg.to_dict(), "step": step}, out / "ckpt.pt")


if __name__ == "__main__":
    main()
