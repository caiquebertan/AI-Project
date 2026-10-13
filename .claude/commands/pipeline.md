---
description: Run the gated delivery pipeline for the next (or a given) feature
argument-hint: [feature-id] [--autonomous]
---
Placeholder (to be built in Phase 0, see `generator/WORKFLOW.md`). Single start point for the delivery pipeline: loads `.work/STATE.json`, picks the feature, and runs the S0–S7 state machine with gates G0/G1/G2 (autonomous behaviour per §9).
