"""Static scan for private StarIntel repository references.

The published site must not link to or name repositories that are not
publicly reachable. This scan is deterministic and offline; the link
liveness gate is its network-side counterpart. Patterns are exact
repository slugs with word boundaries, so "pro actors" prose never
matches while "pro-actors" does. Keep PRIVATE_PATTERNS in sync with
repository visibility policy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from starintel_site_builder.linkcheck import org_files

PRIVATE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bstarintel-pro-actors\b",
        r"\bpro-actors\b",
        r"\bstarintel-biz\b",
        r"\bstarintel-infra\b",
        r"\bstarintel-farm\b",
        r"\bstarintel-discord-reporting\b",
        r"\bohmycaptcha\b",
    )
)


@dataclass(frozen=True)
class PrivateHit:
    """A private repository slug at a concrete location."""

    path: Path
    line: int
    pattern: str
    text: str


def scan_text(text: str) -> list[tuple[int, str, str]]:
    """Return (line, pattern, match) tuples for private slugs in text."""
    hits: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for pattern in PRIVATE_PATTERNS:
            match = pattern.search(line)
            if match:
                hits.append((lineno, pattern.pattern, match.group(0)))
    return hits


def scan_paths(paths: Iterable[Path]) -> list[PrivateHit]:
    """Scan every org file in paths for private repository references."""
    hits: list[PrivateHit] = []
    for path in paths:
        for line, pattern, text in scan_text(path.read_text(encoding="utf-8")):
            hits.append(PrivateHit(path, line, pattern, text))
    return hits
