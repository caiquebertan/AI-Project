# DESIGN

Design principles behind the Aware harness. Decisions and reasons are in [`docs/decisions/`](docs/decisions/).

## Principles
1. **The generator is the deliverable.** The clients are reproducible artifacts. Delete `clients/<app>/`, run `/generate <app>`, get a working client. A web run did exactly that and passed (`docs/runs/P7/`).
2. **The spec is the only source of behavior.** Rules have stable ids (`CORE-AREA-NNN`, `PLAT-*`, `EXT-*`) and acceptance criteria (`AC-Fn-m`). Withdrawn rules stay as one-line tombstones. Disagreements are resolved by reading the spec, never the code.
3. **Core is platform-neutral; platforms and extensions are layered.** `spec/core/` defines the protocol and behavior; `spec/platform/` holds Android and web details; `spec/extensions/` is where new features (reactions, attachments, groups) go without touching the harness.
4. **The generator has no knowledge of this app.** Prompts name no feature (`lint_prompts.py` checks this). What differs per platform lives in `generator/conventions/` and `generator/templates/`.
5. **Reproducibility over cleverness.** Pinned model, pinned wrapper and lockfile templates, explicit permission allowlist, checkpoints (web C0 to C5, Android C0 to C6) with a bounded self-repair budget, and a `.generated` manifest (file hashes, spec version, generator commit, model).
6. **Explicit boundary.** Generated means exactly `clients/android/` and `clients/web/`. Each file carries a `GENERATED` header and `check_headers.py --strict` enforces manifest equals tree.
7. **Proportionate engineering.** The server is a small in-memory Python process. Effort went to the protocol and the generation loop.
8. **Honest verification.** Agents cannot build clients in their sandbox, so every "builds and passes" claim comes from a log on the operator's machine, kept in `docs/runs/`.

## Protocol decisions (spec 0.1.1)
- JSON over HTTP under `/v1`; plain polling every second. Simple to specify, identical on both clients, easy to test.
- Messages have client-generated ids; the server assigns a sequence number. Clients deduplicate by id (created_at is part of duplicate equality).
- Offline queue: send in order, retry until accepted; a permanently rejected message is discarded and written to a diagnostic log (there is no `failed` state, cut for scope).
- Time: strict UTC on the wire (`YYYY-MM-DDTHH:mm:ss.sssZ`); the displayed time is the server's `accepted_at` converted to the device's local zone. No hardcoded zones.

## Workflow
Two entry points, one workflow ([`generator/WORKFLOW.md`](generator/WORKFLOW.md)): `/generate <android|web|all>` is the headless generator; `/pipeline` is the gated delivery pipeline (PM, Tech Lead, Developer, Reviewer, QA agents with human gates on spec, plan and escalation) used to evolve the spec and the generator. The orchestrator is the operator's single point of contact.

## Known limits
See [`FUTURE.md`](FUTURE.md): Android regeneration, acceptance suites and interop are not done.
