"""Build an org-roam sqlite database with Emacs, then consume it.

Emacs owns graph truth. The editor (org-roam-mode + .dir-locals.el) keeps
the repo-local database at ``.cache/org-roam.db`` updated on save; this
module reuses that database and only runs a batch ``org-roam-db-sync`` when
the database is missing or older than the Org content. The site builder
never maintains a parallel graph.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

_DEFAULT_STRAIGHT_REPOS = Path.home() / ".config/emacs/.local/straight/repos"

# org-roam's declared dependencies that live as separate straight repos.
_ROAM_DEPS = ["compat", "dash.el", "emacsql"]
_BUILD_DEPS = ["magit-section"]

DB_RELATIVE = ".cache/org-roam.db"


def shared_db_path(repo_root: Path) -> Path:
    """The repo-local org-roam db, shared between editor and site builder."""
    return repo_root / DB_RELATIVE


def _candidate_straight_repos() -> list[Path]:
    configured = os.environ.get("STARINTEL_STRAIGHT_REPOS")
    candidates = [Path(configured)] if configured else []
    candidates.append(_DEFAULT_STRAIGHT_REPOS)
    return candidates


def resolve_org_roam_load_path() -> list[Path]:
    """Locate org-roam and its dependencies in a local straight install."""
    for repos in _candidate_straight_repos():
        if not repos.is_dir():
            continue
        load_path: list[Path] = []
        for dep in _ROAM_DEPS:
            dep_dir = repos / dep
            if dep_dir.is_dir():
                load_path.append(dep_dir)
        if not (repos / "org-roam").is_dir():
            continue
        load_path.append(repos / "org-roam")
        # magit-section lives in a versioned build directory (Doom/straight).
        for build_dir in sorted(repos.parent.glob("build-*/magit-section")):
            load_path.append(build_dir)
            break
        return load_path
    return []


def _db_is_current(db_path: Path, content_roots: list[Path]) -> bool:
    """True when the db exists and is newer than every Org source."""
    if not db_path.is_file():
        return False
    db_mtime = db_path.stat().st_mtime
    for root in content_roots:
        if not root.is_dir():
            continue
        for org_file in root.rglob("*.org"):
            if org_file.stat().st_mtime > db_mtime:
                return False
    return True


def sync_roam_db(repo_root: Path, db_path: Path | None = None) -> Path:
    """Ensure the org-roam db for repo_root is current; return its path.

    Passing an explicit db_path is supported for tests; production builds
    share the editor's database at DB_RELATIVE.
    """
    target = db_path or shared_db_path(repo_root)
    content_roots = [
        repo_root / "blog",
        repo_root / "docs",
        repo_root / "nsaspy",
    ]
    if _db_is_current(target, content_roots):
        return target

    load_path = resolve_org_roam_load_path()
    if not load_path:
        raise RuntimeError(
            "org-roam not found; set STARINTEL_STRAIGHT_REPOS to the straight repos directory"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    forms = "(progn " + " ".join(
        f"(add-to-list 'load-path {json.dumps(str(p))})" for p in load_path
    ) + ")"
    cmd = [
        "emacs",
        "--batch",
        "-Q",
        *[f"--eval={forms}"],
        "-l",
        str(repo_root / "elisp" / "starintel-roam-graph.el"),
        "--eval",
        "(unless (file-exists-p (starintel-roam-graph-sync "
        f"{json.dumps(str(repo_root))} {json.dumps(str(target))})) "
        "(error \"org-roam db was not created\"))",
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=repo_root, timeout=600
    )
    if result.returncode != 0:
        raise RuntimeError(f"org-roam db sync failed:\n{result.stderr}")
    if not target.is_file():
        raise RuntimeError("org-roam db sync produced no database")
    return target
