---
name: starintel-tutorial
description: Build tutorial source and plans from current StarIntel repositories, tests, commands, and documented behavior.
---

# StarIntel tutorial generation

Tutorials must be grounded in current StarIntel state.

Use the `starintel-local-repositories` workflow before extracting commands or
demo steps. A command from a dirty, behind, or divergent checkout is not a
verified demo command.

1. Inspect the relevant repository and its local instructions.
2. Capture exact source references and commands in `TutorialSource` material.
3. Separate prerequisites, steps, expected results, and troubleshooting.
4. Do not invent an API, actor, option, benchmark, or expected output.
5. Prefer one small verified path over a broad speculative tutorial.
6. Generate Org article, script, or dslide material from the same traced plan.
7. Leave publication and final wording to the human editor.
