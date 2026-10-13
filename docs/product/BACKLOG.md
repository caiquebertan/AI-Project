# Backlog

- **Status:** draft for operator approval (WORKFLOW Q24: the operator approves the backlog once, in Phase 1). Owner: PM. Written for spec 0.1.0-draft.
- **Reading guide.** Epics → features → stories. Features are vertical slices (decision 0002 Q23): each one delivers something a user can see, on both clients. Rule ids point to [`spec/core/client-behavior.md`](../../spec/core/client-behavior.md) (`CORE-LOGIN` ... `CORE-VISIBLE`) and to the TL's protocol rules; acceptance criteria (ACs) are in the spec next to those rules; test ids per scope are in [`TRACEABILITY.md`](TRACEABILITY.md).
- **Statuses:** `done`, `drafted` (written, awaiting operator), `planned`, `blocked`.
- **Chain** (WORKFLOW §5): `full` = first feature per app and any generator or architecture change (plan and gate G1 included); `light` = otherwise.
- **Order of work** (decision 0002 Q7): spec, then server and protocol tests, then generator, then clients.

## Epic overview

| Epic | Phase | What it delivers | Status |
|---|---|---|---|
| E0 Harness | P0 | Agent roles, prompts, scripts, pipeline mechanics | done |
| E1 Spec and backlog | P1 | Protocol, server behavior, client behavior, scenarios, traceability, backlog; gate G0 | drafted |
| E2 Server | P2 | Reference server and protocol tests | planned |
| E3 Generator v1 | P3 | Templates, conventions, generate command; first Android and web builds | planned |
| E4 Messaging product | P4, P5 | Features F1 to F4 on both clients, interop between them | planned |
| E5 Evolution demo | P6 | Feature F5: a new capability added by spec only | planned |
| E6 Regeneration proof | P7 | Delete-and-regenerate from a fresh clone, twice | planned |
| E7 Packaging | P8 | README, DESIGN, FUTURE, archive, clean-sandbox check | planned |

## E1 Spec and backlog (P1)

| Item | Owner | Covers | Status |
|---|---|---|---|
| Protocol, server behavior, schemas, platform rules, hooks, decisions 0004 to 0009 | TL | all `CORE-*` TL areas, `PLAT-*` | drafted (G0) |
| Client behavior, scenarios, acceptance criteria | PM | `CORE-LOGIN` to `CORE-VISIBLE`, `SC-1..8`, `SX-1..5` | drafted (G0) |
| Backlog and traceability | PM | BR-1..4, SC-1..7 | drafted |
| Operator answers to G0 questions (TL Q1 to Q7, PM questions in `docs/planning/g0-review-pm.md`) | OP | defaults assumed in the spec | open |

## E2 Server (P2), chain: light (server)

| Story | Covers | Depends on | Status |
|---|---|---|---|
| S-E2-1 As a developer I can start one local server process that keeps everything in memory and prints its address | CORE-SRV-001, -002, -006 | G0 | planned |
| S-E2-2 Registration, sending with acknowledgement, duplicates and mailboxes follow the protocol | CORE-SESSION, CORE-MSG, CORE-SRV-020 to -036, CORE-SEQ-001 | S-E2-1 | planned |
| S-E2-3 Waiting reads return as soon as a message arrives and are side-effect free | CORE-POLL, CORE-SRV-012 to -014 | S-E2-1 | planned |
| S-E2-4 Errors, limits and unknown message kinds follow the protocol | CORE-ERR, CORE-EXT-001, CORE-SRV-040 | S-E2-2 | planned |
| S-E2-5 Protocol tests (`tests/protocol`) replay the Alice/Bob trace and each error code | Appendix A, E-PROTO-1 | S-E2-2..4 | planned |

## E3 Generator v1 (P3), chain: full

| Story | Covers | Depends on | Status |
|---|---|---|---|
| S-E3-1 Design the generation plan: templates for build infrastructure, conventions per platform, generation order, bounded self-repair, manifest | WORKFLOW §3, PLAT-ANDROID, PLAT-WEB | G0, E2 | planned |
| S-E3-2 Implement the generate command so it reads only the spec and writes only inside `clients/<app>` | E-BOUND-1, E-EVOL-1 | S-E3-1 | planned |
| S-E3-3 First Android build from the spec, in-project tests green | PLAT-ANDROID-019..024 | S-E3-2 | planned |
| S-E3-4 First web build from the spec, in-project tests green | PLAT-WEB-013..017 | S-E3-2 | planned |
| S-E3-5 Gate G1 and review of the first generation (REV on Opus) | WORKFLOW §5 | S-E3-3, -4 | planned |

## E4 Messaging product

### F1: Identity and login (BR-1)

- **Goal.** A person opens either app for the first time, types a name, and lands on an empty conversation screen under that name. Next time they open the app they are already in. It works with no server running.
- **Apps.** Android, web. Server: none (registration happens when the app first connects).
- **Covers.** `CORE-LOGIN-001..005`, `CORE-VISIBLE-001`; wire: `CORE-NAME`, `CORE-SESSION`. ACs `AC-F1-1..7`.
- **Chain.** Android `full`, web `full` (first feature per app; includes app skeleton, connection engine shell, hooks).
- **Depends on.** E1 (G0), E2, E3.
- **Status.** planned.

| Story | App | Chain | Status |
|---|---|---|---|
| S-F1-1 As a first-time user I see a name screen and can continue only with a valid name, with a clear message otherwise | android | full | planned |
| S-F1-2 Same for web | web | full | planned |
| S-F1-3 As a returning user I skip the name screen and see my own name, whichever way I typed it first | android, web | full | planned |
| S-F1-4 As a user with no server running I can still log in and see `Connecting` | android, web | full | planned |
| S-F1-5 Header with name, connection indicator and offline switch on every screen after login | android, web | full | planned |
| S-F1-6 Test hooks and state snapshot available (PLAT-HOOK) | android, web | full | planned |

### F2: Send and receive (BR-2, BR-4)

- **Goal.** Two people each in their own app can exchange text messages. They see their own messages and the other's, in the same order, with clear states.
- **Apps.** Android, web. Server: as built in E2.
- **Covers.** `CORE-SEND-001..011`, `CORE-RECEIVE-001..006`, `CORE-ORDER-001..006`, `CORE-VISIBLE-002..009`; wire: `CORE-MSG`, `CORE-POLL`, `CORE-CURSOR`, `CORE-SEQ`. ACs `AC-F2-1..16`; steps `SC-1`, `SC-2`.
- **Chain.** `light` for both apps.
- **Depends on.** F1.
- **Status.** planned.

| Story | App | Chain | Status |
|---|---|---|---|
| S-F2-1 Start a conversation by typing a name; invalid names refused | android, web | light | planned |
| S-F2-2 Write a message: it appears at once as `Pending` and becomes `Sent` when the server confirms; blank or too long text refused | android, web | light | planned |
| S-F2-3 Messages from others appear by themselves as `Received`, in conversation order | android, web | light | planned |
| S-F2-4 Conversation list with newest conversation first | android, web | light | planned |
| S-F2-5 Unknown message kinds and duplicates are never shown | android, web | light | planned |
| S-F2-6 Notes to self; text shown exactly as typed | android, web | light | planned |
| S-F2-7 Failed look defined and shown (practically unreachable) | android, web | light | planned |

### F3: Offline queue and flush (BR-3)

- **Goal.** A person can switch the app to offline, keep writing, and later reconnect: queued messages are delivered in order without any further action, and what others sent meanwhile appears first. Nothing is lost or shown twice, even after closing the app or restarting the server.
- **Apps.** Android, web.
- **Covers.** `CORE-OFFLINE-001..007`, `CORE-FLUSH-001..006`, `CORE-VISIBLE-008`; wire: `CORE-CONN`, `CORE-OUTBOX`, `CORE-EPOCH`, `CORE-DEDUPE`. ACs `AC-F3-1..15`; steps `SC-3..SC-7`; scenarios `SX-1..SX-3`.
- **Chain.** `light` for both apps.
- **Depends on.** F2.
- **Status.** planned.

| Story | App | Chain | Status |
|---|---|---|---|
| S-F3-1 Offline switch and indicator; no contact with the server while offline | android, web | light | planned |
| S-F3-2 Messages written offline stay `Pending` and survive closing the app | android, web | light | planned |
| S-F3-3 On reconnect, waiting messages appear first, then queued ones are delivered in order | android, web | light | planned |
| S-F3-4 Retry by itself when the server is unreachable; no duplicates after a lost confirmation | android, web | light | planned |
| S-F3-5 Server restart: history cleared, queued messages delivered | android, web | light | planned |

### F4: Interoperability, Android and web (BR-2, BR-3, BR-4; SC-1..SC-8)

- **Goal.** Whatever the combination (Android with web, web with Android, two of the same), the Alice and Bob scenario ends in the same screens. This is the evaluation scenario.
- **Apps.** Android, web, server (tests only).
- **Covers.** Scenario `SC-1..SC-8` in the main scenario file; ACs `AC-F4-1..9`. Needs the Android driver decided at G0 (TL question Q5).
- **Chain.** `light` for both apps (no new client code expected; failures become spec or generator fixes). Test work: QA, full suite design once.
- **Depends on.** F1..F3, E2.
- **Status.** planned.

| Story | App | Chain | Status |
|---|---|---|---|
| S-F4-1 Alice/Bob steps 1 to 7 and 8 pass web with web, with state-based waiting | web, server | light | planned |
| S-F4-2 The same passes Android with web and web with Android | android, web | light | planned |
| S-F4-3 The same passes Android with Android | android | light | planned |
| S-F4-4 Interop runs three times in a row without a failure (E-INTEROP-1) | android, web | light | planned |

### Enabling work around F1 to F4

| Item | Phase | Notes | Status |
|---|---|---|---|
| External checks `tests/web-e2e`, `tests/interop`, `tests/android-conformance` (QA) | P4, P5 | wait on state, never on fixed delays | planned |
| Trace check green for F1..F4 (`check_trace`) | each feature at S6 | every AC has a passing test | planned |
| Regen check after each feature | each feature at S6b | one clean regeneration | planned |

## E5 Evolution demo (P6)

### F5: Reactions extension

- **Goal.** Prove that a new capability is added by writing spec only. A user can attach a reaction to a message; a client without the capability simply does not show it and nothing breaks.
- **Apps.** Android, web. Server: none (the server relays opaque kinds, CORE-EXT-001).
- **Covers.** A new extension file under `spec/extensions/` (its own `EXT-REACTIONS` rules and scenarios, including a mixed pair of capable and core-only clients). No change to any core rule (CORE-EXT-005). Rows are added to `TRACEABILITY.md` when that spec is written (S1 of F5).
- **Chain.** `light` (the generator must not change; E-EVOL-1).
- **Depends on.** F1..F4 done, regen proof (P7) not required.
- **Status.** planned.

| Story | App | Chain | Status |
|---|---|---|---|
| S-F5-1 Write the extension spec (behavior by PM, payloads and platform by TL), gate G0 | spec | light | planned |
| S-F5-2 Regenerate both clients with no prompt changes; reactions work between capable clients | android, web | light | planned |
| S-F5-3 Mixed pair: the core-only client ignores reactions and keeps working | android, web | light | planned |

## E6 Regeneration proof (P7)

| Story | Covers | Status |
|---|---|---|
| S-E6-1 From a fresh clone, delete the generated code, run the documented generate command, both clients build and pass their tests; twice (E-PIPE-1, E-DET-1) | brief "Regeneration works" | planned |
| S-E6-2 The operator repeats it once, following only the README | brief | planned |

## E7 Packaging (P8)

| Story | Covers | Status |
|---|---|---|
| S-E7-1 README naming harness, spec, generator, generated code and boundary; DESIGN; FUTURE | brief "Deliverables" | planned |
| S-E7-2 Lint scripts green, archive built, unpacked and regenerated in a clean sandbox | E-README-1, E-LOCAL-1 | planned |

## Dependencies at a glance

`G0 (spec) → E2 server → E3 generator v1 (G1) → F1 → F2 → F3 → F4 → F5 (G0 for its spec) → E6 → E7`. F1 to F3 need the server for their external tests; F4 needs everything.

## Risks and assumptions

**Assumptions**
- Operator answers match the TL recommendations (Q1 to Q7); otherwise the rules named in `client-behavior.md` section 10 change, plus affected ACs.
- Two screens, names-only list, fixed English texts, no timestamps, switch not remembered and no restart notice are acceptable for v1 (questions in the PM packet).
- Android runs without an emulator in the sandbox (decision 0002 Q19); interop for Android depends on the answer to TL question Q5.

**Risks**
- Volume of testable rules: each `MUST` needs a passing test (E-QA-1). Mitigation: PM presentation rules that are not essential are `SHOULD`; the generator must name several ids per test.
- Timing: long waits (20 seconds idle, up to 8 seconds retry) make tests slow. Mitigation: tests wait for states; in-project tests use injected time.
- Two interpretations of "identical": layout is free, texts and order are fixed. Visual differences must never be reported as defects; a text difference always is.
- F4 depends on every earlier slice and on the Android driver; slip there delays the primary graded scenario. Mitigation: the web/web pairing runs as soon as F3 is done.
- Spec changes after G0 cost a reopen (cap `spec_reopen: 2`); resolve operator questions before P2.
