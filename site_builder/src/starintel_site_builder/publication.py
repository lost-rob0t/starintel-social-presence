"""Fail-closed public site checks for tenant identifiers."""

from __future__ import annotations

import html
import re
from pathlib import Path


TENANT_ID_RE = re.compile(r"\btenant(?:_|-|\s+)(?:ids?|main)\b", re.IGNORECASE)
ESCAPED_CHAR_RE = re.compile(
    r"\\(?:u([0-9a-fA-F]{4})|u\{([0-9a-fA-F]{1,6})\}|x([0-9a-fA-F]{2}))"
)


def contains_tenant_identifier(text: str) -> bool:
    for _ in range(2):
        text = html.unescape(text)
        text = ESCAPED_CHAR_RE.sub(
            lambda match: chr(int(next(part for part in match.groups() if part), 16)),
            text,
        )
    return bool(TENANT_ID_RE.search(text))


def check_public_output(out_dir: Path) -> None:
    for path in out_dir.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(out_dir)
        if contains_tenant_identifier(relative.as_posix()):
            raise RuntimeError(f"public tenant identifier in {relative}")
        content = path.read_bytes().decode("utf-8", errors="ignore")
        if contains_tenant_identifier(content):
            raise RuntimeError(f"public tenant identifier in {relative}")
        if path.suffix == ".html":
            content = re.sub(r"<[^>]*>", "", content)
        if contains_tenant_identifier(content):
            raise RuntimeError(f"public tenant identifier in {relative}")
