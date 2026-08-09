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
- `STARINTEL_WORKSPACE_ROOT` for a parent containing versioned roots such as
  `starintelV4`, `starintelV5`, and later

Treat these checkouts as the local evidence set. Do not maintain a duplicate
repository list in a prompt or Python module.

When `STARINTEL_WORKSPACE_ROOT` is set, inspect its immediate `starintelV*`
directories as well as the direct repository root.  For example, setting it to
the parent of `starintelV4` discovers both `../starintelV4/*` and
`../starintelV5/*` when V5 exists.  Search only those roots and their immediate
children; do not crawl the user home directory.

Before reading Git facts, features, schemas, source documents, or commands:

1. Check whether `$STARINTEL_SOCIAL_ROOT/.cache/local-repositories` already
   exists. If it exists, use those paths and revisions without rescanning or
   pulling again. Refresh only when the operator explicitly asks to refresh
   repositories or when a needed checkout is absent.
2. On the first workspace pass, discover the configured paths and versioned
   roots, then read each repository's `AGENTS.md` and relevant README first.
3. Run `git -C <repo> status --short --branch`.
4. If the worktree is dirty, do not pull, reset, stash, or overwrite it. Report
   that the local evidence may be stale and continue only with the visible
   revision when that is acceptable.
5. For a clean worktree with an upstream, run:

   ```sh
   git -C <repo> fetch --prune
   git -C <repo> pull --ff-only
   ```

6. If fast-forward cannot apply, stop treating the checkout as current until
   the divergence is resolved by the operator. Never force-pull.
7. Record the resolved paths and exact `HEAD` SHA values in
   `$STARINTEL_SOCIAL_ROOT/.cache/local-repositories` after that first pass.
8. Capture the exact `HEAD` SHA used in editorial references, demo plans, and
   findings/feature notes.

For a finding, Auto Dig's canonical document/schema remains authoritative. For
research, preserve Auto Research's explicit status. For features, a fresh
commit is evidence of a change, not proof that it is user-visible or complete.
