---
name: starintel-media-production
description: Plan StarIntel images, comics, and videos through the Prolog-RLM media-gen expert, human approval, and Org production workflow.
---

# StarIntel media production

Use this skill when creating image, comic, meme, or video production material for StarIntel social presence.

## Runtime rule

`media-gen` is a SWI-Prolog application built on `prolog-rlm`.

Do not invoke the retired Python `starintel_media_gen` application path. Do not reconstruct provider routing in prompt prose when the Prolog expert can return an inspectable decision.

## Workflow

1. Start from the human description and identify the technical truth that must survive the joke/art direction.
2. Select the closest flow profile: `comic-explainer`, `show-reference-comic`, `starintel-brand`, `meme`, `tutorial`, `architecture`, or `image-to-video`.
3. Inspect the Prolog expert route before generation.
4. Resolve fictional characters deterministically where possible; ambiguous aliases require universe/project context or explicit human choice.
5. Resolve actual input assets. Approved images outrank generated prose descriptions.
6. For comics, keep scenes large and readable. Specify composition, pose, face, expression, dialogue, and technical truth per beat.
7. Generate the still first through the media graph. Human approval is mandatory before continuing to video.
8. Resume the durable graph after approval rather than holding a worker while a human reviews the still.
9. Use the approved still and relevant character references as actual provider inputs when supported.
10. Keep renders under ignored generated/render directories. Track only curated source assets that belong in the repository.

## Inspect the expert

```bash
swipl -q -s bin/media-gen.pl -- branches

swipl -q -s bin/media-gen.pl -- route image comic-explainer \
  "Rick and Morty explain StarIntel"
```

The route returns stable branch IDs, reference class, resolved characters, configured provider/model route, rationale, and confidence.

Concrete model IDs are configuration, not permanent expert truth. Verify current official provider APIs before adding or changing a live adapter.

## Character expert

The built-in Prolog catalog is currently a deterministic seed used for routing tests and ambiguity behavior. The large catalog remains a Wikidata/Wikimedia-backed follow-up.

Do not restore the old Python OFFSET-paged catalog builder merely to claim feature parity. The catalog scaling ADAR already tracks that design problem.

Use catalog identity only for media-reference resolution. A character-name match is not evidence about StarIntel or a real person.

## Assets

`assets.json` is canonical project asset state and is loaded/validated/updated by Prolog.

Prefer roughly:

```text
explicit current user asset
> approved project asset
> approved character asset
> explicit file/URL
> Wikimedia placeholder
> CharacterProfile
> minimal catalog metadata
```

When the provider supports reference inputs, pass the actual assets rather than only describing them in text.

## Org output

Use the Prolog template generator:

```bash
swipl -q -s bin/media-gen.pl -- template \
  "Rick Explains StarIntel" both comic-explainer \
  "Morty thinks StarIntel is ETL, understands the graph, then fumbles again"
```

The production plan must retain facial-expression/continuity requirements, actual input assets, technical truth, the human-approval gate, and asynchronous continuation semantics.

## Emacs

Use:

```text
M-x starintel-social-media-route
M-x starintel-social-media-template
M-x media-gen-expert-shell
```

`media-gen-expert-shell` is a persistent `comint-mode` SWI-Prolog process. Emacs must not route media-gen through Python.

`M-x starintel-social-media-register-gptel-tool` registers `starintel_media_org_template`. The tool calls the Prolog application; it does not ask the model to memorize routing policy.

## Paid effects

Do not run paid image/video providers in normal CI.

The broader once-only external-effect identity contract is owned upstream by `prolog-rlm`. Do not invent a competing generic effect ledger in media-gen.
