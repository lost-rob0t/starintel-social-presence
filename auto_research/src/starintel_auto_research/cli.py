from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapter import iter_research
from .publishing import build_publish_manifest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Surface Auto Research documents with explicit status")
    p.add_argument("root", type=Path)
    p.add_argument("--approved", action="store_true", help="show only explicitly APPROVED records")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument(
        "--publish-manifest",
        action="store_true",
        help="emit the fail-closed website publishing manifest instead of the status readout",
    )
    p.add_argument(
        "--public-id",
        action="append",
        default=[],
        help="allowlisted org-id for publication (repeatable; empty list publishes nothing)",
    )
    args = p.parse_args(argv)

    if args.publish_manifest:
        manifest = build_publish_manifest(args.root, public_ids=args.public_id)
        print(json.dumps(manifest, indent=2))
        return 0

    records = (
        record
        for record in iter_research(args.root)
        if not args.approved or record.approved
    )
    print(json.dumps([record.to_dict() for _, record in zip(range(args.limit), records)], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
