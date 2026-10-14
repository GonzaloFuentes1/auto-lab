"""Convert a raw source into training shards.

    python -m chessbot.prepare evaldb lichess_db_eval.jsonl.zst data/shards/evaldb --limit 50000000
    python -m chessbot.prepare pgn lichess_db_standard_rated_2025-01.pgn.zst data/shards/human2000 --min-elo 2000

Hold out a validation set from a *different* slice of the source (e.g. --skip past the train
slice, or a different month of PGNs) so positions don't leak between train and val.
"""
from __future__ import annotations

import argparse
import itertools

from .data import iter_eval_db, iter_pgn_games, write_shards


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source", choices=["evaldb", "pgn"])
    ap.add_argument("path")
    ap.add_argument("out_dir")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--skip", type=int, default=0, help="skip the first N records (for disjoint val slices)")
    ap.add_argument("--shard-size", type=int, default=1_000_000)
    ap.add_argument("--min-elo", type=int, default=2000)
    args = ap.parse_args(argv)

    records = iter_eval_db(args.path) if args.source == "evaldb" else iter_pgn_games(args.path, args.min_elo)
    records = itertools.islice(records, args.skip, None)
    n = write_shards(records, args.out_dir, args.shard_size, args.limit)
    print(f"wrote {n:,} positions to {args.out_dir}")


if __name__ == "__main__":
    main()
