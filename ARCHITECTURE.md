# Architecture

## Principle

The deterministic spine owns collection, normalization, traceability, and rendering inputs. LLMs may operate around that spine; they do not replace it.

```text
               StarIntel repositories
                      |
         +------------+-------------+
         |            |             |
 change_fetcher  auto_findings  auto_research
         \            |             /
          \           |            /
           +----- normalized facts -----+
                         |
                         v
                tutorial/editor pipeline
                   /                 \
                  v                   v
               blog.org          video source
                  |          /       |        \
                  v   script.org  video.json  present.org
               exporter               |           |
                  |                    v           v
                  v               video_studio   dslide
                HTML              /    |    \
                           record  render  publish-prep
```

## External authority

### StarIntel server

`starintel-server` remains the runtime authority for its API/server behavior. This repository may read its Git history or use an explicitly configured API; it must not fork the server contract into editorial code.

### Auto Dig

The current Auto Dig repository declares its executable StarIntel document schema as authoritative and stores normalized records at `db/<dtype>/<id>.ndjson`.

`auto_findings` therefore reads existing records and retains `_id`, dtype, dataset, record path, summary/title, and source references. It does not derive association claims from graph adjacency.

### Auto Research

Auto Research owns Org research/design status, approval, and the ADARD/deep-research adapter design. `auto_research` reads research node metadata and status without promoting review-stage work.

### Quasar

Quasar is a source of product state and tutorial material, not the editorial database. The canonical repository location is configured, not embedded in code.

## Normalized boundaries

### `NormalizedChange`

Produced by deterministic Git adapters:

- repository identity/path
- commit SHA
- timestamp
- subject
- changed files
- comparison range

No model summary is required to retain these facts.

### `FindingCandidate`

Produced from an existing Auto Dig document:

- source record path
- `_id`
- dtype
- dataset
- title/summary
- source count and locators

The candidate is an editorial lead, not a new intelligence claim.

### `ResearchRecord`

Produced from an Auto Research Org node:

- path
- title
- description
- explicit status
- approved boolean (`status == APPROVED` only)

### `TutorialSource` / `TutorialPlan`

`TutorialSource` contains traceable facts with stable source IDs and locators. `TutorialPlan` orders those facts into steps without erasing provenance. Renderers produce blog/script/presentation Org documents from the same plan.

### `VideoProject`

`video_studio` loads a checked-in `video.json` boundary containing:

- the local recording path;
- explicit render variants and time windows;
- optional music-bed configuration;
- provider-neutral synthetic-shot requests;
- fictional ARG cues;
- YouTube metadata.

Binary recordings, generated shots, renders, music, and publish artifacts stay in
gitignored media directories. The tracked project file describes what should happen
without pretending that a render or upload happened.

## Deep research

No research engine is vendored in Phase 0.

The existing Auto Research design defines a versioned adapter boundary around deep-research workers while preserving Auto Research supervision, ledgers, validation, review, and promotion authority. Until that design is implemented/promoted there, this repository exposes only configuration/documentation for the integration point.

This prevents two bad outcomes:

1. cloning another research framework into an editorial repository;
2. inventing an incompatible request/result contract before the owning project has implemented it.

## Emacs boundary

`elisp/starintel-social.el` owns the human command surface and Org export backend.

It may call deterministic Python CLIs and optional editorial adapters, but ordinary post creation, browsing, and HTML export work without any model provider.

`elisp/blog-gen/` owns explicit assisted edits. It delegates to a configured rewrite function and never silently rewrites a complete document.

`elisp/blog-deslop/` owns deterministic editorial lint. Findings are inspectable before any rewrite.

`elisp/starintel-site-export.el` owns batch Org->HTML *fragments* for the site: table of contents, body, and footnotes with no page shell. It never styles pages; the shared theme lives in `site-assets/starintel.css`.

`elisp/starintel-roam-graph.el` syncs an org-roam database for the repository content.

## Site publisher boundary

`site_builder` turns Org sources into the static site. Division of ownership:

- Emacs exports article body fragments; the Python builder owns page shells, navigation, badges, card layouts, docs sidebar, taxonomy, timeline, and the graph workspace.
- Graph truth is org-roam's. The repository is an org-roam vault in the editor (`.dir-locals.el`, repo-local `.cache/org-roam.db`); the builder consumes that same database and only runs a batch sync when it is stale. It never re-parses Org links into a parallel graph model.
- Drafts (`#+status: DRAFT`) render for preview only: `noindex`, excluded from listings, sitemap, and graph.
- External repository docs are aggregated from configured `star*` checkouts and published with the source checkout's pinned revision; they are skipped, not invented, when a checkout is absent.
- Syntax highlighting is deterministic (Pygments over exported `src` blocks); no client-side highlighter, no CDN assets.

`scripts/visual-check` renders the built site in a real browser across desktop/laptop/tablet/mobile/narrow viewports, capturing screenshots, console errors, failed assets, and horizontal overflow into `.visual-tests/` (gitignored).

## Video studio boundary

`video_studio` owns deterministic media preparation, not product truth.

- `wf-recorder` capture is a local side effect explicitly invoked by a human or Zara.
- FFmpeg commands are derived from `video.json`; the same project can emit full
  horizontal video plus short horizontal, vertical, and square cuts.
- AI video generation is an external-command protocol. Generator providers never
  become part of the fact/evidence spine.
- ARG cues are production metadata. They require `fictional=true`; in-universe
  clues may be subtle, but the campaign has a real fiction disclosure/landing path
  and must not impersonate authorities or fabricate StarIntel capabilities.
- `publish.json` is preparation only. Uploading to YouTube and buying ads remain
  separately authorized actions.

This gives Zara a stable tool boundary: record a known demo, hand the local media
to the studio, request variants, and return paths/metadata without embedding media
logic in Zara itself.

## Content model

Org remains the canonical editable source.

Generated HTML is an export artifact. Video recordings/renders are local artifacts. Curated images used as article/presentation source assets may be tracked.

## Model/vendor independence

No content store or normalized fact model depends on one LLM vendor. Optional provider/model names live in configuration. A missing model must reduce capability, not break editing/export.
