# Contributing

## Start

```bash
nix develop
bash scripts/check
```

Create a branch before modifying code. Read `AGENTS.md`, `README.md`, and `ARCHITECTURE.md` first.

## Change rules

- Keep adapters read-only unless their architecture explicitly says otherwise.
- Add tests for behavioral changes.
- Do not add a dependency when the standard library or an existing repository interface already solves the problem.
- Keep generated binaries/media out of Git.
- Preserve traceability from generated editorial material to source facts.
- Do not claim validation that was not run.

## Pull requests

Describe:

1. what changed;
2. which external StarIntel contracts were inspected/reused;
3. validation performed;
4. known deferred work.

Do not merge unless the current task explicitly authorizes it.
