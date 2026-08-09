from __future__ import annotations

import argparse
import json
from pathlib import Path

from .models import TutorialPlan, TutorialSource, TutorialStep
from .render import render_blog, render_presentation, render_script


def _load(path: Path) -> TutorialPlan:
    raw = json.loads(path.read_text())
    sources = tuple(TutorialSource(**source) for source in raw["sources"])
    steps = tuple(
        TutorialStep(
            title=step["title"],
            body=step["body"],
            source_refs=tuple(step["source_refs"]),
            command=step.get("command"),
            expected=step.get("expected"),
        )
        for step in raw["steps"]
    )
    return TutorialPlan(
        title=raw["title"],
        slug=raw["slug"],
        description=raw["description"],
        sources=sources,
        steps=steps,
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Render traced TutorialPlan JSON into Org sources")
    p.add_argument("plan", type=Path)
    p.add_argument("--format", choices=("blog", "script", "present"), default="blog")
    p.add_argument("--output", type=Path)
    args = p.parse_args(argv)
    plan = _load(args.plan)
    renderer = {"blog": render_blog, "script": render_script, "present": render_presentation}[args.format]
    text = renderer(plan)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
