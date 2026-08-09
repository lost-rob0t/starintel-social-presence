# StarIntel Social Presence Agent Instructions

`AGENTS.md` is canonical for agents working in this repository.

## Mission

Build an Emacs-first editorial workstation that turns verified StarIntel development and research state into human-directed technical writing, tutorials, presentations, and video source material.

This repository assists an editor. It does not manufacture evidence and it does not autonomously publish.

## Before work

Read, in order:

1. `AGENTS.md`
2. `README.md`
3. `ARCHITECTURE.md`
4. the relevant component README/docs
5. the existing code before introducing abstractions

When work depends on another StarIntel repository, inspect that repository's current `AGENTS.md`, schema, code, and status conventions before writing an adapter.

## Git

- Always create a branch before implementation.
- Keep commits coherent and scoped.
- Never commit secrets.
- Never commit recordings, rendered video/audio, caches, generated binary junk, or local model state.
- Never rewrite unrelated work.
- Do not merge unless explicitly instructed.
- Do not silently modify an external repository.
- Changes to dotfiles or another repository require a separate branch and PR.

## Engineering

- Prefer small composable modules.
- Reuse StarIntel interfaces instead of cloning them.
- Use typed Python.
- Add tests for meaningful behavior.
- Keep deterministic collection/transformation independent from LLMs.
- Define explicit models at subsystem boundaries.
- Configure paths/services through environment/config, not machine-specific constants.
- Avoid framework-first architecture and giant orchestration graphs.
- Do not introduce LangChain/LangGraph for operations that are ordinary subprocess/file parsing.
- If a state-machine/orchestration layer is later justified, keep it above deterministic adapters.

## Content integrity

An LLM draft is not evidence.

Never invent:

- commits or release notes
- StarIntel features/capabilities
- findings or research
- benchmarks or test results
- quotations
- source URLs
- demonstrations

Keep these categories distinguishable:

- raw source material
- extracted facts
- deterministic transformations
- agent suggestions
- human-written material
- generated drafts
- published output

When a claim says StarIntel can do something, prefer evidence from repositories, commits, documentation, tests, or observed live behavior.

## Auto Dig

Auto Dig owns its executable StarIntel document contract. Inspect its current repository instructions/schema before changing this adapter.

The social-presence adapter is read-only. It may surface candidate records and source references, but it must not reinterpret graph adjacency as proof of association.

Do not impose Auto Dig's source policy on unrelated StarIntel software/documentation work.

## Auto Research

Auto Research owns research/design status and approval semantics. Preserve its explicit status. Unapproved or review-stage material must not be presented as settled architecture.

Deep-research execution remains behind the Auto Research adapter boundary unless that repository implements/promotes a different contract.

## Python

Each Python project uses a `src/` layout and exposes only the boundary it owns.

- `change_fetcher`: Git facts and normalized changes
- `auto_findings`: read-only Auto Dig candidate extraction
- `auto_research`: read-only research/status extraction
- `starintel_tutorial_gen`: traceable tutorial IR and renderers

Tests must not require network access.

## Emacs Lisp

- `elisp/starintel-social.el` is the entry point.
- Keep feature modules separate.
- Normal editing/export must work without an LLM.
- Optional model integration must degrade cleanly when unavailable.
- Prefer explicit region/section commands over whole-document replacement.
- Prefer preview/diff review before destructive rewriting.
- Use `transient` when available but do not make package loading depend on it.

## Org source

Org is authoritative for blog posts, scripts, and presentations. Keep source readable without AI tooling.

Do not stuff site HTML/CSS into each post. Export configuration belongs in the Emacs exporter/theme.

## Deslop/editorial cleanup

Start with deterministic, inspectable lint rules. Report locations/reasons. Do not automatically destroy the author's voice.

Optional LLM rewriting must be explicitly invoked on a chosen region and reviewed by the user.

## Skills

Canonical repository skills live under `skills/<name>/SKILL.md`.

Keep skills task-specific and concise. Use portable YAML frontmatter with `name` and `description`. Do not turn skills into global personality prompts.

`install_skills.py` owns destination mapping and overwrite policy.

## Quality gate

Before opening or updating the implementation PR, run:

```bash
nix develop --command bash scripts/check
```

The gate must cover:

- Python tests
- Python compile checks
- skill installer list/dry-run
- Emacs batch load
- Elisp byte compilation where practical
- black/gold Org export smoke test
- `.env` ignore behavior
- generated media ignore behavior
- curated asset trackability
- `git diff --check`

Do not claim a command passed unless it was executed and observed.

## Scope control

Prefer real environment, interfaces, tests, and one or two vertical slices over placeholder subsystems or dependency piles.

Phase 0 does not mean autonomous posting, a full research engine, or a full tutorial generator.
