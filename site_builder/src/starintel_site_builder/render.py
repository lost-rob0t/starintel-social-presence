"""HTML page shells and layout renderers for the StarIntel site.

Python owns the site recipe: page shells (header/nav/footer), badges, card
lists, docs sidebar, portfolio hero, taxonomy/timeline views, and the graph
workspace. The Emacs export backend owns article body fragments only.
"""

from __future__ import annotations

import html
from collections import defaultdict
from dataclasses import dataclass

from .models import GraphModel, SiteModel, SourceDoc

SECTION_LABELS = {
    "blog": "Blog",
    "docs": "Docs",
    "portfolio": "Portfolio",
}


def esc(text: str) -> str:
    return html.escape(text, quote=True)


@dataclass
class NavContext:
    active: str  # blog | docs | portfolio | graph | archive | tags


def _head(title: str, description: str, draft: bool = False) -> str:
    robots = '<meta name="robots" content="noindex, nofollow">' if draft else ""
    return (
        f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{esc(title)} — StarIntel</title>'
        f'<meta name="description" content="{esc(description)}">{robots}'
        f'<link rel="icon" href="data:,">'
        f'<link rel="stylesheet" href="/assets/starintel.css">'
        f"</head>"
    )


def _header(active: str) -> str:
    links = [
        ("blog", "/index.html", "Blog"),
        ("docs", "/docs/index.html", "Docs"),
        ("portfolio", "/portfolio/index.html", "Portfolio"),
        ("graph", "/graph.html", "Graph"),
        ("archive", "/archive.html", "Archive"),
        ("tags", "/tags/index.html", "Tags"),
    ]
    items = "".join(
        f'<a href="{href}"{" aria-current=\"page\"" if key == active else ""}>{label}</a>'
        for key, href, label in links
    )
    return (
        f'<header class="site-header"><div class="site-header__inner">'
        f'<a class="brand" href="/index.html"><span class="brand__mark">★</span> '
        f'StarIntel <span class="brand__sub">editorial desk</span></a>'
        f'<nav class="site-nav" aria-label="Primary">{items}</nav>'
        f"</div></header>"
    )


def _footer() -> str:
    return (
        '<footer class="site-footer"><div class="site-footer__inner">'
        "<span>StarIntel — built from Org sources, published deliberately.</span>"
        '<span><a href="/graph.html">org-roam graph</a> · '
        '<a href="/archive.html">timeline</a> · '
        '<a href="https://starintel.actor">starintel.actor</a></span>'
        "</div></footer>"
    )


def page_shell(
    title: str,
    description: str,
    body: str,
    active: str = "",
    draft: bool = False,
) -> str:
    return (
        f'{_head(title, description, draft)}<body>'
        f'<a class="skip-link" href="#main">Skip to content</a>'
        f"{_header(active)}"
        f'<main class="site-main" id="main">{body}</main>'
        f"{_footer()}</body></html>"
    )


def breadcrumbs(parts: list[tuple[str, str | None]]) -> str:
    """parts: list of (label, url|None). Last part renders as current."""
    chunks = []
    for i, (label, url) in enumerate(parts):
        if url and i < len(parts) - 1:
            chunks.append(f'<a href="{esc(url)}">{esc(label)}</a>')
        else:
            chunks.append(f'<span class="current">{esc(label)}</span>')
    joined = '<span class="sep">/</span>'.join(chunks)
    return f'<nav class="breadcrumbs" aria-label="Breadcrumb">{joined}</nav>'


def meta_row(doc: SourceDoc) -> str:
    badges = []
    if doc.is_draft:
        badges.append('<span class="badge badge--draft">Draft</span>')
    else:
        badges.append('<span class="badge badge--post">Post</span>')
    if doc.revision:
        badges.append(f'<span class="badge badge--rev">rev {esc(doc.revision)}</span>')
    if doc.date:
        badges.append(f'<time class="meta-text" datetime="{esc(doc.date)}">{esc(doc.date)}</time>')
    if doc.author:
        badges.append(f'<span class="meta-text">{esc(doc.author)}</span>')
    for tag in doc.tags:
        badges.append(
            f'<a class="badge badge--tag" href="/tags/{esc(tag.lower())}.html">#{esc(tag)}</a>'
        )
    return f'<div class="meta-row">{"".join(badges)}</div>'


def post_card(doc: SourceDoc, kicker: str = "") -> str:
    kicker_html = f'<span class="card__kicker">{esc(kicker)}</span>' if kicker else ""
    tags = "".join(
        f'<a class="badge badge--tag" href="/tags/{esc(t.lower())}.html">#{esc(t)}</a>'
        for t in doc.tags[:4]
    )
    draft_mark = '<span class="badge badge--draft">Draft</span>' if doc.is_draft else ""
    date_html = f"<time>{esc(doc.date)}</time>" if doc.date else ""
    return (
        f'<article class="card">'
        f"{kicker_html}"
        f'<h3 class="card__title"><a href="{esc(doc.url)}">{esc(doc.title)}</a></h3>'
        f'<p class="card__desc">{esc(doc.description)}</p>'
        f'<div class="card__meta">{date_html}{draft_mark}{tags}</div>'
        f"</article>"
    )


def card_list(cards: list[str]) -> str:
    if not cards:
        return '<div class="empty-state">Nothing here yet.</div>'
    return f'<div class="card-list">{"".join(cards)}</div>'


def section_head(title: str, more_url: str = "", more_label: str = "View all") -> str:
    more = f'<a class="more" href="{esc(more_url)}">{esc(more_label)} →</a>' if more_url else ""
    return f'<div class="section-head"><h2>{esc(title)}</h2>{more}</div>'


def backlinks_section(doc: SourceDoc, model: GraphModel) -> str:
    links = model.backlinks.get(str(doc.path.resolve()), [])
    if not links:
        return ""
    items = "".join(
        f'<li><a href="{esc(url)}">{esc(title)}</a></li>' for url, title in links
    )
    count = len(links)
    return (
        f'<section class="backlinks"><h2>Linked references '
        f'<span class="badge badge--count">{count}</span></h2>'
        f'<ul>{items}</ul></section>'
    )


def pager_section(prev_doc: SourceDoc | None, next_doc: SourceDoc | None) -> str:
    if not prev_doc and not next_doc:
        return ""
    prev_html = ""
    if prev_doc:
        prev_html = (
            f'<a class="prev" href="{esc(prev_doc.url)}">'
            f'<span class="dir">← Previous</span>'
            f'<span class="pager__title">{esc(prev_doc.title)}</span></a>'
        )
    next_html = ""
    if next_doc:
        next_html = (
            f'<a class="next" href="{esc(next_doc.url)}">'
            f'<span class="dir">Next →</span>'
            f'<span class="pager__title">{esc(next_doc.title)}</span></a>'
        )
    return f'<nav class="pager" aria-label="Post navigation">{prev_html}{next_html}</nav>'


def _fragment_document(doc: SourceDoc, fragment_html: str) -> str:
    """Article body: TOC + content fragments prepared by the exporter."""
    fragment = fragment_html.replace(
        '<nav id="table-of-contents"',
        '<nav id="table-of-contents" class="toc"',
        1,
    )
    return fragment


def article_page(
    doc: SourceDoc,
    fragment_html: str,
    model: GraphModel,
    crumbs: list[tuple[str, str | None]],
    prev_doc: SourceDoc | None = None,
    next_doc: SourceDoc | None = None,
    extra_note: str = "",
) -> str:
    body = (
        '<div class="shell">'
        + breadcrumbs(crumbs)
        + '<article class="article">'
        + '<header class="article-header">'
        + f'<h1 class="page-title">{esc(doc.title)}</h1>'
        + f'<p class="page-lead">{esc(doc.description)}</p>'
        + meta_row(doc)
        + (f'<p class="meta-text">{extra_note}</p>' if extra_note else "")
        + "</header>"
        + _fragment_document(doc, fragment_html)
        + "</article>"
        + '<div class="article-footer">'
        + backlinks_section(doc, model)
        + pager_section(prev_doc, next_doc)
        + "</div>"
        + "</div>"
    )
    return page_shell(doc.title, doc.description, body, active=_section_active(doc.section), draft=doc.is_draft)


def _section_active(section: str) -> str:
    return {"blog": "blog", "docs": "docs", "portfolio": "portfolio"}.get(section, "")


def blog_index(model: SiteModel) -> str:
    cards = [post_card(p, kicker="writing") for p in model.posts]
    body = (
        '<div class="shell">'
        + breadcrumbs([("Home", "/index.html"), ("Blog", None)])
        + '<h1 class="page-title">Writing</h1>'
        + '<p class="page-lead">Technical posts and devlogs from the StarIntel editorial desk. '
        "Every claim traces back to the repositories it came from.</p>"
        + card_list(cards)
        + "</div>"
    )
    return page_shell("Blog", "StarIntel technical writing", body, active="blog")


def home_page(model: SiteModel, docs_model: SiteModel) -> str:
    latest = [post_card(p, kicker="latest") for p in model.posts[:4]]
    doc_cards = [post_card(d, kicker="docs") for d in docs_model.docs[:4]]
    projects = [
        p for p in model.portfolio if "/projects/" in p.path.as_posix()
    ]
    project_cards = [post_card(p, kicker="project") for p in projects[:4]]
    body = (
        '<div class="shell shell--wide">'
        + '<section class="hero">'
        + '<div class="hero__eyebrow">StarIntel editorial desk</div>'
        + "<h1>Local-first intelligence,<br>written in the open.</h1>"
        + '<p class="hero__lead">Technical writing, documentation, and project notes '
        "built from verified StarIntel development state — Org sources in, "
        "black-and-gold HTML out, graph included.</p>"
        + '<div class="hero__actions">'
        '<a class="btn btn--gold" href="/index.html">Read the blog</a>'
        '<a class="btn" href="/docs/index.html">Browse docs</a>'
        '<a class="btn" href="/graph.html">Open the graph</a>'
        "</div></section>"
        + section_head("Latest writing", "/archive.html", "Full timeline")
        + card_list(latest)
        + section_head("Documentation", "/docs/index.html")
        + card_list(doc_cards)
        + section_head("Projects", "/portfolio/index.html")
        + card_list(project_cards)
        + "</div>"
    )
    return page_shell("StarIntel", "Local-first intelligence, written in the open.", body, active="blog")


def tag_index(tags: dict[str, list[SourceDoc]]) -> str:
    entries = sorted(tags.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    cloud = "".join(
        f'<a href="/tags/{esc(tag.lower())}.html">#{esc(tag)} '
        f'<span class="count">{len(docs)}</span></a>'
        for tag, docs in entries
    )
    body = (
        '<div class="shell">'
        + breadcrumbs([("Home", "/index.html"), ("Tags", None)])
        + '<h1 class="page-title">Tags</h1>'
        + '<p class="page-lead">Every published tag across writing, docs, and projects.</p>'
        + f'<div class="tag-cloud">{cloud}</div>'
        + "</div>"
    )
    return page_shell("Tags", "Tag taxonomy", body, active="tags")


def tag_page(tag: str, docs: list[SourceDoc]) -> str:
    cards = [post_card(d) for d in docs]
    body = (
        '<div class="shell">'
        + breadcrumbs([("Home", "/index.html"), ("Tags", "/tags/index.html"), (f"#{tag}", None)])
        + f'<h1 class="page-title">#{esc(tag)}</h1>'
        + f'<p class="page-lead">{len(docs)} page(s) tagged #{esc(tag)}.</p>'
        + card_list(cards)
        + "</div>"
    )
    return page_shell(f"#{tag}", f"Pages tagged {tag}", body, active="tags")


def archive_page(posts: list[SourceDoc]) -> str:
    by_year: dict[str, list[SourceDoc]] = defaultdict(list)
    for post in posts:
        year = post.date[:4] if post.date else "undated"
        by_year[year].append(post)
    sections = []
    for year in sorted(by_year, reverse=True):
        by_month: dict[str, list[SourceDoc]] = defaultdict(list)
        for post in by_year[year]:
            month = post.date[5:7] if post.date else ""
            by_month[month].append(post)
        month_html = []
        for month in sorted(by_month):
            items = "".join(
                f"<li><time>{esc(p.date)}</time><a href=\"{esc(p.url)}\">{esc(p.title)}</a>"
                f"{'<span class=\"draft-marker\">draft</span>' if p.is_draft else ''}</li>"
                for p in by_month[month]
            )
            month_html.append(
                f'<div class="timeline__month">{esc(_month_name(month))}</div><ul>{items}</ul>'
            )
        sections.append(
            f'<div class="timeline__year">{esc(year)}</div>'
            f'<div class="timeline">{"".join(month_html)}</div>'
        )
    body = (
        '<div class="shell">'
        + breadcrumbs([("Home", "/index.html"), ("Archive", None)])
        + '<h1 class="page-title">Timeline</h1>'
        + '<p class="page-lead">Every published post, newest first.</p>'
        + f'<div class="archive">{"".join(sections)}</div>'
        + "</div>"
    )
    return page_shell("Archive", "Publication timeline", body, active="archive")


def _month_name(month: str) -> str:
    names = {
        "01": "January", "02": "February", "03": "March", "04": "April",
        "05": "May", "06": "June", "07": "July", "08": "August",
        "09": "September", "10": "October", "11": "November", "12": "December",
    }
    return names.get(month, month)


def portfolio_landing(model: SiteModel, extra_pages: list[SourceDoc]) -> str:
    project_cards = [
        post_card(p, kicker="project") for p in model.portfolio if "/projects/" in p.path.as_posix()
    ]
    other_cards = [post_card(p) for p in extra_pages]
    body = (
        '<div class="shell shell--wide">'
        + breadcrumbs([("Home", "/index.html"), ("Portfolio", None)])
        + '<section class="hero">'
        + '<div class="hero__eyebrow">Portfolio</div>'
        + "<h1>Things I build.</h1>"
        + '<p class="hero__lead">StarIntel and the systems around it: local-first '
        "intelligence, symbolic reasoning, and the editorial desk that writes "
        "about them.</p>"
        + '<div class="hero__actions"><a class="btn btn--gold" href="/portfolio/about.html">About me</a>'
        '<a class="btn" href="/index.html">Read the writing</a></div>'
        + "</section>"
        + section_head("Projects")
        + card_list(project_cards)
        + section_head("More")
        + card_list(other_cards)
        + "</div>"
    )
    return page_shell("Portfolio", "StarIntel projects", body, active="portfolio")


_SIDEBAR_GROUP_LABELS = {
    "server": "Server",
    "documents": "Documents",
    "actors": "Actors",
    "external": "External repositories",
    "external-org": "External repositories",
}


def docs_sidebar(docs: list[SourceDoc], current: SourceDoc | None) -> str:
    """Nested navigation grouped by first-level directory."""
    groups: dict[str, list[SourceDoc]] = defaultdict(list)
    for doc in docs:
        group = "external" if doc.url.startswith("/docs/external/") else doc.path.parent.name
        groups[group].append(doc)
    roots = [d for d in docs if d.path.parent.name == "docs" and d.url != "/docs/index.html"]
    html_parts = ['<div class="docs-sidebar" role="navigation">']
    if roots:
        html_parts.append('<div class="docs-sidebar__title">Documentation</div><ul>')
        for doc in sorted(roots, key=lambda d: d.title):
            active_cls = (
                ' class="active"'
                if current and doc.path == current.path
                else ""
            )
            html_parts.append(
                f'<li><a href="{esc(doc.url)}"{active_cls}>{esc(doc.title)}</a></li>'
            )
        html_parts.append("</ul>")
    for group in sorted(groups):
        if group == "docs":
            continue
        pages = sorted(groups[group], key=lambda d: d.title)
        label = _SIDEBAR_GROUP_LABELS.get(group, group.capitalize())
        html_parts.append(
            f'<div class="docs-sidebar__title">{esc(label)}</div><ul>'
        )
        for doc in pages:
            active_cls = (
                ' class="active"'
                if current and doc.path == current.path
                else ""
            )
            html_parts.append(
                f'<li><a href="{esc(doc.url)}"{active_cls}>{esc(doc.title)}</a></li>'
            )
        html_parts.append("</ul>")
    html_parts.append("</div>")
    return "".join(html_parts)


def docs_landing(model: SiteModel) -> str:
    cards = [post_card(d, kicker="docs") for d in model.docs]
    body = (
        '<div class="shell shell--wide">'
        + breadcrumbs([("Home", "/index.html"), ("Docs", None)])
        + '<h1 class="page-title">Documentation</h1>'
        + '<p class="page-lead">Operational documentation for StarIntel components. '
        "Aggregated pages keep their source repository and revision visible.</p>"
        + card_list(cards)
        + "</div>"
    )
    return page_shell("Docs", "StarIntel documentation", body, active="docs")


def docs_page(
    doc: SourceDoc,
    fragment_html: str,
    model: SiteModel,
    graph: GraphModel,
) -> str:
    body = (
        '<div class="shell shell--wide docs-layout">'
        + docs_sidebar(model.docs, doc)
        + '<div class="docs-content">'
        + breadcrumbs(
            [
                ("Home", "/index.html"),
                ("Docs", "/docs/index.html"),
                (doc.title, None),
            ]
        )
        + '<article class="article">'
        + '<header class="article-header">'
        + f'<h1 class="page-title">{esc(doc.title)}</h1>'
        + f'<p class="page-lead">{esc(doc.description)}</p>'
        + meta_row(doc)
        + "</header>"
        + _fragment_document(doc, fragment_html)
        + "</article>"
        + '<div class="article-footer">'
        + backlinks_section(doc, graph)
        + "</div>"
        + "</div></div>"
    )
    return page_shell(doc.title, doc.description, body, active="docs")


def graph_page(model: GraphModel) -> str:
    sections = sorted({node.section for node in model.nodes})
    checkboxes = "".join(
        f'<label><input type="checkbox" data-section="{esc(s)}" checked> '
        f"{esc(SECTION_LABELS.get(s, s))}</label>"
        for s in sections
    )
    body = (
        '<div class="graph-workspace">'
        + '<div class="graph-toolbar">'
        + '<div class="graph-sections">'
        + checkboxes
        + "</div>"
        + '<button id="graph-reheat" type="button">Reheat</button>'
        + '<span class="graph-toolbar__stats" id="graph-stats"></span>'
        + "</div>"
        + '<div class="graph-canvas-wrap">'
        + '<canvas id="graph-canvas" data-src="/graph.json"></canvas>'
        + '<div class="graph-legend">'
        + '<span><i style="background:#f5cf58"></i> blog</span>'
        + '<span><i style="background:#8fb573"></i> docs</span>'
        + '<span><i style="background:#9fc6e8"></i> portfolio</span>'
        + "</div>"
        + '<div class="graph-tooltip" id="graph-tooltip"></div>'
        + '<div class="graph-hint">org-roam graph · drag nodes · click to open</div>'
        + "</div></div>"
    )
    return page_shell(
        "Graph",
        "StarIntel org-roam graph workspace",
        body,
        active="graph",
    ) + '<script src="/assets/graph.js"></script>'


def sitemap(urls: list[str]) -> str:
    items = "".join(f"<url><loc>https://starintel.actor{esc(u)}</loc></url>" for u in urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{items}</urlset>"
    )
