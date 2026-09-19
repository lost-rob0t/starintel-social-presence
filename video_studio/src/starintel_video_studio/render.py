from __future__ import annotations

from pathlib import Path
import subprocess

from .models import ARGClue, RenderVariant, VideoProject


def output_path(project: VideoProject, variant: RenderVariant, root: Path) -> Path:
    return root / "youtube" / "renders" / project.slug / f"{variant.name}.mp4"


def _filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _frame_clues(project: VideoProject) -> tuple[ARGClue, ...]:
    if project.arg is None:
        return ()
    return tuple(
        clue
        for clue in project.arg.clues
        if clue.kind == "frame_text"
        and clue.start_seconds is not None
        and clue.duration_seconds is not None
    )


def _clue_file(project: VideoProject, clue: ARGClue, root: Path) -> Path:
    return root / "youtube" / "renders" / project.slug / "arg" / f"{clue.clue_id}.txt"


def _video_filter(
    project: VideoProject,
    variant: RenderVariant,
    root: Path,
) -> str:
    filters = [
        (
            f"scale={variant.width}:{variant.height}:"
            "force_original_aspect_ratio=increase"
        ),
        f"crop={variant.width}:{variant.height}",
    ]
    for clue in _frame_clues(project):
        start = clue.start_seconds
        end = start + clue.duration_seconds
        clue_path = _filter_path(_clue_file(project, clue, root))
        filters.append(
            "drawtext="
            f"textfile='{clue_path}':"
            "fontcolor=white:fontsize=20:"
            "x=24:y=h-th-24:"
            "box=1:boxcolor=black@0.55:"
            f"enable='between(t,{start:.3f},{end:.3f})'"
        )
    return ",".join(filters)


def render_command(
    project: VideoProject,
    variant: RenderVariant,
    root: Path,
) -> list[str]:
    source = root / project.recording
    output = output_path(project, variant, root)
    command = ["ffmpeg", "-y"]
    if variant.start_seconds:
        command.extend(["-ss", f"{variant.start_seconds:.3f}"])
    command.extend(["-i", str(source)])

    music_index: int | None = None
    if project.music is not None:
        music_index = 1
        command.extend(["-stream_loop", "-1", "-i", str(root / project.music.path)])

    video_filter = _video_filter(project, variant, root)
    if project.music is not None and project.recording_has_audio:
        command.extend(
            [
                "-filter_complex",
                (
                    f"[0:v]{video_filter}[v];"
                    f"[{music_index}:a]volume={project.music.gain_db}dB[music];"
                    "[0:a][music]amix=inputs=2:duration=first:"
                    "dropout_transition=2[a]"
                ),
                "-map",
                "[v]",
                "-map",
                "[a]",
            ]
        )
    else:
        command.extend(["-vf", video_filter, "-map", "0:v:0"])
        if project.music is not None:
            command.extend(["-map", f"{music_index}:a:0", "-shortest"])
        elif project.recording_has_audio:
            command.extend(["-map", "0:a?"])

    if variant.max_seconds is not None:
        command.extend(["-t", f"{variant.max_seconds:.3f}"])

    command.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    return command


def _write_clue_files(project: VideoProject, root: Path) -> None:
    for clue in _frame_clues(project):
        path = _clue_file(project, clue, root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(clue.text + "\n", encoding="utf-8")


def render_variant(
    project: VideoProject,
    variant: RenderVariant,
    root: Path,
) -> Path:
    output = output_path(project, variant, root)
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_clue_files(project, root)
    subprocess.run(render_command(project, variant, root), check=True)
    return output


def select_variants(
    project: VideoProject,
    variant_name: str | None,
) -> tuple[RenderVariant, ...]:
    if variant_name is None:
        return project.variants
    matches = tuple(
        variant for variant in project.variants if variant.name == variant_name
    )
    if not matches:
        raise ValueError(f"unknown render variant: {variant_name}")
    return matches
