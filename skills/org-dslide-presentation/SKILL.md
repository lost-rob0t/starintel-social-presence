---
name: org-dslide-presentation
description: Create or update the actual Org/dslide deck and companion script from verified StarIntel material.
---

# Org/dslide presentation generation

## Required deliverable

For every request to make a presentation, video slides, a slide deck, or a
dslide, create or update:

```text
youtube/video-source/<slug>/present.org
```

Do not return only an outline, a prompt, a script, or a scaffold. `script.org`
is companion spoken copy; it does not satisfy a deck request.

## Workflow

1. Start from verified tutorial/article source material and inspect the current
   `present.org` if it exists.
2. Write a complete, dslide-compatible Org deck in `present.org`.
   - top-level headings are slide boundaries;
   - keep one idea per slide;
   - use short slide titles;
   - use lists, source blocks, quote blocks, and image links only where they
     support the slide.
3. Keep commands, expected output, and demo checkpoints explicit. Put narrative
   and recording direction in the sibling `script.org`, not instead of the deck.
4. Include only verified product claims. Mark roadmap/review material as such.
5. Put source links and research notes under a top-level `:noexport:` heading
   so they remain available in Org without becoming slides.
6. Reference curated images through the video's `assets/images/` directory.
7. Do not generate or commit rendered video.

Before finishing, verify that `present.org` exists and contains real slide
content rather than empty headings.
