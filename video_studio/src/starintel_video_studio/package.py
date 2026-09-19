from __future__ import annotations

import json
from pathlib import Path

from .models import VideoProject
from .render import output_path


def publish_manifest(project: VideoProject, root: Path) -> dict[str, object]:
    arg = None
    if project.arg is not None:
        arg = {
            "fictional": project.arg.fictional,
            "landing_page": project.arg.landing_page,
            "description_tokens": [
                clue.text
                for clue in project.arg.clues
                if clue.kind == "description_token"
            ],
        }

    return {
        "version": 1,
        "slug": project.slug,
        "youtube": {
            "title": project.youtube.title,
            "description": project.youtube.description,
            "tags": list(project.youtube.tags),
        },
        "assets": [
            {
                "variant": variant.name,
                "width": variant.width,
                "height": variant.height,
                "path": str(output_path(project, variant, root)),
            }
            for variant in project.variants
        ],
        "arg": arg,
        "publishing": {
            "mode": "human-approved",
            "note": (
                "This package is ready for an uploader or ads adapter, "
                "but this repository does not autonomously publish or spend money."
            ),
        },
    }


def write_publish_manifest(project: VideoProject, root: Path) -> Path:
    path = root / "youtube" / "renders" / project.slug / "publish.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(publish_manifest(project, root), indent=2) + "\n",
        encoding="utf-8",
    )
    return path
