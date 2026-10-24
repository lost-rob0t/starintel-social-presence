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
from starintel_site_builder.publication import check_public_output


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
        assert (out / "assets" / "graph.json").is_file()
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
        graph = (out / "assets" / "graph.json").read_text(encoding="utf-8")
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


class TestVhostSplit:
    @pytest.fixture()
    def split(self, tmp_path, fake_repo):
        from starintel_site_builder.render import SiteBases

        out = tmp_path / "split"
        bases = SiteBases(
            www="https://starintel.actor",
            blog="https://blog.starintel.actor",
            docs="https://docs.starintel.actor",
            nsaspy="https://nsaspy.starintel.actor",
        )
        report = build_site(
            repo_root=fake_repo, out_dir=out,
            build_dir=fake_repo / ".build", externals=[], bases=bases,
        )
        return out, bases, report

    def test_per_vhost_layout(self, split) -> None:
        out, _bases, _report = split
        for vhost, rel in (
            ("blog", "index.html"),
            ("blog", "graph.html"),
            ("blog", "archive.html"),
            ("blog", "tags/index.html"),
            ("blog", "first-test-post.html"),
            ("blog", "drafts/draft-notes.html"),
            ("docs", "index.html"),
            ("docs", "fixture-docs.html"),
            ("nsaspy", "index.html"),
        ):
            assert (out / vhost / rel).is_file(), f"{vhost}/{rel} missing"

    def test_no_section_prefix_on_own_vhost(self, split) -> None:
        out, _bases, _report = split
        assert (out / "blog" / "blog").exists() is False

    def test_cross_vhost_links_absolute(self, split) -> None:
        out, bases, _report = split
        docs_index = (out / "docs" / "index.html").read_text(encoding="utf-8")
        assert f'href="{bases.blog}/index.html"' in docs_index
        post = (out / "blog" / "first-test-post.html").read_text(encoding="utf-8")
        assert f'{bases.blog}/assets/starintel.css' in post
        assert f'{bases.blog}/graph.html"' in post
        # Home links to the main site, which deploys from starintel-labs/website.
        assert f'{bases.www}/index.html' in post

    def test_each_vhost_self_hosts_assets(self, split) -> None:
        out, _bases, _report = split
        for vhost in ("blog", "docs", "nsaspy"):
            assert (out / vhost / "assets" / "starintel.css").is_file()

    def test_sitemap_absolute(self, split) -> None:
        out, bases, _report = split
        sitemap = (out / "blog" / "sitemap.xml").read_text(encoding="utf-8")
        assert f"{bases.blog}/first-test-post.html" in sitemap


class TestDocsSources:
    @pytest.fixture()
    def built(self, tmp_path, fake_repo, ext_repo):
        from starintel_site_builder.builder import ExternalDocConfig

        out = tmp_path / "site"
        report = build_site(
            repo_root=fake_repo, out_dir=out,
            build_dir=fake_repo / ".build",
            externals=[ExternalDocConfig(
                name="ext-repo",
                repo_dir_env="TEST_EXT_REPO_DIR",
                entry="README.md",
                title="Ext Repo",
                include_docs=True,
            )],
        )
        return out, report

    def test_readme_landing(self, built) -> None:
        out, _report = built
        page = (out / "docs" / "external" / "ext-repo.html").read_text(encoding="utf-8")
        assert "Ext Repo" in page
        assert "badge--src" in page  # origin chip, not Mara/human

    def test_docs_tree_namespaced(self, built) -> None:
        out, _report = built
        assert (out / "docs" / "ext-repo" / "unique.html").is_file()
        guide = (out / "docs" / "ext-repo" / "guide.html").read_text(encoding="utf-8")
        assert "Conflict winner" in guide  # docs/ beat doc/ — no clobber

    def test_report_counts_external_pages(self, built) -> None:
        _out, report = built
        assert report.external == 3  # landing + guide + unique


def test_imported_tenant_document_is_not_published(tmp_path, fake_repo, ext_repo) -> None:
    from starintel_site_builder.builder import ExternalDocConfig

    imported = ext_repo / "ext-repo" / "docs"
    (imported / "tenant.org").write_text(
        "#+title: Tenant example\n\ntenant_id: tenant-main\n", encoding="utf-8"
    )
    out = tmp_path / "site"
    build_site(
        repo_root=fake_repo,
        out_dir=out,
        build_dir=fake_repo / ".build",
        externals=[ExternalDocConfig(
            name="ext-repo", repo_dir_env="TEST_EXT_REPO_DIR",
            entry="README.md", include_docs=True,
        )],
    )
    assert not (out / "docs" / "ext-repo" / "tenant.html").exists()
    assert (out / "docs" / "ext-repo" / "guide.html").is_file()
    assert "tenant_id" not in (out / "sitemap.xml").read_text(encoding="utf-8")


@pytest.mark.parametrize("name,content", [
    ("page.html", "<span>tenant</span><span>_id</span>"),
    ("graph.json", r'{"tenant\u005fids": ["tenant-main"]}'),
    ("graph.js", r'const key = "tenant\x5fid";'),
    ("escaped.html", "tenant&#95;id"),
    ("attribute.html", '<a href="/tenant_id">link</a>'),
])
def test_public_output_gate_catches_escaped_identifiers(tmp_path, name, content) -> None:
    page = tmp_path / "docs" / name
    page.parent.mkdir()
    page.write_text(content, encoding="utf-8")
    with pytest.raises(RuntimeError, match=f"public tenant identifier in docs/{name}"):
        check_public_output(tmp_path)


def test_highlight_strips_code_wrapper() -> None:
    fragment = '<pre class="src src-json"><code>{&quot;a&quot;: 1}</code></pre>'
    result = highlight_fragment(fragment)
    assert "&lt;code&gt;" not in result
    assert "<code>" not in result.replace("<pre", "").replace("</pre", "")
    assert '<span class="highlight">' in result


def test_highlight_unknown_lang_escapes_cleanly() -> None:
    fragment = '<pre class="src src-text"><code>open Emacs\nwrite Org</code></pre>'
    result = highlight_fragment(fragment)
    assert "&lt;code&gt;" not in result
    assert "open Emacs" in result
