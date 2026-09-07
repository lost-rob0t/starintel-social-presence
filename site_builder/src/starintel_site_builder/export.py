"""Org -> HTML fragment export through Emacs batch, plus Markdown conversion."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

EMACS_MANIFEST_ENTRY_LIMIT = 10000


def export_fragments(
    entries: list[dict[str, str]],
    repo_root: Path,
    build_dir: Path,
) -> dict[Path, Path]:
    """Export {src, out} Org entries to HTML fragments in build_dir.

    Returns a mapping of source Org path -> fragment path. All entries are
    exported in one Emacs process; org-roam [[id:...]] links resolve across
    the whole manifest.
    """
    if not entries:
        return {}
    build_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_dir / "export-manifest.json"
    manifest.write_text(json.dumps(entries), encoding="utf-8")
    elisp_file = repo_root / "elisp" / "starintel-site-export.el"
    cmd = [
        "emacs",
        "--batch",
        "-Q",
        "-l",
        str(elisp_file),
        "--eval",
        f'(starintel-site-export-manifest {json.dumps(str(manifest))})',
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=repo_root, timeout=600
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"emacs site export failed ({result.returncode}):\n{result.stderr}"
        )
    mapping: dict[Path, Path] = {}
    for entry in entries:
        src = Path(entry["src"])
        out = Path(entry["out"])
        if not out.is_file():
            raise RuntimeError(f"emacs did not export fragment for {src}: {out}")
        mapping[src] = out
    return mapping


def markdown_to_org(md_path: Path, build_dir: Path) -> Path:
    """Convert a Markdown file to Org with pandoc, into build_dir."""
    build_dir.mkdir(parents=True, exist_ok=True)
    out_path = build_dir / (md_path.stem + ".org")
    result = subprocess.run(
        ["pandoc", "-f", "gfm", "-t", "org", str(md_path)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pandoc failed for {md_path}: {result.stderr}")
    out_path.write_text(result.stdout, encoding="utf-8")
    return out_path


def external_repo_revision(repo_dir: Path) -> str:
    """Short HEAD revision of an external checkout, or empty string."""
    git = shutil.which("git")
    if git is None:
        return ""
    try:
        result = subprocess.run(
            [git, "-C", str(repo_dir), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def temp_manifest_dir() -> tempfile.TemporaryDirectory:
    return tempfile.TemporaryDirectory(prefix="starintel-site-")
