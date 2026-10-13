# Agent pipeline workflow (AI-readable)

> **Source:** operator instruction of 2026-10-13 12:51, verbatim in [`docs/human-input/OPERATOR_MESSAGES.md`](../docs/human-input/OPERATOR_MESSAGES.md).
> This file translates that instruction into explicit roles, triggers, stages, gates, loops, artifacts and evals. Where this file and the operator's words disagree, the operator's words win; where either disagrees with the brief ([`docs/brief/aware-test-brief.md`](../docs/brief/aware-test-brief.md)), the brief wins.
> **Status:** v0.1 draft. Open items are marked `GAP-xx` and collected in §10. The gap analysis is in [`docs/planning/workflow-gap-analysis.md`](../docs/planning/workflow-gap-analysis.md).

---

## 1. Goal

Deliver the Aware project (spec → generated Android + web clients + hand-written Python server) through a **pipeline of specialised agents**, always **human-in-the-loop** at defined gates, while being **replicable and launchable without a human** from a **single entry point**.

## 2. Roles

| ID | Role | Model | Owns | Never does |
|---|---|---|---|---|
| ORC | **Orchestrator / manager** (main session) | session model | Plan, project status, prompts for each agent, triage, diff file freshness, gates, parallelism decisions, retros | Writes production code itself (delegates) |
| PM | **Product manager** | Sonnet | WHAT: acceptance criteria (ACs) for android, web and server, in non-technical language; backlog of epics → features → stories; final AC acceptance check | Technical design |
| TL | **Tech lead** | **Opus, always** | HOW: implementation plan per app (android, web, server), per feature, the first time that feature is implemented | Code |
| DEV | **Developer** | Opus for the **first implementation**; Sonnet when the task maps objectively to the TL plan; Opus again when ORC judges it needs interpretation or must test scenarios/options | Implementation + **simple** unit tests only | Robust or UI test suites (QA's job) |
| REV | **Reviewer** | Sonnet; **Opus if the diff is > 400 changed lines** | Review report classifying each finding as **blocker** or **nit**, from magic strings/numbers up to race conditions and wrong-thread calls | Fixes code |
| QA | **QA engineer** | _unspecified (GAP-01)_ | Robust unit tests + UI tests where they fit; reports implementation changes needed to ORC | Changes production code directly |
| OP | **Operator** (human) | — | Approves TL plans; decides when review loop exceeds 3; answers escalations | — |

The operator always talks to ORC. ORC never lets agents talk to the operator directly.

## 3. Artifacts

| Artifact | Path (proposed) | Written by | Read by |
|---|---|---|---|
| Brief (authoritative) | `docs/brief/aware-test-brief.md` | — | all |
| Spec (behavior source of truth) | `spec/` | ORC / TL (GAP-02) | all |
| ACs, all apps, one document | `docs/product/ACCEPTANCE_CRITERIA.md` | PM | TL, DEV, QA, PM-accept |
| Backlog (epics, features, stories) | `docs/product/BACKLOG.md` | PM | ORC |
| TL plan per app per feature | `docs/plans/<feature-id>/<app>.md` (`app` ∈ android, web, server) | TL | OP (approval), DEV, REV |
| **Working diff file** | `.work/<feature-id>/<app>/diff.patch` + `diff.meta` (base commit, head commit, stage, timestamp) | ORC | next agent |
| Review report | `.work/<feature-id>/<app>/review-<n>.md` | REV | ORC, DEV |
| QA report | `.work/<feature-id>/<app>/qa.md` | QA | ORC |
| PM acceptance report | `.work/<feature-id>/acceptance.md` | PM | ORC |
| Retrospective (per feature) | `docs/retros/<feature-id>.md` (template: `docs/retros/TEMPLATE.md`) | ORC | OP, evaluators |
| Operator messages | `docs/human-input/OPERATOR_MESSAGES.md` | ORC (verbatim copy) | evaluators |
| Pipeline state | `.work/STATE.md` (current feature, stage, loop counters, gate status) | ORC | ORC on resume / autonomous run |

`.work/` is scratch (git-ignored, GAP-03); anything evaluators should see is summarised into the retro.

## 4. Pipeline

### 4.0 Phase 0 — AI structure (one-off)
Build the harness itself: agent definitions (`.claude/agents/`), entry point (§7), prompts (`generator/prompts/`), templates, this workflow. Respects the brief's deliverables (README, DESIGN.md, AGENTS.md/CLAUDE.md, spec, generator, marked generated code, FUTURE.md).

### 4.1 Per-project
| Step | Trigger | Agent | Output | Exit |
|---|---|---|---|---|
| P1 Backlog | Phase 0 done | PM | `BACKLOG.md` (epics → features → stories) + `ACCEPTANCE_CRITERIA.md` | ORC checks every brief requirement maps to ≥1 AC (eval E-PM-1). Operator gate? GAP-04 |

### 4.2 Per-feature loop (one feature at a time)

```
 S1 PM ACs ─► S2 TL plan ─► [G1 OPERATOR APPROVES PLAN] ─► S3 DEV ─► S4 REVIEW ⟲ (≤3) ─► S5 QA ─► S6 PM ACCEPT ─► S7 RETRO
                                   ▲ reject: back to S2          ▲   │ blockers → DEV     │ code change needed:
                                                                 │   └ >3 loops → [G2 OPERATOR]│ ORC triages → DEV
                                                                 └──── flow change ◄────────────┘ (nit → skip REV)
                                                        S6 unmet AC → ORC decides: new task / reopen (GAP-05)
```

| Step | Trigger | Agent / model | Input | Output | Exit / next |
|---|---|---|---|---|---|
| S1 | Feature selected from backlog | PM (Sonnet) | brief, spec, backlog | ACs for this feature, per app | ACs present for every affected app → S2 |
| S2 | ACs ready **and** first implementation of this feature | TL (Opus) | ACs, spec, existing code | One plan per affected app | → **G1** |
| **G1** | Plan written | **Operator** | plans | approve / request changes | approve → S3; changes → S2 |
| S3 | Plan approved (or, for non-first iterations, task assigned by ORC) | DEV (model per §2) | plan, ACs, diff file | Code + simple unit tests; ORC regenerates diff file | Builds + its tests pass → S4 |
| S4 | Diff file updated after DEV | REV (Sonnet / Opus > 400 lines) | diff file, plan, spec, ACs | Review report: blockers, nits | No blockers → S5. Blockers → DEV → S4 again. Loop counter +1. **Counter > 3 → G2** |
| **G2** | 4th review loop would start | **Operator** | review history | decide how to proceed | per operator |
| S5 | Review passed | QA (GAP-01) | diff file, ACs, plan | Unit + UI tests; QA report | Needs code change → ORC triage: **flow change** → DEV → S4 (counter rules GAP-06); **nit** → DEV → back to S5 directly. Clean → S6 |
| S6 | QA passed | PM (Sonnet) | ACs, QA report, running behavior evidence (GAP-07) | Acceptance report per AC: met / unmet / invalid AC | All met → S7. Unmet → ORC decides new task or reopen. Invalid AC → PM revises AC (GAP-05) |
| S7 | Feature accepted | ORC | all reports | `docs/retros/<feature-id>.md`; commits | Next feature → S1 |

### 4.3 Diff-file rule (all steps)
- At every stage transition ORC regenerates `.work/<feature-id>/<app>/diff.patch` from `git diff <base>...HEAD` (plus working tree if uncommitted) and updates `diff.meta`.
- No agent is launched unless `diff.meta.head` == current HEAD of the feature branch. ORC verifies before each handoff.
- Agents read the diff file; they do not run `git diff` themselves.
- "Changed lines" for the REV model rule = insertions + deletions from `git diff --shortstat`, excluding generated client code? (GAP-08)

### 4.4 Parallelism rule
ORC may run agents in parallel only when it can show they touch **disjoint file sets** (e.g. android DEV and server DEV on the same feature, since `clients/android/` and `server/` don't overlap). Shared files (`spec/`, `docs/product/`, root docs) are serialised. ORC records the decision in `STATE.md`.

## 5. Triggers (event → action)

| Event | Action |
|---|---|
| Operator asks for a feature / says "next" | ORC picks next backlog feature → S1 |
| ACs written | ORC checks: first implementation? → S2 TL; else → S3 |
| TL plan written | Stop; present to operator (G1). Autonomous mode: GAP-09 |
| Operator approves plan | S3, choose DEV model |
| DEV done | Refresh diff → S4, choose REV model by line count |
| REV report: blockers | Loop counter +1; ≤3 → DEV with report; >3 → G2 |
| REV report: nits only | ORC decides fix-now vs defer (GAP-10) → S5 |
| QA reports code change | ORC classifies flow vs nit → DEV (± REV) |
| PM acceptance fails | ORC: new task in backlog or reopen feature |
| Feature accepted | S7 retro, commit, update backlog status |
| Spec changes (GAP-02) | Regenerate affected clients, re-run QA/acceptance for affected features |

## 6. Prompts for agents
ORC builds each agent prompt from: role file (`.claude/agents/<role>.md`), scope (feature id, app), inputs (paths, not pasted content), the **boundaries** (brief constraints, generated-code rules from `AGENTS.md`), required output path and format, and the exit criteria from §4. Prompt templates live in `generator/prompts/`.

## 7. Single entry point & autonomous mode
- One entry point (proposed: a Claude Code skill / command `/pipeline`, with `docs`-level fallback `generator/RUN.md`).
- Modes: `interactive` (default; stops at G1, G2 and escalations) and `autonomous` (no human). Behaviour of gates in autonomous mode: **GAP-09**.
- Resumable from `.work/STATE.md`.

## 8. Retrospective (per feature)
ORC writes `docs/retros/<feature-id>.md` at S7 using `docs/retros/TEMPLATE.md`: what was delivered, loop counts, models used, gaps found, decisions taken, what to improve for the next ticket, changes proposed to this workflow.

## 9. Evals

| ID | Stage | Check |
|---|---|---|
| E-PM-1 | P1/S1 | Every brief "Required behavior" and the Alice/Bob scenario map to ≥1 AC per affected app |
| E-PM-2 | S1 | ACs are testable (observable outcome, no implementation terms) |
| E-TL-1 | S2 | Plan references the spec sections it implements; follows context-doc stack (Kotlin/Compose/Hilt/Retrofit/multi-module; Python in-memory server); no messaging SDKs |
| E-DEV-1 | S3 | Builds; DEV unit tests pass; GENERATED headers present in `clients/*` |
| E-REV-1 | S4 | Every finding labelled blocker/nit with file:line |
| E-QA-1 | S5 | Tests cover offline queue/flush and Alice/Bob scenario where the feature touches them |
| E-PM-3 | S6 | Each AC marked met/unmet with evidence |
| E-PIPE-1 | project | **Regeneration works**: delete generated code, run generator, clients pass conformance + interop (brief's primary criterion) |
| E-PIPE-2 | project | Spec is authoritative: no behavior exists only in code |
| E-PIPE-3 | project | Commit history shows stages; authorship (human vs agent) is clear |

## 10. Known gaps (initial; expanded by the gap analysis)
- **GAP-01** QA model not specified.
- **GAP-02** Who writes/owns `spec/` (the brief's source of truth)? PM writes ACs (WHAT), TL writes plans (HOW) — the platform-neutral protocol spec has no owner. ACs must not become a second source of truth.
- **GAP-03** Should review/QA reports be committed (evidence for evaluators) or stay scratch?
- **GAP-04** Is there an operator gate on ACs/backlog?
- **GAP-05** Rules for "unmet AC": new task vs reopen; who may change an AC.
- **GAP-06** Does a QA-triggered flow change reset or continue the review loop counter?
- **GAP-07** What evidence does PM use in S6 (test results? demo run of the scenario?)
- **GAP-08** 400-line threshold: count generated code or not?
- **GAP-09** Autonomous mode: what replaces G1/G2 (auto-approve with logged rationale, or halt)?
- **GAP-10** Nits: must they be fixed before QA?
- **GAP-11** Brief's **generator** (delete generated code → regenerate) vs this **delivery pipeline**: how does a regeneration run work — does it re-run TL/DEV/REV/QA, or a lighter deterministic path? Clients are "generated", so DEV writes code only inside `clients/*` via the generator?
- **GAP-12** Branching/commit policy per stage (feature branches? commit after each stage?).
- **GAP-13** Order of apps: server first so clients have something to talk to?
