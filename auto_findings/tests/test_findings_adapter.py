from pathlib import Path

from starintel_auto_findings import iter_candidates


def test_preserves_identity_and_sources_without_graph_inference(tmp_path: Path) -> None:
    db = tmp_path / "db" / "person"
    db.mkdir(parents=True)
    (db / "starintel:person:test.ndjson").write_text(
        '{"_id":"starintel:person:test","dtype":"person","dataset":"demo",'
        '"title":"Test Person","summary":"Explicit record summary",'
        '"sources":[{"url":"https://example.invalid/source"}]}\n'
    )
    candidate = list(iter_candidates(tmp_path))[0]
    assert candidate.document_id == "starintel:person:test"
    assert candidate.dtype == "person"
    assert candidate.source_count == 1
    assert candidate.source_locators == ("https://example.invalid/source",)
    assert not hasattr(candidate, "associations")
