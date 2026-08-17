from __future__ import annotations

import os

from .catalog import CharacterCatalog
from .flows import get_flow
from .models import MediaKind, MediaRequest, ReferenceClass, RouteDecision


def _reference_class(matches) -> ReferenceClass:
    star = any(match.source == "starintel" for match in matches)
    show = any(match.source != "starintel" for match in matches)
    if star and show:
        return ReferenceClass.MIXED
    if show:
        return ReferenceClass.SHOW_REFERENCE
    if star:
        return ReferenceClass.STARINTEL_ONLY
    return ReferenceClass.GENERIC


def route(request: MediaRequest, catalog: CharacterCatalog) -> RouteDecision:
    if request.kind == MediaKind.BOTH:
        raise ValueError("route one stage at a time; BOTH is a template-level request")

    matches = catalog.match(request.description, request.explicit_characters)
    ref_class = _reference_class(matches)
    flow = get_flow(request.flow)

    if request.kind == MediaKind.VIDEO:
        provider = request.provider_override or "google"
        model = os.getenv("STARINTEL_VIDEO_GOOGLE_MODEL", "veo-3.1-generate-preview")
        reason = "Veo 3.1 is the production video stage; it can animate an approved keyframe and preserve reference continuity."
        if provider == "openai":
            if os.getenv("STARINTEL_ALLOW_LEGACY_OPENAI_VIDEO") != "1":
                raise ValueError("OpenAI video is legacy/deprecated; set STARINTEL_ALLOW_LEGACY_OPENAI_VIDEO=1 for an explicit override")
            model = os.getenv("STARINTEL_VIDEO_OPENAI_MODEL", "sora-2-pro")
            reason = "Explicit legacy OpenAI video override requested."
        return RouteDecision(provider, model, ref_class, matches, reason, 0.99, "video")

    if request.provider_override:
        provider = request.provider_override
        reason = "Explicit provider override."
        confidence = 1.0
    elif ref_class in (ReferenceClass.SHOW_REFERENCE, ReferenceClass.MIXED):
        provider = "google"
        reason = "Recognizable show/fiction reference detected; route still generation to Google's reference-heavy image model."
        confidence = 0.98
    elif ref_class == ReferenceClass.STARINTEL_ONLY or "starintel" in request.description.casefold():
        provider = "openai"
        reason = "StarIntel-native material detected; route still generation to GPT Image 2 for brand-controlled generation."
        confidence = 0.99
    elif flow.image_bias:
        provider = flow.image_bias
        reason = f"Flow profile {flow.name!r} prefers {provider} for this image stage."
        confidence = 0.9
    else:
        provider = "openai"
        reason = "No external-character reference detected; default still generation uses GPT Image 2."
        confidence = 0.8

    if provider == "google":
        model = os.getenv("STARINTEL_IMAGE_GOOGLE_MODEL", "gemini-3-pro-image")
    elif provider == "openai":
        model = os.getenv("STARINTEL_IMAGE_OPENAI_MODEL", "gpt-image-2")
    else:
        raise ValueError(f"unsupported provider: {provider}")
    return RouteDecision(provider, model, ref_class, matches, reason, confidence, "image")
