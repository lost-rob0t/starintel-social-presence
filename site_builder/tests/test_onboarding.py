"""Onboarding content contracts: links, runnable examples and publication provenance."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import subprocess

import pytest

from starintel_site_builder.org import extract_links, parse_id_property, parse_keywords, parse_filetags
from starintel_site_builder.private_links import scan_text

ROOT = Path(__file__).resolve().parents[2]
LEGACY_HTTP_ROUTE = re.compile(r"(?:https?://[^\s/]+|[\"'=\s])/(?:new/document|new/target|document)/")
TUTORIALS = ("getting-started", "api-keys", "mcp", "cli", "actors", "local-install")
CHANGED = [ROOT / "docs/index.org", ROOT / "docs/projects.org"] + [
    ROOT / "docs/tutorials" / f"{name}.org" for name in TUTORIALS
] + [ROOT / "docs/server/quickstart.org", ROOT / "docs/documents/schema-v9.org", ROOT / "docs/documents/star-lang-0.10.1.org"]


@pytest.mark.parametrize("path", CHANGED, ids=lambda p: p.name)
def test_authored_docs_have_publication_provenance_and_working_local_links(path):
    text = path.read_text()
    metadata = parse_keywords(text)
    assert metadata["AI_GENERATED"] == "t"
    assert metadata["ROAM_VISIBILITY"] == "public"
    assert metadata["ROAM_SCHEMA"] == "org-roam-meta/v1"
    assert metadata["SOURCE"]
    ai_tag = metadata["AI_TAG"]
    assert re.fullmatch(r"ai_[a-z0-9]{12,}", ai_tag)
    tags = parse_filetags(metadata["FILETAGS"])
    assert ai_tag in tags
    assert len([tag for tag in tags if tag != "ai" and not tag.startswith("ai_")]) >= 2
    for target, _label in extract_links(text):
        if target.startswith("file:"):
            assert (path.parent / target[5:].split("::", 1)[0]).is_file(), target
    assert not scan_text(text)
    assert not LEGACY_HTTP_ROUTE.search(text)


@pytest.mark.parametrize("example", [
    "http://127.0.0.1:5000/document/example",
    '"/new/document/document"',
    " POST /new/target/actor",
])
def test_legacy_route_check_rejects_http_examples(example):
    assert LEGACY_HTTP_ROUTE.search(example)


def test_legacy_route_check_accepts_canonical_filesystem_layout():
    assert not LEGACY_HTTP_ROUTE.search("db/training/document/documents.ndjson")


def test_ids_and_ai_tags_are_unique_and_existing_ids_are_preserved():
    ids = [parse_id_property(path.read_text()) for path in CHANGED]
    tags = [parse_keywords(path.read_text())["AI_TAG"] for path in CHANGED]
    assert len(ids) == len(set(ids))
    assert len(tags) == len(set(tags))
    assert ids[0] == "docs-index"
    assert parse_id_property((ROOT / "docs/server/quickstart.org").read_text()) == "docs-server-quickstart"
    assert parse_id_property((ROOT / "docs/documents/schema-v9.org").read_text()) == "docs-documents-schema"


@pytest.mark.parametrize("name", TUTORIALS)
def test_tutorials_are_complete_and_examples_parse(name):
    text = (ROOT / "docs/tutorials" / f"{name}.org").read_text()
    assert len(text.split()) >= 600
    assert len(re.findall(r"^\* ", text, re.MULTILINE)) >= 6
    assert "troubleshoot" in text.lower() or "recovery" in text.lower() or "401" in text
    for language, code in re.findall(r"^#\+begin_src (\S+)[^\n]*\n(.*?)^#\+end_src", text, re.MULTILINE | re.DOTALL | re.IGNORECASE):
        if language in {"sh", "bash"}:
            subprocess.run(["bash", "-n"], input=code, text=True, check=True)
        elif language == "python":
            ast.parse(code)
        elif language == "json":
            json.loads(code)


def test_landing_links_every_learning_path():
    landing = (ROOT / "docs/index.org").read_text()
    for name in TUTORIALS:
        assert f"file:tutorials/{name}.org" in landing
    assert "file:projects.org" in landing
