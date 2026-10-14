# Backlog

- **Status:** approved by the operator at P1 (decision 0013, OM-0011), with the MVP cuts applied by the PM as below. Owner: PM. Written for spec 0.1.0 (version and tag set by ORC after the cuts merge).
- **Acceptance and delivery rules (decision 0013).** Acceptance is gated by the acceptance criteria (ACs); coverage of spec rules by tests is reported, not gated. F1, F2 and F3 are one single core delivery, **D1**, generated and reviewed as one unit per app. F4 and F5 stay separate deliveries. **Cut order if time is short:** (1) F5 reactions (P6), only started after interop passes; (2) message-time display (S-F2-8, `CORE-VISIBLE-009..012`, `CORE-TIME-*`, SX-6, `AC-F2-17..23`), kept modular so it can be withdrawn without touching other rules. Nothing else is cut.
- **Times.** UTC everywhere: the wire, the stored data and the tests use UTC; no time zone is hardcoded anywhere. A client shows the server's `accepted_at` converted to the device's local time (`CORE-TIME-001..003`, `CORE-VISIBLE-009..012`).
- **Withdrawn.** The `failed` message state is withdrawn (decision 0014): the rule and the two acceptance criteria that described it are one-line tombstones in the behavior spec (list: `docs/planning/pm-packet-cuts.md`). A message the server rejects for good is discarded and logged, with no user-visible state.
- **Reading guide.** Epics → features → stories. Features are vertical slices (decision 0002 Q23): each one delivers something a user can see, on both clients. Rule ids point to [`spec/core/client-behavior.md`](../../spec/core/client-behavior.md) (`CORE-LOGIN` ... `CORE-VISIBLE`) and to the TL's protocol rules; acceptance criteria (ACs) are in the spec next to those rules; test ids per scope are in [`TRACEABILITY.md`](TRACEABILITY.md).
- **Statuses:** `done`, `drafted` (written, awaiting operator), `planned`, `blocked`, `optional` (not needed for acceptance), `withdrawn`.
- **Chain** (WORKFLOW §5): `full` = first feature per app and any generator or architecture change (plan and gate G1 included); `light` = otherwise.
- **Order of work** (decision 0002 Q7): spec, then server and protocol tests, then generator, then clients.

## Epic overview

| Epic | Phase | What it delivers | Status |
|---|---|---|---|
| E0 Harness | P0 | Agent roles, prompts, scripts, pipeline mechanics | done |
| E1 Spec and backlog | P1 | Protocol, server behavior, client behavior, scenarios, traceability, backlog; gate G0 | done: spec 0.1.0 approved at G0 (OM-0011, decision 0013) and tagged `spec-v0.1.0`; clarified as 0.1.1 (decision 0018, tag `spec-v0.1.1`) |
| E2 Server | P2 | Reference server and protocol tests | planned |
| E3 Generator v1 | P3 | Templates, conventions, generate command; first Android and web builds | planned |
| E4 Messaging product | P4 (D1), P5 (F4) | D1 core messaging (F1+F2+F3) on both clients in P4; F4 interop (web with web, Android driver with web) is one delivery run entirely in P5 (decision 0016 Q3) | planned |
| E5 Evolution demo | P6 | Feature F5: a new capability added by spec only; first cut if time is short, starts only after interop passes | planned |
| E6 Regeneration proof | P7 | Delete-and-regenerate from a fresh clone, twice | planned |
| E7 Packaging | P8 | README, DESIGN, FUTURE, archive, clean-sandbox check | planned |

## E1 Spec and backlog (P1)

| Item | Owner | Covers | Status |
|---|---|---|---|
| Protocol, server behavior, schemas, platform rules, hooks, decisions 0004 to 0009 | TL | all `CORE-*` TL areas, `PLAT-*` | approved 0.1.0 (G0) |
| Client behavior, scenarios, acceptance criteria | PM | `CORE-LOGIN` to `CORE-VISIBLE`, `SC-1..8`, `SX-1..6` | approved 0.1.0 (G0, cuts applied) |
| Backlog and traceability | PM | BR-1..4, SC-1..7 | approved (G0) |
| Operator answers to G0 questions (TL Q1 to Q7, PM questions in `docs/planning/g0-review-pm.md`) | OP | defaults accepted in decision 0013 | done (OM-0011) |

## E2 Server (P2), chain: light (server: DEV, one review, protocol tests; no TL plan, no QA agent)

| Story | Covers | Depends on | Status |
|---|---|---|---|
| S-E2-1 As a developer I can start one local server process that keeps everything in memory and prints its address | CORE-SRV-001, -002, -006 | G0 | planned |
| S-E2-2 Registration, sending with acknowledgement, duplicates and mailboxes follow the protocol | CORE-SESSION, CORE-MSG, CORE-SRV-020 to -036, CORE-SEQ-001 | S-E2-1 | planned |
| S-E2-3 Reads answer at once with what is in the mailbox and are side-effect free (plain polling, no held requests) | CORE-POLL, CORE-SRV-003, -004 | S-E2-1 | planned |
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

### D1: Core messaging = F1 + F2 + F3

One delivery per app: F1, F2 and F3 below are generated, reviewed and accepted together (full chain, first generation), not as three loops (decision 0013, cut 2). Their stories, rules and ACs stay as listed; the trace rows stay under the F1, F2 and F3 headings, and D1 is accepted when every AC of F1, F2 and F3 is met (acceptance gated by ACs; rule coverage informational).

### F1: Identity and login (BR-1)

- **Goal.** A person opens either app for the first time, types a name, and lands on an empty conversation screen under that name. Next time they open the app they are already in. It works with no server running.
- **Apps.** Android, web. Server: none (registration happens when the app first connects).
- **Covers.** `CORE-LOGIN-001..006`, `CORE-VISIBLE-001`; wire: `CORE-NAME`, `CORE-SESSION`. ACs `AC-F1-1..7`.
- **Chain.** Part of D1 (Android `full`, web `full`): the first delivery per app includes app skeleton, connection engine shell, hooks.
- **Depends on.** E1 (G0), E2, E3.
- **Status.** planned.

| Story | App | Chain | Status |
|---|---|---|---|
| S-F1-1 As a first-time user I see a name screen and can continue only with a valid name, with a clear message otherwise | android | D1 (full) | planned |
| S-F1-2 Same for web | web | D1 (full) | planned |
| S-F1-3 As a returning user I skip the name screen and see my own name, whichever way I typed it first | android, web | D1 (full) | planned |
| S-F1-4 As a user with no server running I can still log in and see `Connecting` | android, web | D1 (full) | planned |
| S-F1-5 Header with name, connection indicator and offline switch on every screen after login | android, web | D1 (full) | planned |
| S-F1-6 Test hooks and state snapshot available (PLAT-HOOK) | android, web | D1 (full) | planned |

### F2: Send and receive (BR-2, BR-4)

- **Goal.** Two people each in their own app can exchange text messages. They see their own messages and the other's, in the same order, with clear states.
- **Apps.** Android, web. Server: as built in E2.
- **Covers.** `CORE-SEND-001..008`, `-010`, `-011` (`-009` withdrawn), `CORE-RECEIVE-001..006`, `CORE-ORDER-001..006`, `CORE-VISIBLE-002..012`; wire: `CORE-MSG`, `CORE-POLL`, `CORE-CURSOR`, `CORE-SEQ`. ACs `AC-F2-1..11` and `AC-F2-14..23`; scenario `SX-6`; steps `SC-1`, `SC-2`.
- **Chain.** Part of D1 (single delivery with F1 and F3).
- **Depends on.** F1.
- **Status.** planned.

| Story | App | Chain | Status |
|---|---|---|---|
| S-F2-1 Start a conversation by typing a name; invalid names refused | android, web | D1 | planned |
| S-F2-2 Write a message: it appears at once as `Pending` and becomes `Sent` when the server confirms; blank or too long text refused | android, web | D1 | planned |
| S-F2-3 Messages from others appear by themselves as `Received`, in conversation order | android, web | D1 | planned |
| S-F2-4 Conversation list with newest conversation first | android, web | D1 | planned |
| S-F2-5 Unknown message kinds and duplicates are never shown | android, web | D1 | planned |
| S-F2-6 Notes to self; text shown exactly as typed | android, web | D1 | planned |
| S-F2-7 Withdrawn (decision 0014): there is no `Failed` look; a message the server rejects for good is discarded and logged | android, web | - | withdrawn |
| S-F2-8 Each confirmed or received message shows the time it reached the server (UTC on the wire), converted to the device's local time as `HH:mm` (with the date when it is not today); pending messages show none (operator decision OM-0010). Second on the cut line, after F5 | android, web | D1 | planned |

### F3: Offline queue and flush (BR-3)

- **Goal.** A person can switch the app to offline, keep writing, and later reconnect: queued messages are delivered in order without any further action, and what others sent meanwhile appears first. Nothing is lost or shown twice, even after closing the app or restarting the server.
- **Apps.** Android, web.
- **Covers.** `CORE-OFFLINE-001..007`, `CORE-FLUSH-001..006`, `CORE-VISIBLE-008`; wire: `CORE-CONN`, `CORE-OUTBOX`, `CORE-EPOCH`, `CORE-DEDUPE`. ACs `AC-F3-1..15`; steps `SC-3..SC-7`; scenarios `SX-1..SX-3`.
- **Chain.** Part of D1 (single delivery with F1 and F2).
- **Depends on.** F2.
- **Status.** planned.

| Story | App | Chain | Status |
|---|---|---|---|
| S-F3-1 Offline switch and indicator; no new request while offline (a request already running may finish) | android, web | D1 | planned |
| S-F3-2 Messages written offline stay `Pending` and survive closing the app | android, web | D1 | planned |
| S-F3-3 On reconnect, waiting messages appear first, then queued ones are delivered in order | android, web | D1 | planned |
| S-F3-4 Retry by itself, once a second, when the server is unreachable; no duplicates after a lost confirmation | android, web | D1 | planned |
| S-F3-5 Server restart: history cleared, queued messages delivered | android, web | D1 | planned |

### F4: Interoperability, Android and web (BR-2, BR-3, BR-4; SC-1..SC-8)

- **Goal.** The Alice and Bob scenario ends in the same states for the required pairings: web with web through the UI, and the Android JVM driver (Alice) with the web UI (Bob). This is the evaluation scenario. Other pairings are optional (decision 0013, cut 6).
- **Apps.** Android, web, server (tests only).
- **Covers.** Scenario `SC-1..SC-8` in the main scenario file; ACs `AC-F4-1..9`. The Android side is the generated JVM driver (`PLAT-ANDROID-031..033`), no emulator.
- **Chain.** `light` for both apps (no new client code expected; failures become spec or generator fixes). Test work: QA, full suite design once.
- **Depends on.** F1..F3, E2.
- **Status.** planned.

| Story | App | Chain | Status |
|---|---|---|---|
| S-F4-1 Alice/Bob steps 1 to 7 and 8 pass web with web, with state-based waiting | web, server | light | planned |
| S-F4-2 The same passes with the Android JVM driver as Alice and the web UI as Bob | android, web | light | planned |
| S-F4-3 Optional, not part of acceptance: other pairings (web as Alice with the driver as Bob, driver with driver) | android, web | light | optional |
| S-F4-4 Interop runs three times in a row without a failure (E-INTEROP-1) | android, web | light | planned |

### Enabling work around D1 and F4

| Item | Phase | Notes | Status |
|---|---|---|---|
| External checks `tests/web-e2e`, `tests/interop`, `tests/android-conformance` (QA) | P4, P5 | wait on state, never on fixed delays | planned |
| Trace check green for D1 (F1+F2+F3) and F4 (`check_trace`) | D1 and F4 at S6 | every AC has a passing test; rule coverage is reported, not gated | planned |
| Regeneration check | once, at P7 | one clean delete-and-regenerate, not after every feature (decision 0013, cut 8) | planned |

## E5 Evolution demo (P6)

### F5: Reactions extension

- **Goal.** Prove that a new capability is added by writing spec only. A user can attach a reaction to a message; a client without the capability simply does not show it and nothing breaks.
- **Apps.** Android, web. Server: none (the server relays opaque kinds, CORE-EXT-001).
- **Covers.** A new extension file under `spec/extensions/` (its own `EXT-REACTIONS` rules and scenarios, including a mixed pair of capable and core-only clients). No change to any core rule (CORE-EXT-005). Rows are added to `TRACEABILITY.md` when that spec is written (S1 of F5).
- **Chain.** `light` (the generator must not change; E-EVOL-1).
- **Depends on.** F1..F4 done and interop (P5) passed; regen proof (P7) not required. First thing cut if time is short.
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

`G0 (spec) → E2 server → E3 generator v1 (G1) → D1 (F1+F2+F3) → F4 → F5 (G0 for its spec, only after interop passes) → E6 → E7`. D1 needs the server for its external tests; F4 needs everything.

## Risks and assumptions

**Assumptions**
- The operator accepted the defaults of Q1 to Q7 and P1 to P8 (decision 0013); changing one now would change the rules named in `client-behavior.md` section 10 plus affected ACs, and counts against `spec_reopen` after the tag.
- Android runs without an emulator (decision 0002 Q19); interop for Android uses the JVM driver (decision 0014). Android screens are checked only by in-project Robolectric tests.

**Risks**
- Message times depend on the device clock and time zone: tests must fix the clock and zone (injected ports) and the server's accepted times, otherwise they are flaky around midnight and in other time zones. The server's accepted time is shown (not the sender's), so a skewed device clock cannot show a time that contradicts the order.
- Volume of testable rules: rule coverage is reported, not gated (decision 0013); the ACs gate acceptance, so every AC must have tests. Tests are still named by the rule ids they cover.
- Timing: plain polling once a second means a change can take about a second plus request time to reach the other client, and `Online` can show before queued messages turn `Sent`. Mitigation: tests wait for states, never count cycles; in-project tests use injected time.
- A defective client could drop a rejected message silently (it is only written to the diagnostic log); accepted for the MVP (decision 0013).
- Two interpretations of "identical": layout is free, texts and order are fixed. Visual differences must never be reported as defects; a text difference always is.
- F4 depends on D1 and on the Android driver; slip there delays the primary graded scenario. Mitigation: the web/web pairing runs as soon as D1 is done.
- Spec changes after G0 cost a reopen (cap `spec_reopen: 2`); resolve operator questions before P2.
