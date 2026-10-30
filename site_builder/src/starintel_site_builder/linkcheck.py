"""Deterministic link verification for web-facing Org sources.

Every http(s) link in the published scopes must open: an HTTP 2xx or 3xx
response passes, anything else fails with the file, line, and reason.
Code blocks are skipped so sample URLs never trip the gate, and hosts
reserved for documentation examples are never fetched.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

USER_AGENT = "starintel-social-presence-linkcheck/1"
DEFAULT_TIMEOUT = 15.0

URL_RE = re.compile(r"https?://[^\s<>\"')\]]+")
BEGIN_RE = re.compile(r"^\s*#\+begin_(?:src|example)\b")
END_RE = re.compile(r"^\s*#\+end_(?:src|example)\b")

SKIP_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
SKIP_SUFFIXES = (".example.com", ".example.org", ".example.net", ".invalid", ".test")

Fetcher = Callable[[str], int]


def default_fetcher(url: str, timeout: float = DEFAULT_TIMEOUT) -> int:
    """Return the HTTP status for url, following redirects.

    HEAD first; a server that rejects the method (405/501) is retried
    with GET before giving up.
    """
    headers = {"User-Agent": USER_AGENT}
    try:
        request = urllib.request.Request(url, method="HEAD", headers=headers)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status)
    except urllib.error.HTTPError as error:
        if error.code not in (405, 501):
            raise
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status)


def hostname(url: str) -> str:
    return urllib.parse.urlsplit(url).hostname or ""


def is_example(url: str) -> bool:
    """True for hosts that exist only to appear in documentation."""
    host = hostname(url)
    if host in SKIP_HOSTS:
        return True
    return host.startswith("example.") or host.endswith(SKIP_SUFFIXES)


def extract_urls(text: str) -> list[tuple[int, str]]:
    """Return (line, url) pairs for fetchable http(s) URLs in Org text."""
    found: list[tuple[int, str]] = []
    in_block = False
    for lineno, line in enumerate(text.splitlines(), start=1):
        if BEGIN_RE.match(line):
            in_block = True
            continue
        if END_RE.match(line):
            in_block = False
            continue
        if in_block:
            continue
        for match in URL_RE.finditer(line):
            url = match.group(0).rstrip(".")
            if not is_example(url):
                found.append((lineno, url))
    return found


@dataclass(frozen=True)
class LinkFailure:
    """A URL that did not open, with the location that referenced it."""

    path: Path
    line: int
    url: str
    reason: str


def check_text(text: str, fetch: Fetcher) -> list[tuple[int, str, str]]:
    """Return (line, url, reason) for every URL that does not open."""
    failures: list[tuple[int, str, str]] = []
    for line, url in extract_urls(text):
        try:
            status = fetch(url)
        except urllib.error.HTTPError as error:
            failures.append((line, url, f"HTTP {error.code}"))
        except (urllib.error.URLError, OSError, ValueError) as error:
            failures.append((line, url, f"request failed: {error}"))
        else:
            if not 200 <= status < 400:
                failures.append((line, url, f"HTTP {status}"))
    return failures


def check_paths(paths: Iterable[Path], fetch: Fetcher = default_fetcher) -> list[LinkFailure]:
    """Check every org file in paths against the live link gate."""
    failures: list[LinkFailure] = []
    for path in paths:
        for line, url, reason in check_text(path.read_text(encoding="utf-8"), fetch):
            failures.append(LinkFailure(path, line, url, reason))
    return failures


def org_files(root: Path, scopes: Sequence[str] = ("blog/posts", "nsaspy")) -> list[Path]:
    """Web-facing Org sources, mirroring validate-web-org.py scopes."""
    files: list[Path] = []
    for scope in scopes:
        base = root / scope
        if base.is_dir():
            files.extend(sorted(p for p in base.rglob("*.org") if p.is_file()))
    return files
