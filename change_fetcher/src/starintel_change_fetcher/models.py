from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class NormalizedChange:
    repository: str
    commit: str
    timestamp: str
    author: str
    message: str
    changed_files: tuple[str, ...]
    comparison_range: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["changed_files"] = list(self.changed_files)
        return value
