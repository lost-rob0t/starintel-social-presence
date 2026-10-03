from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator


@dataclass(frozen=True, slots=True)
class FindingCandidate:
    document_id: str
    dtype: str
    dataset: str | None
    title: str
    summary: str
    source_path: str
    source_count: int
    source_locators: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["source_locators"] = list(self.source_locators)
        return value


def _locator(source: object) -> str | None:
    if not isinstance(source, dict):
        return None
    for key in ("uri", "url", "locator"):
        value = source.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _candidate(path: Path, root: Path) -> FindingCandidate:
    raw = json.loads(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"expected JSON object: {path}")
    canonical = raw.get("schemaVersion") == "0.10.1"
    if "schemaVersion" in raw:
        from starintel_canonical import validate_document
        validate_document(raw)
    document_id = raw.get("id") if canonical else raw.get("_id")
    dtype = raw.get("dtype")
    if not isinstance(document_id, str) or not isinstance(dtype, str):
        raise ValueError(f"missing document identity/dtype: {path}")
    sources = raw.get("sources") or []
    if not isinstance(sources, list):
        raise ValueError(f"sources must be an array: {path}")
    locators = (tuple(raw.get("sourceUrls", [])) if canonical else
                tuple(locator for item in sources if (locator := _locator(item))))
    return FindingCandidate(
        document_id=document_id,
        dtype=dtype,
        dataset=raw.get("dataset") if isinstance(raw.get("dataset"), str) else None,
        title=str(raw.get("title") or raw.get("displayName") or raw.get("fullName") or document_id),
        summary=str(raw.get("summary") or raw.get("description") or raw.get("bio") or raw.get("rawContent") or ""),
        source_path=str(path.relative_to(root)),
        source_count=len(sources) + (len(raw.get("sourceUrls", [])) if canonical else 0),
        source_locators=locators,
    )


def iter_candidates(auto_dig_root: Path | str) -> Iterator[FindingCandidate]:
    root = Path(auto_dig_root).expanduser().resolve()
    db = root / "db"
    if not db.is_dir():
        raise FileNotFoundError(f"Auto Dig database not found: {db}")
    for path in sorted(db.glob("*/*.ndjson")):
        yield _candidate(path, root)
