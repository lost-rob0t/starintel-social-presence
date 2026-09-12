from pathlib import Path

from starintel_auto_research import build_publish_manifest


def write_org(
    path: Path,
    status: str,
    approval_state: str | None,
    evidence: str | None,
    org_id: str | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["#+title: Sample", "#+description: fixture", f"#+status: {status}"]
    if approval_state is not None:
        lines.append(f"#+approval_state: {approval_state}")
    if evidence is not None:
        lines.append(f"#+approval_evidence: {evidence}")
    if org_id is not None:
        lines += [":PROPERTIES:", f":ID:       {org_id}", ":END:", ""]
    lines.append("* Body")
    path.write_text("\n".join(lines) + "\n")


def test_fail_closed_without_allowlist(tmp_path: Path) -> None:
    write_org(tmp_path / "roam/research/a.org", "APPROVED", "APPROVED", "evidence-1", "id-a")
    manifest = build_publish_manifest(tmp_path, public_ids=[])
    assert manifest["publishable_count"] == 0
    assert manifest["gated_count"] == 1
    assert "org-id not in publish allowlist" in manifest["gated"][0]["gated_reasons"]


def test_allowlisted_approved_record_publishes(tmp_path: Path) -> None:
    # DONE is the terminal workflow state in the owning repo; approval is
    # expressed by approval_state + evidence and must not be blocked by it.
    write_org(tmp_path / "roam/research/a.org", "DONE", "APPROVED", "evidence-1", "id-a")
    write_org(tmp_path / "roam/design/b.org", "REVIEW", "PENDING", None, "id-b")
    manifest = build_publish_manifest(tmp_path, public_ids=["id-a"])
    assert manifest["publishable_count"] == 1
    assert manifest["gated_count"] == 1
    pub = manifest["publishable"][0]
    assert pub["org_id"] == "id-a"
    assert pub["workflow_status"] == "DONE"
    assert manifest["gated"][0]["gated_reasons"]  # explicit reasons kept


def test_approval_state_is_required_not_promoted(tmp_path: Path) -> None:
    # approval_state missing -> gated even when allowlisted
    write_org(tmp_path / "roam/research/c.org", "DONE", None, None, "id-c")
    manifest = build_publish_manifest(tmp_path, public_ids=["id-c"])
    assert manifest["publishable_count"] == 0
    assert any("approval_state" in r for r in manifest["gated"][0]["gated_reasons"])


def test_evidence_is_required(tmp_path: Path) -> None:
    write_org(tmp_path / "roam/research/d.org", "DONE", "APPROVED", None, "id-d")
    manifest = build_publish_manifest(tmp_path, public_ids=["id-d"])
    assert manifest["publishable_count"] == 0
    assert any("approval_evidence" in r for r in manifest["gated"][0]["gated_reasons"])
