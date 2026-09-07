# Changelog

All repository-level changes are recorded here.

## Unreleased

### Added

- Static site publisher (`site_builder`): blog index, article pages, docs
  section with nested navigation, portfolio, tag taxonomy, archive timeline,
  and an org-roam graph workspace, all sharing one black/gold theme.
- Graph truth stays in org-roam: the repository is an org-roam vault in the
  editor (`.dir-locals.el`, repo-local database), and the site builder
  consumes the same sqlite database, syncing through Emacs batch only when
  the database is stale.
- Emacs batch Org->HTML fragment exporter (`starintel-site-export.el`) with
  pygments re-highlighting and deterministic cross-page link resolution.
- Draft (`#+status: DRAFT`) and revision (`#+revision:`) metadata handling:
  drafts render for preview only, with noindex, excluded from listings,
  sitemap, and graph.
- External repository docs aggregation: configured `star*` checkouts'
  READMEs are converted to Org (pandoc for Markdown) and published with the
  source repository's pinned revision.
- Browser visual verification: Playwright smoke suite plus
  `scripts/visual-check` capturing multi-viewport screenshots, console
  errors, failed assets, and horizontal overflow into `.visual-tests/`.
- Emacs-first repository architecture and developer environment.
- Canonical agent instructions plus thin Claude/Codex/OpenCode adapters.
- Deterministic Git `change_fetcher` vertical slice.
- Read-only Auto Dig and Auto Research adapters based on current repository contracts.
- Traceable tutorial source/plan Org renderer vertical slice.
- Repository-local skills and multi-agent skill installer.
- Black/gold Org HTML exporter and Emacs command surface.
- Deterministic editorial/deslop lint and optional region rewrite adapter.
- CI quality gate and media/content ignore policy.
- Separate documented boundary for Auto Research deep-research integration.
