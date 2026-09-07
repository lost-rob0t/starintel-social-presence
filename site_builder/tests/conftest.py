"""Fixtures for deterministic site builder tests: a tiny fake repo."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

POST_A = """:PROPERTIES:
:ID: test-post-a
:END:
#+title: First Test Post
#+date: [2026-01-02 Thu]
#+author: tester
#+description: The first deterministic fixture post.
#+slug: first-test-post
#+tags: testing fixtures
#+status: POST
#+revision: 2

Intro paragraph with a link to [[id:test-doc-a][the docs page]] and a
footnote.[fn:1]

* Section One

#+begin_src json
{"key": "value", "n": 3}
#+end_src

** Nested subsection

Some prose.

* Section Two

- alpha
- beta

1. one
2. two

* Footnotes
[fn:1] A footnote body.
"""

POST_B = """:PROPERTIES:
:ID: test-post-b
:END:
#+title: Second Test Post
#+date: [2026-01-10 Sat]
#+author: tester
#+description: The second fixture post, linking back to the first.
#+slug: second-test-post
#+tags: testing

See [[id:test-post-a][the first post]].
"""

DRAFT = """#+title: Draft Notes
#+date: [2026-01-11 Sun]
#+author: tester
#+description: Unpublished fixture draft.
#+slug: draft-notes
#+status: DRAFT

A draft links to [[id:test-post-a][a published post]].
"""

DOC_A = """:PROPERTIES:
:ID: test-doc-a
:END:
#+title: Fixture Docs
#+date: [2026-01-03 Fri]
#+description: Documentation fixture with a table.
#+slug: fixture-docs
#+filetags: :docs:testing:

| Name | Role |
|------+------|
| a    | x    |
| b    | y    |
"""

DOC_NESTED = """:PROPERTIES:
:ID: test-doc-nested
:END:
#+title: Nested Docs Page
#+description: A docs page in a subdirectory.
#+slug: nested-docs

Links to [[id:test-doc-a][fixture docs]].
"""

POST_HUMAN = """:PROPERTIES:
:ID: test-post-human
:END:
#+title: Human Written Post
#+date: [2026-01-12 Mon]
#+author: nsaspy
#+description: A fixture post the editor wrote themselves.
#+slug: human-written-post
#+tags: testing human

Written by the editor, not the model.
"""

DOC_LONELY = """:PROPERTIES:
:ID: test-doc-lonely
:END:
#+title: Lonely Page
#+description: An isolated node with no links at all.
#+slug: lonely-page

Nothing links here.
"""


def write_repo(root: Path) -> None:
    (root / "blog" / "posts").mkdir(parents=True)
    (root / "blog" / "drafts").mkdir(parents=True)
    (root / "docs" / "sub").mkdir(parents=True)
    (root / "site-assets").mkdir(parents=True)
    (root / "elisp").mkdir(parents=True)
    (root / "scripts").mkdir(parents=True)
    (root / "site-assets" / "starintel.css").write_text("/* test css */\n", encoding="utf-8")
    (root / "site-assets" / "graph.js").write_text("// test js\n", encoding="utf-8")
    (root / "elisp" / "starintel-site-export.el").write_text("(provide 'starintel-site-export)\n", encoding="utf-8")
    (root / "elisp" / "starintel-roam-graph.el").write_text("(provide 'starintel-roam-graph)\n", encoding="utf-8")
    (root / "blog" / "posts" / "2026-01-02-first-test-post.org").write_text(POST_A, encoding="utf-8")
    (root / "blog" / "posts" / "2026-01-10-second-test-post.org").write_text(POST_B, encoding="utf-8")
    (root / "blog" / "drafts" / "2026-01-11-draft-notes.org").write_text(DRAFT, encoding="utf-8")
    (root / "docs" / "fixture-docs.org").write_text(DOC_A, encoding="utf-8")
    (root / "docs" / "sub" / "nested.org").write_text(DOC_NESTED, encoding="utf-8")
    (root / "blog" / "posts" / "2026-01-12-human-written-post.org").write_text(POST_HUMAN, encoding="utf-8")
    (root / "docs" / "lonely.org").write_text(DOC_LONELY, encoding="utf-8")
    # Use the repository's real exporter for full-build tests.
    repo_elisp = Path(__file__).resolve().parents[2] / "elisp" / "starintel-site-export.el"
    if repo_elisp.is_file():
        (root / "elisp" / "starintel-site-export.el").write_text(
            repo_elisp.read_text(encoding="utf-8"), encoding="utf-8"
        )


def write_roam_db(root: Path, db_path: Path) -> None:
    """Create a schema-compatible org-roam db fixture (no Emacs needed)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE files (file TEXT PRIMARY KEY, hash TEXT NOT NULL, meta TEXT);
        CREATE TABLE nodes (id TEXT PRIMARY KEY, file TEXT NOT NULL, "level" INT,
                            todo TEXT, priority TEXT, scheduled TEXT, deadline TEXT,
                            title TEXT, properties TEXT, olp TEXT);
        CREATE TABLE tags (node_id TEXT NOT NULL, tag TEXT NOT NULL);
        CREATE TABLE links (pos INT, source TEXT NOT NULL, dest TEXT NOT NULL,
                            "type" TEXT NOT NULL, properties TEXT);
        CREATE TABLE refs (node_id TEXT NOT NULL, "type" TEXT NOT NULL, ref TEXT NOT NULL);
        CREATE TABLE aliases (node_id TEXT NOT NULL, alias TEXT NOT NULL);
        CREATE TABLE keywords (key TEXT NOT NULL, value TEXT NOT NULL, file TEXT NOT NULL);
        """
    )
    q = lambda p: json_quote(str(root / p))
    nodes = [
        ("test-post-a", "blog/posts/2026-01-02-first-test-post.org", "First Test Post"),
        ("test-post-human", "blog/posts/2026-01-12-human-written-post.org", "Human Written Post"),
        ("test-post-b", "blog/posts/2026-01-10-second-test-post.org", "Second Test Post"),
        ("test-doc-a", "docs/fixture-docs.org", "Fixture Docs"),
        ("test-doc-nested", "docs/sub/nested.org", "Nested Docs Page"),
        ("test-doc-lonely", "docs/lonely.org", "Lonely Page"),
    ]
    for node_id, rel, title in nodes:
        conn.execute(
            'INSERT INTO nodes VALUES (?, ?, 0, NULL, NULL, NULL, NULL, ?, NULL, NULL)',
            (json_quote(node_id), q(rel), json_quote(title)),
        )
    conn.execute(
        "INSERT INTO tags VALUES (?, ?)",
        (json_quote("test-post-a"), json_quote("testing")),
    )
    links = [
        ("test-post-a", "test-doc-a", "id"),
        ("test-post-b", "test-post-a", "id"),
        ("test-doc-nested", "test-doc-a", "id"),
        ("test-post-a", "https://example.com", "https"),
    ]
    for src, dst, typ in links:
        conn.execute(
            'INSERT INTO links VALUES (1, ?, ?, ?, NULL)',
            (json_quote(src), json_quote(dst), json_quote(typ)),
        )
    conn.commit()
    conn.close()


def json_quote(value: str) -> str:
    """emacsql stores strings json-encoded; mirror that in the fixture."""
    import json

    return json.dumps(value)


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    write_repo(root)
    write_roam_db(root, root / ".cache" / "org-roam.db")
    return root
