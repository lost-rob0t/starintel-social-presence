"""Browser smoke suite: representative pages render cleanly in Chromium.

Requires playwright + a chromium binary; skips cleanly otherwise so the
deterministic suite never depends on a browser. Full screenshot sweeps are
run by scripts/visual-check.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from starintel_site_builder.visual import (
    DEFAULT_PAGES,
    PageResult,
    find_chromium,
    run_visual_checks,
)

PLAYWRIGHT_AVAILABLE = True
try:
    import playwright  # noqa: F401
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

BROWSER_AVAILABLE = PLAYWRIGHT_AVAILABLE and find_chromium() is not None

pytestmark = pytest.mark.skipif(
    not BROWSER_AVAILABLE, reason="playwright/chromium not available"
)

SMOKE_PAGES = [
    ("home", "/index.html"),
    ("blog-post", "/blog/first-test-post.html"),
    ("docs-page", "/docs/fixture-docs.html"),
    ("graph", "/graph.html"),
]
SMOKE_VIEWPORTS = [
    ("desktop", 1440, 900),
    ("mobile", 390, 844),
]


@pytest.fixture(scope="module")
def smoke_repo(tmp_path_factory) -> Path:
    from conftest import write_repo, write_roam_db

    root = tmp_path_factory.mktemp("smoke-repo") / "repo"
    root.mkdir(parents=True)
    write_repo(root)
    write_roam_db(root, root / ".cache" / "org-roam.db")
    return root


@pytest.fixture(scope="module")
def smoke_site(tmp_path_factory, smoke_repo) -> Path:
    from starintel_site_builder.builder import build_site

    out = tmp_path_factory.mktemp("smoke") / "site"
    build_site(
        repo_root=smoke_repo,
        out_dir=out,
        build_dir=smoke_repo / ".build",
        externals=[],
    )
    return out


@pytest.fixture(scope="module")
def smoke_results(smoke_site, tmp_path_factory) -> list[PageResult]:
    return run_visual_checks(
        site_dir=smoke_site,
        out_dir=tmp_path_factory.mktemp("shots"),
        pages=SMOKE_PAGES,
        viewports=SMOKE_VIEWPORTS,
        executable_path=find_chromium(),
    )


def test_all_smoke_pages_clean(smoke_results) -> None:
    bad = [r for r in smoke_results if not r.ok]
    assert not bad, f"failing pages: {[(r.page, r.viewport, r.console_errors) for r in bad]}"


def test_no_uncaught_errors(smoke_results) -> None:
    for r in smoke_results:
        assert r.console_errors == [], f"{r.page}/{r.viewport}: {r.console_errors}"


def test_no_horizontal_overflow(smoke_results) -> None:
    for r in smoke_results:
        assert not r.horizontal_overflow, f"{r.page} overflows at {r.viewport}"


def test_primary_content_present(smoke_results) -> None:
    for r in smoke_results:
        assert not r.missing_primary_content, f"{r.page} missing content at {r.viewport}"


def test_screenshots_captured(smoke_results) -> None:
    for r in smoke_results:
        assert r.screenshot, f"no screenshot for {r.page}/{r.viewport}"


def test_default_page_matrix_covers_required_surfaces() -> None:
    urls = {u for _n, u in DEFAULT_PAGES}
    for required in (
        "/index.html",
        "/blog/what-is-starintel.html",
        "/drafts/quasar-workbench-notes.html",
        "/tags/index.html",
        "/archive.html",
        "/docs/index.html",
        "/docs/external/starintel-server.html",
        "/portfolio/index.html",
        "/portfolio/resume.html",
        "/graph.html",
    ):
        assert required in urls, f"required page missing from visual matrix: {required}"
