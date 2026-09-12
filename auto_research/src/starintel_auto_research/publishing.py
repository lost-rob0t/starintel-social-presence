from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterator

from .adapter import ResearchRecord, _keywords, iter_research

_ID_LINE = re.compile(r"^:ID:\s*(\S+)\s*$", re.MULTILINE)


def _record_id(path: Path) -> str | None:
    """Org-roam ID from the :PROPERTIES: drawer before the first heading."""
    header = path.read_text(errors="replace")
    cutoff = header.find("\n* ")
    if cutoff >= 0:
        header = header[:cutoff]
    match = _ID_LINE.search(header)
    return match.group(1) if match else None


def publish_decision(
    record: ResearchRecord,
    root: Path,
    public_ids: tuple[str, ...] | list[str],
) -> dict[str, Any]:
    """Fail-closed publish gate for one Auto Research record.

    Mirrors the website publisher's research gate exactly: approval_state
    APPROVED with evidence plus an explicit allowlist entry. `#+status` is
    the repo's workflow state (DONE is terminal); it never gates approval,
    so approved work in any workflow state is publishable and no state is
    silently promoted.
    """
    meta = _keywords(root / record.path)
    approval_state = meta.get("approval_state", "").strip().upper()
    evidence = meta.get("approval_evidence", "").strip()
    org_id = _record_id(root / record.path)
    allowlisted = bool(org_id and org_id in public_ids)

    reasons: list[str] = []
    if approval_state != "APPROVED":
        reasons.append(f"approval_state={approval_state or 'NONE'} != APPROVED")
    if not evidence:
        reasons.append("approval_evidence missing")
    if not allowlisted:
        reasons.append("org-id not in publish allowlist")

    return {
        "path": record.path,
        "kind": record.kind,
        "title": record.title,
        "status": record.status,
        "workflow_status": record.status,
        "org_id": org_id,
        "approval_state": approval_state or None,
        "approval_evidence": evidence or None,
        "publishable": not reasons,
        "gated_reasons": reasons,
    }


def iter_publish_manifest(
    auto_research_root: Path | str,
    public_ids: tuple[str, ...] | list[str] = (),
) -> Iterator[dict[str, Any]]:
    """Yield publish decisions for every Auto Research research/design record."""
    root = Path(auto_research_root).expanduser().resolve()
    for record in iter_research(root):
        yield publish_decision(record, root, public_ids)


def build_publish_manifest(
    auto_research_root: Path | str,
    public_ids: tuple[str, ...] | list[str] = (),
) -> dict[str, Any]:
    """Complete publish manifest: publishable set, gated set, fail-closed counts."""
    decisions = list(iter_publish_manifest(auto_research_root, public_ids))
    publishable = [d for d in decisions if d["publishable"]]
    gated = [d for d in decisions if not d["publishable"]]
    return {
        "public_ids": list(public_ids),
        "count": len(decisions),
        "publishable_count": len(publishable),
        "gated_count": len(gated),
        "publishable": publishable,
        "gated": gated,
    }
