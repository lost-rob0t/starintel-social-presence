from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TutorialSource:
    repository: str
    revision: str
    path: str
    fact: str

    @property
    def reference(self) -> str:
        return f"{self.repository}@{self.revision}:{self.path}"


@dataclass(frozen=True, slots=True)
class TutorialStep:
    title: str
    body: str
    source_refs: tuple[str, ...]
    command: str | None = None
    expected: str | None = None


@dataclass(frozen=True, slots=True)
class TutorialPlan:
    title: str
    slug: str
    description: str
    sources: tuple[TutorialSource, ...]
    steps: tuple[TutorialStep, ...]
