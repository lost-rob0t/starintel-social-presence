from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapter import iter_candidates


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Surface canonical Auto Dig documents for editorial review")
    p.add_argument("root", type=Path)
    p.add_argument("--dtype")
    p.add_argument("--limit", type=int, default=50)
    args = p.parse_args(argv)
    candidates = (
        candidate
        for candidate in iter_candidates(args.root)
        if args.dtype is None or candidate.dtype == args.dtype
    )
    print(json.dumps([candidate.to_dict() for _, candidate in zip(range(args.limit), candidates)], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
