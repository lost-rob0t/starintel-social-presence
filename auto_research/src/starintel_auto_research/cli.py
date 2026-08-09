from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapter import iter_research


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Surface Auto Research documents with explicit status")
    p.add_argument("root", type=Path)
    p.add_argument("--approved", action="store_true", help="show only explicitly APPROVED records")
    p.add_argument("--limit", type=int, default=100)
    args = p.parse_args(argv)
    records = (
        record
        for record in iter_research(args.root)
        if not args.approved or record.approved
    )
    print(json.dumps([record.to_dict() for _, record in zip(range(args.limit), records)], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
