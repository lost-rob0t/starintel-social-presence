#!/usr/bin/env python3
"""Notify configured webhooks when a push adds a published blog post."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.request
from pathlib import Path


def added_post_paths(base: str, head: str) -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--diff-filter=A", "--name-only", base, head, "--", "blog/posts/*.org"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def post_metadata(path: Path) -> dict[str, str] | None:
    fields: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("#+") or ":" not in line:
            continue
        key, value = line[2:].split(":", 1)
        fields[key.lower()] = value.strip()
    if fields.get("status", "").upper() != "POST":
        return None
    required = ("title", "slug", "description")
    if any(not fields.get(key) for key in required):
        raise ValueError(f"{path}: published post is missing title, slug, or description")
    return {key: fields[key] for key in required}


def message(post: dict[str, str], origin: str) -> str:
    return f"New StarIntel post: **{post['title']}**\n{post['description']}\n{origin.rstrip('/')}/{post['slug']}.html"


def send(url: str, payload: dict[str, str]) -> None:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "starintel-post-notifier/1"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        if response.status >= 300:
            raise RuntimeError(f"webhook returned HTTP {response.status}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="HEAD^")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--origin", default="https://blog.starintel.actor")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    posts = [meta for path in added_post_paths(args.base, args.head) if (meta := post_metadata(path))]
    deliveries = []
    for post in posts:
        text = message(post, args.origin)
        targets = (
            (os.environ.get("DISCORD_WEBHOOK_URL"), {"content": text}),
            (os.environ.get("SLACK_WEBHOOK_URL"), {"text": text}),
            (os.environ.get("POST_WEBHOOK_URL"), {"text": text, "title": post["title"], "url": f"{args.origin.rstrip('/')}/{post['slug']}.html"}),
        )
        for url, payload in targets:
            if not url:
                continue
            deliveries.append(payload)
            if not args.dry_run:
                send(url, payload)
    print(json.dumps({"new_posts": len(posts), "deliveries": len(deliveries)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
