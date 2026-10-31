#!/usr/bin/env python3
"""Gate check: every http(s) link in web-facing Org must open (2xx/3xx).

Requires the site_builder package on PYTHONPATH; scripts/check exports it.

    python3 scripts/check_links.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from starintel_site_builder.linkcheck import check_paths, org_files

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    failures = check_paths(org_files(ROOT))
    for failure in failures:
        rel = failure.path.relative_to(ROOT)
        print(f"{rel}:{failure.line}: {failure.url}: {failure.reason}", file=sys.stderr)
    if failures:
        print(f"{len(failures)} dead link(s)", file=sys.stderr)
        return 1
    print("all links open")
    return 0


if __name__ == "__main__":
    sys.exit(main())
