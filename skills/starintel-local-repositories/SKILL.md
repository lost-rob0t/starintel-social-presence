---
name: starintel-local-repositories
description: Use the configured local StarIntel checkout set as current evidence, refreshing only safe clean repositories before editorial or implementation work.
---

# StarIntel local repositories

Read the gitignored `.env` in `starintel-social-presence`.  The primary local
paths are:

- `STARINTEL_SERVER_DIR`
- `STARINTEL_AUTO_DIG_DIR`
- `STARINTEL_AUTO_RESEARCH_DIR`
- `STARINTEL_QUASAR_DIR`
- `STARINTEL_QUASAR_UI_DIR`
- `STARINTEL_REPOSITORIES_DIR` for extra immediate `star*` or `quasar*` repos

Treat these checkouts as the local evidence set. Do not maintain a duplicate
repository list in a prompt or Python module.

Before reading Git facts, features, schemas, source documents, or commands:

1. Read the repository's `AGENTS.md` and relevant README first.
2. Run `git -C <repo> status --short --branch`.
3. If the worktree is dirty, do not pull, reset, stash, or overwrite it. Report
   that the local evidence may be stale and continue only with the visible
   revision when that is acceptable.
4. For a clean worktree with an upstream, run:

   ```sh
   git -C <repo> fetch --prune
   git -C <repo> pull --ff-only
   ```

5. If fast-forward cannot apply, stop treating the checkout as current until
   the divergence is resolved by the operator. Never force-pull.
6. Capture the exact `HEAD` SHA used in editorial references, demo plans, and
   findings/feature notes.

For a finding, Auto Dig's canonical document/schema remains authoritative. For
research, preserve Auto Research's explicit status. For features, a fresh
commit is evidence of a change, not proof that it is user-visible or complete.
