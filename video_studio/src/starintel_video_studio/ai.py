from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

from .models import AIShot, VideoProject


GENERATOR_ENV = "STARINTEL_AI_VIDEO_COMMAND_JSON"


def generator_command_from_env() -> list[str]:
    raw = os.environ.get(GENERATOR_ENV)
    if not raw:
        raise RuntimeError(
            f"{GENERATOR_ENV} is not set; configure a local or remote generator adapter"
        )
    value = json.loads(raw)
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{GENERATOR_ENV} must be a JSON array of argv strings")
    return value


def request_for_shot(shot: AIShot, root: Path) -> dict[str, object]:
    return {
        "version": 1,
        "id": shot.shot_id,
        "prompt": shot.prompt,
        "duration_seconds": shot.duration_seconds,
        "aspect": shot.aspect,
        "output": str(root / shot.output),
    }


def generate_shot(
    shot: AIShot,
    root: Path,
    *,
    command: list[str] | None = None,
) -> Path:
    argv = command or generator_command_from_env()
    output = root / shot.output
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        argv,
        input=json.dumps(request_for_shot(shot, root)),
        text=True,
        check=True,
    )
    if not output.exists():
        raise RuntimeError(
            f"generator exited successfully but did not create {output}"
        )
    return output


def select_shots(project: VideoProject, shot_id: str | None) -> tuple[AIShot, ...]:
    if shot_id is None:
        return project.ai_shots
    matches = tuple(shot for shot in project.ai_shots if shot.shot_id == shot_id)
    if not matches:
        raise ValueError(f"unknown AI shot: {shot_id}")
    return matches
