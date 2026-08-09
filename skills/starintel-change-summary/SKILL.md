---
name: starintel-change-summary
description: Turn verified Git change records from StarIntel repositories into candidate editorial summaries without inventing behavior.
---

# StarIntel change summary

Use `change_fetcher` or direct repository evidence first. Preserve repository, commit SHA, timestamp, changed paths, and comparison range.

Use the `starintel-local-repositories` workflow before collection. Enumerate
the configured `.env` repository paths and any qualifying checkout beneath
`STARINTEL_REPOSITORIES_DIR`; do not rely on a fixed prompt list.

1. Read the raw normalized changes before summarizing.
2. Group changes only when the shared topic is visible in paths or commit messages.
3. Describe what changed, not what you assume the change enables.
4. Link every material claim back to a commit or changed file.
5. Mark uncertain implications as editorial questions, not facts.
6. Return a candidate summary for human review; do not publish it.
