from pathlib import Path

from starintel_auto_research import iter_research


def write_org(path: Path, status: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"#+title: Sample {status}\n#+description: status fixture\n#+status: {status}\n\n* Body\n"
    )


def test_only_explicit_approved_is_approved(tmp_path: Path) -> None:
    write_org(tmp_path / "roam/research/x/a.org", "APPROVED")
    write_org(tmp_path / "roam/design/x/b.org", "REVIEW")
    records = {record.status: record for record in iter_research(tmp_path)}
    assert records["APPROVED"].approved is True
    assert records["REVIEW"].approved is False
