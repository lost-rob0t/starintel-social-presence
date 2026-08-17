from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FlowProfile:
    name: str
    beats: tuple[str, ...]
    description: str
    image_bias: str | None = None


FLOW_PROFILES: dict[str, FlowProfile] = {
    "auto": FlowProfile("auto", ("brief", "scene", "continuity", "approval"), "General media production with explicit human approval."),
    "comic-explainer": FlowProfile(
        "comic-explainer",
        ("misconception", "correction", "technical reveal", "comprehension", "fumble", "button"),
        "Large-scene technical comedy where the character learns the concept, then fumbles the punchline.",
    ),
    "show-reference-comic": FlowProfile(
        "show-reference-comic",
        ("setup", "reference reveal", "technical truth", "escalation", "punchline"),
        "Reference-heavy comic using recognizable fictional characters.",
        image_bias="google",
    ),
    "starintel-brand": FlowProfile(
        "starintel-brand",
        ("brand setup", "technical idea", "visual proof", "button"),
        "StarIntel-native brand art, explainers, and character material.",
        image_bias="openai",
    ),
    "meme": FlowProfile("meme", ("setup", "escalation", "punchline"), "Single-image or short-panel meme workflow."),
    "tutorial": FlowProfile("tutorial", ("goal", "prerequisites", "steps", "verification", "next action"), "Tutorial visual or video with explicit verification checkpoints."),
    "architecture": FlowProfile(
        "architecture",
        ("problem", "components", "data flow", "reasoning", "verification"),
        "Technical architecture diagram or explainer.",
        image_bias="openai",
    ),
    "image-to-video": FlowProfile(
        "image-to-video",
        ("approved still", "motion", "camera", "continuity", "audio", "final check"),
        "Animate an approved keyframe without changing character identity or composition unexpectedly.",
    ),
}


def get_flow(name: str) -> FlowProfile:
    return FLOW_PROFILES.get(name, FLOW_PROFILES["auto"])
