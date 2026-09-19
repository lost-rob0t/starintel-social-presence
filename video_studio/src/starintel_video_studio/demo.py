from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

from .models import VideoProject


DEMO_ENV = "STARINTEL_VIDEO_DEMO_COMMAND_JSON"


def demo_command_from_env() -> list[str]:
    raw = os.environ.get(DEMO_ENV)
    if not raw:
        raise RuntimeError(
            f"{DEMO_ENV} is not set; configure a Quasar/demo driver adapter"
        )
    value = json.loads(raw)
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{DEMO_ENV} must be a JSON array of argv strings")
    return value


def request_for_demo(project: VideoProject, root: Path) -> dict[str, object]:
    if project.demo is None:
        raise ValueError(f"video project {project.slug!r} has no demo scenario")
    return {
        "version": 1,
        "slug": project.slug,
        "title": project.title,
        "scenario": project.demo.scenario,
        "root": str(root),
    }


def run_demo(
    project: VideoProject,
    root: Path,
    *,
    command: list[str] | None = None,
) -> str:
    argv = command or demo_command_from_env()
    result = subprocess.run(
        argv,
        input=json.dumps(request_for_demo(project, root)),
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = " ".join((result.stderr or result.stdout).split())[:1000]
        suffix = f": {detail}" if detail else ""
        raise RuntimeError(
            f"demo driver failed with exit {result.returncode}{suffix}"
        )
    return result.stdout.strip() or "Demo completed."
