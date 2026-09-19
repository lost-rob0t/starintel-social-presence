from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True, slots=True)
class RenderVariant:
    name: str
    width: int
    height: int
    start_seconds: float = 0.0
    max_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class MusicBed:
    path: str
    gain_db: float = -16.0


@dataclass(frozen=True, slots=True)
class AIShot:
    shot_id: str
    prompt: str
    duration_seconds: float
    aspect: str
    output: str


@dataclass(frozen=True, slots=True)
class ARGClue:
    clue_id: str
    kind: str
    text: str
    start_seconds: float | None = None
    duration_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class ARGConfig:
    fictional: bool
    landing_page: str | None
    clues: tuple[ARGClue, ...]


@dataclass(frozen=True, slots=True)
class YouTubeMetadata:
    title: str
    description: str
    tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VideoProject:
    version: int
    slug: str
    title: str
    recording: str
    recording_has_audio: bool
    variants: tuple[RenderVariant, ...]
    music: MusicBed | None
    ai_shots: tuple[AIShot, ...]
    arg: ARGConfig | None
    youtube: YouTubeMetadata


def _require_relpath(value: Any, field: str) -> str:
    path = Path(str(value))
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field} must be a repository-relative path")
    return path.as_posix()


def _variant(raw: dict[str, Any]) -> RenderVariant:
    name = str(raw["name"])
    width = int(raw["width"])
    height = int(raw["height"])
    start = float(raw.get("start_seconds", 0.0))
    max_seconds = raw.get("max_seconds")
    if width <= 0 or height <= 0:
        raise ValueError(f"variant {name!r} dimensions must be positive")
    if start < 0:
        raise ValueError(f"variant {name!r} start_seconds must be >= 0")
    if max_seconds is not None and float(max_seconds) <= 0:
        raise ValueError(f"variant {name!r} max_seconds must be > 0")
    return RenderVariant(
        name=name,
        width=width,
        height=height,
        start_seconds=start,
        max_seconds=None if max_seconds is None else float(max_seconds),
    )


def load_project(path: str | Path) -> VideoProject:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    version = int(raw.get("version", 1))
    if version != 1:
        raise ValueError(f"unsupported video project version: {version}")

    slug = str(raw["slug"])
    if not _SLUG.fullmatch(slug):
        raise ValueError("slug must be lowercase kebab-case")

    source = raw["source"]
    variants = tuple(_variant(item) for item in raw.get("variants", ()))
    if not variants:
        raise ValueError("at least one render variant is required")
    if len({item.name for item in variants}) != len(variants):
        raise ValueError("render variant names must be unique")

    music_raw = raw.get("music")
    music = None
    if music_raw:
        music = MusicBed(
            path=_require_relpath(music_raw["path"], "music.path"),
            gain_db=float(music_raw.get("gain_db", -16.0)),
        )

    shots = tuple(
        AIShot(
            shot_id=str(item["id"]),
            prompt=str(item["prompt"]),
            duration_seconds=float(item["duration_seconds"]),
            aspect=str(item["aspect"]),
            output=_require_relpath(item["output"], "ai_shots.output"),
        )
        for item in raw.get("ai_shots", ())
    )

    arg_raw = raw.get("arg")
    arg = None
    if arg_raw:
        if arg_raw.get("fictional") is not True:
            raise ValueError("ARG projects must set arg.fictional=true")
        clues = tuple(
            ARGClue(
                clue_id=str(item["id"]),
                kind=str(item["kind"]),
                text=str(item["text"]),
                start_seconds=(
                    None
                    if item.get("start_seconds") is None
                    else float(item["start_seconds"])
                ),
                duration_seconds=(
                    None
                    if item.get("duration_seconds") is None
                    else float(item["duration_seconds"])
                ),
            )
            for item in arg_raw.get("clues", ())
        )
        arg = ARGConfig(
            fictional=True,
            landing_page=(
                None
                if arg_raw.get("landing_page") is None
                else str(arg_raw["landing_page"])
            ),
            clues=clues,
        )

    youtube_raw = raw.get("youtube", {})
    youtube = YouTubeMetadata(
        title=str(youtube_raw.get("title", raw["title"])),
        description=str(youtube_raw.get("description", "")),
        tags=tuple(str(tag) for tag in youtube_raw.get("tags", ())),
    )

    return VideoProject(
        version=version,
        slug=slug,
        title=str(raw["title"]),
        recording=_require_relpath(source["recording"], "source.recording"),
        recording_has_audio=bool(source.get("has_audio", True)),
        variants=variants,
        music=music,
        ai_shots=shots,
        arg=arg,
        youtube=youtube,
    )
