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

Media production is a separate Prolog-RLM application boundary rather than another Python editorial adapter:

```text
                         Emacs
                           |
                           v
                       media-gen
                       SWI-Prolog
                           |
                           v
                      Prolog-RLM
                +----------+----------+
                |          |          |
            rlm_chain   rlm_graph   rlm_async
                |          |          |
            OpenRouter   durable     Futures
                        workflow
                           |
                           v
                 generic media API
                           |
                  image / video / voice
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

### Prolog-RLM

`prolog-rlm` owns the reusable media-gen execution substrate: Futures, async scheduling, durable graph execution, artifact references, provider/chain integration, authority, and pending-operation semantics.

media-gen consumes those APIs. It must not vendor or fork them.

The development shell pins a known Prolog-RLM revision and exposes it through `PROLOG_RLM_DIR`; local development may point that variable at another inspected checkout when deliberately testing newer runtime work.

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

### media-gen request and route

media-gen accepts ground, validated Prolog request data and produces an inspectable expert decision containing:

- media stage;
- reference class;
- resolved characters;
- provider class;
- configured model identifier;
- stable expert branch IDs;
- rationale/confidence.

LLM output is data to validate, not executable Prolog.

### generic media request

The reusable `prolog/media/` layer owns provider-neutral image/video/voice request terms. It contains no StarIntel, Emacs, or social-platform assumptions.

The canonical direction is:

```text
execute predicate
  -> rlm_async Future
  -> optional caller await
```

## media-gen workflow

`rlm_graph` is the media workflow engine. The first executable vertical slice performs:

```text
expert plan
  -> generation context
  -> provider request
  -> fake provider execution
  -> human-review interrupt
  -> resume
  -> completion
```

The fake provider uses the same generic media request boundary as future live providers, allowing graph/async behavior to be tested without spending money.

Long remote-provider jobs must later persist stable remote job IDs and resume polling without holding an `rlm_async` worker asleep. Human review likewise uses graph interruption/pending-operation semantics rather than blocking a worker.

Prolog-RLM issue #57 currently tracks the broader once-only external-effect identity ledger. media-gen must not invent a competing generic ledger; paid/retry-sensitive provider integration must either reuse that upstream mechanism when available or remain bounded until the required upstream invariant exists.

## Deep research

No research engine is vendored in Phase 0.

The existing Auto Research design defines a versioned adapter boundary around deep-research workers while preserving Auto Research supervision, ledgers, validation, review, and promotion authority. Until that design is implemented/promoted there, this repository exposes only configuration/documentation for the integration point.

This prevents two bad outcomes:

1. cloning another research framework into an editorial repository;
2. inventing an incompatible request/result contract before the owning project has implemented it.

## Emacs boundary

`elisp/starintel-social.el` owns the human command surface and Org export backend.

Existing editorial adapters may call their deterministic Python CLIs. media-gen does not: `elisp/starintel-social-media.el` calls the SWI-Prolog application directly and exposes a persistent `comint-mode` expert shell.

Ordinary post creation, browsing, and HTML export continue to work without any model provider.

`elisp/blog-gen/` owns explicit assisted edits. It delegates to a configured rewrite function and never silently rewrites a complete document.

`elisp/blog-deslop/` owns deterministic editorial lint. Findings are inspectable before any rewrite.

## Content model

Org remains the canonical editable source.

Generated HTML is an export artifact. Video recordings/renders are local artifacts. Curated images used as article/presentation source assets may be tracked.

For media projects, `assets.json` remains the intended canonical project asset manifest. Large generated payloads belong outside Prolog facts; durable state should retain stable identifiers/artifact references instead.

## Model/vendor independence

No content store or normalized fact model depends on one LLM vendor. Optional provider/model names live in configuration. A missing model must reduce capability, not break editing/export.

media-gen expert rules choose provider/capability classes; mutable concrete model identifiers remain configuration rather than permanent expert truth.
