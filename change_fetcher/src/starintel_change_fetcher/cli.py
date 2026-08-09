from __future__ import annotations

import argparse
import json
from pathlib import Path

from .git import GitChangeSource


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Normalize real Git changes for editorial use")
    p.add_argument("repository", type=Path)
    p.add_argument("--range", dest="revision_range", default="HEAD~10..HEAD")
    p.add_argument("--limit", type=int, default=100)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    changes = GitChangeSource(args.repository).changes(args.revision_range, args.limit)
    print(json.dumps([change.to_dict() for change in changes], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
