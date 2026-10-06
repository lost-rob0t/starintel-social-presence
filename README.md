# starintel-social-presence

Emacs-first editorial workstation for turning real StarIntel development and research activity into technical posts, devlogs, tutorials, Org/dslide material, and video source documents.

This repository is not a generic CMS and it is not an autonomous content farm. Org files are the human-editable source of truth. Automation may collect facts, normalize changes, suggest structure, lint prose, and prepare drafts, but publication remains explicit and human-directed.

## What belongs here

- technical blog posts and development logs
- deployment, management, customization, actor, dataset, and Quasar tutorials
- Org-mode presentation and spoken-script sources
- normalized change summaries from StarIntel repositories
- reviewed Auto Dig finding candidates
- Auto Research status/readout adapters
- repository-local agent skills for recurring editorial tasks
- Emacs commands for writing, previewing, exporting, and assisted editing

Rendered video, recordings, audio, caches, local exports, model caches, downloaded research scratch, and secrets do not belong in Git. Curated source images referenced by Org documents may be tracked under `assets/images/`.

## Relationship to StarIntel

This workspace reads StarIntel state; it does not redefine it.

- `starintel-server` is the server/control/ingest/search runtime.
- `star-lang` owns the StarIntel 0.10.1 document contract; `starintel-gpt-auto-dig` owns its corpus.
- `starintel-auto-research` owns research/design status and approval semantics.
- `quasar` is the canonical Quasar runtime; related forks remain separate repositories.

Claims about StarIntel behavior should be traceable to source repositories, commits, tests, documentation, live output, or explicitly imported research facts. An LLM draft is never evidence.

## Repository map

```text
.
├── change_fetcher/         # deterministic Git change ingestion
├── auto_findings/          # read-only Auto Dig candidate adapter
├── auto_research/          # read-only Auto Research status adapter
├── deep_research/          # integration boundary; no vendored engine
├── starintel_tutorial_gen/ # source -> plan -> Org renderers
├── site_builder/           # deterministic static site publisher
├── site-assets/            # shared black/gold theme + graph workspace JS
├── skills/                 # canonical repository-local SKILL.md packages
├── blog/                   # human Org posts, drafts, assets, templates
├── docs/                   # documentation sources (nested Org tree)
├── nsaspy/                 # portfolio/about/project Org sources
├── youtube/video-source/   # script.org + present.org + curated assets
├── elisp/                  # Emacs entry point and editorial modules
└── scripts/                # repository validation helpers
```

See `ARCHITECTURE.md` for subsystem boundaries and `ROADMAP.md` for staged work.

## Development environment

The supported developer shell is Nix.

```bash
cp .env.example .env
# edit local paths in .env
direnv allow
```

Or enter directly:

```bash
nix develop
```

The shell intentionally stays small: Python, pytest, uv, Emacs, Git, FFmpeg, Pandoc, Graphviz, ripgrep, and basic shell tooling. Content is not packaged as a Nix artifact.

`.envrc` loads the flake and then `.env` when present. Secrets belong only in `.env` or external secret stores; `.env` is ignored.

## Environment variables

The important variables are repository locations, not invented service credentials:

- `STARINTEL_SOCIAL_ROOT`
- `STARINTEL_SERVER_DIR`
- `STARINTEL_AUTO_DIG_DIR`
- `STARINTEL_AUTO_RESEARCH_DIR`
- `STARINTEL_QUASAR_DIR`
- `STARINTEL_QUASAR_UI_DIR`
- `STARINTEL_REPOSITORIES_DIR` (optional parent directory for additional local
  `star*` and `quasar*` checkouts)
- `STARINTEL_WORKSPACE_ROOT` (optional parent containing versioned roots such
  as `starintelV4`, `starintelV5`, and later)
- `STARINTEL_API_URL` when a live server is intentionally used
- optional model/provider settings for editorial assistance

Deep research is intentionally configured as an integration boundary through Auto Research. The current Auto Research design defines adapter semantics; this repository does not vendor or pretend to implement a research engine.

## Run the checks

```bash
bash scripts/check
```

The check script:

1. runs all Python tests;
2. compiles Python sources;
3. exercises `install_skills.py --list` and dry-run behavior;
4. batch-loads the Emacs package;
5. exports a small Org document through the black/gold backend;
6. runs `git diff --check` when inside a Git checkout.

CI runs the same command inside `nix develop`.

## Change desk

`change_fetcher` obtains raw Git facts without LangChain/LangGraph in the collection path.

```bash
PYTHONPATH=change_fetcher/src \
python -m starintel_change_fetcher.cli \
  "$STARINTEL_SERVER_DIR" \
  --range HEAD~20..HEAD \
  --limit 20
```

Output is a JSON array containing repository identity, commit SHA, timestamp, author, subject, changed files, and comparison range. Raw facts remain usable without an LLM.

## Auto Dig adapter

The adapter reads flat StarLang 0.10.1 records under `db/<dtype>/<id>.ndjson`, validating them with the immutable merged Python consumer pinned in `auto_findings/pyproject.toml`. Install `python -m pip install -e auto_findings` first. Historical `_id` records retain a separate read-only compatibility path and are never relabeled. It does not infer associations from graph adjacency.

```bash
PYTHONPATH=auto_findings/src \
python -m starintel_auto_findings.cli \
  "$STARINTEL_AUTO_DIG_DIR" \
  --limit 20
```

Every candidate retains the source record path, StarIntel `id` (historical `_id`), dtype, dataset, title/summary, and source-reference count. Canonical `sourceUrls` are exposed as locators; a URL is not counted as an additional independent source alongside a reference.

## Auto Research adapter

The Auto Research adapter reads `roam/research/**/*.org` and preserves the repository's explicit status. Only `#+status: APPROVED` is treated as approved here; review/draft states are not silently promoted.

```bash
PYTHONPATH=auto_research/src \
python -m starintel_auto_research.cli \
  "$STARINTEL_AUTO_RESEARCH_DIR"
```

## Discovery and production

Discovery is deliberately a set of direct Emacs commands over local canonical
checkouts, not an editorial service or a second StarIntel database.

The installed `starintel-local-repositories` skill keeps these checkouts usable
by refusing dirty/divergent repositories and refreshing clean ones only with
`git pull --ff-only` during its first workspace pass. The resolved local
catalog is cached under `.cache/`; use `M-x starintel-social-refresh-repositories`
or an explicit agent refresh request when repositories are added, moved, or
should be updated again. Paths are configured in `.env`, never embedded in
agent prompts or source code.

- `M-x starintel-social-findings` opens source-preserving Auto Dig candidates.
- `M-x starintel-social-features` opens recent commits from configured local
  StarIntel checkouts. Set `STARINTEL_REPOSITORIES_DIR` to additionally discover
  immediate `star*` and `quasar*` Git repositories. Set
  `STARINTEL_WORKSPACE_ROOT` to its parent to include every immediate
  `starintelV*` root—V4, V5, and later—without maintaining a Python repository
  list.
- Press `RET` to inspect exact records, source URLs, commit IDs, and changed
  files; press `t` to create a selected `editorial/topics/<slug>.org` topic.
- `M-x starintel-social-topic-production` creates linked blog, `script.org`,
  `present.org`, and `demo.org` source files. The topic keeps the source
  references; generated Org starts as a human-reviewed scaffold.

Feature views report Git facts. They do not claim that a commit is a completed
feature until the editor inspects its linked code, documentation, and demo.
Finding views preserve canonical records and sources; they do not infer a
relationship from graph adjacency.

## Tutorial pipeline

The first vertical slice uses a deterministic intermediate representation:

```text
real facts -> TutorialSource -> TutorialPlan -> blog.org / script.org / present.org
```

Render the presentation directly into its canonical dslide source:

```bash
PYTHONPATH=starintel_tutorial_gen/src \
python -m starintel_tutorial_gen.cli plan.json --format present \
  --output youtube/video-source/<slug>/present.org
```

A request for a deck must update that `present.org` file; a script or outline
alone is not a presentation deliverable.

The input `TutorialPlan` contains traced `TutorialSource` records, and every rendered step retains its source references so a later editor can inspect where claims came from.

## Emacs workflow

`elisp/starintel-social.el` is the package entry point. It does not require a configured model for normal writing/export.

Useful commands:

- `M-x starintel-social-menu`
- `M-x starintel-social-open-workspace`
- `M-x starintel-social-list-blog`
- `M-x starintel-social-new-post`
- `M-x starintel-social-export-current`
- `M-x starintel-social-open-video-source`
- `M-x starintel-social-fetch-changes`
- `M-x starintel-social-insert-change-at-point`
- `M-x starintel-social-blog-assist-region`
- `M-x starintel-social-deslop`

When `transient` is available, the menu is a transient. Without it, the package still loads and exposes the commands. LLM-assisted editing is similarly optional: the adapter uses `gptel-request` only when that function exists and writes the result to a preview buffer.

### Optional dotfiles loading

The companion dotfiles integration reads `STARINTEL_SOCIAL_ROOT`. If it is unset or the checkout is absent, Doom starts normally and nothing is loaded. Set the variable before Emacs starts to enable the package.

Both `.doom.d/config.org` and the active `.doom.d/config.el` are updated in a separate dotfiles branch/PR so literate and generated configuration stay aligned.

## Org blog source

Posts remain ordinary Org files. The currently consumed metadata is:

```org
#+title:
#+date:
#+author:
#+description:
#+slug:
#+tags:
#+status:      # POST or DRAFT
#+revision:    # shown in the page's revision badge
```

Export uses a dedicated derived HTML backend with a responsive black/gold theme. Source Org stays clean; styling is not copied into each article.

## Static site publishing

The repository builds a complete static site from Org sources:

```bash
nix develop --command bash scripts/build-site   # outputs ./site
nix develop --command bash scripts/visual-check # build + browser verification
```

The site covers:

- blog index, article pages with TOC/footnotes/pager/backlinks, tag taxonomy, and an archive timeline;
- `docs/` with nested sidebar navigation, plus pages aggregated from configured external `star*` checkouts (`starintel-server`, `quasar`) with the source revision pinned in a badge;
- `nsaspy/` as the portfolio (hero landing, project pages, about/resume/daily);
- an org-roam graph workspace built from the editor's own roam database.

The repository is a real org-roam vault: `.dir-locals.el` points org-roam at the repository with a repo-local database (`.cache/org-roam.db`), so backlinks, node insert, and org-roam-ui work in the editor, and the site builder consumes the same database. `[[id:...]]` links become both in-page HTML links and graph edges.

DRAFT behavior: `#+status: DRAFT` renders the page for preview with a DRAFT badge and `noindex`, but excludes it from the index, tags, archive, sitemap, and graph. Publication remains explicit.

Visual verification is part of the definition of done: `scripts/visual-check` builds the site, serves it, renders every page in headless Chromium at 1440x900, 1280x800, 768x1024, 390x844, and 320px, and fails on console errors, failed assets, horizontal overflow, or missing content. Screenshots land in `.visual-tests/` (gitignored) for human review.

## dslide / video source

Canonical per-video source layout:

```text
youtube/video-source/<slug>/
├── script.org
├── present.org
└── assets/
    └── images/
```

`script.org` is spoken copy and production notes. `present.org` is the presentation source. Rendered media remains ignored.

## Editorial assistance

`elisp/blog-gen/` contains explicit, region-oriented assisted editing. It never silently replaces a complete article.

`elisp/blog-deslop/` starts with deterministic lint rules for repetitive generated-writing patterns. The intended flow is:

```text
lint -> inspect findings -> select edit -> diff/review
```

The initial implementation reports issues and leaves edits to the author or an explicitly invoked region rewrite.

## Agent skills

Canonical skills live in `skills/<name>/SKILL.md`. `install_skills.py` can copy or directory-symlink them into supported agent locations.

```bash
python install_skills.py --list
python install_skills.py --dry-run --target codex
python install_skills.py --target opencode
python install_skills.py --target claude
python install_skills.py --target agent-zero
```

Current project-local mappings are:

- Codex: `.agents/skills/`
- OpenCode: `.opencode/skills/`
- Claude Code: `.claude/skills/`
- Agent Zero: `$A0_USR/skills/` when `A0_USR` is set, or an existing `/a0/usr/skills/`

The installer refuses destructive replacement by default and is idempotent.

## Generated-content policy

Generated drafts must be labeled by workflow/context, and factual claims must remain traceable to imported facts. Do not fabricate commits, features, findings, benchmarks, quotes, research, or demonstrations. Do not use adjacency as proof of association.

## Status

Phase 0 establishes the environment, contracts, deterministic readers, tutorial IR/rendering slice, Emacs package/exporter, skill installer, tests, and documentation. Autonomous social posting is deliberately out of scope.
