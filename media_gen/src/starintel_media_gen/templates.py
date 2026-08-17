from __future__ import annotations

from .catalog import CharacterCatalog
from .flows import get_flow
from .models import MediaKind, MediaRequest
from .router import route


def _decision_lines(request: MediaRequest, catalog: CharacterCatalog) -> list[str]:
    kinds = (MediaKind.IMAGE, MediaKind.VIDEO) if request.kind == MediaKind.BOTH else (request.kind,)
    lines: list[str] = []
    for kind in kinds:
        decision = route(
            MediaRequest(
                description=request.description,
                kind=kind,
                flow=request.flow,
                explicit_characters=request.explicit_characters,
                reference_images=request.reference_images,
                provider_override=request.provider_override,
            ),
            catalog,
        )
        lines.extend(
            (
                f"- {kind.value} provider :: {decision.provider}",
                f"- {kind.value} model :: {decision.model}",
                f"- {kind.value} route :: {decision.reason}",
            )
        )
    return lines


def render_org(title: str, request: MediaRequest, catalog: CharacterCatalog) -> str:
    flow = get_flow(request.flow)
    matches = catalog.match(request.description, request.explicit_characters)
    characters = ", ".join(f"{m.canonical} [{m.universe}]" for m in matches) or "none detected"
    beat_sections = "\n".join(
        f"** {index}. {beat.title()}\n- Composition ::\n- Character pose ::\n- Facial expression ::\n- Dialogue / text ::\n- Technical truth ::\n"
        for index, beat in enumerate(flow.beats, 1)
    )
    route_lines = "\n".join(_decision_lines(request, catalog))
    return f"""#+title: {title}
#+media_kind: {request.kind.value}
#+flow: {flow.name}
#+media_status: DRAFT
#+generator: starintel-media-gen

* Brief
{request.description}

* Expert route
{route_lines}
- detected characters :: {characters}

* Workflow
1. Lock the premise and factual/technical truth before visual generation.
2. Choose the flow profile and let the routing expert classify StarIntel-only vs show-reference material.
3. Write large scene descriptors. Avoid tiny panels unless the format explicitly needs them.
4. Specify facial features and expression changes for every speaking character.
5. Generate the still/keyframe with the routed image model.
6. Human reviews the still. Do not advance on an unapproved image.
7. Generate video from the approved still using the routed video model.
8. Review continuity, text legibility, motion, audio, and factual claims before export.

* Scene plan
{beat_sections}
* Character continuity
- Canonical character names :: {characters}
- Face / hair / clothing anchors ::
- Scale / body proportions ::
- Props ::
- Do-not-change details ::
- Reference images :: {', '.join(request.reference_images) or 'none'}

* Image prompt
:PROPERTIES:
:stage: image
:END:
High-resolution final still. Use large readable scenes, clear faces, consistent character identity, and legible text. Preserve the technical truth from the scene plan.

* Human approval gate
- [ ] Character identity is correct.
- [ ] Facial features and expressions read correctly.
- [ ] Scene scale is large enough.
- [ ] Dialogue/text is legible.
- [ ] StarIntel technical claims are accurate.
- [ ] Still is approved as the video keyframe.

* Video prompt
:PROPERTIES:
:stage: video
:END:
Animate the approved still without redesigning the characters. Preserve face, clothing, composition, props, and technical UI. Add only intentional camera motion, body motion, dialogue timing, and audio described here.

* Video motion plan
- Camera ::
- Character motion ::
- Facial animation ::
- Dialogue timing ::
- Ambient motion ::
- Audio / SFX ::
- Final-frame continuity ::

* Provenance :noexport:
- This file is a production plan, not evidence.
- Provider routing is deterministic and inspectable.
- External fictional-character detection is a routing hint, not a factual claim about StarIntel.
"""
