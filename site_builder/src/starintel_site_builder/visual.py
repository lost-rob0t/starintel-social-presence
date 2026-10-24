"""Browser-based visual verification.

Builds nothing by itself: given a built site directory, it serves it,
renders every check page in a real browser (Playwright + Chromium),
captures screenshots, and records console errors, failed assets, and
horizontal overflow per page/viewport. This module is optional: it
imports Playwright lazily so deterministic builds never require it.
"""

from __future__ import annotations

import functools
import http.server
import json
import shutil
import socket
import threading
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_VIEWPORTS = [
    ("desktop", 1440, 900),
    ("laptop", 1280, 800),
    ("tablet", 768, 1024),
    ("mobile", 390, 844),
    ("narrow", 320, 640),
]

DEFAULT_PAGES = [
    ("home", "/index.html"),
    ("blog-what-is-starintel", "/blog/what-is-starintel.html"),
    ("blog-bootstrapping", "/blog/bootstrapping-the-starintel-web-platform.html"),
    ("blog-git-facts", "/blog/git-facts-without-llms.html"),
    ("draft-quasar-notes", "/drafts/quasar-workbench-notes.html"),
    ("tags", "/tags/index.html"),
    ("tag-starintel", "/tags/starintel.html"),
    ("archive", "/archive.html"),
    ("docs-landing", "/docs/index.html"),
    ("docs-server-overview", "/docs/server/overview.html"),
    ("docs-ingest-dataflow", "/docs/server/ingest-dataflow.html"),
    ("docs-schema", "/docs/documents/schema-v9.html"),
    ("docs-external-server", "/docs/external/starintel-server.html"),
    ("docs-external-quasar", "/docs/external/quasar.html"),
    ("portfolio", "/portfolio/index.html"),
    ("portfolio-resume", "/portfolio/resume.html"),
    ("portfolio-starintel", "/portfolio/projects/starintel.html"),
    ("portfolio-prolog-rlm", "/portfolio/projects/prolog-rlm.html"),
    ("portfolio-about", "/portfolio/about.html"),
    ("graph", "/graph.html"),
]


@dataclass
class PageResult:
    page: str
    url: str
    viewport: str
    screenshot: str | None = None
    console_errors: list[str] = field(default_factory=list)
    failed_requests: list[str] = field(default_factory=list)
    horizontal_overflow: bool = False
    missing_primary_content: bool = False

    @property
    def ok(self) -> bool:
        return (
            not self.console_errors
            and not self.failed_requests
            and not self.horizontal_overflow
            and not self.missing_primary_content
        )


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:  # noqa: ANN002
        pass


@functools.cache
def _playwright():
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    return sync_playwright


def find_chromium() -> str | None:
    for name in ("chromium", "chromium-browser", "google-chrome", "chrome"):
        path = shutil.which(name)
        if path:
            return path
    return None


def serve_site(site_dir: Path) -> tuple[str, threading.Thread, http.server.HTTPServer]:
    """Serve site_dir on an ephemeral localhost port. Returns (base_url, thread, server)."""

    class Handler(_QuietHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(site_dir), **kwargs)

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return f"http://127.0.0.1:{port}", thread, server


def _graph_settled(page) -> bool:
    """Wait until the graph canvas has rendered its stats line."""
    try:
        page.wait_for_function(
            "() => { const el = document.getElementById('graph-stats');"
            " return el && el.textContent.trim().length > 0; }",
            timeout=8000,
        )
        return True
    except Exception:  # noqa: BLE001
        return False


def run_visual_checks(
    site_dir: Path,
    out_dir: Path,
    pages: list[tuple[str, str]] | None = None,
    viewports: list[tuple[str, int, int]] | None = None,
    executable_path: str | None = None,
    include_narrow_overflow: bool = True,
) -> list[PageResult]:
    """Render pages at viewports, capture screenshots, collect problems."""
    sync_playwright = _playwright()
    pages = pages if pages is not None else DEFAULT_PAGES
    viewports = viewports if viewports is not None else DEFAULT_VIEWPORTS
    out_dir.mkdir(parents=True, exist_ok=True)

    base_url, thread, server = serve_site(site_dir)
    results: list[PageResult] = []
    try:
        with sync_playwright() as p:
            launch_kwargs = {"headless": True}
            executable_path = executable_path or find_chromium()
            if executable_path:
                launch_kwargs["executable_path"] = executable_path
            browser = p.chromium.launch(**launch_kwargs)
            for vp_name, width, height in viewports:
                context = browser.new_context(viewport={"width": width, "height": height})
                page = context.new_page()
                console_errors: list[str] = []
                failed: list[str] = []
                page.on(
                    "console",
                    lambda msg: console_errors.append(msg.text)
                    if msg.type == "error"
                    else None,
                )
                page.on(
                    "requestfailed",
                    lambda req: failed.append(req.url),
                )
                page.on(
                    "response",
                    lambda resp: failed.append(f"{resp.status} {resp.url}")
                    if resp.status >= 400
                    else None,
                )
                for page_name, url_path in pages:
                    result = PageResult(
                        page=page_name, url=url_path, viewport=vp_name
                    )
                    console_errors.clear()
                    failed.clear()
                    try:
                        page.goto(base_url + url_path, wait_until="networkidle")
                        page.evaluate("document.fonts.ready")
                        if url_path == "/graph.html":
                            _graph_settled(page)
                        page.wait_for_timeout(400)
                        result.console_errors = list(console_errors)
                        result.failed_requests = [
                            f for f in failed if url_path in f or "assets" in f
                        ]
                        result.horizontal_overflow = page.evaluate(
                            "document.documentElement.scrollWidth"
                            " > document.documentElement.clientWidth"
                        )
                        main = page.evaluate(
                            "() => { const m = document.getElementById('main');"
                            " return m ? m.innerText.trim().length : 0; }"
                        )
                        result.missing_primary_content = main < 40
                        shot = out_dir / f"{page_name}-{vp_name}.png"
                        page.screenshot(path=str(shot), full_page=True)
                        result.screenshot = shot.name
                    except Exception as exc:  # noqa: BLE001
                        result.console_errors.append(f"render failure: {exc}")
                    results.append(result)
                if include_narrow_overflow and vp_name == "mobile":
                    # 320px overflow sweep is part of the mobile viewport pass
                    pass
                context.close()
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
    (out_dir / "report.json").write_text(
        json.dumps(
            [
                {
                    "page": r.page,
                    "url": r.url,
                    "viewport": r.viewport,
                    "screenshot": r.screenshot,
                    "console_errors": r.console_errors,
                    "failed_requests": r.failed_requests,
                    "horizontal_overflow": r.horizontal_overflow,
                    "missing_primary_content": r.missing_primary_content,
                    "ok": r.ok,
                }
                for r in results
            ],
            indent=1,
        ),
        encoding="utf-8",
    )
    return results
