# Scenario: Alice and Bob, offline and reconnect

- **Status:** draft for G0 (spec 0.1.0-draft). Owner: PM. Source: the brief's "Required behavior" scenario, steps 1 to 7 (`SC-1`..`SC-7`), plus an extra step 8 (`SC-8`) beyond the brief.
- **Rules exercised:** [`../core/client-behavior.md`](../core/client-behavior.md) and the protocol rules it cites. The wire-level trace of the same steps is [`../core/protocol.md` Appendix A](../core/protocol.md#appendix-a--worked-trace-of-the-alicebob-scenario-normative-example); server mailbox columns below are copied from it and are normative for tests.
- **Rule:** both clients MUST produce the same observable states at every step, for every pairing in section 3. Other scenarios: [`additional-scenarios.md`](additional-scenarios.md).

## 1. Fixed test data and set-up

| Label | Written by | To | Text (exact) |
|---|---|---|---|
| A1 | Alice | Bob | `Hi Bob, I have something important to tell you` (brief step 1) |
| B1 | Bob | Alice | `What is it?` (brief step 2) |
| A2 | Alice | Bob | `Queued by Alice while offline` (fixed for tests, protocol Appendix A) |
| B2 | Bob | Alice | `Queued by Bob while offline` (fixed for tests, protocol Appendix A) |

Message ids are random in real clients (CORE-ENV-002); tests identify a message by its text and its author, never by id. The fixed ids in Appendix A serve only the replay test against a fake server.

**Set-up (step 0, a precondition, not a brief step).** A server freshly started (empty, new server epoch). Alice's client and Bob's client freshly installed, each pointing at that server. Alice enters `Alice` at the login screen, Bob enters `Bob`; both headers show the lowercase names. Both offline switches are off.

**Step 0 completion** (the point at which step 1 may start): on both clients the connection indicator is `Online`, the conversation list is empty (`No conversations yet.`), no unsent messages, and the server has accepted no message (counter 0).

**Reading the tables.** "View" is the ordered message list of the conversation between the two users, top to bottom, as `label (state, server order)`, where state is the machine value (`pending`, `sent`, `received`) behind the label (CORE-VISIBLE-005 / section 8.1 of the behavior spec) and server order is the number the server gave (`-` for unsent). "Unsent" counts the user's `pending` messages. "Cursor" is the client's stored position in its own mailbox (CORE-CURSOR-001). Server mailbox contents are `[server order: label]`. Tests read the view from the screen and the numbers from the state snapshot (PLAT-HOOK-006..008) and wait on the completion condition instead of a fixed delay.

## 2. Steps

### SC-1: Alice writes A1 to Bob

- **Action.** On Alice's client the user opens a conversation with `Bob` (entering `Bob`) and sends A1.
- **Rules.** CORE-SEND-001, CORE-SEND-003, CORE-SEND-005, CORE-SEND-008, CORE-RECEIVE-001, CORE-RECEIVE-003, CORE-VISIBLE-002; wire: CORE-MSG-001, CORE-SEQ-001.
- **Completion condition.** Alice shows A1 as `sent` AND Bob shows A1 as `received`.

| | Expected after SC-1 |
|---|---|
| Server | counter 1; mailbox `bob` = [1: A1]; mailbox `alice` = [] |
| Alice view | A1 (sent, 1) |
| Bob view | A1 (received, 1) |
| Alice list / Bob list | entry `bob` / entry `alice` |
| Connection | Alice `online`; Bob `online` |
| Unsent | Alice 0; Bob 0 |
| Cursor | Alice 0; Bob 1 |

Between sending and completion Alice's view shows A1 (pending, -) (CORE-SEND-005).

### SC-2: Bob replies with B1

- **Action.** On Bob's client the user opens the conversation `alice` from the list and sends B1.
- **Rules.** CORE-VISIBLE-004, CORE-SEND-005, CORE-SEND-008, CORE-RECEIVE-001, CORE-ORDER-001, CORE-ORDER-005.
- **Completion condition.** Bob shows B1 as `sent` AND Alice shows B1 as `received`.

| | Expected after SC-2 |
|---|---|
| Server | counter 2; `bob` = [1: A1]; `alice` = [2: B1] |
| Alice view | A1 (sent, 1), B1 (received, 2) |
| Bob view | A1 (received, 1), B1 (sent, 2) |
| Connection | both `online` |
| Unsent | Alice 0; Bob 0 |
| Cursor | Alice 2; Bob 1 |

### SC-3: Alice goes offline and queues A2

- **Action.** On Alice's client the user switches `Offline mode` on, then sends A2 in the conversation with `bob`.
- **Rules.** CORE-OFFLINE-001, CORE-OFFLINE-002, CORE-OFFLINE-003, CORE-SEND-010, CORE-ORDER-002; wire: CORE-CONN-004, CORE-OUTBOX-001, CORE-OUTBOX-002.
- **Completion condition.** Alice's indicator is `Offline` AND A2 is shown as `pending` AND Alice's unsent count is 1. From the moment the switch is on, Alice's client makes no further request to the server.

| | Expected after SC-3 |
|---|---|
| Server | unchanged from SC-2: counter 2; `bob` = [1: A1]; `alice` = [2: B1] |
| Alice view | A1 (sent, 1), B1 (received, 2), A2 (pending, -) |
| Bob view | A1 (received, 1), B1 (sent, 2) (unchanged) |
| Connection | Alice `offline`; Bob `online` |
| Unsent | Alice 1; Bob 0 |
| Cursor | Alice 2; Bob 1 |

### SC-4: Bob goes offline and queues B2

- **Action.** On Bob's client the user switches `Offline mode` on, then sends B2 in the conversation with `alice`.
- **Rules.** as SC-3, for Bob.
- **Completion condition.** Bob's indicator is `Offline` AND B2 is shown as `pending` AND Bob's unsent count is 1.

| | Expected after SC-4 |
|---|---|
| Server | unchanged: counter 2; `bob` = [1: A1]; `alice` = [2: B1] |
| Alice view | A1 (sent, 1), B1 (received, 2), A2 (pending, -) |
| Bob view | A1 (received, 1), B1 (sent, 2), B2 (pending, -) |
| Connection | both `offline` |
| Unsent | Alice 1; Bob 1 |
| Cursor | Alice 2; Bob 1 |

### SC-5: Alice reconnects, A2 reaches the server

- **Action.** On Alice's client the user switches `Offline mode` off.
- **Rules.** CORE-OFFLINE-005, CORE-FLUSH-001, CORE-FLUSH-002, CORE-FLUSH-004, CORE-FLUSH-006, CORE-ORDER-003; wire: CORE-CONN-005, CORE-CONN-006, CORE-OUTBOX-003, CORE-OUTBOX-004.
- **Completion condition.** Alice's indicator is `Online` AND A2 is shown as `sent` with server order 3 AND Alice's unsent count is 0. Alice's indicator passes through `Connecting` first. Bob's client is offline and shows nothing new.

| | Expected after SC-5 |
|---|---|
| Server | counter 3; `bob` = [1: A1, 3: A2]; `alice` = [2: B1] (B2 is still only on Bob's client) |
| Alice view | A1 (sent, 1), B1 (received, 2), A2 (sent, 3) |
| Bob view | A1 (received, 1), B1 (sent, 2), B2 (pending, -) (unchanged) |
| Connection | Alice `online`; Bob `offline` |
| Unsent | Alice 0; Bob 1 |
| Cursor | Alice 2; Bob 1 |

### SC-6: Alice goes offline again

- **Action.** On Alice's client the user switches `Offline mode` on.
- **Rules.** CORE-OFFLINE-001, CORE-OFFLINE-002.
- **Completion condition.** Alice's indicator is `Offline`.

| | Expected after SC-6 |
|---|---|
| Server | unchanged from SC-5 |
| Alice view | A1 (sent, 1), B1 (received, 2), A2 (sent, 3) |
| Bob view | A1 (received, 1), B1 (sent, 2), B2 (pending, -) |
| Connection | both `offline` |
| Unsent | Alice 0; Bob 1 |
| Cursor | Alice 2; Bob 1 |

### SC-7: Bob reconnects, receives A2 and delivers B2

- **Action.** On Bob's client the user switches `Offline mode` off.
- **Rules.** CORE-OFFLINE-005, CORE-RECEIVE-002, CORE-FLUSH-001, CORE-FLUSH-003, CORE-FLUSH-004, CORE-ORDER-002, CORE-ORDER-003, CORE-ORDER-005; wire: CORE-CONN-006, CORE-SEQ-002, CORE-SEQ-004.
- **Completion condition.** Bob's indicator is `Online` AND A2 is shown as `received` with server order 3 AND B2 is shown as `sent` with server order 4 AND Bob's unsent count is 0.
- **Transient (not a completion condition, checked by in-project tests with a fake server).** Between receiving A2 and the acknowledgement of B2, Bob's view is A1, B1, A2 (received, 3), B2 (pending, -): A2 appears above the pending B2 before B2 takes its place (CORE-FLUSH-003, CORE-ORDER-002).

| | Expected after SC-7 |
|---|---|
| Server | counter 4; `bob` = [1: A1, 3: A2]; `alice` = [2: B1, 4: B2] |
| Alice view | A1 (sent, 1), B1 (received, 2), A2 (sent, 3). She does **not** see B2: she is offline. |
| Bob view | A1 (received, 1), B1 (sent, 2), A2 (received, 3), B2 (sent, 4) |
| Connection | Alice `offline`; Bob `online` |
| Unsent | Alice 0; Bob 0 |
| Cursor | Alice 2; Bob 3 |

Note: B2 was written before Bob saw A2, yet A2 is above it because it reached the server first (CORE-SEQ-002; operator question Q4).

### SC-8 (beyond the brief): Alice reconnects and receives B2

- **Action.** On Alice's client the user switches `Offline mode` off.
- **Rules.** CORE-OFFLINE-005, CORE-RECEIVE-002, CORE-ORDER-005; wire: CORE-CONN-006.
- **Completion condition.** Alice's indicator is `Online` AND B2 is shown as `received` with server order 4.

| | Expected after SC-8 |
|---|---|
| Server | unchanged from SC-7: counter 4 |
| Alice view | A1 (sent, 1), B1 (received, 2), A2 (sent, 3), B2 (received, 4) |
| Bob view | A1 (received, 1), B1 (sent, 2), A2 (received, 3), B2 (sent, 4) |
| Connection | both `online` |
| Unsent | Alice 0; Bob 0 |
| Cursor | Alice 4; Bob 3 |

The two views list the same four messages, in the same order, by the same texts (CORE-ORDER-005); only the labels differ with the viewpoint (author: `Sent`; other user: `Received`).

## 3. Client pairings

The scenario MUST pass, with identical expected states, for each pairing (Alice's client + Bob's client), against the same server:

| Pairing | Alice | Bob |
|---|---|---|
| P-1 | Android | Web |
| P-2 | Web | Android |
| P-3 | Android | Android |
| P-4 | Web | Web |

Identical means: every row of every table above holds for every pairing; the only permitted differences are layout, colors and fonts. Where a platform's emulator is not available, the sandbox gate runs the Android side through its unit-test suite and the protocol-level replay of Appendix A (PLAT-ANDROID-019); see the packet for the interop question.

## 4. Acceptance criteria

Given/When/Then; each cites the step ids and rules it checks. Test ids per scope are in [`docs/product/TRACEABILITY.md`](../../docs/product/TRACEABILITY.md).

- **AC-F4-1** — Given two freshly logged-in, online clients as `alice` and `bob`, When Alice sends A1 to `Bob`, Then Alice shows A1 as `Sent` and Bob shows A1 as `Received` with an entry `alice` in his list, and both stay `Online`. (SC-1; CORE-SEND-001, CORE-SEND-008, CORE-RECEIVE-001, CORE-VISIBLE-002)
- **AC-F4-2** — Given SC-1 is complete, When Bob opens the conversation with `alice` and sends B1, Then Bob shows A1 `Received`, B1 `Sent`, and Alice shows A1 `Sent`, B1 `Received`, in that order on both. (SC-2; CORE-VISIBLE-004, CORE-ORDER-001, CORE-ORDER-005)
- **AC-F4-3** — Given SC-2 is complete, When Alice switches `Offline mode` on and sends A2, Then Alice's indicator shows `Offline`, A2 is shown last as `Pending`, the server has received nothing from Alice since the switch, and Bob's screen is unchanged. (SC-3; CORE-OFFLINE-002, CORE-OFFLINE-003)
- **AC-F4-4** — Given SC-3 is complete, When Bob switches `Offline mode` on and sends B2, Then Bob's indicator shows `Offline`, B2 is shown last as `Pending`, and nothing else changes on either screen. (SC-4; CORE-OFFLINE-002, CORE-OFFLINE-003)
- **AC-F4-5** — Given SC-4 is complete, When Alice switches `Offline mode` off, Then her indicator goes through `Connecting` to `Online`, A2 turns `Sent`, her list order stays A1, B1, A2, and Bob's screen does not change. (SC-5; CORE-OFFLINE-005, CORE-FLUSH-001, CORE-FLUSH-004)
- **AC-F4-6** — Given SC-5 is complete, When Alice switches `Offline mode` on, Then her indicator shows `Offline` and her messages are unchanged. (SC-6; CORE-OFFLINE-001)
- **AC-F4-7** — Given SC-6 is complete, When Bob switches `Offline mode` off, Then A2 appears as `Received` above his `Pending` B2, B2 turns `Sent` after it, Bob sees A1, B1, A2, B2 in that order with no unsent message left, and Alice's screen does not show B2. (SC-7; CORE-RECEIVE-002, CORE-FLUSH-003, CORE-FLUSH-004, CORE-ORDER-002)
- **AC-F4-8** — Given SC-7 is complete, When Alice switches `Offline mode` off, Then B2 appears as `Received` last in her conversation and Alice and Bob see the same four messages in the same order. (SC-8; CORE-RECEIVE-002, CORE-ORDER-005)
- **AC-F4-9** — Given the steps SC-1 to SC-8, When they are run for each pairing P-1 to P-4, Then the screens show the same states, order and texts at every step. (section 3; CORE-ORDER-005)
