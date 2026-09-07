"""Tests for Org metadata parsing and the site models."""

from __future__ import annotations

from pathlib import Path

from starintel_site_builder import org as org_mod
from starintel_site_builder.models import SourceDoc

from conftest import POST_A, write_repo


def test_parse_keywords_and_tags() -> None:
    keywords = org_mod.parse_keywords(POST_A)
    assert keywords["TITLE"] == "First Test Post"
    assert keywords["SLUG"] == "first-test-post"
    assert keywords["STATUS"] == "POST"
    assert keywords["REVISION"] == "2"
    tags = org_mod.split_tags(keywords.get("TAGS"), keywords.get("FILETAGS"))
    assert tags == ("testing", "fixtures")


def test_parse_id_property() -> None:
    assert org_mod.parse_id_property(POST_A) == "test-post-a"


def test_strip_date_prefix() -> None:
    assert org_mod._strip_date_prefix("2026-01-02-first-test-post") == "first-test-post"
    assert org_mod._strip_date_prefix("resume") == "resume"


def test_first_date() -> None:
    assert org_mod._first_date("[2026-01-02 Thu]") == "2026-01-02"
    assert org_mod._first_date("2026-01-02") == "2026-01-02"
    assert org_mod._first_date("") == ""


def test_links_extraction() -> None:
    links = org_mod.extract_links(
        "See [[id:abc][x]] and [[file:~/notes.org]] and [[https://ex.com][web]]."
    )
    assert ("id:abc", "x") in links
    assert ("file:~/notes.org", "") in links
    assert all(not t.startswith("https") for t, _ in links)


def test_badge_labels(tmp_path: Path) -> None:
    doc = SourceDoc(path=tmp_path / "a.org", section="blog", title="t", slug="t", revision="3")
    assert doc.badge_labels() == ["Mara", "POST", "rev 3"]
    draft = SourceDoc(
        path=tmp_path / "b.org", section="blog", title="t", slug="t", status="DRAFT"
    )
    assert draft.is_draft and draft.badge_labels()[1] == "DRAFT"
    human = SourceDoc(
        path=tmp_path / "c.org", section="blog", title="t", slug="t", human=True
    )
    assert human.byline == "human"
    assert not doc.human and doc.byline == "Mara"


def test_scan_via_parse_source_doc(tmp_path: Path) -> None:
    write_repo(tmp_path)
    path = tmp_path / "blog" / "posts" / "2026-01-02-first-test-post.org"
    args = org_mod.parse_source_doc(path, "blog", "/blog/first-test-post.html")
    assert args["title"] == "First Test Post"
    assert args["slug"] == "first-test-post"
    assert args["doc_id"] == "test-post-a"
    assert args["date"] == "2026-01-02"
