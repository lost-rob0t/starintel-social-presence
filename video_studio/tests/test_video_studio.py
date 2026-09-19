from __future__ import annotations

import json
from pathlib import Path

import pytest

from starintel_video_studio.ai import request_for_shot
from starintel_video_studio.models import load_project
from starintel_video_studio.package import publish_manifest
from starintel_video_studio.record import wf_recorder_command
from starintel_video_studio.render import render_command


def write_project(tmp_path: Path, *, fictional: bool = True) -> Path:
    path = tmp_path / "video.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "slug": "developer-makes-skynet",
                "title": "Developer Makes Skynet",
                "source": {
                    "recording": "youtube/recordings/developer-makes-skynet/master.mkv",
                    "has_audio": True,
                },
                "music": {
                    "path": "youtube/audio/developer-makes-skynet/music.wav",
                    "gain_db": -18,
                },
                "variants": [
                    {
                        "name": "youtube",
                        "width": 1920,
                        "height": 1080,
                    },
                    {
                        "name": "short",
                        "width": 1080,
                        "height": 1920,
                        "start_seconds": 12,
                        "max_seconds": 30,
                    },
                ],
                "ai_shots": [
                    {
                        "id": "boot",
                        "prompt": "A terminal boot screen used as a fictional bumper.",
                        "duration_seconds": 2.0,
                        "aspect": "16:9",
                        "output": "youtube/recordings/developer-makes-skynet/ai/boot.mp4",
                    }
                ],
                "arg": {
                    "fictional": fictional,
                    "landing_page": "https://example.invalid/arg",
                    "clues": [
                        {
                            "id": "node-7",
                            "kind": "frame_text",
                            "text": "NODE 7",
                            "start_seconds": 8.2,
                            "duration_seconds": 0.35,
                        },
                        {
                            "id": "description-1",
                            "kind": "description_token",
                            "text": "signal:47-09-18",
                        },
                    ],
                },
                "youtube": {
                    "title": "Developer Makes Skynet",
                    "description": "A normal devlog about building the Skynet runtime.",
                    "tags": ["starintel", "quasar", "prolog"],
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_load_project_and_commands(tmp_path: Path) -> None:
    project = load_project(write_project(tmp_path))
    assert project.slug == "developer-makes-skynet"
    assert len(project.variants) == 2

    record = wf_recorder_command(project, tmp_path)
    assert record[:2] == ["wf-recorder", "-a"]
    assert record[-1].endswith("/master.mkv")

    command = render_command(project, project.variants[0], tmp_path)
    joined = " ".join(command)
    assert "1920:1080" in joined
    assert "amix=inputs=2" in joined
    assert "drawtext=" in joined
    assert command[-1].endswith("/youtube.mp4")


def test_ai_request_is_provider_neutral(tmp_path: Path) -> None:
    project = load_project(write_project(tmp_path))
    request = request_for_shot(project.ai_shots[0], tmp_path)
    assert request["id"] == "boot"
    assert request["aspect"] == "16:9"
    assert str(request["output"]).endswith("/ai/boot.mp4")


def test_publish_manifest_has_three_boundaries(tmp_path: Path) -> None:
    project = load_project(write_project(tmp_path))
    manifest = publish_manifest(project, tmp_path)
    assert manifest["youtube"]["title"] == "Developer Makes Skynet"
    assert len(manifest["assets"]) == 2
    assert manifest["arg"]["fictional"] is True
    assert manifest["publishing"]["mode"] == "human-approved"


def test_arg_must_be_explicitly_fictional(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="fictional"):
        load_project(write_project(tmp_path, fictional=False))


def test_rejects_parent_path_escape(tmp_path: Path) -> None:
    path = write_project(tmp_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["source"]["recording"] = "../escape.mkv"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="repository-relative"):
        load_project(path)
