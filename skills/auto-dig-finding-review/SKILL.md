---
name: auto-dig-finding-review
description: Review source-backed Auto Dig records as candidate stories while preserving document identity, evidence, and uncertainty.
---

# Auto Dig finding review

Treat the Auto Dig repository's executable schema and canonical database as authority.

Use the `starintel-local-repositories` workflow first so the configured
`STARINTEL_AUTO_DIG_DIR` checkout is current and its exact revision is recorded.

1. Read canonical `db/<dtype>/<id>.ndjson` records or the repository's own validated query output.
2. Preserve `_id`, dtype, dataset, sources, and source path in the review record.
3. A relation or graph edge may be described when the record explicitly represents it.
4. Never turn graph proximity, shared dataset membership, or adjacency into evidence of association.
5. Distinguish source-backed facts, attributed claims, inference, and open questions.
6. Return candidate editorial material only; do not alter Auto Dig data from this repository.
