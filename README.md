# Aware — spec-driven client generator

A reusable, reproducible agentic harness that turns a written specification into working client code. A small local messaging system (Python server + Android/Kotlin client + web client) is the example used to evaluate it.

> Status: **spec 0.1.1, reference server, generator and both generated clients are done.** The web client was deleted and regenerated successfully. Both clients were run together by the operator (web in Chrome, Android in the emulator, real server) and the scenario was validated by hand, with a recording in [`docs/demo/`](docs/demo/). Android regeneration, the automated acceptance suites and automated interop were cut for budget (decision 0020). What is verified and what is not is listed below. Next steps: [`FUTURE.md`](FUTURE.md). Plan: [`docs/PLAN.md`](docs/PLAN.md).

| Phase | Status |
|---|---|
| P0 Harness, P1 Spec 0.1.1 | done (decisions 0003, 0013) |
| P2 Server | done, 138 protocol tests green, known gaps in decision 0019 |
| P3 Generator v1 | done (decision 0017), smoke-verified on the operator's machine |
| P4 D1 first generation | web 126 tests, Android 129 tests, all passing on the operator's machine; acceptance suites cut |
| P5 Interop | manual run done and recorded (web Bob and Android emulator Alice, human-validated, `docs/demo/`); automated `tests/interop/` cut |
| P6 Reactions | not done (FUTURE.md) |
| P7 Regeneration check | web **PASS**; Android not run (`docs/runs/P7/`) |
| P8 Packaging | README, DESIGN, AGENTS, FUTURE done; signing rebase cut |

### Verified and not verified
| Verified (logs in `docs/runs/`) | Not verified |
|---|---|
| Web: delete `clients/web`, `/generate web`, build, 126 tests, header and manifest checks: PASS | Android delete-and-regenerate (first generation only) |
| Android first generation: 8 checkpoints, 129 JUnit tests, 0 failures | Scripted (repeatable) runs against the real server |
| Both clients replay the Alice/Bob scenario in tests (fake server and clock) | Automated interop runs (3 in a row), determinism of two regenerations, README-only run by someone else |
| **Manual run, human-validated:** web client (Chrome) and Android client (emulator) talking through the real server, including Offline mode and Pending delivery: [`docs/demo/`](docs/demo/) | Automated browser tests (Playwright) and automated Android UI tests on the emulator |
| Server: 138 protocol tests; harness: 142 tests | Acceptance traceability (`check_trace` 0/172, see FUTURE.md) |

## How it works (two entry points)

| Entry point | What it does | Human gates |
|---|---|---|
| `/generate <android\|web\|all>` | **The generator.** Reads `spec/`, plans, writes `clients/<app>/`, builds and tests it. This is what you run to regenerate. | None |
| `/pipeline` | **The delivery pipeline** we used to build this project: PM, Tech Lead, Developer, Reviewer and QA agents evolve the spec and the generator, then call `/generate`. | Spec approval, plan approval, escalation |

Full workflow: [`generator/WORKFLOW.md`](generator/WORKFLOW.md).

## Where to find things

| What | Where | Status |
|---|---|---|
| Authoritative brief | [`docs/brief/aware-test-brief.md`](docs/brief/aware-test-brief.md) | ✔ |
| Project context | [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) | ✔ |
| Build environment (required tools) | [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) | ✔ |
| **Spec (source of truth)** | [`spec/`](spec/) | ✔ 0.1.1 approved (tags `spec-v0.1.0`, `spec-v0.1.1`) |
| **Agentic harness / generator** | [`generator/`](generator/), [`.claude/`](.claude/), workflow [`generator/WORKFLOW.md`](generator/WORKFLOW.md) | ✔ |
| Harness (Phase 0) | state machine + scripts [`generator/scripts/`](generator/scripts/), sub-agents [`.claude/agents/`](.claude/agents/), prompts [`generator/prompts/`](generator/prompts/), commands [`.claude/commands/`](.claude/commands/), fallback [`generator/RUN.md`](generator/RUN.md), self-test `python3 -m unittest discover -s generator/tests` | ✔ (P0 approved) |
| Generated Android client | [`clients/android/`](clients/android/) | ✔ generated, 129 tests |
| Generated web client | [`clients/web/`](clients/web/) | ✔ generated, 126 tests, regeneration PASS |
| Server (maintained, not generated) | [`server/`](server/) | ✔ P2 |
| External AC checks (protocol, interop, e2e) | [`tests/`](tests/) | protocol ✔ P2; web-e2e, android-conformance, interop not done (FUTURE.md) |
| Operator's own messages (human-written) | [`docs/human-input/OPERATOR_MESSAGES.md`](docs/human-input/OPERATOR_MESSAGES.md) | ✔ |
| Workflow gap analysis | [`docs/planning/workflow-gap-analysis.md`](docs/planning/workflow-gap-analysis.md) | ✔ |
| Traceability (BR/SC → spec → AC → test) | [`docs/product/TRACEABILITY.md`](docs/product/TRACEABILITY.md) | ✔ rows for F1 to F5 |
| Per-feature run logs and retros | [`docs/runs/INDEX.md`](docs/runs/INDEX.md), [`docs/retros/`](docs/retros/) | index ✔, retros P0 to P2 and D1 ✔ |
| Design principles | [`DESIGN.md`](DESIGN.md) | ✔ |
| Agent setup | [`AGENTS.md`](AGENTS.md), [`CLAUDE.md`](CLAUDE.md) | ✔ |
| Decisions log | [`docs/decisions/`](docs/decisions/) | ✔ |
| Next steps | [`FUTURE.md`](FUTURE.md) | ✔ |

## Prerequisites (read first)

Building the clients needs the toolchain and network access that agent sandboxes do not have: **Android SDK, JDK, Node.js and npm, Python 3.10+, Git and the Claude Code CLI**, with access to the npm, Maven Central, Google Maven and Gradle plugin registries. Full list, the reason, and what runs where: [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md). Check with `python3 generator/scripts/preflight.py --strict`.

## Regeneration boundary

Generated code is **exactly** `clients/android/` and `clients/web/`: whole directories, including their unit and UI tests. Each has a `.generated` manifest (file list, hashes, spec version, generator commit, model id). Everything outside `clients/` is maintained, not regenerated.

To regenerate: delete `clients/<app>/` and run `/generate <app>` in Claude Code (model id, build/test commands and permission flags are pinned in `generator/config/generator.json`). Quick start (the grader's path), from the repo root:
```
python3 generator/scripts/setup_env.py --check      # Python 3.10+, JDK 17+, Android SDK, Node 22+, Claude Code
rm -rf clients/web && claude -p "/generate web"     # or: python3 generator/scripts/regen_check.py --app web --clone
rm -rf clients/android && claude -p "/generate android"
```
`generator.json` holds the exact flags (model `claude-opus-5-5`, turn and budget limits, allowlist). Budget: web about 22 minutes and $7.5, Android about 41 minutes and $15 (list prices); a Claude Pro window covers roughly one Android run. Without slash commands: [`generator/RUN.md`](generator/RUN.md). See [`generator/README.md`](generator/README.md).

Every generated file that supports comments carries: `GENERATED by the Aware harness from spec <version> — do not edit; change the spec and regenerate.`

## Authorship

Two separate labels: **boundary** (generated = rebuilt by `/generate`; maintained = not) and **authorship** (who wrote it).

| Path | Boundary | Authorship |
|---|---|---|
| `docs/human-input/` | maintained | **human** (verbatim operator messages; lines starting `AI note:` are AI) |
| `docs/brief/` | maintained | human (assessment brief, transcribed) |
| `docs/decisions/` | maintained | operator decisions, written up by agent |
| `spec/` | maintained | agent-drafted (PM/TL), **human-approved** at G0 |
| `generator/`, `.claude/`, `AGENTS.md`, `DESIGN.md` | maintained | agent-drafted, human-directed and approved |
| `server/`, `tests/` | maintained | agent |
| `clients/*` | **generated** | agent via `/generate` |

Per-commit detail: every commit is authored and committed by the operator (decision 0015); the agent that did the work appears only in the trailers (`Agent`, `Model`, `Authored-By-Role`), which also record area, boundary, stage and approval.

## Repository layout

```
docs/        brief, project context, decisions, operator messages, planning, run logs, retros
spec/        platform-neutral spec: core protocol + schema, scenarios, extensions, platform notes
generator/   harness: workflow, prompts, conventions, templates, config, scripts
.claude/     Claude Code commands and sub-agents
server/      Python in-memory server (maintained, not generated)
clients/     GENERATED android/ and web/ clients
tests/       external AC checks: protocol, interop, e2e
```
