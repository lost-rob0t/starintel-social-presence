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
- Emacs commands for writing, previewing, exporting, assisted editing, and media production

Rendered video, recordings, audio, caches, local exports, model caches, downloaded research scratch, and secrets do not belong in Git. Curated source images referenced by Org documents may be tracked under `assets/images/`.

## Relationship to StarIntel

This workspace reads StarIntel state; it does not redefine it.

- `starintel-server` is the server/control/ingest/search runtime.
- `starintel-gpt-auto-dig` owns its executable StarIntel document schema and canonical Auto Dig data.
- `starintel-auto-research` owns research/design status and approval semantics.
- `quasar` is the canonical Quasar runtime; related forks remain separate repositories.
- `prolog-rlm` is the reusable runtime used by the `media-gen` application for async execution, durable graphs, model/chain integration, artifacts, and authority/pending-operation semantics.

Claims about StarIntel behavior should be traceable to source repositories, commits, tests, documentation, live output, or explicitly imported research facts. An LLM draft is never evidence.

## Repository map

```text
.
├── change_fetcher/         # deterministic Git change ingestion
├── auto_findings/          # read-only Auto Dig candidate adapter
├── auto_research/          # read-only Auto Research status adapter
├── deep_research/          # integration boundary; no vendored engine
├── starintel_tutorial_gen/ # source -> plan -> Org renderers
├── prolog/                 # media-gen Prolog-RLM application + generic media API
├── test/                   # PlUnit and fresh-process media-gen acceptance tests
├── bin/media-gen.pl        # Prolog CLI / comint expert shell entrypoint
├── skills/                 # canonical repository-local SKILL.md packages
├── blog/                   # human Org posts, drafts, assets, templates
├── youtube/video-source/   # script.org + present.org + curated assets
├── elisp/                  # Emacs entry point and editorial/media modules
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

The shell intentionally stays small: Python, pytest, uv, SWI-Prolog, Emacs, Git, FFmpeg, Pandoc, Graphviz, ripgrep, and basic shell tooling. Content is not packaged as a Nix artifact.

The flake pins an inspected `prolog-rlm` revision and exports it as `PROLOG_RLM_DIR` inside the development shell. A developer can deliberately override that variable with another inspected checkout when testing newer runtime work.

`.envrc` loads the flake and then `.env` when present. Secrets belong only in `.env` or external secret stores; `.env` is ignored.

## Environment variables

The important variables are repository locations and explicit provider configuration:

- `STARINTEL_SOCIAL_ROOT`
- `STARINTEL_SERVER_DIR`
- `STARINTEL_AUTO_DIG_DIR`
- `STARINTEL_AUTO_RESEARCH_DIR`
- `STARINTEL_QUASAR_DIR`
- `STARINTEL_QUASAR_UI_DIR`
- `STARINTEL_REPOSITORIES_DIR` (optional parent directory for additional local `star*` and `quasar*` checkouts)
- `STARINTEL_WORKSPACE_ROOT` (optional parent containing versioned roots such as `starintelV4`, `starintelV5`, and later)
- `STARINTEL_API_URL` when a live server is intentionally used
- `PROLOG_RLM_DIR` for the Prolog-RLM dependency when overriding the pinned development-shell copy
- optional image/video model identifiers and provider credentials for explicit live media work

Deep research is intentionally configured as an integration boundary through Auto Research. The current Auto Research design defines adapter semantics; this repository does not vendor or pretend to implement a research engine.

## Run the checks

```bash
bash scripts/check
```

The check script:

1. runs the existing editorial Python tests and compile checks;
2. loads pinned Prolog-RLM and the media-gen application;
3. independently loads the generic Prolog media library, including the remote-video job API;
4. runs media-gen PlUnit acceptance tests for expert routing, assets, async media, remote jobs, and graph interrupt/resume;
5. launches three separate SWI-Prolog processes against one persistent graph backend to prove review pause -> remote submit -> restart -> poll -> completion without a duplicate graph submission;
6. exercises `install_skills.py --list` and dry-run behavior;
7. batch-loads the Emacs package and media expert shell command;
8. exports a small Org document through the black/gold backend;
9. runs `git diff --check` when inside a Git checkout.

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

Auto Dig currently stores canonical v0.9.0 records under `db/<dtype>/<id>.ndjson`. The adapter reads those records and surfaces inspectable candidates; it does not invent associations from graph adjacency.

```bash
PYTHONPATH=auto_findings/src \
python -m starintel_auto_findings.cli \
  "$STARINTEL_AUTO_DIG_DIR" \
  --limit 20
```

Every candidate retains the source record path, StarIntel `_id`, dtype, dataset, title/summary, and source count.

## Auto Research adapter

The Auto Research adapter reads `roam/research/**/*.org` and preserves the repository's explicit status. Only `#+status: APPROVED` is treated as approved here; review/draft states are not silently promoted.

```bash
PYTHONPATH=auto_research/src \
python -m starintel_auto_research.cli \
  "$STARINTEL_AUTO_RESEARCH_DIR"
```

## Discovery and production

Discovery is deliberately a set of direct Emacs commands over local canonical checkouts, not an editorial service or a second StarIntel database.

The installed `starintel-local-repositories` skill keeps these checkouts usable by refusing dirty/divergent repositories and refreshing clean ones only with `git pull --ff-only` during its first workspace pass. The resolved local catalog is cached under `.cache/`; use `M-x starintel-social-refresh-repositories` or an explicit agent refresh request when repositories are added, moved, or should be updated again. Paths are configured in `.env`, never embedded in agent prompts or source code.

- `M-x starintel-social-findings` opens source-preserving Auto Dig candidates.
- `M-x starintel-social-features` opens recent commits from configured local StarIntel checkouts. Set `STARINTEL_REPOSITORIES_DIR` to additionally discover immediate `star*` and `quasar*` Git repositories. Set `STARINTEL_WORKSPACE_ROOT` to its parent to include every immediate `starintelV*` root without maintaining a Python repository list.
- Press `RET` to inspect exact records, source URLs, commit IDs, and changed files; press `t` to create a selected `editorial/topics/<slug>.org` topic.
- `M-x starintel-social-topic-production` creates linked blog, `script.org`, `present.org`, and `demo.org` source files. The topic keeps the source references; generated Org starts as a human-reviewed scaffold.

Feature views report Git facts. They do not claim that a commit is a completed feature until the editor inspects its linked code, documentation, and demo. Finding views preserve canonical records and sources; they do not infer a relationship from graph adjacency.

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

A request for a deck must update that `present.org` file; a script or outline alone is not a presentation deliverable.

The input `TutorialPlan` contains traced `TutorialSource` records, and every rendered step retains its source references so a later editor can inspect where claims came from.

## media-gen

`media-gen` is a Prolog-RLM application. The earlier Python media package has been removed from the media-gen runtime path.

The current executable slice is:

```text
plain description
  -> Prolog character resolution
  -> Prolog expert routing
  -> generation context
  -> provider-neutral request
  -> async fake keyframe generation
  -> rlm_graph human-review interrupt
  -> resume approved
  -> explicit fake remote-video submission
  -> persist remote job ID
  -> rlm_graph remote-pending interrupt
  -> process may exit
  -> fresh process reopens checkpoint
  -> resume poll
  -> video artifact
  -> completion
```

The fake provider is intentional. It exercises the real request, `rlm_async`, explicit remote-job, and `rlm_graph` boundaries without spending money. Live image/video adapters belong behind the same generic API after current official provider contracts are verified.

Try the Prolog CLI:

```bash
swipl -q -s bin/media-gen.pl -- ready
swipl -q -s bin/media-gen.pl -- branches
swipl -q -s bin/media-gen.pl -- route image comic-explainer \
  "Rick and Morty explain StarIntel"
```

Generate the Org production template:

```bash
swipl -q -s bin/media-gen.pl -- template \
  "Rick Explains StarIntel" both comic-explainer \
  "Morty thinks StarIntel is ETL, understands the graph, then fumbles again"
```

The generic `prolog/media/media.pl` module deliberately contains no StarIntel or Emacs assumptions. Its public generation API is async-first through Prolog-RLM Futures and includes explicit submit/poll/cancel operations for remote video jobs.

`assets.json` is canonical project asset state and is loaded/validated/updated in Prolog. Provider/model identifiers are configuration rather than permanent expert truth; unset model IDs remain visibly `unconfigured`.

The fresh-process acceptance gate proves that once a remote job has been checkpointed, restarting SWI resumes the same job and the graph's `submit_count` remains exactly one. Broader once-only identity for the crash window between a real paid side effect and its durable observation remains an upstream Prolog-RLM concern tracked by issue #57; media-gen does not maintain a competing generic effect ledger.

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
- `M-x starintel-social-media-route`
- `M-x starintel-social-media-template`
- `M-x media-gen-expert-shell`
- `M-x starintel-social-blog-assist-region`
- `M-x starintel-social-deslop`

`media-gen-expert-shell` is a persistent `comint-mode` process speaking directly to SWI-Prolog. The media commands do not invoke Python.

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
```

Export uses a dedicated derived HTML backend with a responsive black/gold theme. Source Org stays clean; styling is not copied into each article.

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

Phase 0 establishes the environment, contracts, deterministic readers, tutorial IR/rendering slice, Emacs package/exporter, skill installer, tests, documentation, and an executable Prolog-RLM media-generation slice with persistent remote-job restart coverage. Autonomous social posting and paid media generation in normal CI are deliberately out of scope.
