"""Typed models for the StarIntel site builder."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SourceDoc:
    """A publishable Org source document with its site metadata."""

    path: Path
    section: str  # blog | docs | portfolio
    title: str
    slug: str
    description: str = ""
    author: str = ""
    date: str = ""  # ISO date when present
    tags: tuple[str, ...] = ()
    status: str = "POST"  # POST | DRAFT
    revision: str = ""  # explicit revision label, e.g. "2"
    doc_id: str = ""  # org-roam :ID: property
    url: str = ""  # site-relative URL of the rendered page
    human: bool = False  # tagged :human: -> the editor's own writing
    origin: str = ""  # "" = this desk; "repo:<name>" = aggregated from a repo
    vhost: str = ""  # www | blog | docs | nsaspy (empty -> derived from section)

    @property
    def is_draft(self) -> bool:
        return self.status.upper() == "DRAFT"

    @property
    def byline(self) -> str:
        return "human" if self.human else "Mara"

    def vhost_name(self) -> str:
        if self.vhost:
            return self.vhost
        return {"blog": "blog", "docs": "docs", "portfolio": "nsaspy"}.get(
            self.section, "www"
        )

    def badge_labels(self) -> list[str]:
        labels = ["human" if self.human else "Mara"]
        labels.append(self.status.upper())
        if self.revision:
            labels.append(f"rev {self.revision}")
        return labels


@dataclass
class GraphNode:
    doc_id: str
    title: str
    section: str
    href: str
    degree: int = 0
    tags: list[str] = field(default_factory=list)


@dataclass
class GraphEdge:
    source: str
    target: str


@dataclass
class GraphModel:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    backlinks: dict[str, list[tuple[str, str]]] = field(default_factory=dict)

    def to_json(self) -> dict:
        return {
            "nodes": [
                {
                    "id": n.doc_id,
                    "title": n.title,
                    "section": n.section,
                    "href": n.href,
                    "degree": n.degree,
                    "tags": n.tags,
                }
                for n in self.nodes
            ],
            "edges": [{"source": e.source, "target": e.target} for e in self.edges],
        }


@dataclass
class SiteModel:
    posts: list[SourceDoc] = field(default_factory=list)
    drafts: list[SourceDoc] = field(default_factory=list)
    docs: list[SourceDoc] = field(default_factory=list)
    portfolio: list[SourceDoc] = field(default_factory=list)

    def all_published(self) -> list[SourceDoc]:
        return [*self.posts, *self.docs, *self.portfolio]

    def all_including_drafts(self) -> list[SourceDoc]:
        return [*self.posts, *self.drafts, *self.docs, *self.portfolio]
