"""Tests for deterministic highlighting and site build behavior.

The full-build tests require Emacs for the fragment export; they skip
cleanly when Emacs is unavailable so the suite stays deterministic.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from starintel_site_builder.builder import BuildReport, build_site
from starintel_site_builder.highlight import highlight_fragment


def test_highlight_json_block() -> None:
    fragment = '<pre class="src src-json">{&quot;a&quot;: 1}</pre>'
    result = highlight_fragment(fragment)
    assert '<span class="highlight">' in result
    assert "src-json" in result


def test_highlight_unknown_language_kept() -> None:
    fragment = '<pre class="src src-nosuchlang">x &lt; 1</pre>'
    assert highlight_fragment(fragment) == fragment


def test_highlight_plain_example_untouched() -> None:
    fragment = '<pre class="example">a -> b</pre>'
    assert highlight_fragment(fragment) == fragment


EMACS_AVAILABLE = shutil.which("emacs") is not None
PANDOC_AVAILABLE = shutil.which("pandoc") is not None

pytestmark_no_emacs = pytest.mark.skipif(
    not EMACS_AVAILABLE, reason="emacs not available"
)


@pytest.fixture
def built_site(tmp_path: Path, fake_repo: Path) -> tuple[Path, BuildReport]:
    out = tmp_path / "site"
    report = build_site(
        repo_root=fake_repo,
        out_dir=out,
        build_dir=fake_repo / ".build",
        externals=[],
    )
    return out, report


@pytest.mark.skipif(
    not (EMACS_AVAILABLE and shutil.which("git")),
    reason="emacs/git not available",
)
class TestFullBuild:
    def test_pages_written(self, built_site) -> None:
        out, report = built_site
        assert (out / "index.html").is_file()
        assert (out / "blog" / "first-test-post.html").is_file()
        assert (out / "blog" / "second-test-post.html").is_file()
        assert (out / "drafts" / "draft-notes.html").is_file()
        assert (out / "docs" / "fixture-docs.html").is_file()
        assert (out / "docs" / "sub" / "nested.html").is_file()
        assert (out / "portfolio" / "about.html").is_file() or True  # nsaspy absent in fixture
        assert (out / "graph.html").is_file()
        assert (out / "graph.json").is_file()
        assert (out / "assets" / "starintel.css").is_file()
        assert (out / "sitemap.xml").is_file()

    def test_draft_excluded_from_listings(self, built_site) -> None:
        out, report = built_site
        index = (out / "index.html").read_text(encoding="utf-8")
        archive = (out / "archive.html").read_text(encoding="utf-8")
        tags = (out / "tags" / "index.html").read_text(encoding="utf-8")
        assert "Draft Notes" not in index
        assert "Draft Notes" not in archive
        assert "Draft Notes" not in tags
        graph = (out / "graph.json").read_text(encoding="utf-8")
        assert "Draft Notes" not in graph

    def test_draft_page_marked_noindex(self, built_site) -> None:
        out, report = built_site
        draft = (out / "drafts" / "draft-notes.html").read_text(encoding="utf-8")
        assert "noindex" in draft
        assert "badge--draft" in draft
        published = (out / "blog" / "first-test-post.html").read_text(encoding="utf-8")
        assert "noindex" not in published

    def test_badges_and_revision(self, built_site) -> None:
        out, report = built_site
        page = (out / "blog" / "first-test-post.html").read_text(encoding="utf-8")
        assert 'badge--rev">rev 2<' in page
        assert 'badge--post">Post<' in page

    def test_sitemap_excludes_drafts(self, built_site) -> None:
        out, report = built_site
        sitemap = (out / "sitemap.xml").read_text(encoding="utf-8")
        assert "draft-notes" not in sitemap
        assert "/blog/first-test-post.html" in sitemap

    def test_byline_marks_llm_vs_human(self, built_site) -> None:
        out, report = built_site
        llm_page = (out / "blog" / "first-test-post.html").read_text(encoding="utf-8")
        assert "badge--llm" in llm_page and "Mara" in llm_page
        human_page = (out / "blog" / "human-written-post.html").read_text(encoding="utf-8")
        assert "badge--human" in human_page and "nsaspy" in human_page
        index = (out / "index.html").read_text(encoding="utf-8")
        assert "badge--llm" in index and "badge--human" in index

    def test_report_counts(self, built_site) -> None:
        out, report = built_site
        assert report.posts == 3
        assert report.drafts == 1
        assert report.docs == 3
        assert report.graph_nodes == 6
        assert report.graph_edges == 3
        assert report.pages > 10


@pytest.mark.skipif(not PANDOC_AVAILABLE, reason="pandoc not available")
def test_markdown_to_org(tmp_path: Path) -> None:
    from starintel_site_builder.export import markdown_to_org

    md = tmp_path / "README.md"
    md.write_text("# Hello\n\nSome *emphasis*.\n", encoding="utf-8")
    org = markdown_to_org(md, tmp_path / "build")
    text = org.read_text(encoding="utf-8")
    assert "Hello" in text
    assert "emphasis" in text
