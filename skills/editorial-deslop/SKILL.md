---
name: editorial-deslop
description: Review technical prose for concrete low-quality generated-writing patterns before applying any optional rewrite.
---

# Editorial deslop

Run deterministic checks first. Flag, do not silently rewrite:

- generic throat-clearing introductions
- repeated thesis or conclusion statements
- excessive section fragmentation
- fake or unsupported quotations
- meaningless intensifiers
- excessive em dashes
- repetitive rhetorical triads
- "not just X, but Y" constructions
- meta-language and model self-reference
- corporate/marketing vocabulary where technical description belongs
- claims not supported by imported factual material

Show findings with locations. Apply only selected rewrites and preserve a reviewable diff.
