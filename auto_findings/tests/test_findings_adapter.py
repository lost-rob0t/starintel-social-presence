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


def test_canonical_flat_record_preserves_sources(tmp_path: Path) -> None:
    import json
    db = tmp_path / 'db' / 'person'
    db.mkdir(parents=True)
    (db / 'person.ndjson').write_text(json.dumps({'id':'person:test','schemaVersion':'0.10.1','dtype':'person','dataset':'test','fullName':'Test','bio':'Explicit bio','sources':[{'schema':'source','id':'source:one'}],'sourceUrls':['https://example.invalid/']}))
    candidate = list(iter_candidates(tmp_path))[0]
    assert candidate.document_id == 'person:test'
    assert candidate.title == 'Test'
    assert candidate.summary == 'Explicit bio'
    assert candidate.source_count == 1  # URL does not establish a second independent source
    assert candidate.source_locators == ('https://example.invalid/',)


def test_canonical_malformed_record_rejects(tmp_path: Path) -> None:
    import json
    import pytest
    db = tmp_path / 'db' / 'person'
    db.mkdir(parents=True)
    (db / 'person.ndjson').write_text(json.dumps({'_id':'person:test','schemaVersion':'0.10.1','dtype':'person','dataset':'test'}))
    with pytest.raises(ValueError):
        list(iter_candidates(tmp_path))
