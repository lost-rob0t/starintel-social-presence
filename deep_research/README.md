# Deep research integration boundary

This repository does **not** vendor a deep-research engine.

`starintel-auto-research` already contains the reviewed design for versioned deep-research execution adapters behind the Auto Research/ADARD control plane. That design keeps run supervision, budgets, evidence normalization, review, and promotion authority in Auto Research while external engines remain bounded workers.

The social-presence repository consumes reviewed or approved Auto Research output. It must not bypass that boundary or silently promote a `REVIEW` design into implemented architecture.

`STARINTEL_DEEP_RESEARCH_INTEGRATION=auto-research-adapter` records the intended integration. A future implementation here should be a thin client/adapter to the approved Auto Research contract, not a cloned research framework.
