from __future__ import annotations

from pathlib import Path
import subprocess

from .models import VideoProject


def recording_path(project: VideoProject, root: Path) -> Path:
    return root / project.recording


def wf_recorder_command(
    project: VideoProject,
    root: Path,
    *,
    audio: bool = True,
    geometry: str | None = None,
) -> list[str]:
    output = recording_path(project, root)
    command = ["wf-recorder"]
    if audio:
        command.append("-a")
    if geometry:
        command.extend(["-g", geometry])
    command.extend(["-f", str(output)])
    return command


def record(
    project: VideoProject,
    root: Path,
    *,
    audio: bool = True,
    geometry: str | None = None,
) -> Path:
    output = recording_path(project, root)
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        wf_recorder_command(project, root, audio=audio, geometry=geometry),
        check=True,
    )
    return output
