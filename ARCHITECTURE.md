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
                  |             /            \
                  v        script.org     present.org
               exporter                         |
                  |                             v
                  v                          dslide
                HTML
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

## Content model

Org remains the canonical editable source.

Generated HTML is an export artifact. Video recordings/renders are local artifacts. Curated images used as article/presentation source assets may be tracked.

## Model/vendor independence

No content store or normalized fact model depends on one LLM vendor. Optional provider/model names live in configuration. A missing model must reduce capability, not break editing/export.
