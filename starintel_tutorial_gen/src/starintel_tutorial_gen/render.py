from __future__ import annotations

from .models import TutorialPlan


def _metadata(plan: TutorialPlan) -> list[str]:
    return [
        f"#+title: {plan.title}",
        f"#+description: {plan.description}",
        f"#+slug: {plan.slug}",
    ]


def _source_block(plan: TutorialPlan) -> list[str]:
    lines = ["* Source material"]
    for source in plan.sources:
        lines.append(f"- ={source.reference}= :: {source.fact}")
    return lines


def _steps(plan: TutorialPlan, *, include_production_notes: bool = False) -> list[str]:
    lines: list[str] = []
    for index, step in enumerate(plan.steps, 1):
        lines.extend([f"* {index}. {step.title}", "", step.body, ""])
        if step.command:
            lines.extend(["#+begin_src shell", step.command, "#+end_src", ""])
        if step.expected:
            lines.extend(["Expected:", f": {step.expected}", ""])
        lines.append("Sources: " + ", ".join(f"={ref}=" for ref in step.source_refs))
        if include_production_notes:
            lines.extend(["", "- [ ] Verify command immediately before recording."])
        lines.append("")
    return lines


def render_blog(plan: TutorialPlan) -> str:
    lines = _metadata(plan)
    lines.extend(["#+tags: starintel tutorial", "", *(_steps(plan)), *(_source_block(plan)), ""])
    return "\n".join(lines)


def render_script(plan: TutorialPlan) -> str:
    lines = _metadata(plan)
    lines.extend(["#+filetags: :starintel:video:script:", "", *(_steps(plan, include_production_notes=True)), *(_source_block(plan)), ""])
    return "\n".join(lines)


def render_presentation(plan: TutorialPlan) -> str:
    lines = _metadata(plan)
    lines.extend(["#+filetags: :starintel:dslide:presentation:", ""])
    for step in plan.steps:
        lines.extend([f"* {step.title}", step.body, ""])
        if step.command:
            lines.extend(["#+begin_src shell", step.command, "#+end_src", ""])
        lines.append("Sources: " + ", ".join(f"={ref}=" for ref in step.source_refs))
        lines.append("")
    lines.extend(_source_block(plan))
    lines.append("")
    return "\n".join(lines)
