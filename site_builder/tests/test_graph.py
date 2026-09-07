"""Tests for the org-roam sqlite consumer and graph model."""

from __future__ import annotations

from pathlib import Path

from starintel_site_builder.builder import _scan_section
from starintel_site_builder.graph import build_graph


def _docs(root: Path):
    posts = _scan_section(root / "blog" / "posts", "blog", "/blog/")
    drafts = _scan_section(root / "blog" / "drafts", "blog", "/drafts/", force_draft=True)
    docs = _scan_section(root / "docs", "docs", "/docs/")
    return posts, drafts, docs


def test_graph_from_roam_db(fake_repo: Path) -> None:
    root = fake_repo
    posts, drafts, docs = _docs(root)
    model = build_graph(root / ".cache" / "org-roam.db", [*posts, *docs], root)

    by_title = {n.title: n for n in model.nodes}
    assert "First Test Post" in by_title
    assert len(model.nodes) == 6  # drafts excluded
    # edges: post-a -> doc-a, post-b -> post-a, doc-nested -> doc-a
    assert len(model.edges) == 3

    first = by_title["First Test Post"]
    assert first.degree == 2  # linked from post-b; links to doc-a
    doc_a = by_title["Fixture Docs"]
    assert doc_a.degree == 2  # inbound from post-a and doc-nested

    backlinks = {title for (_url, title) in model.backlinks.get(str((root / "docs" / "fixture-docs.org").resolve()), [])}
    assert backlinks == {"First Test Post", "Nested Docs Page"}


def test_drafts_excluded_from_graph(fake_repo: Path) -> None:
    root = fake_repo
    posts, drafts, docs = _docs(root)
    assert drafts and drafts[0].is_draft
    model = build_graph(root / ".cache" / "org-roam.db", [*posts, *docs], root)
    assert "Draft Notes" not in {n.title for n in model.nodes}


def test_https_links_ignored(fake_repo: Path) -> None:
    root = fake_repo
    posts, _drafts, docs = _docs(root)
    model = build_graph(root / ".cache" / "org-roam.db", [*posts, *docs], root)
    assert all("https" not in (e.source + e.target) for e in model.edges)


def test_isolated_nodes_reported(fake_repo: Path) -> None:
    root = fake_repo
    posts, _drafts, docs = _docs(root)
    model = build_graph(root / ".cache" / "org-roam.db", [*posts, *docs], root)
    isolated = {n.title for n in model.nodes if n.degree == 0}
    # The lonely page has no links in or out.
    assert "Lonely Page" in isolated
    # The nested page links out, so it is not isolated.
    assert "Nested Docs Page" not in isolated


def test_roam_link_type_resolves_by_title(tmp_path: Path) -> None:
    from conftest import write_repo, write_roam_db
    import sqlite3
    import json

    root = tmp_path / "repo2"
    root.mkdir()
    write_repo(root)
    db = root / ".cache" / "org-roam.db"
    write_roam_db(root, db)
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO links VALUES (1, ?, ?, ?, NULL)",
        (json.dumps("test-post-b"), json.dumps("Fixture Docs"), json.dumps("roam")),
    )
    conn.commit()
    conn.close()
    posts, _drafts, docs = _docs(root)
    model = build_graph(db, [*posts, *docs], root)
    doc_a = next(n for n in model.nodes if n.title == "Fixture Docs")
    assert doc_a.degree == 3
