# G0 review packet — PM behavior, scenarios, backlog and traceability (P1, spec 0.1.0-draft)

> **Author:** PM agent (claude-sonnet-5-5), stage S0 (behavior part) and the P1 backlog step, ref OM-0008. AI-written; awaiting operator decision at G0 and backlog approval (WORKFLOW Q24).
> **Read with:** `spec/core/client-behavior.md` (rules and ACs F1 to F3), `spec/scenarios/alice-bob-offline.md` (SC-1..SC-8, ACs F4), `spec/scenarios/additional-scenarios.md` (SX-1..SX-5), `docs/product/BACKLOG.md`, `docs/product/TRACEABILITY.md`, and the TL packet `docs/planning/g0-review-tl.md`.
> **Numbers:** 50 behavior rules (`CORE-LOGIN-001..006`, `SEND-001..011`, `OFFLINE-001..007`, `FLUSH-001..006`, `RECEIVE-001..006`, `ORDER-001..006`, `VISIBLE-001..008`), 47 acceptance criteria (`AC-F1-1..7`, `AC-F2-1..16`, `AC-F3-1..15`, `AC-F4-1..9`), 192 trace rows, 8 scenario steps, 5 extra scenarios. Spec version stays `0.1.0-draft`; the index in `spec/README.md` is the TL's and still lists the two PM files as skeletons (see section d).

## (a) What a user sees, screen by screen

1. **First launch: login screen.** One field for a name and a button `Continue`. The name may have 1 to 32 letters, digits, underscores or hyphens, nothing else (no spaces, not even at the ends). Anything else shows `Names use 1 to 32 letters, digits, underscores or hyphens.` and keeps what was typed. A valid name logs in at once, even with no server running. `Alice`, `ALICE` and `alice` are the same person and the app shows `alice`. The name is remembered: the next launch goes straight to the main screen. There is no logout.
2. **Header (every screen after login).** The user's name, a connection indicator (`Offline`, `Connecting`, `Online`) and an `Offline mode` switch. The switch always starts off at launch. Switched on, the app does not talk to the server at all and the indicator reads `Offline`. Switched off (or the device network returns), the indicator reads `Connecting` and then `Online` without further action. `Connecting` is also what is shown if the server is down and the switch is off; the app keeps trying by itself.
3. **Conversation list.** A field to type a recipient name and a button `Open`. Below it the list: one entry per person you have exchanged at least one message with (names only), newest conversation first. An empty list says `No conversations yet.` Typing a name opens a conversation (any valid name; no check that the person exists). Opening a conversation does not add it to the list until a message exists. After a relaunch the app always starts on this list.
4. **Conversation screen.** `Back`, the peer's name, the messages oldest first with the newest at the bottom, and below them a text field with `Send`. Each message shows who wrote it, its text exactly as typed (spaces and line breaks kept) and a label: `Pending` (written, not yet confirmed by the server), `Sent` (confirmed), `Received` (from the other person), `Failed` (rejected for good; shown in error style, never resent; practically unreachable). Own and the other's messages look different. No times, receipts, typing signs or unread counts. Blank text or text over 4096 bytes is refused with `Type a message first.` or `Message is too long. The limit is 4096 bytes.` and stays in the field. Sending works in every connection state.
5. **Offline, reconnect.** While offline a user can read everything, start conversations and write; each new message shows `Pending` at the bottom and survives closing the app. On reconnect, messages that waited on the server appear first as `Received`, then the user's pending messages turn `Sent` one at a time in the order written. A message that becomes `Sent` moves to the place the server's order gives it, which can be above messages that arrived while it was pending.
6. **Server restart.** The next time the app connects it silently drops all `Sent` and `Received` history (the server's memory is gone), keeps and delivers pending messages, and conversations with nothing left leave the list. No notice is shown.
7. **Alice and Bob.** After step 7 Bob sees A1, B1, A2, B2 (his B2 was typed before he saw A2, but A2 reached the server first). Alice, offline, sees A1, B1, A2 and not B2 until step 8 (she reconnects), after which both see the same four in the same order.

## (b) Assumed defaults pending the operator's answers

Used exactly as the TL recommended; changing one means editing the rules listed (also in `client-behavior.md` section 10).

| TL Q | Assumed default | Rules and scenarios affected if changed |
|---|---|---|
| Q1 | Unknown recipient accepted; messages wait in a lazy mailbox | SEND-001/002, SX-1 (message to `dave` who never connected) |
| Q2 | History cleared on server restart; unsent kept | VISIBLE-008, SX-3, AC-F3-10, AC-F3-15 |
| Q3 | Names shown in lowercase | LOGIN-004, SEND-001, SEND-007, VISIBLE-001; all scenario texts that show names |
| Q4 | Order = server acceptance order | ORDER-001..005, VISIBLE-003; SC-7 view of Bob |
| Q5 | JVM command-line driver for Android interop (TL: "(b) + optional (a)") | pairing text in the main scenario section 3; F4 stories |
| Q6 | Web hook always present, Android provider debug only | none in behavior |
| Q7 | Notes to self allowed | SEND-011, SX-4 step 6, AC-F2-11 |

## (c) Open questions for the operator (product), with recommendations

| # | Question | Options | Recommendation |
|---|---|---|---|
| P1 | What does a conversation list entry show? | (a) peer name only (current); (b) name plus a preview of the latest message; (c) name plus last state | **(a).** A preview needs precise truncation and line-break rules to stay identical across platforms. Cheap to add later as a rule. |
| P2 | How is a conversation started? | (a) type the name (current); (b) pick from the registered users the server lists | **(a).** Works offline and with a server that has not seen the person yet (Q1). (b) can be an extension later. |
| P3 | Is the offline switch remembered across launches? | (a) no, off at every launch (current); (b) yes | **(a).** Deterministic for tests and graders; a switch left on is a trap in a demo. |
| P4 | Should the user be told when the server was restarted and history vanished? | (a) no notice in v1 (current); (b) a one-line notice in the list screen | **(a)**, with (b) as a follow-up; (b) needs a new element and hook. Users will see conversations vanish with no explanation, which I accept for a local demo. |
| P5 | What does `Failed` look like, and can the user act on it? | (a) label plus error style, no action (current); (b) a retry control | **(a).** Failed is practically unreachable because the client validates first; (b) adds a rule the brief does not need. |
| P6 | Show message times? | (a) none (current); (b) local times from the sender's clock | **(a).** Clocks differ between devices and order must not depend on them (CORE-SEQ-003). |
| P7 | A connection that cannot reach the server with the switch off shows `Connecting`, not `Offline`; with no device network it shows `Offline` while the switch reads off. Acceptable? | (a) yes (current); (b) a fourth indicator value | **(a).** Matches the TL's three states. |
| P8 | Language | (a) fixed English texts (current); (b) localized | **(a)** for v1. |

## (d) Requests to the TL

1. **New hooks (`test-hooks.md`).** (a) `conversation-back` for the `Back` control; (b) `new-conversation-error` for the invalid-recipient message (CORE-SEND-002). Without them SX-4 step 3 and the navigation in SC-2 cannot be driven. (c) Extend PLAT-HOOK-002 to `conversation-list`: entries in rendered order, so CORE-VISIBLE-003 can be tested. (d) Optional: expose the message author as a readable value of `message-<id>` (the snapshot has it, the screen shows it).
2. **Header on both screens.** `current-user`, `connection-status`, `offline-toggle` are present on the list and conversation screens (CORE-VISIBLE-001); PLAT-HOOK-003 uniqueness holds because only one screen is shown at a time. Please state in `test-hooks.md` that these three live in the header.
3. **App relaunch control.** SX-1 and AC-F1-5 need "close and launch again" with storage kept. Define it per platform (page reload for web; process restart for Android, debug-only) next to the other test controls.
4. **Server request visibility.** AC-F4-3 and CORE-OFFLINE-002 assert that an offline client makes no request. CORE-SRV-007 (request log) is a `SHOULD`; tests need a dependable way to count requests per client (promote it to `MUST`, or add a test-only counter).
5. **Spec index.** `spec/README.md` lists `client-behavior.md` and `alice-bob-offline.md` as skeletons and does not list `additional-scenarios.md`. I did not edit it (TL owns it); the PM role file allows me to bump the version, but I was told not to.
6. **Android interop driver (Q5).** The rule for the command-line driver is still to be added at P3.
7. **Characters CORE-TEXT-003 forbids.** U+0000 and unpaired surrogates in composed text are refused by protocol, but no visible text exists for that case (see section e).
8. **Platform tests.** Platform files name the label texts nowhere; component tests will take them from `client-behavior.md` section 8.1. Confirm that is the intent.

## (e) Gaps and inconsistencies found

No rule in the TL files contradicts the brief or the behavior spec. No `SPEC_ISSUE` is raised. Minor points:

- **Forbidden characters in text.** CORE-TEXT-003 rejects text with U+0000 or unpaired surrogates, and CORE-TEXT-004 requires local validation, but no message text is defined. Normal input cannot produce either. Proposal: a third fixed text such as `Message contains characters that cannot be sent.` Reusing the blank-text message would mislead. It needs an operator or TL nod; until then clients refuse the message and no text is defined (not covered by an AC).
- **`online` precedes flush.** CORE-CONN-006 sets `online` after the registration, before catch-up and flush. I documented that `Online` does not mean delivered (CORE-OFFLINE-006) and scenario completion conditions always include message states and the unsent count.
- **Enqueue order of failed messages.** CORE-SEQ-002 orders `failed` after sequenced messages by local enqueue order, but a failed message has left the outbox. The platform files only say the outbox order is an explicit column; the generator must keep that number on the message after it fails.
- **Failed messages survive an epoch reset.** CORE-EPOCH-004 deletes messages that have a `seq`; `failed` ones have none and stay. I followed this in CORE-VISIBLE-008. Say so in the protocol if intended.
- **Appendix A uses `Alice` typed with a capital** while the snapshot and mailboxes use lowercase: consistent with CORE-NAME-004, noted only because tests must type `Alice` and `Bob` at login.
- **The brief's step 7 vs the TL's transient.** Bob's view between receiving A2 and acknowledging B2 is not observable reliably from outside; I made it a unit-level check, not a completion condition.
- **Scenario 7 and Alice.** The brief ends at step 7; Alice does not see B2 there (she is offline). I added step 8 as `SC-8`, marked beyond the brief.
- **Harness test now fails by design.** `generator/tests/test_checks.py::CheckTrace::test_repo_template_parses_to_zero_rows` asserts that `docs/product/TRACEABILITY.md` has no rows. That was true before P1 and is false now that the PM added the rows P1 requires. The test belongs to the harness (not a PM file) and needs the DEV or TL to change it, for example to assert that the file parses and every row has a known scope.
- **Hooks without behavior or behavior without hooks.** Every hook in `test-hooks.md` is accounted for in the behavior spec (table below); the reverse gaps are in section d.1.

### Hook accounting

| Hook | Where in behavior |
|---|---|
| `login-name-input`, `login-submit`, `login-error` | CORE-LOGIN-001..003 |
| `current-user`, `connection-status`, `offline-toggle` | CORE-VISIBLE-001, CORE-OFFLINE-001/006 |
| `conversation-list`, `conversation-item-<peer>` | CORE-VISIBLE-002..004 |
| `new-conversation-input`, `new-conversation-submit` | CORE-SEND-001/002 |
| `conversation-peer`, `message-list`, `message-<id>` | CORE-SEND-003/007/008, CORE-ORDER-001 |
| `composer-input`, `composer-send`, `composer-error` | CORE-SEND-004/005 |

## (f) Coverage: brief requirement and scenario step to rules and ACs

BR-1..BR-4 are the four "Required behavior" lines in order; SC-1..SC-7 are the seven scenario steps in order; SC-8 is beyond the brief. Rows come from `docs/product/TRACEABILITY.md`. Every `MUST` rule of the PM areas appears in at least one AC and one trace row (checked by script); none is marked "covered indirectly". Test ids are all `pending`; `check_trace.py` parses the file and reports every row unmet until tests exist.

| BR / SC | Rules (trace rows) | ACs |
|---|---|---|
| BR-1 | LOGIN-001, LOGIN-004, VISIBLE-001, LOGIN-002, LOGIN-003, LOGIN-005, LOGIN-006 | F1-1, F1-2, F1-3, F1-4, F1-5, F1-6, F1-7, F2-15, F3-13 |
| BR-2 | VISIBLE-002, SEND-001, SEND-003, SEND-002, SEND-005, SEND-007, SEND-008, SEND-004, SEND-006, SEND-011, SEND-009, SEND-010 | F1-2, F2-1, F2-2, F2-3, F2-4, F2-5, F2-6, F2-11, F2-12, F2-13, F2-15, F3-2 |
| BR-3 | OFFLINE-006, OFFLINE-001, OFFLINE-002, OFFLINE-003, OFFLINE-004, OFFLINE-005, FLUSH-001, FLUSH-002, FLUSH-004, FLUSH-003, FLUSH-005, VISIBLE-008, OFFLINE-007, FLUSH-006 | F1-4, F1-6, F3-1, F3-2, F3-3, F3-4, F3-5, F3-6, F3-7, F3-8, F3-9, F3-10, F3-11, F3-12, F3-13, F3-14, F3-15 |
| BR-4 | VISIBLE-004, RECEIVE-006, RECEIVE-001, RECEIVE-003, VISIBLE-007, ORDER-001, ORDER-002, ORDER-003, VISIBLE-003, RECEIVE-005, RECEIVE-004, ORDER-004, VISIBLE-005, VISIBLE-006, ORDER-005, ORDER-006, RECEIVE-002 | F1-5, F2-5, F2-6, F2-7, F2-8, F2-9, F2-10, F2-12, F2-13, F2-14, F2-16, F3-2, F3-6, F3-7, F3-9, F3-14, F4-9 |
| SC-1 | SEND-001, SEND-008, RECEIVE-001, VISIBLE-002 | F4-1 |
| SC-2 | VISIBLE-004, ORDER-001, ORDER-005 | F4-2 |
| SC-3 | OFFLINE-002, OFFLINE-003 | F4-3 |
| SC-4 | OFFLINE-002, OFFLINE-003 | F4-4 |
| SC-5 | OFFLINE-005, FLUSH-001, FLUSH-004 | F4-5 |
| SC-6 | OFFLINE-001 | F4-6 |
| SC-7 | RECEIVE-002, FLUSH-003, FLUSH-004, ORDER-002 | F4-7 |
| SC-8 | RECEIVE-002, ORDER-005 | F4-8 |

Scope of rows per AC: one `core` row per rule (external checks), one `platform:android` and one `platform:web` row (in-project tests); F4 has platform rows for the replay of the scenario against each app's fake server; F5 has a table and no rows until its extension spec exists.
