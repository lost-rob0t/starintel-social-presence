---
name: llm-deslop
description: Research current LLM-slop patterns with Brave, apply them to a drafted article, and record the pass so generated posts do not ship with machine-writing tells.
---

# LLM deslop (research-driven)

Apply this after a draft exists, never as a substitute for evidence work.

## 1. Research pass (Brave, recorded)

Run the slop-pattern research through the verification helper so the query
and results are recorded with the work:

```sh
prolog-verify brave --query "LLM-generated text slop phrases to avoid editing guide em dashes rule of three not only but also"
```

Read the returned guides and extract concrete, checkable rules. The 2026-09
consensus across sources (Stop Slop, Anti-Slop Guide, avoid-ai-writing):

- no em dashes; use commas, colons, or periods
- break rule-of-three constructions; two items or one
- no "not X, it's Y" / "no ..., just ..." negative parallelism chains
  (a single supported reversal is acceptable)
- vary paragraph openers; no "So", "Furthermore", "Moreover" starts
- cut throat-clearing ("It turns out", "In this section we will")
- flatten pull-quotes and punchy one-liner endings unless the sentence
  carries a concrete claim
- ban-list words: delve, leverage, seamless, robust, unlock, harness,
  pivotal, transformative, landscape, ecosystem filler
- mix sentence lengths; end paragraphs differently

## 2. Application pass

1. `grep -c "—" draft.org` — drive em dashes to zero.
2. Re-read section by section; fix one pattern class at a time.
3. Preserve meaning, links, and metadata exactly. Deslop edits never touch
   factual claims, IDs, or provenance notes.
4. Do not delete the author's voice: supported reversals and one strong
   closing line per section may stay.

## 3. Deterministic lint

Run the repository's own lint (`M-x starintel-blog-deslop` or the
`editorial-deslop` skill) and reconcile its findings with the Brave-derived
list. Deterministic findings are inspectable; rewrite only with review.

## 4. Record

Note in the article's provenance block that a research-driven deslop pass
was applied, and keep the Brave evidence digest in the verification state
(`prolog-verify` facts), not in the article.
