---
name: starintel-media-production
description: Plan StarIntel images, comics, and videos with expert provider routing, character-reference detection, human approval, and Org production templates.
---

# StarIntel media production

Use this skill when creating image, comic, meme, or video production material for StarIntel social presence.

## Workflow

1. Start from the human description and identify the technical truth that must survive the joke/art direction.
2. Select the closest flow profile: `comic-explainer`, `show-reference-comic`, `starintel-brand`, `meme`, `tutorial`, `architecture`, or `image-to-video`.
3. Use `starintel_media_gen.cli route` before generation. Do not guess the provider in prose when the expert can classify it.
4. For comics, keep scenes large and readable. Specify composition, pose, face, expression, dialogue, and technical truth per beat.
5. Generate the still first. Human approval is mandatory before video.
6. Use the approved still as the video reference. Video prompts describe motion, camera, timing, and audio; they do not silently redesign the character.
7. Keep renders under ignored generated/render directories. Track only curated source assets that belong in the repository.

## Routing policy

- StarIntel-only still: OpenAI / `gpt-image-2`.
- Show-reference or mixed still: Google / `gemini-3-pro-image`.
- Video: Google / `veo-3.1-generate-preview`.
- OpenAI video is a legacy explicit override only; never select it silently.

The provider table may be overridden by environment variables, but the default policy should remain inspectable and tested.

## Character expert

The built-in catalog is only a seed. Load `.cache/fictional-characters.jsonl` when present and additional paths from `STARINTEL_CHARACTER_CATALOGS`.

Use the catalog to detect references and choose a provider. Do not treat a character-name match as evidence about StarIntel or any real person. Ambiguous aliases should require universe context or another disambiguating signal.

## Org output

Use the canonical template generator rather than inventing a new document shape:

```bash
python -m starintel_media_gen.cli template \
  --kind both \
  --flow comic-explainer \
  --title "..." \
  --output path/to/media-plan.org \
  "description"
```

The template must retain brief, expert route, scene beats, facial-expression fields, character continuity, image prompt, human approval gate, video prompt/motion plan, and noexport provenance notes.

## gptel

`M-x starintel-social-media-register-gptel-tool` registers `starintel_media_org_template`.

The tool converts a media description into the canonical Org template. It delegates routing to the deterministic expert rather than asking the LLM to remember vendor/model policy.
