"""Consume the org-roam sqlite database into the site graph model.

Graph truth is owned by org-roam: Emacs syncs the db (see roam.py), and this
module reads ``nodes``, ``links``, and ``tags`` tables with stdlib sqlite3.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import GraphEdge, GraphModel, GraphNode, SourceDoc


def _connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.is_file():
        raise RuntimeError(f"org-roam db not found: {db_path}")
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


def _decode(value: object) -> object:
    """Decode emacsql-encoded strings (json-quoted) from raw sqlite reads."""
    if isinstance(value, str) and len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
    return value


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _level0_titles(conn: sqlite3.Connection) -> dict[str, tuple[str, str]]:
    """Map file path -> (node id, title) for file-level nodes."""
    result: dict[str, tuple[str, str]] = {}
    for node_id, file, level, title in conn.execute(
        'SELECT id, file, "level", title FROM nodes'
    ):
        node_id, file, title = _decode(node_id), _decode(file), _decode(title)
        if str(level) == "0" and file not in result:
            result[file] = (node_id, title or Path(file).stem)
    return result


def _node_id_to_file(conn: sqlite3.Connection) -> dict[str, str]:
    return {
        _decode(node_id): _decode(file)
        for node_id, file in conn.execute("SELECT id, file FROM nodes")
    }


def _resolve_file_link(dest: str, source_file: Path, repo_root: Path) -> Path | None:
    candidates = [Path(dest)]
    if not Path(dest).is_absolute():
        candidates.append(source_file.parent / dest)
        candidates.append(repo_root / dest)
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.suffix == ".org" and resolved.is_file():
            return resolved
    return None


def build_graph(
    db_path: Path,
    docs: list[SourceDoc],
    repo_root: Path,
) -> GraphModel:
    """Build the site graph from an org-roam db over the published docs.

    The links table stores (pos, source-node-id, dest, type, properties).
    Source and destination node IDs are mapped back to their files;
    ``roam`` fuzzy links are resolved by title. Draft documents are
    excluded from the graph entirely.
    """
    conn = _connect(db_path)
    try:
        titles = _level0_titles(conn)
        id_to_file = _node_id_to_file(conn)
        has_tags = _table_exists(conn, "tags")
        title_to_file = {
            title.lower(): file
            for file, (_id, title) in titles.items()
        }

        published: dict[str, SourceDoc] = {}
        for doc in docs:
            if doc.is_draft:
                continue
            published[str(doc.path.resolve())] = doc

        model = GraphModel()
        page_ids: dict[str, str] = {}
        for file_str, doc in published.items():
            node_id, _title = titles.get(file_str, (f"file:{doc.slug}", doc.title))
            page_ids[file_str] = node_id
            model.nodes.append(
                GraphNode(
                    doc_id=node_id,
                    title=doc.title,
                    section=doc.section,
                    href=doc.url,
                )
            )

        seen_edges: set[tuple[str, str]] = set()
        for source_id, dest, link_type in conn.execute(
            "SELECT source, dest, \"type\" FROM links"
        ):
            source_id, dest, link_type = (
                _decode(source_id),
                _decode(dest),
                _decode(link_type),
            )
            source_file = id_to_file.get(source_id)
            if not source_file or source_file not in published:
                continue
            target_file: str | None = None
            if link_type == "id":
                target_file = id_to_file.get(dest)
            elif link_type == "file":
                resolved = _resolve_file_link(
                    dest, Path(source_file), repo_root
                )
                target_file = str(resolved) if resolved else None
            elif link_type == "roam":
                target_file = title_to_file.get(dest.lower())
            if not target_file or target_file not in published:
                continue
            if target_file == source_file:
                continue
            edge = (page_ids[source_file], page_ids[target_file])
            if edge in seen_edges:
                continue
            seen_edges.add(edge)
            model.edges.append(GraphEdge(source=edge[0], target=edge[1]))
            model.backlinks.setdefault(target_file, []).append(
                (published[source_file].url, published[source_file].title)
            )

        for node in model.nodes:
            node.degree = sum(
                1
                for e in model.edges
                if e.source == node.doc_id or e.target == node.doc_id
            )

        if has_tags:
            _attach_tags(conn, model, titles)
        return model
    finally:
        conn.close()


def _attach_tags(
    conn: sqlite3.Connection,
    model: GraphModel,
    titles: dict[str, tuple[str, str]],
) -> None:
    """Attach org-roam tags to graph nodes via each page's file-level node."""
    tags_by_node: dict[str, list[str]] = {}
    for node_id, tag in conn.execute("SELECT node_id, tag FROM tags"):
        tags_by_node.setdefault(_decode(node_id), []).append(_decode(tag))
    for node in model.nodes:
        node.tags = sorted(set(tags_by_node.get(node.doc_id, [])))


def export_json(model: GraphModel) -> dict:
    return model.to_json()
