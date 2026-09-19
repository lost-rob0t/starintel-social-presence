from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ai import request_for_shot, select_shots, generate_shot
from .models import load_project
from .package import publish_manifest, write_publish_manifest
from .record import record, wf_recorder_command
from .render import render_command, render_variant, select_variants


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="starintel-video")
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--project", required=True, help="video project JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="print deterministic production plan")
    plan.add_argument("--variant")
    plan.add_argument("--shot")

    record_cmd = sub.add_parser("record", help="record a Wayland screen session")
    record_cmd.add_argument("--no-audio", action="store_true")
    record_cmd.add_argument("--geometry")
    record_cmd.add_argument("--dry-run", action="store_true")

    render_cmd = sub.add_parser("render", help="render one or all output variants")
    render_cmd.add_argument("--variant")
    render_cmd.add_argument("--dry-run", action="store_true")

    generate_cmd = sub.add_parser(
        "generate",
        help="run configured external AI video generator for one or all shots",
    )
    generate_cmd.add_argument("--shot")
    generate_cmd.add_argument("--dry-run", action="store_true")

    sub.add_parser("package", help="write YouTube/ads publish-prep manifest")
    return parser


def _root_and_project(args: argparse.Namespace):
    root = Path(args.root).resolve()
    project = load_project(Path(args.project))
    return root, project


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root, project = _root_and_project(args)

    if args.command == "plan":
        variants = select_variants(project, args.variant)
        shots = select_shots(project, args.shot)
        payload = {
            "record": wf_recorder_command(project, root),
            "renders": {
                item.name: render_command(project, item, root) for item in variants
            },
            "ai_shots": [request_for_shot(item, root) for item in shots],
            "publish": publish_manifest(project, root),
        }
        print(json.dumps(payload, indent=2))
        return 0

    if args.command == "record":
        if args.dry_run:
            print(
                json.dumps(
                    wf_recorder_command(
                        project,
                        root,
                        audio=not args.no_audio,
                        geometry=args.geometry,
                    )
                )
            )
            return 0
        path = record(
            project,
            root,
            audio=not args.no_audio,
            geometry=args.geometry,
        )
        print(path)
        return 0

    if args.command == "render":
        variants = select_variants(project, args.variant)
        if args.dry_run:
            print(
                json.dumps(
                    {
                        item.name: render_command(project, item, root)
                        for item in variants
                    },
                    indent=2,
                )
            )
            return 0
        for item in variants:
            print(render_variant(project, item, root))
        return 0

    if args.command == "generate":
        shots = select_shots(project, args.shot)
        if args.dry_run:
            print(
                json.dumps(
                    [request_for_shot(item, root) for item in shots],
                    indent=2,
                )
            )
            return 0
        for shot in shots:
            print(generate_shot(shot, root))
        return 0

    if args.command == "package":
        print(write_publish_manifest(project, root))
        return 0

    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
