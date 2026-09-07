"""Deterministic Org header/metadata and link parsing.

This module never interprets Org body content: it reads document-level
keywords, the :PROPERTIES: drawer (org-roam :ID:), and outbound links,
which is all the site builder and graph need.
"""

from __future__ import annotations

import re
from pathlib import Path

_KEYWORD_RE = re.compile(r"^#\+([A-Za-z_-]+):\s*(.*?)\s*$", re.MULTILINE)
_FILETAGS_RE = re.compile(r":([A-Za-z0-9_@()%.#]+):")
_ID_PROP_RE = re.compile(r"^\s*:ID:\s*(\S+)\s*$", re.MULTILINE)
_LINK_RE = re.compile(r"\[\[([^]]+)\](?:\[([^]]*?)\])?\]")


def parse_keywords(text: str) -> dict[str, str]:
    """Parse Org document-level keywords from the text before the first heading."""
    header = text.split("\n* ", 1)[0]
    keywords: dict[str, str] = {}
    for match in _KEYWORD_RE.finditer(header):
        key = match.group(1).upper()
        if key not in keywords:
            keywords[key] = match.group(2).strip()
    return keywords


def parse_filetags(value: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_FILETAGS_RE.findall(value)))


def split_tags(raw: str | None, filetags: str | None) -> tuple[str, ...]:
    tags: list[str] = []
    if raw:
        tags.extend(part.strip() for part in re.split(r"[,\s]+", raw) if part.strip())
    if filetags:
        tags.extend(parse_filetags(filetags))
    return tuple(dict.fromkeys(tags))


def parse_id_property(text: str) -> str:
    match = _ID_PROP_RE.search(text)
    return match.group(1) if match else ""


def extract_links(text: str) -> list[tuple[str, str]]:
    """Return (target, label) pairs for id: and file: links."""
    pairs = []
    for m in _LINK_RE.finditer(text):
        target = m.group(1).strip()
        if target.startswith(("id:", "file:")):
            pairs.append((target, (m.group(2) or "").strip()))
    return pairs


def parse_source_doc(path: Path, section: str, url: str) -> dict:
    """Parse one Org file into SourceDoc constructor arguments (minus path/section)."""
    text = path.read_text(encoding="utf-8")
    keywords = parse_keywords(text)
    title = keywords.get("TITLE") or path.stem
    raw_slug = keywords.get("SLUG") or path.stem
    slug = _strip_date_prefix(raw_slug)
    status = (keywords.get("STATUS") or "POST").strip().upper()
    if status not in {"POST", "DRAFT"}:
        status = "POST"
    tags = split_tags(keywords.get("TAGS"), keywords.get("FILETAGS"))
    return {
        "title": title,
        "slug": slug,
        "description": keywords.get("DESCRIPTION", ""),
        "author": keywords.get("AUTHOR", ""),
        "date": _first_date(keywords.get("DATE", "")),
        "tags": tags,
        "status": status,
        "revision": keywords.get("REVISION", ""),
        "doc_id": parse_id_property(text) or f"file:{slug}",
        "url": url,
        "human": "human" in tags,
    }


def _strip_date_prefix(slug: str) -> str:
    return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", slug)


def _first_date(value: str) -> str:
    match = re.search(r"<(\d{4}-\d{2}-\d{2})", value) or re.search(
        r"(\d{4}-\d{2}-\d{2})", value
    )
    return match.group(1) if match else ""


def default_url(section: str, path: Path, root: Path, slug: str) -> str:
    if section == "blog":
        return f"/blog/{slug}.html"
    rel = path.relative_to(root).with_suffix(".html")
    prefix = "docs" if section == "docs" else "portfolio"
    return f"/{prefix}/{rel.as_posix()}"
