"""Tests for the link liveness gate. No network access: fetchers are fakes."""

from __future__ import annotations

import urllib.error
from pathlib import Path

from starintel_site_builder.linkcheck import (
    LinkFailure,
    check_paths,
    check_text,
    extract_urls,
    is_example,
)

import pytest


def fake_fetcher(responses: dict[str, int | Exception]):
    def fetch(url: str) -> int:
        result = responses[url]
        if isinstance(result, Exception):
            raise result
        return result

    return fetch


def test_extract_urls_finds_org_links_and_bare_urls() -> None:
    text = (
        "See [[https://docs.couchdb.org/intro][the docs]] and https://www.rabbitmq.com/docs/exchanges.\n"
        "Trailing dot gets stripped: https://pouchdb.com/guides/.\n"
    )
    assert extract_urls(text) == [
        (1, "https://docs.couchdb.org/intro"),
        (1, "https://www.rabbitmq.com/docs/exchanges"),
        (2, "https://pouchdb.com/guides/"),
    ]


def test_extract_urls_skips_code_and_example_blocks() -> None:
    text = (
        "#+begin_src json\n"
        '{"url": "https://fake.example.com/inside"}\n'
        "#+end_src\n"
        "#+begin_example\n"
        "https://also-skipped.invalid\n"
        "#+end_example\n"
        "Real: [[https://git.starintel.actor/][forgejo]]\n"
    )
    assert extract_urls(text) == [(7, "https://git.starintel.actor/")]


def test_extract_urls_skips_example_hosts_and_loopback() -> None:
    text = (
        "https://localhost:8080/health\n"
        "https://example.com/what\n"
        "https://api.test/v1\n"
        "https://real.starintel.actor/ok\n"
    )
    assert extract_urls(text) == [(4, "https://real.starintel.actor/ok")]


def test_is_example_matches_documentation_only_hosts() -> None:
    assert is_example("https://example.org/a")
    assert is_example("https://sub.example.com/a")
    assert is_example("https://host.invalid")
    assert not is_example("https://spec.starintel.actor/latest/")


def test_check_text_passes_2xx_and_3xx() -> None:
    text = "a [[https://ok.starintel.actor/a][x]] and https://redirect.starintel.actor/b"
    fetch = fake_fetcher({"https://ok.starintel.actor/a": 200, "https://redirect.starintel.actor/b": 301})
    assert check_text(text, fetch) == []


def test_check_text_reports_http_failures_with_lines() -> None:
    text = "fine: https://ok.starintel.actor/a\nbroken: https://dead.starintel.actor/b\n"
    fetch = fake_fetcher({"https://ok.starintel.actor/a": 200, "https://dead.starintel.actor/b": 404})
    assert check_text(text, fetch) == [(2, "https://dead.starintel.actor/b", "HTTP 404")]


def test_check_text_reports_transport_errors() -> None:
    text = "https://unreachable.starintel.actor/a\n"
    fetch = fake_fetcher(
        {"https://unreachable.starintel.actor/a": urllib.error.URLError("no route")}
    )
    failures = check_text(text, fetch)
    assert len(failures) == 1
    line, url, reason = failures[0]
    assert line == 1
    assert url == "https://unreachable.starintel.actor/a"
    assert reason.startswith("request failed:")


def test_check_paths_reports_file_and_line(tmp_path: Path) -> None:
    post = tmp_path / "post.org"
    post.write_text("line one\n[[https://dead.starintel.actor/x][dead]]\n", encoding="utf-8")
    fetch = fake_fetcher({"https://dead.starintel.actor/x": 404})

    failures = check_paths([post], fetch)

    assert failures == [
        LinkFailure(path=post, line=2, url="https://dead.starintel.actor/x", reason="HTTP 404")
    ]


def test_check_paths_ignores_urls_in_blocks(tmp_path: Path) -> None:
    post = tmp_path / "post.org"
    post.write_text(
        "#+begin_src text\nhttps://dead.starintel.actor/never-fetched\n#+end_src\n",
        encoding="utf-8",
    )

    assert check_paths([post], fake_fetcher({})) == []


def test_module_never_imports_network_side_effects() -> None:
    # The gate runs with fakes only; importing the module must not fetch.
    import starintel_site_builder.linkcheck as module

    assert module.DEFAULT_TIMEOUT > 0
