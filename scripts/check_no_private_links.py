#!/usr/bin/env python3
"""Gate check: web-facing Org must not link to or name private repositories.

Offline counterpart to check_links.py. Reports path:line for every
private repository slug and fails closed.

    python3 scripts/check_no_private_links.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from starintel_site_builder.private_links import scan_paths
from starintel_site_builder.linkcheck import org_files

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    hits = scan_paths(org_files(ROOT))
    for hit in hits:
        rel = hit.path.relative_to(ROOT)
        print(f"{rel}:{hit.line}: private repository reference {hit.pattern!r}: {hit.text}", file=sys.stderr)
    if hits:
        print(f"{len(hits)} private repository reference(s)", file=sys.stderr)
        return 1
    print("no private repository references")
    return 0


if __name__ == "__main__":
    sys.exit(main())
