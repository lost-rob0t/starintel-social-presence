"""Site build orchestration: scan -> export -> graph -> render."""

from __future__ import annotations

import json
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from . import export as export_mod
from . import org as org_mod
from . import render
from .graph import build_graph
from .highlight import highlight_fragment
from .models import GraphModel, SiteModel, SourceDoc
from .roam import sync_roam_db

HREF_RE = re.compile(r'href="([^"]+)"')
_ID_ATTR_RE = re.compile(r'id="([^"]+)"')


@dataclass
class ExternalDocConfig:
    name: str
    repo_dir_env: str
    entry: str = "README.md"
    title: str = ""

    def repo_dir(self) -> Path | None:
        value = None
        import os

        raw = os.environ.get(self.repo_dir_env)
        if raw:
            candidate = Path(raw).expanduser()
            if not candidate.is_absolute():
                candidate = Path.cwd() / candidate
            if candidate.is_dir():
                value = candidate
        return value


@dataclass
class BuildReport:
    posts: int = 0
    drafts: int = 0
    docs: int = 0
    portfolio: int = 0
    external: int = 0
    pages: int = 0
    graph_nodes: int = 0
    graph_edges: int = 0
    isolated: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "posts": self.posts,
            "drafts": self.drafts,
            "docs": self.docs,
            "portfolio": self.portfolio,
            "external": self.external,
            "pages": self.pages,
            "graph_nodes": self.graph_nodes,
            "graph_edges": self.graph_edges,
            "isolated": self.isolated,
        }


def _scan_section(root: Path, section: str, url_base: str, force_draft: bool = False) -> list[SourceDoc]:
    docs: list[SourceDoc] = []
    for path in sorted(root.rglob("*.org")):
        if section == "blog":
            # Blog URLs use the slug; docs/portfolio keep tree structure.
            rel = path.relative_to(root).with_suffix(".html").as_posix()
            url = f"{url_base}{rel}"
            args = org_mod.parse_source_doc(path, section, url)
            args["url"] = f"{url_base}{args['slug']}.html"
        else:
            rel = path.relative_to(root).with_suffix(".html").as_posix()
            url = f"{url_base}{rel}"
            args = org_mod.parse_source_doc(path, section, url)
        if force_draft:
            args["status"] = "DRAFT"
        docs.append(SourceDoc(path=path.resolve(), section=section, **args))
    return docs


def build_site(
    repo_root: Path,
    out_dir: Path,
    build_dir: Path,
    externals: list[ExternalDocConfig] | None = None,
) -> BuildReport:
    repo_root = repo_root.resolve()
    out_dir = out_dir.resolve()
    build_dir = build_dir.resolve()
    build_dir.mkdir(parents=True, exist_ok=True)

    posts = _scan_section(repo_root / "blog" / "posts", "blog", "/blog/")
    drafts = _scan_section(repo_root / "blog" / "drafts", "blog", "/drafts/", force_draft=True)
    docs = _scan_section(repo_root / "docs", "docs", "/docs/")
    portfolio = _scan_section(repo_root / "nsaspy", "portfolio", "/portfolio/")

    externals = externals or []
    external_docs = _prepare_external_docs(externals, build_dir, docs)
    docs = docs + external_docs

    model = SiteModel(posts=posts, drafts=drafts, docs=docs, portfolio=portfolio)

    # Graph truth: the editor's org-roam db is reused; Emacs batch syncs it
    # only when the db is missing or older than the Org content.
    db_path = sync_roam_db(repo_root)

    url_of_source: dict[Path, str] = {
        d.path: d.url for d in model.all_including_drafts()
    }

    # Export every page fragment (drafts included for local preview).
    fragment_dir = build_dir / "fragments"
    entries = []
    for doc in model.all_including_drafts():
        key = doc.url.strip("/").removesuffix(".html").replace("/", "_")
        entries.append(
            {"src": str(doc.path), "out": str(fragment_dir / f"{key}.fr.html")}
        )
    fragments = export_mod.export_fragments(entries, repo_root, fragment_dir)

    graph_model = build_graph(db_path, model.all_published(), repo_root)

    # Clean output tree, then render every page.
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    report = BuildReport(
        posts=len(posts),
        drafts=len(drafts),
        docs=len(docs) - len(external_docs),
        portfolio=len(portfolio),
        external=len(external_docs),
        graph_nodes=len(graph_model.nodes),
        graph_edges=len(graph_model.edges),
    )
    report.isolated = sorted(n.title for n in graph_model.nodes if n.degree == 0)

    anchors = _collect_anchor_ids(list(fragments.values()))
    pages_written = 0
    for doc in model.all_including_drafts():
        key = doc.url.strip("/").removesuffix(".html").replace("/", "_")
        fragment_html = fragments[doc.path].read_text(encoding="utf-8")
        fragment_html = highlight_fragment(fragment_html)
        fragment_html = _rewrite_links(
            fragment_html, doc.path, url_of_source, repo_root, anchors
        )
        page = _render_doc_page(doc, fragment_html, model, graph_model)
        target = out_dir / doc.url.strip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        pages_written += 1

    # Landing / taxonomy / timeline / graph pages.
    _write(out_dir, "index.html", render.home_page(
        SiteModel(posts=posts, portfolio=portfolio), SiteModel(docs=docs)
    ))
    pages_written += 1

    extra_pages = [
        d for d in portfolio if "/projects/" not in d.path.as_posix()
    ]
    _write(
        out_dir,
        "portfolio/index.html",
        render.portfolio_landing(
            SiteModel(posts=posts, portfolio=portfolio), extra_pages
        ),
    )
    pages_written += 1

    tags = _collect_tags(model.all_published())
    _write(out_dir, "tags/index.html", render.tag_index(tags))
    for tag, tagged in tags.items():
        _write(out_dir, f"tags/{tag.lower()}.html", render.tag_page(tag, tagged))
        pages_written += 1
    pages_written += 1

    _write(out_dir, "archive.html", render.archive_page(posts))
    pages_written += 1

    _write(out_dir, "graph.html", render.graph_page(graph_model))
    _write(out_dir, "graph.json", json.dumps(graph_model.to_json(), indent=1))
    pages_written += 2

    assets = out_dir / "assets"
    assets.mkdir(exist_ok=True)
    shutil.copy(repo_root / "site-assets" / "starintel.css", assets / "starintel.css")
    shutil.copy(repo_root / "site-assets" / "graph.js", assets / "graph.js")

    sitemap_urls = [d.url for d in model.all_published()] + [
        "/index.html",
        "/archive.html",
        "/tags/index.html",
        "/docs/index.html",
        "/portfolio/index.html",
        "/graph.html",
    ]
    _write(out_dir, "sitemap.xml", render.sitemap(sorted(set(sitemap_urls))))
    pages_written += 1

    report.pages = pages_written
    (build_dir / "report.json").write_text(
        json.dumps(report.to_json(), indent=1), encoding="utf-8"
    )
    return report


def _write(out_dir: Path, rel: str, content: str) -> None:
    target = out_dir / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _render_doc_page(
    doc: SourceDoc,
    fragment_html: str,
    model: SiteModel,
    graph_model: GraphModel,
) -> str:
    if doc.section == "docs":
        return render.docs_page(doc, fragment_html, model, graph_model)
    crumbs: list[tuple[str, str | None]]
    prev_doc = next_doc = None
    if doc.section == "blog" and not doc.is_draft:
        crumbs = [("Home", "/index.html"), ("Blog", "/index.html"), (doc.title, None)]
        chronological = sorted(model.posts, key=lambda d: d.date)
        index = chronological.index(doc)
        prev_doc = chronological[index - 1] if index > 0 else None
        next_doc = (
            chronological[index + 1] if index + 1 < len(chronological) else None
        )
    elif doc.is_draft:
        crumbs = [("Home", "/index.html"), ("Draft", None), (doc.title, None)]
    else:
        crumbs = [
            ("Home", "/index.html"),
            ("Portfolio", "/portfolio/index.html"),
            (doc.title, None),
        ]
    extra_note = ""
    if doc.section == "portfolio" and "/projects/" in doc.path.as_posix():
        extra_note = ""
    return render.article_page(
        doc, fragment_html, graph_model, crumbs, prev_doc, next_doc, extra_note
    )


def _collect_tags(docs: list[SourceDoc]) -> dict[str, list[SourceDoc]]:
    tags: dict[str, list[SourceDoc]] = defaultdict(list)
    for doc in docs:
        for tag in doc.tags:
            tags[tag].append(doc)
    return dict(tags)


def _rewrite_links(
    fragment_html: str,
    source_path: Path,
    url_of_source: dict[Path, str],
    repo_root: Path,
    anchors: set[str] | None = None,
) -> str:
    """Rewrite exported file/id link hrefs to site URLs.

    Anchors that do not exist in the target fragment are dropped: a
    file-level org-roam node id has no headline anchor in the target page.
    """

    def replace(match: re.Match) -> str:
        href = match.group(1)
        if (
            href.startswith(("http://", "https://", "mailto:", "#", "data:", "/"))
            or ":" in href.split("#")[0]
        ):
            return match.group(0)
        path_part, _, anchor = href.partition("#")
        if not (path_part.endswith(".html") or path_part.endswith(".org")):
            return match.group(0)
        candidate = Path(path_part)
        if not candidate.is_absolute():
            candidate = source_path.parent / candidate
        resolved = candidate.resolve()
        if resolved.suffix == ".html":
            resolved = resolved.with_suffix(".org")
        url = url_of_source.get(resolved)
        if url is None:
            return match.group(0)
        if anchor and anchors is not None and anchor not in anchors:
            anchor = ""
        suffix = f"#{anchor}" if anchor else ""
        return f'href="{url}{suffix}"'

    return HREF_RE.sub(replace, fragment_html)


def _collect_anchor_ids(fragment_paths: list[Path]) -> set[str]:
    anchors: set[str] = set()
    for fragment in fragment_paths:
        try:
            text = fragment.read_text(encoding="utf-8")
        except OSError:
            continue
        anchors.update(_ID_ATTR_RE.findall(text))
    return anchors


def _prepare_external_docs(
    externals: list[ExternalDocConfig],
    build_dir: Path,
    existing_docs: list[SourceDoc],
) -> list[SourceDoc]:
    """Aggregate docs pages from configured external star* repositories."""
    docs: list[SourceDoc] = []
    ext_dir = build_dir / "external-org"
    for config in externals:
        repo_dir = config.repo_dir()
        if repo_dir is None:
            continue
        entry = repo_dir / config.entry
        if not entry.is_file():
            continue
        if entry.suffix == ".org":
            org_source = entry
        else:
            org_source = export_mod.markdown_to_org(entry, ext_dir)
        revision = export_mod.external_repo_revision(repo_dir)
        url = f"/docs/external/{config.name}.html"
        args = org_mod.parse_source_doc(org_source, "docs", url)
        args.setdefault("description", "")
        title = config.title or (
            args["title"] if args["title"] != org_source.stem else config.name
        )
        doc = SourceDoc(
            path=org_source.resolve(),
            section="docs",
            title=title,
            slug=config.name,
            description=args["description"]
            or f"Aggregated from {config.name} ({config.entry}).",
            status="POST",
            revision=revision,
            doc_id=f"external:{config.name}",
            url=url,
        )
        docs.append(doc)
    return docs
