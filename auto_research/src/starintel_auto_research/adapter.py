from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator


_KEYWORD = re.compile(r"^#\+([A-Za-z0-9_-]+):\s*(.*?)\s*$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class ResearchRecord:
    path: str
    kind: str
    title: str
    description: str
    status: str
    approved: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _keywords(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("*"):
            break
        match = _KEYWORD.match(line)
        if match:
            values[match.group(1).lower()] = match.group(2)
    return values


def iter_research(auto_research_root: Path | str) -> Iterator[ResearchRecord]:
    root = Path(auto_research_root).expanduser().resolve()
    roam = root / "roam"
    if not roam.is_dir():
        raise FileNotFoundError(f"Auto Research roam tree not found: {roam}")
    for kind in ("research", "design"):
        base = roam / kind
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.org")):
            meta = _keywords(path)
            status = meta.get("status", "UNKNOWN").strip().upper()
            yield ResearchRecord(
                path=str(path.relative_to(root)),
                kind=kind,
                title=meta.get("title", path.stem),
                description=meta.get("description", ""),
                status=status,
                approved=status == "APPROVED",
            )
