"""Taxonomy links follow the blog surface, including on documentation pages."""

from pathlib import Path
import re

import pytest

from starintel_site_builder import render
from starintel_site_builder.models import GraphModel, SiteModel, SourceDoc


@pytest.fixture(params=["production", "staging", "single-tree"])
def bases(request, monkeypatch):
    if request.param == "single-tree":
        value = render.SiteBases()
    else:
        suffix = "starintel.actor" if request.param == "production" else "staging.example.test"
        value = render.SiteBases(
            **{host: f"https://{host}.{suffix}/" for host in render.VHOSTS}
        )
    monkeypatch.setattr(render, "_BASES", value)
    monkeypatch.setattr(render, "_PAGE_VHOST", "docs")
    return value


@pytest.mark.parametrize("surface", ["docs-page", "docs-landing", "home", "tag-index", "tag-page"])
def test_taxonomy_links_use_blog_base(bases, surface):
    doc = SourceDoc(
        path=Path("docs/tutorials/getting-started.org"),
        section="docs",
        title="Getting started",
        slug="getting-started",
        tags=("Docs", "tutorials", "human"),
        url=f"{bases.for_vhost('docs')}/tutorials/getting-started.html",
    )
    model = SiteModel(docs=[doc])
    if surface == "docs-page":
        page = render.docs_page(doc, "<p>Offline fixture</p>", model, GraphModel())
    elif surface == "docs-landing":
        page = render.docs_landing(model)
    elif surface == "home":
        render.set_page_vhost("www")
        page = render.home_page(SiteModel(), model)
    else:
        render.set_page_vhost("blog" if bases.split else "www")
        if surface == "tag-index":
            page = render.tag_index({"Docs": [doc], "tutorials": [doc]})
        else:
            page = render.tag_page("Docs", [doc])

    taxonomy_links = [
        href for href in re.findall(r'href="([^"]+)"', page) if "/tags/" in href
    ]
    blog = bases.for_vhost("blog")
    assert set(taxonomy_links) == {
        f"{blog}/tags/index.html",
        f"{blog}/tags/docs.html",
        f"{blog}/tags/tutorials.html",
    }
    if surface == "tag-page":
        # Both the primary navigation and breadcrumb must target the index.
        assert taxonomy_links.count(f"{blog}/tags/index.html") == 2
    if bases.split:
        assert f'{bases.for_vhost("www")}/tags/' not in page
    else:
        assert all(href.startswith("/tags/") for href in taxonomy_links)
