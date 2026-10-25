"""Site build orchestration: scan -> export -> graph -> render."""

from __future__ import annotations

import dataclasses
import json
import re
from urllib.parse import urlparse
import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from pathlib import Path

from . import export as export_mod
from . import org as org_mod
from . import render
from .graph import build_graph
from .highlight import highlight_fragment
from .models import GraphModel, SiteModel, SourceDoc
from .publication import check_public_output, contains_tenant_identifier
from .roam import sync_roam_db

HREF_RE = re.compile(r'href="([^"]+)"')
_ID_ATTR_RE = re.compile(r'id="([^"]+)"')


@dataclass
class ExternalDocConfig:
    """A public repository whose docs the site aggregates.

    The README (or configured entry) becomes the repository's landing page;
    with include_docs, every ``docs/**.org`` in the checkout is published
    under /docs/<name>/..., revision-pinned to the checkout's HEAD.
    """

    name: str
    repo_dir_env: str
    entry: str = "README.md"
    title: str = ""
    include_docs: bool = False

    @property
    def display_name(self) -> str:
        return self.title

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
    bases: render.SiteBases | None = None,
    docs_sources: list[ExternalDocConfig] | None = None,
) -> BuildReport:
    repo_root = repo_root.resolve()
    out_dir = out_dir.resolve()
    build_dir = build_dir.resolve()
    build_dir.mkdir(parents=True, exist_ok=True)
    bases = bases or render.SiteBases()
    render.set_bases(bases)

    posts = _scan_section(repo_root / "blog" / "posts", "blog", "/blog/")
    drafts = _scan_section(repo_root / "blog" / "drafts", "blog", "/drafts/", force_draft=True)
    docs = _scan_section(repo_root / "docs", "docs", "/docs/")
    archive_file = repo_root / "docs/archive.json"
    archived_paths = set(json.loads(archive_file.read_text())) if archive_file.exists() else set()
    docs = [
        dataclasses.replace(
            doc, archived=doc.path.relative_to(repo_root / "docs").as_posix() in archived_paths
        )
        for doc in docs
    ]
    portfolio = _scan_section(repo_root / "nsaspy", "portfolio", "/portfolio/")

    sources = docs_sources if docs_sources is not None else externals or []
    external_docs = _prepare_external_docs(sources, build_dir, docs)
    docs = docs + external_docs

    model = SiteModel(posts=posts, drafts=drafts, docs=docs, portfolio=portfolio)

    # Apply per-vhost base URLs. On its own vhost a page drops the section
    # prefix: blog.starintel.actor/what-is-starintel.html, not /blog/... .
    # The based copies become the authoritative model for every downstream
    # renderer (cards, graph, pager, backlinks, sitemap).
    all_docs = model.all_including_drafts()
    if bases.split:
        based = []
        for d in all_docs:
            path = re.sub(r"^/(blog|docs|portfolio)/", "/", d.url)
            based.append(
                dataclasses.replace(d, url=bases.for_vhost(d.vhost_name()) + path)
            )
        model = SiteModel(
            posts=[d for d in based if d.section == "blog" and not d.is_draft],
            drafts=[d for d in based if d.is_draft],
            docs=[d for d in based if d.section == "docs"],
            portfolio=[d for d in based if d.section == "portfolio"],
        )
    url_of_source: dict[Path, str] = {d.path: d.url for d in model.all_including_drafts()}

    # Export every page fragment (drafts included for local preview).
    fragment_dir = build_dir / "fragments"
    entries = []
    for doc in model.all_including_drafts():
        key = urlparse(doc.url).path.strip("/").removesuffix(".html").replace("/", "_")
        entries.append(
            {"src": str(doc.path), "out": str(fragment_dir / f"{key}.fr.html")}
        )
    fragments = export_mod.export_fragments(entries, repo_root, fragment_dir)

    # Graph truth: the editor's org-roam db is reused; Emacs batch syncs it
    # only when the db is missing or older than the Org content.
    db_path = sync_roam_db(repo_root)
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
        key = urlparse(doc.url).path.strip("/").removesuffix(".html").replace("/", "_")
        fragment_html = fragments[doc.path].read_text(encoding="utf-8")
        fragment_html = highlight_fragment(fragment_html)
        fragment_html = _rewrite_links(
            fragment_html, doc.path, url_of_source, repo_root, anchors
        )
        if doc.path == repo_root / "docs/index.org":
            for archived in model.docs:
                if archived.archived:
                    fragment_html = re.sub(
                        r'<a href="' + re.escape(archived.url) + r'">.*?</a>',
                        '<a href="https://spec.starintel.actor/latest/">Current StarIntel specification</a>',
                        fragment_html,
                    )
        render.set_page_vhost(doc.vhost_name())
        page = _render_doc_page(doc, fragment_html, model, graph_model)
        target = _out_path(out_dir, bases, doc.vhost_name(), doc.url)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8")
        pages_written += 1

    # Landing / taxonomy / timeline / graph pages live on the www vhost.
    def www_write(rel: str, build: callable) -> None:
        nonlocal pages_written
        render.set_page_vhost("www")
        _write_out(out_dir, bases, "www", rel, build())
        pages_written += 1

    if not bases.split:
        www_write("index.html", lambda: render.home_page(
            SiteModel(posts=posts, portfolio=portfolio), SiteModel(docs=docs)
        ))

    # Blog vhost landing: the chronological blog index.
    render.set_page_vhost("blog")
    _write_out(out_dir, bases, "blog", "index.html", render.blog_index(
        SiteModel(posts=posts)
    ))
    pages_written += 1

    # Docs vhost landing: content-provided index.org wins; otherwise a
    # generated landing keeps the vhost root resolvable.
    if not any(
        d.section == "docs" and d.url.endswith("/index.html") for d in docs
    ):
        render.set_page_vhost("docs")
        _write_out(out_dir, bases, "docs", "index.html", render.docs_landing(
            SiteModel(docs=docs)
        ))
        pages_written += 1

    render.set_page_vhost("docs")
    archived_docs = [d for d in model.docs if d.archived]
    archive_links = "".join(
        f'<li><a href="{render.esc(d.url)}">{render.esc(d.title)}</a></li>'
        for d in archived_docs
    )
    _write_out(out_dir, bases, "docs", "versions.html", render.page_shell(
        "Older documentation", "Historical documentation retained for existing consumers",
        '<div class="shell"><h1>Older documentation</h1>'
        '<p><a href="https://spec.starintel.actor/latest/">Current specification</a> · '
        '<a href="https://spec.starintel.actor/versions.json">Spec releases</a></p>'
        f'<ul>{archive_links}</ul></div>', active="docs", draft=True))
    pages_written += 1

    extra_pages = [
        d for d in portfolio if "/projects/" not in d.path.as_posix()
    ]
    render.set_page_vhost("nsaspy")
    _write_out(
        out_dir, bases, "nsaspy", "index.html",
        render.portfolio_landing(
            SiteModel(posts=posts, portfolio=portfolio), extra_pages
        ),
    )
    pages_written += 1

    tags = _collect_tags(model.all_published())
    # Timeline, taxonomy, and the graph workspace ride the blog vhost
    # (the www/main-site vhost deploys from starintel-labs/website).
    surface = "blog" if bases.split else "www"

    def surface_write(rel: str, build: callable) -> None:
        nonlocal pages_written
        render.set_page_vhost("blog" if bases.split else "www")
        _write_out(out_dir, bases, surface, rel, build())
        pages_written += 1

    surface_write("tags/index.html", lambda: render.tag_index(tags))
    for tag, tagged in tags.items():
        surface_write(f"tags/{tag.lower()}.html",
                      lambda t=tag, docs=tagged: render.tag_page(t, docs))

    surface_write("archive.html", lambda: render.archive_page(posts))

    surface_write("graph.html", lambda: render.graph_page(graph_model))
    _write_out(out_dir, bases, surface, "assets/graph.json",
               json.dumps(graph_model.to_json(), indent=1))

    vhosts = render.VHOSTS if bases.split else ("",)
    for vhost in vhosts:
        assets = out_dir / vhost / "assets" if bases.split else out_dir / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        shutil.copy(repo_root / "site-assets" / "starintel.css", assets / "starintel.css")
        shutil.copy(repo_root / "site-assets" / "graph.js", assets / "graph.js")

    if bases.split:
        sitemap_urls = [d.url for d in model.all_published()] + [
            render.home_url(),
            f"{render.vbase('blog')}/archive.html",
            f"{render.vbase('blog')}/tags/index.html",
            f"{render.vbase('docs')}/index.html",
            f"{render.vbase('nsaspy')}/index.html",
            f"{render.vbase('blog')}/graph.html",
        ]
    else:
        sitemap_urls = [d.url for d in model.all_published()] + [
            "/index.html",
            "/archive.html",
            "/tags/index.html",
            "/docs/index.html",
            "/portfolio/index.html",
            "/graph.html",
        ]
    _write_out(out_dir, bases, "blog" if bases.split else "www",
               "sitemap.xml", render.sitemap(sorted(set(sitemap_urls))))
    pages_written += 1

    check_public_output(out_dir)
    report.pages = pages_written
    (build_dir / "report.json").write_text(
        json.dumps(report.to_json(), indent=1), encoding="utf-8"
    )
    return report


def _write(out_dir: Path, rel: str, content: str) -> None:
    target = out_dir / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _out_path(out_dir: Path, bases: render.SiteBases, vhost: str, url: str) -> Path:
    rel = urlparse(url).path.lstrip("/")
    if bases.split:
        return out_dir / vhost / rel
    return out_dir / rel


_COMBINED_DIR = {"blog": "blog", "docs": "docs", "nsaspy": "portfolio"}


def _write_out(
    out_dir: Path, bases: render.SiteBases, vhost: str, rel: str, content: str
) -> None:
    if bases.split:
        _write(out_dir / vhost, rel, content)
    elif vhost == "www" or vhost == "":
        _write(out_dir, rel, content)
    else:
        # Single-tree preview: landings nest under their URL section.
        _write(out_dir / _COMBINED_DIR[vhost], rel, content)


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
        crumbs = [("Home", render.home_url()), ("Blog", render.home_url()), (doc.title, None)]
        chronological = sorted(model.posts, key=lambda d: d.date)
        index = next(i for i, d in enumerate(chronological) if d.path == doc.path)
        prev_doc = chronological[index - 1] if index > 0 else None
        next_doc = (
            chronological[index + 1] if index + 1 < len(chronological) else None
        )
    elif doc.is_draft:
        crumbs = [("Home", render.home_url()), ("Draft", None), (doc.title, None)]
    else:
        crumbs = [
            ("Home", render.home_url()),
            ("Portfolio", f"{render.vbase('nsaspy')}/index.html"),
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
    """Aggregate docs pages from configured external star* repositories.

    Each page gets a stable synthetic :ID: (external-<name>) in a
    build-local copy of the source, so roam-style id links can target it
    without mutating the upstream checkout.
    """
    docs: list[SourceDoc] = []
    ext_dir = build_dir / "external-org"
    ext_dir.mkdir(parents=True, exist_ok=True)
    for config in externals:
        repo_dir = config.repo_dir()
        entry = repo_dir / config.entry if repo_dir else None
        synthetic_id = f"external-{config.name}"
        org_source = ext_dir / f"{config.name}.org"
        if entry and entry.is_file():
            if entry.suffix == ".org":
                body = entry.read_text(encoding="utf-8")
            else:
                body = export_mod.markdown_to_org(entry, ext_dir).read_text(
                    encoding="utf-8"
                )
            revision = export_mod.external_repo_revision(repo_dir)
            description = f"Aggregated from {config.name} ({config.entry})."
            if contains_tenant_identifier(body):
                body = "* Not available on the public site\n"
        else:
            body = (
                f"* Not available in this build\n\n"
                f"Aggregation skipped: the {config.name} checkout is not "
                "configured in this environment. This page exists so links "
                "to it resolve; it will carry the repository's README once "
                "the checkout is configured.\n"
            )
            revision = ""
            description = (
                f"Placeholder: {config.name} ({config.entry}) is not "
                "configured in this build environment."
            )
        header = f":PROPERTIES:\n:ID: {synthetic_id}\n:END:\n"
        if not re.search(r"^#\+title:", body, re.MULTILINE | re.IGNORECASE):
            header += f"#+title: {config.display_name or config.name}\n"
        org_source.write_text(header + body, encoding="utf-8")
        url = f"/docs/external/{config.name}.html"
        args = org_mod.parse_source_doc(org_source, "docs", url)
        args.setdefault("description", "")
        title = config.display_name or (
            args["title"] if args["title"] != org_source.stem else config.name
        )
        doc = SourceDoc(
            path=org_source.resolve(),
            section="docs",
            title=title,
            slug=config.name,
            description=args["description"] or description,
            status="POST",
            revision=revision,
            doc_id=synthetic_id,
            url=url,
            origin=f"repo:{config.name}",
        )
        docs.append(doc)
        if config.include_docs and repo_dir:
            docs.extend(_repo_docs_pages(config, repo_dir, ext_dir, revision))
    return docs


def _repo_docs_pages(
    config: ExternalDocConfig,
    repo_dir: Path,
    ext_dir: Path,
    revision: str,
) -> list[SourceDoc]:
    """Publish every docs/**.org (and doc/**.org) from a repository checkout.

    Pages are namespaced under /docs/<name>/ and carry origin metadata so
    they are attributed to the repository, not to the desk. ``docs/`` is
    scanned first; ``doc/`` entries only fill paths that ``docs/`` did not
    claim, so neither directory clobbers the other.
    """
    candidates: dict[str, Path] = {}
    for subdir in ("docs", "doc"):
        root = repo_dir / subdir
        if not root.is_dir():
            continue
        for org_file in sorted(root.rglob("*.org")):
            rel = org_file.relative_to(root).as_posix()
            candidates.setdefault(rel, org_file)
    if not candidates:
        return []
    pages: list[SourceDoc] = []
    for rel_posix, org_file in sorted(candidates.items()):
        text = org_file.read_text(encoding="utf-8")
        if contains_tenant_identifier(rel_posix) or contains_tenant_identifier(text):
            continue
        rel = PurePosixPath(rel_posix)
        synthetic_id = "external-{}-{}".format(
            config.name,
            re.sub(r"[^a-z0-9]+", "-", rel_posix.lower()).strip("-"),
        )
        out_org = ext_dir / config.name / rel
        out_org.parent.mkdir(parents=True, exist_ok=True)
        if ":ID:" not in text:
            text = f":PROPERTIES:\n:ID: {synthetic_id}\n:END:\n" + text
        else:
            text = re.sub(
                r"^\s*:ID:\s*(\S+)\s*$",
                f":ID: {synthetic_id}",
                text,
                count=1,
                flags=re.MULTILINE,
            )
        out_org.write_text(text, encoding="utf-8")
        url = f"/docs/{config.name}/{rel.with_suffix('.html').as_posix()}"
        args = org_mod.parse_source_doc(out_org, "docs", url)
        page = SourceDoc(
            path=out_org.resolve(),
            section="docs",
            title=args["title"],
            slug=f"{config.name}-{args['slug']}",
            description=args["description"]
            or f"{config.name} documentation ({rel_posix}).",
            status="POST",
            revision=revision,
            doc_id=synthetic_id,
            url=url,
            origin=f"repo:{config.name}",
        )
        pages.append(page)
    return pages
