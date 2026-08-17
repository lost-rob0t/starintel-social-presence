from __future__ import annotations

import argparse
import json
from pathlib import Path

from .catalog import CharacterCatalog
from .catalog_build import build_catalog
from .models import MediaKind, MediaRequest
from .providers import generate_image, generate_video
from .router import route
from .templates import render_org


def _request(args) -> MediaRequest:
    description = Path(args.prompt_file).read_text() if getattr(args, "prompt_file", None) else args.description
    return MediaRequest(
        description=description,
        kind=MediaKind(args.kind),
        flow=args.flow,
        explicit_characters=tuple(args.character or ()),
        reference_images=tuple(args.reference_image or ()),
        provider_override=args.provider,
    )


def _catalog() -> CharacterCatalog:
    root = Path(__file__).resolve().parents[3]
    return CharacterCatalog.from_environment(root)


def _add_common(parser: argparse.ArgumentParser, *, allow_both: bool = False) -> None:
    choices = ["image", "video", "both"] if allow_both else ["image", "video"]
    parser.add_argument("description")
    parser.add_argument("--kind", choices=choices, default="image")
    parser.add_argument("--flow", default="auto")
    parser.add_argument("--character", action="append")
    parser.add_argument("--reference-image", action="append")
    parser.add_argument("--provider", choices=("openai", "google"))
    parser.add_argument("--prompt-file")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Route and generate StarIntel social media assets")
    sub = parser.add_subparsers(dest="command", required=True)

    route_p = sub.add_parser("route", help="Inspect the expert routing decision")
    _add_common(route_p)

    template_p = sub.add_parser("template", help="Render a canonical Org production template")
    _add_common(template_p, allow_both=True)
    template_p.add_argument("--title", required=True)
    template_p.add_argument("--output", type=Path)

    catalog_p = sub.add_parser("catalog", help="Build a large fictional-character routing catalog from Wikidata")
    catalog_p.add_argument("--output", type=Path, default=Path(".cache/fictional-characters.jsonl"))
    catalog_p.add_argument("--batch-size", type=int, default=5000)
    catalog_p.add_argument("--max-rows", type=int)

    generate_p = sub.add_parser("generate", help="Execute the routed image or video generation stage")
    _add_common(generate_p)
    generate_p.add_argument("--output", type=Path, required=True)
    generate_p.add_argument("--aspect-ratio", default="16:9")

    args = parser.parse_args(argv)
    if args.command == "catalog":
        count = build_catalog(args.output, batch_size=args.batch_size, max_rows=args.max_rows)
        print(f"wrote {count} characters to {args.output}")
        return 0

    request = _request(args)
    catalog = _catalog()

    if args.command == "route":
        decision = route(request, catalog)
        print(json.dumps({
            "provider": decision.provider,
            "model": decision.model,
            "reference_class": decision.reference_class.value,
            "reason": decision.reason,
            "confidence": decision.confidence,
            "characters": [match.__dict__ for match in decision.matched_characters],
        }, indent=2))
        return 0

    if args.command == "template":
        text = render_org(args.title, request, catalog)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text)
        else:
            print(text, end="")
        return 0

    decision = route(request, catalog)
    if request.kind == MediaKind.IMAGE:
        generate_image(decision, request.description, args.output, aspect_ratio=args.aspect_ratio)
    else:
        generate_video(
            decision,
            request.description,
            args.output,
            reference_images=request.reference_images,
            aspect_ratio=args.aspect_ratio,
        )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
