from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MediaKind(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    BOTH = "both"


class ReferenceClass(StrEnum):
    STARINTEL_ONLY = "starintel-only"
    SHOW_REFERENCE = "show-reference"
    MIXED = "mixed"
    GENERIC = "generic"


@dataclass(frozen=True)
class CharacterEntry:
    canonical: str
    aliases: tuple[str, ...]
    universe: str
    source: str
    ambiguous_aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class CharacterMatch:
    canonical: str
    universe: str
    source: str
    matched_alias: str


@dataclass(frozen=True)
class MediaRequest:
    description: str
    kind: MediaKind
    flow: str = "auto"
    explicit_characters: tuple[str, ...] = ()
    reference_images: tuple[str, ...] = ()
    provider_override: str | None = None


@dataclass(frozen=True)
class RouteDecision:
    provider: str
    model: str
    reference_class: ReferenceClass
    matched_characters: tuple[CharacterMatch, ...]
    reason: str
    confidence: float
    stage: str
