"""Tests for the private repository reference scan. Offline by design."""

from __future__ import annotations

from pathlib import Path

from starintel_site_builder.private_links import scan_paths, scan_text


def test_scan_text_flags_private_slugs_with_lines() -> None:
    text = (
        "Source: [[https://github.com/starintel-labs/starintel-biz/commit/da88ad4][biz]]\n"
        "clean line\n"
        "the pro-actors README gets deleted\n"
    )
    hits = scan_text(text)
    assert [(line, match) for line, _, match in hits] == [(1, "starintel-biz"), (3, "pro-actors")]


def test_scan_text_is_case_insensitive() -> None:
    assert scan_text("StarIntel-Farm merged verdicts") != []


def test_scan_text_does_not_flag_public_or_prose() -> None:
    text = (
        "starintel-server merged consumer timeout work\n"
        "paid pro actors wired into Quasar\n"
        "https://git.starintel.actor/nsaspy/star-lang\n"
    )
    assert scan_text(text) == []


def test_scan_paths_reports_file_locations(tmp_path: Path) -> None:
    post = tmp_path / "post.org"
    post.write_text("see ohmycaptcha harness\n", encoding="utf-8")

    hits = scan_paths([post])

    assert len(hits) == 1
    assert hits[0].path == post
    assert hits[0].line == 1
    assert hits[0].pattern == r"\bohmycaptcha\b"
