"""Fetch explicitly selected, commit-pinned upstream checkouts without resetting work."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def fetch(name: str, source: dict[str, str]) -> None:
    destination = ROOT / "vendor" / name
    if not destination.exists():
        subprocess.run(["git", "clone", "--no-checkout", source["url"], str(destination)], check=True)
        subprocess.run(["git", "-C", str(destination), "checkout", "--detach", source["commit"]], check=True)
    revision = subprocess.check_output(["git", "-C", str(destination), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(destination), "status", "--porcelain"], text=True)
    if revision != source["commit"] or dirty:
        raise SystemExit(f"{destination}: modified or not at pinned commit; left unchanged")
    print(f"{name}: {revision}")


def main() -> None:
    sources = json.loads((ROOT / "sources.json").read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="+", choices=sorted(sources))
    args = parser.parse_args()
    for name in args.names:
        fetch(name, sources[name])


if __name__ == "__main__":
    main()
