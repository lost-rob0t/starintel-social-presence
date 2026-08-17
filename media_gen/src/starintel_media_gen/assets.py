from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ASSET_SCHEMA_VERSION = 1


def empty_manifest(title: str = "") -> dict[str, Any]:
    return {
        "schema_version": ASSET_SCHEMA_VERSION,
        "title": title,
        "assets": [],
    }


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("assets.json must contain a JSON object")
    if data.get("schema_version") != ASSET_SCHEMA_VERSION:
        raise ValueError(
            f"unsupported assets.json schema_version: {data.get('schema_version')!r}"
        )
    assets = data.get("assets")
    if not isinstance(assets, list):
        raise ValueError("assets.json 'assets' must be a list")
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            raise ValueError(f"asset {index} must be an object")
        if not asset.get("id"):
            raise ValueError(f"asset {index} is missing id")
        source = asset.get("source")
        if not isinstance(source, dict) or not source.get("type") or not source.get("value"):
            raise ValueError(f"asset {asset.get('id')!r} must have source.type and source.value")
    return data


def ensure_manifest(path: Path, title: str = "") -> dict[str, Any]:
    if path.exists():
        return load_manifest(path)
    data = empty_manifest(title)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
    return data


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value)
    return str(value).replace("|", "\\vert{}")


def render_org(manifest: dict[str, Any], json_path: Path) -> str:
    title = manifest.get("title") or json_path.parent.name or "Media assets"
    rows = []
    for asset in manifest["assets"]:
        source = asset["source"]
        rows.append(
            "| {id} | {kind} | {source_type} | {source_value} | {role} | {status} | {characters} |".format(
                id=_cell(asset.get("id")),
                kind=_cell(asset.get("kind")),
                source_type=_cell(source.get("type")),
                source_value=_cell(source.get("value")),
                role=_cell(asset.get("role")),
                status=_cell(asset.get("status")),
                characters=_cell(asset.get("characters")),
            )
        )
    table = "\n".join(rows) if rows else "| /no assets yet/ | | | | | | |"
    return f"""#+title: {title} — assets
#+generated_from: {json_path.name}
#+startup: overview

* Canonical manifest
This file is a generated Emacs/Org view. Do not treat it as authoritative.
Edit [[file:{json_path.name}][{json_path.name}]] and regenerate this view.

* Assets
| ID | Kind | Source type | Source | Role | Status | Characters |
|----+------+-------------+--------+------+--------+------------|
{table}

* Source semantics
- =file= :: repository/local named asset path.
- =url= :: external image/media URL.
- =generated= :: generated output path, normally ignored unless deliberately curated.
- =asset= :: reference to another asset ID in this manifest.

* Provenance :noexport:
- Canonical data lives in ={json_path.name}=.
- This Org file may be regenerated at any time.
"""


def write_org_view(json_path: Path, org_path: Path | None = None) -> Path:
    manifest = load_manifest(json_path)
    output = org_path or json_path.with_suffix(".org")
    output.write_text(render_org(manifest, json_path))
    return output
