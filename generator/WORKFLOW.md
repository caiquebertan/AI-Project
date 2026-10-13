# Agent pipeline workflow (AI-readable) — v0.2.1

> **Sources:** operator instructions in [`docs/human-input/OPERATOR_MESSAGES.md`](../docs/human-input/OPERATOR_MESSAGES.md) (12:51 workflow; 13:24 and 13:29 decisions), decisions in [`docs/decisions/0002-workflow-gap-answers.md`](../docs/decisions/0002-workflow-gap-answers.md), gap analysis in [`docs/planning/workflow-gap-analysis.md`](../docs/planning/workflow-gap-analysis.md).
> **Precedence:** brief > operator's words > this file. If they conflict, stop and ask the operator (or log `BLOCKED` in autonomous mode).
> **v0.2.1:** §8 requires all commit trailers in one final block.
> **Changes from v0.1:** generator is the development step (two entry points); spec stage S0 + gate G0; S1 becomes Trace; S2 only for generator/architecture changes; S6 automated; new S6b regen-check; return codes, counters, abort paths; commit-addressed diff rule; worktrees for parallel work; run log; executable evals.

---

## 1. Goal and the two machines

Deliver the Aware project through a gated multi-agent pipeline whose **development step is the generator**. Client code is only ever produced by the generator from the spec, so the path graders run ("delete generated code → run generator → working clients") is exercised on every feature.

| | **Delivery pipeline** `/pipeline` | **Generator** `/generate <android\|web\|all>` |
|---|---|---|
| Purpose | Evolve spec, generator, server, external tests | Rebuild `clients/<app>/` from `spec/` + `generator/` |
| Run by | Operator → ORC (interactive) or ORC (autonomous) | Graders, CI, and pipeline stage S3 / S6b |
| Human gates | G0, G1, G2 | **None** (operator decision, Q9): reads specs → builds plan → executes |
| Writes | `spec/`, `generator/`, `server/`, `tests/`, `docs/` | **Only** `clients/<app>/` (incl. its unit + UI tests and `.generated` manifest) |
| Quality gate | REV, QA, trace check, regen-check | Automated: build → in-project unit/UI tests → bounded self-repair (≤3) → fail loudly |

Hard rule: **no agent ever hand-edits `clients/*`.** A defect in generated code is fixed in `spec/` or `generator/` (prompts, conventions, templates), then regenerated.

## 2. Roles

| ID | Role | Model | Owns | Never |
|---|---|---|---|---|
| ORC | Orchestrator / manager (main session) | session model | Plan, `STATE.json`, run log, rendering prompts from templates, triage, diff snapshots, gates, parallelism, retros, operator log | Writes production code |
| PM | Product manager | Sonnet | WHAT: backlog (epics → features → stories); drafts `spec/core/client-behavior.md` + `spec/scenarios/`; `docs/product/TRACEABILITY.md` (ACs as references to spec IDs); handles acceptance exceptions | Technical design |
| TL | Tech lead | **Opus always** | HOW: drafts `spec/core/protocol.md`, `server-behavior.md`, `schema/`, `spec/platform/*`; designs generator (`generator/conventions`, `templates`, `prompts`); server plan | Code |
| DEV | Developer | **Opus** for first generation of a module/app and when interpretation or trying options is needed; **Sonnet** when the change maps objectively to an approved plan | Edits generator inputs and runs `/generate` (clients); writes `server/` + its simple unit tests | Hand-edits `clients/*`; writes robust/UI suites |
| REV | Reviewer | Sonnet; **Opus if changed lines > 400**, first generation of a module, or concurrency/threading paths | Review report: `blocker` / `nit` / `design-concern`, from magic strings/numbers to race conditions and wrong-thread calls | Fixes code |
| QA | QA engineer | Opus to design a suite (once per app/suite); Sonnet to extend one | External AC checks in `tests/` (protocol, interop, e2e); test requirements for in-project unit/UI tests, delivered as generator conventions (Q8) | Changes production code |
| OP | Operator (human) | — | G0, G1, G2; backlog approval once | — |

Every launch is logged with `model`, `model_id`, `reason` (§8).

## 3. Artifacts

| Artifact | Path | Writer |
|---|---|---|
| Brief | `docs/brief/aware-test-brief.md` | — |
| **Spec** (only source of behavior), versioned semver + git tag `spec-vX.Y.Z` | `spec/` (`core/`, `core/schema/`, `scenarios/`, `platform/`, `extensions/`) | PM + TL at S0 only |
| Backlog | `docs/product/BACKLOG.md` | PM |
| Traceability: brief req (`BR-n`, `SC-n`) → spec ID → AC ID → test ID → status | `docs/product/TRACEABILITY.md` | PM (rows), `check-trace` (status) |
| Generator inputs | `generator/{prompts,conventions,templates,config,scripts}/` | TL design, DEV implementation |
| Plans (history only; generator never reads them) | `docs/plans/<feature>/<app>.md` | TL |
| Generated clients + manifest | `clients/<app>/**`, `clients/<app>/.generated` (paths, sha256, spec version, generator commit, model id) | `/generate` only |
| Server (maintained) | `server/` | DEV |
| External AC checks | `tests/protocol/`, `tests/interop/`, `tests/web-e2e/`, `tests/android-conformance/` | QA |
| Working diff snapshot | `.work/<feature>/<app>/diff.patch` + `diff.meta.json` | ORC |
| Pipeline state | `.work/STATE.json` (+ rendered `STATE.md`) | ORC |
| Worktrees for parallel agents | `.work/wt/<feature>-<app>/` | ORC |
| Run log + final reports (committed) | `docs/runs/<feature>/{run.jsonl, review-<n>.md, qa.md, acceptance.md}`, `docs/runs/INDEX.md` | ORC |
| Retro | `docs/retros/<feature>.md` (template `docs/retros/TEMPLATE.md`) | ORC (+ operator "Human notes") |
| Operator messages | `docs/human-input/OPERATOR_MESSAGES.md` (`OM-nnnn` ids) | ORC appends verbatim, operator confirms |
| Decisions | `docs/decisions/NNNN-*.md` | ORC / TL |

`.work/` is git-ignored scratch.

## 4. Phases (project level)

| Phase | Steps | Gate | Exit |
|---|---|---|---|
| **P0 Harness** | Agent role files `.claude/agents/{pm,tech-lead,developer,reviewer,qa}.md`; prompt templates `generator/prompts/`; scripts `generator/scripts/` (`snapshot-diff`, `count-lines`, `run-log`, `check-headers`, `check-trace`, `regen-check`, `lint-commits`, `preflight`); `/pipeline` + `/generate` commands, `generator/RUN.md` fallback; `STATE.json` + run-log schemas; README/AGENTS updates | OP reviews harness | Dry run of `/pipeline` on a stub feature passes E-WF-1 |
| **P1 Backlog + core spec** | PM backlog (F1 identity, F2 send/receive, F3 offline queue/flush, F4 interop, F5 reactions extension) + TRACEABILITY skeleton; decision records (transport = HTTP + polling/long-poll with per-recipient cursor; message identity; ordering; delivery/dedupe; generic-relay `type`+payload; app-controlled offline); `spec/core/*` with `CORE-xxx` ids, `schema/`, Alice/Bob expected states, test hooks (test tags / `data-testid`, JVM-testable Android core module) | OP approves backlog once; **G0** spec v0.1.0 | `check-trace`: every BR/SC has a spec id |
| **P2 Server** (light chain) | TL-lite plan → DEV server + `tests/protocol` → REV | G1-light | E-PROTO-1 green |
| **P3 Generator v1** | TL generator design (templates for build infra and module skeletons, conventions per platform, generation order, self-repair bound, manifest) → DEV implements → first `/generate android` + `/generate web` (parallel worktrees) | **G1** | Both clients build + in-project tests pass |
| **P4 Feature loops** | F1 → F3 via §5 | per §5 | per §5 |
| **P5 Interop** | QA `tests/interop/` runs Alice/Bob both pairings (android↔web) against the real server | — | E-INTEROP-1 green ×3 |
| **P6 Evolution demo** | F5 reactions as `spec/extensions/reactions.md` → `/generate` with no prompt changes | G0 | E-EVOL-1 |
| **P7 Regen verification** | `regen-check` from a fresh clone ×2; operator repeats once following only README | OP | E-PIPE-1 |
| **P8 Packaging** | Final README / DESIGN / AGENTS / FUTURE (from retros); lint scripts; archive; unzip + regen in clean sandbox | OP final review | Submitted |

## 5. Per-feature state machine

Chains: **full** = first feature per app, or any generator/architecture change (S2 + G1 run). **light** = everything else (S2/G1 skipped).

```
 S0 SPEC ─► [G0] ─► S1 TRACE ─► (S2 TL ─► [G1])? ─► S3 GENERATE ─► S4 REVIEW ─► S5 QA ─► S6 ACCEPT ─► S6b REGEN ─► S7 RETRO
```

| Step | Trigger | Agent | Output | Next |
|---|---|---|---|---|
| **S0 Spec delta** | Feature selected; or any `SPEC_ISSUE` | PM (behavior, scenarios) + TL (protocol, schema, platform) | Spec diff + version bump | delta → G0; none needed → S1 |
| **G0** | Spec delta drafted | **OP** | approve / revise / descope | approve → S1 (tag); revise → S0; descope → backlog |
| **S1 Trace** | G0 approved | PM | TRACEABILITY rows for the feature, per app (`core` / `platform:android` / `platform:web`) | AC needs behavior not in spec → S0. Generator/arch change needed → S2. Else → S3 |
| **S2 TL plan** | Full chain only | TL (Opus) | Plan per affected app (`docs/plans/`) + proposed edits to `generator/conventions`, `templates`, `spec/platform` | → G1 |
| **G1** | Plan written | **OP** | approve / revise-plan / revise-spec / descope | → S3 / S2 / S0 / backlog |
| **S3 Generate / implement** | G1 approved or light chain from S1 | DEV | Clients: edits to generator inputs + `/generate <app>` (module-scoped). Server: code + simple unit tests. ORC commits and snapshots the diff | build + in-project tests OK → S4. `PLAN_DEVIATION` → S2 (G1-delta). `SPEC_ISSUE` → S0. Self-repair exhausted / `ENV_FAILURE` → G2 |
| **S4 Review** | Fresh diff snapshot | REV (model by §2) | `review-<n>.md` with YAML front matter `{blockers, nits, design_concerns}` | no blockers → S5. Blockers and `review_rounds` < 3 → S3. `design-concern` → S2 (plan/convention) or S0 (spec), not counted. Blockers after round 3 → **G2** |
| **S5 QA** | Review passed | QA | External AC checks in `tests/`; test requirements for in-project tests as conventions; **full** suite run (regression) | green → S6. Flow change → S3 → S4 (review counter continues). Nit-level → S3 → back to S5 (`qa_fix` ≤ 2). Untestable AC / `SPEC_ISSUE` → S0. Exhausted → G2 |
| **S6 Accept** | QA green | `check-trace` (automated); PM only on failure | `acceptance.md`: every AC → passing test id | all met → S6b. Unmet (code) → S3 (`accept_reopen` ≤ 1). Unmet (spec gap) / invalid AC → S0. New work → backlog. Second unmet → G2 |
| **S6b Regen-check** | Accepted | ORC runs `regen-check` | Fresh worktree, delete `clients/<app>`, `/generate`, full tests | green → S7. Fail → S3 (`regen_check` ≤ 2) → then G2 |
| **S7 Retro** | Regen green | ORC | `docs/runs/<feature>/`, retro from run log, merge `feat/<id>` `--no-ff`, update backlog + INDEX | next feature → S0 |
| **G2 Escalation** | Any counter exhausted, `ENV_FAILURE`, or conflict | **OP** | change spec / replan / one more round / defer / stop | → S0 / S2 / S3 / backlog / ABORTED |

### 5.1 Return codes (every agent ends with exactly one)
`OK` · `SPEC_ISSUE{spec_id, question}` · `PLAN_DEVIATION{reason, proposal}` · `STALE_DIFF` · `ENV_FAILURE{detail}` · `BLOCKED{reason}`.
ORC routes non-`OK` codes per the table above and never lets an agent continue past one.

### 5.2 Counters and budgets (`STATE.json`, per feature per app)

| Counter | Cap | On exceed |
|---|---|---|
| `review_rounds` (round 1 = first review; includes QA-triggered re-reviews) | 3 | G2 |
| `qa_fix` | 2 | G2 |
| `accept_reopen` | 1 | G2 |
| `g1_rejections` | 2 | ORC asks operator for a discussion instead of another round |
| `spec_reopen` | 2 | G2 |
| `gen_self_repair` (per `/generate` run) | 3 | `/generate` fails → G2 |
| `regen_check` | 2 | G2 |
| Budget: wall time, tokens (soft / hard) | set per feature at S1 | soft → note in retro; hard → G2 |

Caps, the §2 reviewer threshold (400 changed lines) and the §6 split threshold (2000) live only in `generator/config/generator.json` (`limits`); `generator/scripts/state.py` enforces the caps (exceeding one routes to G2).

### 5.3 Abort and failure
`BLOCKED` = feature parked with reason; ORC continues independent features. `ABORTED` = branch kept, STATE + partial retro written. Rollback = reset feature branch to the last green stage commit. `ENV_FAILURE` is retried at most once, then G2. `preflight` checks JDK, Android SDK, Node, Python versions before P3.

## 6. Diff snapshot rule
1. Before every handoff ORC commits (WIP commits allowed) so the diff is commit-addressed, then runs `snapshot-diff` → `diff.patch` + `diff.meta.json` `{base_sha, head_sha, worktree, porcelain_clean, patch_sha256, numstat, changed_lines, created_at, stage}`.
2. `changed_lines` = insertions + deletions from `git diff --numstat base...head`, excluding lockfiles, wrapper/binaries and `.generated` manifests (`count-lines`). This value drives the REV model rule.
3. Every agent's first action: check `HEAD == head_sha` and a clean worktree; otherwise return `STALE_DIFF`.
4. Agents read the snapshot; they do not run `git diff` themselves. If `changed_lines` > 2000, the snapshot is a file list + per-module patches and agents read the files.
5. ORC must not launch a stage on a stale snapshot.

## 7. Parallelism
- Allowed only for DEV / REV / QA of **different apps** after G0 (and G1 if run), each in its own worktree `.work/wt/<feature>-<app>`.
- `spec/`, `docs/product/`, `generator/` shared files and root files are serialised through ORC.
- ORC merges worktrees sequentially, re-snapshots, and logs `parallel_with` in the run log.

## 8. Prompts, logging, commits
- **Prompts:** templates in `generator/prompts/<role>.md` with variables only (feature, app, input paths, output path, boundaries, exit criteria, return codes). ORC fills variables; the rendered prompt's sha256 goes in the run log. Generator prompts must not name features (E-EVOL-1).
- **Run log:** one JSON line per transition in `docs/runs/<feature>/run.jsonl` (ts, feature, app, stage, event, agent, model, model_id, model_reason, counters, base/head sha, changed_lines, spec_version, prompt_sha256, inputs, outputs, result, findings, return_code, duration, tokens, gate, decided_by, operator_msg_ref, parallel_with).
- **Commits:** branch `feat/<id>`, one commit per stage output, merge `--no-ff`, no squash. Generated output in its own commit: `regen(<app>): spec X.Y.Z @ gen <sha>`. No commit touches both `spec/` and `clients/`. Agent commits use author `Aware Agent (<ROLE>/<model>) <agent@aware.local>`, operator as committer. Trailers: `Area`, `Boundary: generated|maintained`, `Authored-By-Role: human|agent`, `Agent`, `Model`, `Stage`, `Feature`, `Approved-By: operator` (gates), `Refs: OM-nnnn`. All trailers go in a single final block with no blank line inside it, because git reads only the last paragraph as trailers.
- **Operator log:** ORC appends verbatim with an `OM-nnnn` id; AI notes prefixed `AI note:`; operator confirms in the commit (`Approved-By: operator`).

## 9. Autonomous mode (`/pipeline --autonomous`)
| Gate | Behaviour |
|---|---|
| G0 | Halt the feature (`BLOCKED`), continue independent features |
| G1 | Auto-approve if E-TL-1 passes; log rationale; flag for operator review |
| G2 | Halt the feature (`BLOCKED`), continue independent features |
| Hard budget | Halt |
Resumable from `STATE.json` + run log; ORC checkpoints after every transition.
`/generate` never has gates in either mode.

## 10. Retrospective (per feature)
Rendered at S7 from `run.jsonl` (stage table, counters, models, durations, backward transitions, spec version in/out, regen result, budget actuals), then ORC adds: gaps found, decisions, what to improve next ticket, proposed workflow changes (with status). The operator may add "Human notes". `docs/runs/INDEX.md` links every feature.

## 11. Evals

| ID | Check | How |
|---|---|---|
| E-PM-1 | Every BR/SC maps to spec id + AC per affected app | `check-trace` |
| E-PM-2 | ACs testable, no implementation terms | Given/When/Then regex + denylist lint |
| E-TL-1 | Plan cites spec ids; stack matches context doc; no messaging SDKs | grep plan; check `libs.versions.toml` / Gradle modules / `package.json`; dependency denylist |
| E-DEV-1 | Build + in-project tests pass; manifest == tree; headers | `./gradlew assembleDebug testDebugUnitTest`, `npm ci && npm run build && npm test`, `check-headers` |
| E-REV-1 | Report schema valid | YAML front matter + `- [blocker\|nit\|design] path:line — ` lines |
| E-QA-1 | Every `CORE-xxx` MUST has ≥1 test carrying its id | `check-trace` over JUnit XML / Playwright JSON |
| E-PM-3 | Every AC → passing test id | `check-trace` |
| E-PROTO-1 | Server conforms to schema + server-behavior | `tests/protocol` (pytest) |
| E-INTEROP-1 | Alice/Bob step states match spec, android↔web both pairings | `tests/interop/run.sh` |
| E-BOUND-1 | `/generate` writes only inside `clients/<app>` | `git status --porcelain` after regen |
| E-LOCAL-1 | No external hosts | grep for non-localhost / 10.0.2.2 URLs |
| E-DET-1 | Two regens: same file set per module, same test results | `regen-check` ×2 |
| E-EVOL-1 | Harness generic | prompt lint (no feature nouns); F5 regenerates with no prompt edits |
| E-PIPE-1 | **Regeneration works** (primary criterion) | `regen-check` from fresh clone, pinned model, full suites |
| E-PIPE-2 | Spec authoritative | E-QA-1 at 100% + E-DET-1 + no open `SPEC_ISSUE` at release |
| E-PIPE-3 | Commit history and attribution | `lint-commits` |
| E-README-1 | README covers each brief deliverable | checklist script |
| E-WF-1 | State machine mechanics | stub-agent dry run with injected `SPEC_ISSUE`, 4 blocker rounds, `STALE_DIFF` |
| E-WF-2 | Resume works | kill ORC mid-S4, resume, no duplicated/skipped stage |
| E-ATTR-1 | Operator log append-only, AI notes prefixed | git-blame check |
| E-COST-1 | Budget adherence | run.jsonl totals vs caps |

## 12. Remaining open items
- Exact budgets per feature (set at P1).
- Pinned model IDs and fallback for `/generate` (`generator/config`, set at P3).
- Messaging-SDK denylist contents (review at P0).
