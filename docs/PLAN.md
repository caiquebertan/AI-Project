# Final plan — Aware (P2 to P8)

> **Author:** TL agent (claude-opus-5-5) for ORC, phase P1, ref OM-0011 ("present to me the final plan"). AI-written; awaiting the operator's reading.
> **Base:** `main` @ `a6e3bb5`, spec `0.1.0` (tag `spec-v0.1.0` → `a38460f`), `generator/WORKFLOW.md` v0.3.0, decisions 0002, 0003, 0011, 0013, 0014, 0015.
> **Precedence:** brief > operator's words > WORKFLOW > this plan. Where the documents disagree, §8 lists it; this plan does not silently pick a side.

## 1. Goal and where we are

**Goal (brief, primary criterion):** delete `clients/android/` and `clients/web/`, run `/generate`, get working clients that pass their tests and interoperate through the server as the spec says. Everything below serves that; anything that does not is after the cut line.

| Phase | Status | What it produced |
|---|---|---|
| P0 Harness | done, approved (OM-0008, decision 0003); retro `docs/retros/P0.md` | `generator/scripts/` (state machine, snapshot, trace, regen, lint, preflight), `.claude/agents/`, `.claude/commands/{pipeline,generate}.md`, `generator/prompts/`, `generator/RUN.md`, 82 harness self-tests |
| P1 Backlog + core spec | done, approved (OM-0011, decision 0013) | spec **0.1.0** tagged: 242 rule ids (239 `MUST`), **52 ACs**; `spec/core/{protocol,server-behavior,client-behavior}.md`, `spec/core/schema/`, `spec/scenarios/` (SC-1..SC-8, SX-1..SX-6), `spec/platform/{android,web,test-hooks}.md`; decisions 0004–0009, 0012, 0014; `BACKLOG.md` (E0–E7, D1 = F1+F2+F3, F4, F5); `TRACEABILITY.md` (210 AC-scope rows); ten MVP cuts (0013); environment rule (0011); operator-authored commits (0015); retro `docs/retros/P1.md` |
| P2 Server | done, closed with known gaps (OM-0017, decision 0019) | spec **0.1.1** (decision 0018, tag `spec-v0.1.1`); `server/`, `tests/protocol/` (138 tests green); review rounds 1 and 2 and fix passes in `docs/runs/P2/`; retro `docs/retros/P2.md` |
| P3 Generator v1 | next (design approved at G1, decision 0017; plan defaults accepted, decision 0016) | not started |
| P4 to P8 | planned | as §2 |

**Not done yet, and never tried:** no generator conventions or templates (`generator/conventions/`, `generator/templates/` do not exist), `generate_model` and build/test commands are `TBD-at-P3`, `/generate` stops with "generator not yet configured". **No client has ever been generated, built or run.** Retros for P0, P1 and P2 exist in `docs/retros/`.

## 2. Remaining phases

Ordered as WORKFLOW §4. "Cloud" = agents in the cloud workspace (Python only). "Operator" = the operator's machine with Claude Code locally (decision 0011, WORKFLOW §5.4). Effort is a rough guess in operator sessions (one sitting at the keyboard), because operator time is the bottleneck, not agent time.

### P2 Server — light server chain (WORKFLOW §5.5, BACKLOG E2)
- **Purpose:** reference server + protocol tests, so D1's external tests have something real to talk to.
- **Where / agents:** cloud. DEV (Sonnet; Opus only if interpretation is needed) → one REV round (Sonnet). No TL plan, no QA agent, no PM acceptance, no G1. ORC sends S5 `green` / S6 `met` once protocol tests pass (`state.py start-feature P2 --apps server --chain light`).
- **Inputs:** `spec/core/protocol.md`, `server-behavior.md`, `schema/`, Appendix A. **Outputs:** `server/` (Python stdlib, in-memory, threaded HTTP), `tests/protocol/` (Appendix A replay, every error code, strict UTC validation `CORE-TIME-*`).
- **Exit:** E-PROTO-1 green in the cloud; stories S-E2-1..5 done. **Gates:** none (G2 only if review cap hit).
- **Risk / effort:** low. 0 operator sessions (operator only reviews the merge).

### P3 Generator v1 — full chain (BACKLOG E3)
- **Purpose:** turn the spec into clients with no hand edits: conventions per platform, templates for build infra and module skeletons, generation order, bounded self-repair (≤3), manifest, pinned model.
- **Where / agents:** design and implementation in the cloud: TL (Opus) design → **G1** → DEV (Opus, first generation) writes `generator/conventions/{android,web}.md`, `generator/templates/{android,web}/`, fills `generator/config/generator.json` (`generate_model`, fallback, build/test commands, toolchain pins). Then **operator**: `preflight.py --strict`, first `/generate android` and `/generate web` (parallel worktrees allowed), commit the `regen(<app>)` outputs + logs. REV (Opus, first generation) reads the generated code in the cloud.
- **Inputs:** whole spec 0.1.0, `spec/platform/*`, decision 0001 (React + TS + Vite), 0002 Q17/Q19. **Outputs:** generator inputs, two `regen(<app>)` commits with `.generated` manifests, build/test logs from the operator's machine.
- **Exit:** both clients build and in-project unit/UI tests pass **on the operator's machine** (E-DEV-1, E-BOUND-1, `check_headers.py`); `lint_prompts.py` clean (E-EVOL-1).
- **Gates:** **G1** (plan approval on the generator design, before DEV implements). G2 on `gen_self_repair` exhaustion or `ENV_FAILURE`.
- **Risk / effort:** **highest.** Android first (Gradle, Room, Robolectric, `:tools:driver`), web second. Expect 2–4 operator sessions, most of them Android.

### P4 Core delivery D1 (F1+F2+F3)
- **Purpose:** accept D1 per app against its ACs; build the external checks.
- **Where / agents:** cloud: REV (S4), QA (Opus, designs `tests/web-e2e/`, `tests/android-conformance/`, `tests/interop/` once), PM only if `check_trace` fails. **Operator:** every regeneration after a fix (`/generate <app>`), Gradle/npm tests, Playwright, the Android driver, and sending back JUnit XML / Playwright JSON for `check_trace`.
- **Inputs:** P3 output, TRACEABILITY F1–F3. **Outputs:** `docs/runs/D1/{run.jsonl,review-n.md,qa.md,acceptance.md}`, retro `docs/retros/D1.md`.
- **Exit:** `check_trace.py --feature F1,F2,F3` exit 0 for android and web (every AC has a passing test; rule coverage reported, not gated).
- **Gates:** G2 on any cap (review 3, qa_fix 2, accept_reopen 1, spec_reopen 2). Any spec fix = S0 + G0 + version bump (counts against `spec_reopen`).
- **Risk / effort:** high (concurrency in the polling cycle, store-then-cursor atomicity, Android UI provable only by Robolectric). 2–4 operator sessions; each fix loop costs one.

### P5 Interop (F4, BACKLOG S-F4-1..4)
- **Purpose:** the brief's Alice/Bob scenario, end to end, through the real server.
- **Where / agents:** QA in the cloud writes `tests/interop/run.sh`; the **operator** runs it (server + web UI via Playwright + Android JVM driver).
- **Required pairings (cut 6):** web↔web through the UI; Android driver (Alice) ↔ web UI (Bob). Others optional (S-F4-3).
- **Exit:** E-INTEROP-1 green **×3 in a row**; `check_trace --feature F4` exit 0; retro F4.
- **Gates:** G2. **Risk / effort:** medium-high (timing; driver is new code). 1–2 operator sessions.

### P6 Evolution demo (F5 reactions) — **the cut line**
- Only started after P5 is green (WORKFLOW §4.1). PM + TL write `spec/extensions/reactions.md` → **G0** → `/generate` with **no prompt changes** (E-EVOL-1) → operator builds and runs the mixed-pair scenario.
- **Exit:** E-EVOL-1. **Effort:** 1–2 operator sessions. Cut first if time is short.

### P7 Regeneration verification (BACKLOG E6)
- **Purpose:** prove the primary criterion. **Operator only.**
- `python3 generator/scripts/regen_check.py --app all --clone` twice (android then web, fresh clone, pinned model, full suites) → E-PIPE-1, E-DET-1. Then the operator repeats once following only the README (S-E6-2).
- **Gate:** OP. Failure → fix in spec/generator → G2 if it repeats. **Risk:** high, because it runs once, late (see §5). 1–2 operator sessions.

### P8 Packaging (BACKLOG E7)
- Cloud: final README / DESIGN / AGENTS / FUTURE (from retros), `lint_commits.py --strict-trailers`, `lint_prompts.py`, E-README-1, E-LOCAL-1.
- **Operator:** signing rebase with his key (decision 0003), then **re-create tags** (the rebase rewrites every hash, so `spec-v0.1.0` and later tags would point at unsigned commits), force-push `main`, push tags from his Mac, build the archive, unzip and regenerate in a clean sandbox.
- **Gate:** OP final review. **Effort:** 1 operator session.

**Order by risk (where to spend attention):** P3 Android > P7 regen > P4 D1 > P5 interop > P3 web > P6 > P8 > P2.

## 3. Operator environment and local runs

**Checklist before P3** (`docs/ENVIRONMENT.md`): Python 3.10+, Git, `claude` CLI logged in, JDK 17+ (21 known good), Android SDK with `ANDROID_HOME`, Node 22 LTS + npm, Playwright browsers (`npx playwright install`), network to npm, Maven Central, Google Maven, Gradle plugin portal. Then:

```
python3 generator/scripts/preflight.py --strict      # must exit 0
```

`preflight --strict` checks tool presence only: **not** registry access and **not** Playwright browsers. The first `/generate` is the real network check; if it fails with dependency download errors that is `ENV_FAILURE`, not a generator bug.

**What the operator runs, and when** (ORC hands over the exact command each time and logs it as `decided_by: operator`):

| When | Command (operator's machine) | Send back / commit |
|---|---|---|
| Start of P3 | `preflight.py --strict` | output |
| P3 first generation | `claude -p "/generate android" --model <pinned>`, same for `web` | `regen(<app>)` commit, build + test logs |
| P4 each fix loop | `/generate <app>`; `./gradlew testDebugUnitTest`; `npm test`; Playwright; driver tests | `regen` commit, JUnit XML, Playwright JSON |
| P5 | `tests/interop/run.sh` ×3 | logs + reports |
| P6 (if kept) | `/generate all` after the extension's G0 | `regen` commits, logs |
| P7 | `regen_check.py --app all --clone` ×2, then README-only run | `.work/regen/` reports summarised in the run log |
| P8 | signing rebase, re-tag, push `main` + tags, archive, clean-sandbox regen | archive, `git log --show-signature` |

Cloud-only (no operator time): P2 server and protocol tests, spec deltas, generator design and code, reviews by reading, QA test code, docs, lints.

## 4. Cut line and cut order (decision 0013, WORKFLOW §4.1)

Phase order stays P5 → P6 → P7 → P8. If time runs short:
1. **P6 / F5 reactions** — first; never started while interop is red. **[Fixed: 0003 and 0002 Q13 annotated as superseded by 0015. Commit: "docs: fix stale and contradictory text (PLAN §8)"]**
2. **Message-time display** — second: S-F2-8, `CORE-VISIBLE-009..012`, `CORE-TIME-*` display rules, SX-6, `AC-F2-17..23`. Note: the strict-UTC wire rules (server validates UTC `created_at`) are part of the protocol; withdrawing the *display* must not remove UTC validation on the wire (§8 item 6). **[Open (resolved by decision 0016 Q7; WORKFLOW/BACKLOG S-E3-5 wording not part of this commit).]**

Never cut: D1, F4 interop, P7 regeneration check, P8 packaging. Each cut is recorded in the retro and the README.

## 5. Risks and mitigations (top 6)

| # | Risk | Why it is real | Mitigation |
|---|---|---|---|
| 1 | **Nothing client-side has ever been built or run.** | All client rules, templates and the generate prompt are untested against real toolchains. | Treat P3 as an experiment: generate the smallest buildable skeleton first (templates), then fill modules; REV on Opus; keep the operator loop short by batching fixes into one regeneration. |
| 2 | **Android is the biggest risk.** | Gradle + AGP + Room + Robolectric version matrix, `:core:*` modules and the `:tools:driver` CLI, all from an LLM, built only on the operator's Mac. | Pin AGP/Kotlin/Gradle/SDK in templates (copied, not generated, decision 0002 Q17); ship the Gradle wrapper in templates; generate Android first so failures surface early; G2 early rather than burning self-repair rounds. |
| 3 | **Regen checked only once, at P7** (cut 8). | A non-deterministic or environment-dependent generation would be found at the very end, with the least time to fix. | Recommend one informal, non-gating regen run after D1 is accepted (§6 Q1). Every P4 fix is already a full `/generate`, so most of the path is exercised. |
| 4 | **Weak external Android evidence.** | No emulator; Android UI texts and times are proven only by Robolectric (PM open point 3: AC-F2-2, -4, -15, -17..23); the driver counts its own `Transport` calls (weaker than the withdrawn proxy, 0014). | State this plainly in README and DESIGN; keep the driver's counter at the `Transport` boundary; optional manual emulator run documented in FUTURE. |
| 5 | **Silent drop of a rejected message.** | No `failed` state (cut 4): a class-P rejection removes the message with only a diagnostic log line. | Unreachable for a correct client (local validation first); in-project tests cover removal + log line; interop asserts every scenario message reaches `Sent`. Listed in FUTURE. |
| 6 | **About 1 s send latency, `Online` before `Sent`.** | Plain polling at `CYCLE_INTERVAL_MS = 1000`; flush runs after the poll in the same cycle. | Tests wait on states (snapshot), never on sleeps or cycle counts (SC-5). Accept for the demo; start-cycle-on-enqueue stays rejected unless the operator says otherwise (§6 Q4). |

Also watched: spec reopens are capped at 2 after the tag; time tests must inject clock and zone (BACKLOG risks).

## 6. Open decisions for the operator (recommended default in bold)

| # | Question | Options | Recommended default |
|---|---|---|---|
| Q1 | Regen check before P7? | (a) only at P7 as in cut 8; (b) one informal run after D1, not gating, `regen_check.py --app all --clone` once | **(b)**: costs one operator session, removes the worst late surprise. Cut 8's gate stays at P7 |
| Q2 | PM/QA acceptance for the server? | (a) as WORKFLOW §5.5: protocol tests are acceptance, ORC sends `green`/`met`; (b) add QA review of `tests/protocol` | **(a)**: no server ACs exist; server rule coverage is reported by `check_trace`, informational |
| Q3 | Fold F4 into P5? (accepted (b), decision 0016) | (a) as written: F4 "feature-level work" at the end of P4, tests at P5; (b) F4 is one delivery run entirely in P5 | **(b)**: F4 expects no new client code (BACKLOG, light chain); one delivery, one retro, removes the P4/P5 overlap (§8 item 3) |
| Q4 | Send latency: start a cycle when a message is queued? | (a) keep rejected (0014); (b) add the trigger (spec reopen, both clients) | **(a)**: 1 s is fine locally; (b) adds trigger races and costs a `spec_reopen` |
| Q5 | AC for "no receipts / typing / unread indicators" (`CORE-VISIBLE-005`, `-006`)? | (a) leave as rule-level tests, informational; (b) PM adds a new AC (new id, patch bump) | **(a)**, but bundle (b) into the first spec reopen if one happens anyway |
| Q6 | Start P3 design while P2 runs? | (a) strictly sequential (0002 Q7); (b) TL designs the generator in parallel with P2 (different files, both cloud) | **(b)**: design does not read server code; saves wall time. DEV implementation and first generation still wait for P2 |
| Q7 | Do P3's first generation and D1's S2/G1 count as one? | (a) separate (P3 G1, then D1 full chain with its own S2 + G1); (b) P3's G1 is D1's G1 and P3's first `/generate` is D1's S3 | **(b)**: the first `/generate` reads the whole spec 0.1.0, so it *is* the D1 generation (§8 item 2) |

## 7. What I need from you next

1. Answer Q1–Q7 (or "defaults"); ORC records them as `OM-0013` and a decision record.
2. Approve this plan so ORC starts P2 (cloud, no operator time) and, if Q6 = (b), the P3 design.
3. Get the machine ready now: install the Android SDK, set `ANDROID_HOME`, run `npx playwright install`, and send the output of `python3 generator/scripts/preflight.py --strict`.
4. Reserve time for the P3 first-generation session (likely the longest one, Android first).
5. Push the `spec-v0.1.0` tag from your Mac if it is not on origin yet (tag pushes fail from the cloud).

## 8. Contradictions and stale text found

1. **Decision 0003 vs 0015.** 0003's signing command says "authors stay `Aware Agent (...)`; the committer becomes the signing operator". 0015 supersedes that author convention and history is already operator-authored (89/89 commits). 0003's comment is stale; the command itself still works. 0002 Q13 (distinct agent author) is likewise superseded but not annotated. **[Fixed: 0003 and 0002 Q13 annotated as superseded by 0015. Commit: "docs: fix stale and contradictory text (PLAN §8)"]**
2. **G1 placement.** WORKFLOW P3 puts G1 on the generator design *before* DEV implements; BACKLOG S-E3-5 puts "Gate G1 and review of the first generation" *after* the first builds (S-E3-3, -4). Separately, D1 is "full chain, first generation" (S2 + G1 again) right after P3. Proposed resolution: Q7. **[Open (resolved by decision 0016 Q7; WORKFLOW/BACKLOG S-E3-5 wording not part of this commit).]**
3. **F4 straddles P4 and P5.** WORKFLOW P4 says "then F4 interop (feature-level work; the P5 tests exercise it)"; BACKLOG E4 lists P4, P5; P5 has no gate and its own exit. Proposed resolution: Q3. **[Fixed in BACKLOG E4/F4 and PLAN (F4 is one run entirely in P5, decision 0016 Q3). WORKFLOW P4 wording is left to the WORKFLOW change. Commit: "docs: fix stale and contradictory text (PLAN §8)"]**
4. **Regen at S6b vs once at P7.** AGENTS.md "Definition of done" still requires "Clean delete-and-regenerate check passes (S6b)"; `docs/ENVIRONMENT.md` "What runs where" lists "S6b regen-check"; 0002 Q16 says "full clean regeneration at S6b". Cut 8 / WORKFLOW v0.3.0 / `regen.per_feature=false` make it once at P7. **[Fixed: AGENTS.md and ENVIRONMENT.md say once at P7; 0002 Q16 annotated as amended by 0013. Commit: "docs: fix stale and contradictory text (PLAN §8)"]**
5. **Server chain.** 0002 Q6 says "TL-lite → DEV → REV"; cut 7 and WORKFLOW §5.5 say no TL plan. 0002 is not annotated as amended. **[Fixed: 0002 Q6 annotated as superseded by 0013 cut 7. Commit: "docs: fix stale and contradictory text (PLAN §8)"]**
6. **Time display vs UTC wire rules in the cut.** BACKLOG cut order lists all `CORE-TIME-*` under "message-time display", but `CORE-TIME-*` also carries the operator's strict-UTC wire rule (OM-0011: server expects and validates UTC). Cutting display must keep the wire rules; the PM/TL should list exactly which ids go if this cut is taken. **[Open (PM/TL to list exact ids if the cut is taken).]**
7. **Stale status text.** README says "Phase 0 harness built… Spec … still to be written", spec "☐ skeleton", workflow "v0.2"; `spec/README.md` header says approved 0.1.0 but every index row says "draft (G0)"; BACKLOG E1 says "drafted (… version and tag set by ORC)" though the tag exists. To fix in one docs commit at the start of P2 or at P8. **[Fixed: README status, spec/README.md index rows, BACKLOG E1. Commit: "docs: fix stale and contradictory text (PLAN §8)"]**
8. **Missing retros.** WORKFLOW §10 asks for a retro per phase; none exists for P0 or P1. **[Fixed: `docs/retros/P0.md`, `P1.md`, `P2.md`. Commit: "docs: fix stale and contradictory text (PLAN §8)"]**
9. **Preflight scope.** ENVIRONMENT requires registry access and Playwright browsers; `preflight.py --strict` checks neither (see §3). **[Fixed: ENVIRONMENT.md states the preflight scope and mentions `setup_env.py`. Commit: "docs: fix stale and contradictory text (PLAN §8)"]**
