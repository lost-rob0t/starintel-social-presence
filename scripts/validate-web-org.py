#!/usr/bin/env python3
"""Validate web-facing Org metadata for the StarIntel website publisher.

Covers content the website consumes: blog posts (blog/posts/) and the nsaspy
site (nsaspy/). Fails closed: missing required keywords are errors.

    python3 scripts/validate-web-org.py [--changed-since REV]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_SCOPES = ["blog/posts", "nsaspy"]
DAILY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def org_files() -> list[Path]:
    files: list[Path] = []
    for scope in WEB_SCOPES:
        base = ROOT / scope
        if base.is_dir():
            files.extend(sorted(p for p in base.rglob("*.org") if p.is_file()))
    return files


def changed_files(rev: str) -> list[Path] | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "diff", "--name-only", "--diff-filter=ACM", f"{rev}", "HEAD", "--", *WEB_SCOPES],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return None
    return [ROOT / line for line in out.stdout.splitlines() if line.endswith(".org")]


def parse_keywords(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    first_heading = text.find("\n* ")
    header = text[: first_heading if first_heading >= 0 else len(text)]
    keywords: dict[str, str] = {}
    for match in re.finditer(r"^\s*#\+([A-Za-z_-]+):\s*(.*?)\s*$", header, re.MULTILINE):
        key = match.group(1).upper()
        if key not in keywords:
            keywords[key] = match.group(2)
    return keywords


def validate(path: Path) -> list[str]:
    problems: list[str] = []
    keywords = parse_keywords(path)
    rel = path.relative_to(ROOT)
    if not keywords.get("TITLE"):
        problems.append(f"{rel}: missing #+title")
    if not keywords.get("DESCRIPTION"):
        problems.append(f"{rel}: missing #+description")
    if "blog/posts" in str(rel):
        if not keywords.get("DATE"):
            problems.append(f"{rel}: blog post missing #+date")
        if not keywords.get("AUTHOR"):
            problems.append(f"{rel}: blog post missing #+author")
    if DAILY_RE.match(path.stem):
        if not keywords.get("DATE"):
            problems.append(f"{rel}: daily missing #+date")
        else:
            m = re.search(r"(\d{4}-\d{2}-\d{2})", keywords["DATE"])
            if not m or m.group(1) != path.stem:
                problems.append(f"{rel}: daily #+date {m.group(1) if m else '?'} does not match filename")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--changed-since", default=None, help="only validate files changed since REV")
    args = parser.parse_args()

    files = org_files()
    if args.changed_since:
        changed = changed_files(args.changed_since)
        if changed is not None:
            files = [f for f in files if f in changed]

    if not files:
        print("no web-facing org files to validate")
        return 0

    failures = 0
    for path in files:
        for problem in validate(path):
            print(f"INVALID {problem}")
            failures += 1
    print(f"validated {len(files)} file(s), {failures} problem(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
