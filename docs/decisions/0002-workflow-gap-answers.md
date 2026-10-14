# 0002 — Operator answers to workflow gap-analysis questions
- Status: accepted (Q1 confirmed 2026-10-13 13:29, OM-0006)
- Date: 2026-10-13
- Source: questions in `docs/planning/workflow-gap-analysis.md` §5; operator reply verbatim in `docs/human-input/OPERATOR_MESSAGES.md` (13:24). The operator accepted every recommendation unless noted.

| Q | Topic | Decision |
|---|---|---|
| 1 | Pipeline vs generator | **The generator is the pipeline's development step.** The pipeline (gated) evolves `spec/` and `generator/`; client code comes only from `/generate`, which is headless and is the same command graders run. The spec is written one feature ahead of the code. No hand edits to `clients/*`. Operator's original idea (pipeline builds apps, generator built afterwards from a spec written alongside) was rejected for reproducibility risk (OM-0005, OM-0006). |
| 2 | Spec owner | PM drafts behavior and scenarios, TL drafts protocol and platform; operator approves at G0. Core protocol decisions recorded as decision records. |
| 3 | Main human gate | G0 on spec deltas; G1 only for architecture or generator design changes |
| 4 | Chain weight | Full chain for the first feature per app and for architecture/generator changes; light chain otherwise |
| 5 | PM acceptance | Automated `check-trace` (every AC has a passing test); PM only on failure or missing test |
| 6 | Server | Light chain: TL-lite → DEV → REV → `tests/protocol` *(Superseded by [0013](0013-approvals-and-mvp-cuts.md) cut 7: no TL plan, no QA agent; DEV, one review, protocol tests.)* |
| 7 | Build order | Spec → server + protocol tests → generator → clients |
| 8 | Test location | **(c), operator comment:** external `tests/` hold the AC checks; inside each project (`clients/*`), unit and UI tests for the code. Consequence: in-project tests are regenerated, so they must be produced by the generator. |
| 9 | Autonomous gates | Delivery pipeline: halt on G0 and G2; auto-approve G1 when its evals pass (flagged for review). **Operator comment:** the generator flow has **no human gate**: it reads the specs, builds the plan and executes. |
| 10 | Review cap | 3 review rounds per app per feature in total, including QA-triggered re-reviews |
| 11 | Nits | Pattern nits become generator conventions; others deferred to the retro; nits never block |
| 12 | Commits | One commit per stage output on `feat/<id>`, merged `--no-ff`, no squash, spec versions tagged |
| 13 | Commit identity | Agent commits use a distinct author (`Aware Agent (<ROLE>/<model>)`), operator as committer, plus trailers *(Superseded by [0015](0015-operator-authored-commits.md): operator is author and committer; agents only in trailers.)* |
| 14 | Reports | Condensed `docs/runs/<feature>/` committed (run.jsonl + final reports); `.work/` stays ignored |
| 15 | Model pinning | Exact model IDs pinned in `generator/config` and the manifest, with a documented fallback |
| 16 | Generation granularity | Module-scoped during the loop; full clean regeneration at S6b *(Amended by [0013](0013-approvals-and-mvp-cuts.md) cut 8 and [0016](0016-plan-defaults-accepted.md): the clean regeneration check runs once at P7, not per feature.)* |
| 17 | Scaffolding | Build infra and module skeletons copied from templates; the LLM fills in the source |
| 18 | Web stack | React + TypeScript + Vite (see 0001) |
| 19 | Android verification | Hybrid: JVM suite (pure-Kotlin core/network module + Robolectric) is the gate; emulator tests optional and documented. Spec defines going offline as app-controlled (offline toggle / swappable connectivity monitor). |
| 20 | Transport | HTTP REST with polling / long-poll and a per-recipient cursor |
| 21 | Evolution demo | Yes: one small extension (reactions) after core features. Protocol to consider a generic-relay design (server forwards `type` + opaque payload) so client-only extensions need no server change. |
| 22 | Operator log | ORC appends, operator confirms in the commit; AI notes visibly separated (`AI note:` prefix) |
| 23 | Feature slicing | Vertical slices: F1 identity, F2 send/receive, F3 offline queue/flush, F4 interop, F5 evolution demo |
| 24 | Backlog approval | Operator approves the backlog once, in Phase 1 |
