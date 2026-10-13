# Additional scenarios

- **Status:** draft for G0 (spec 0.1.0-draft). Owner: PM. They pin behavior the brief's scenario ([`alice-bob-offline.md`](alice-bob-offline.md)) does not reach. Ids `SX-1`..`SX-5` (extra, not brief steps).
- **Rules exercised:** [`../core/client-behavior.md`](../core/client-behavior.md) and the protocol rules it cites.
- **Pairings.** Each scenario runs once per client (Android, Web) as the client under test. Where a second user appears (`bob`), it runs for the same pairings as in the main scenario, section 3, but no more than the pairings P-1 and P-2 are required.
- **Method.** "The test" means the external test harness. It may talk to the server directly using the protocol (as a stand-in for a user or to stop and start the server), and reads each client's state snapshot (PLAT-HOOK-006..008). It waits on conditions, not on fixed delays. Messages are identified by text.

## SX-1: Login with no server, queue, relaunch, connect later

Pins BR-1 + BR-3: login and sending need no server; the queue survives a relaunch; connecting needs no user action.

1. **Set-up.** No server is running. A freshly installed client (call it Carol's).
2. **Login.** The user enters `Carol` and activates `Continue`. Expected: the conversation list screen with `carol` in the header, `No conversations yet.`, indicator `Connecting`, switch off. (CORE-LOGIN-002, CORE-LOGIN-004, CORE-OFFLINE-006)
3. **Send.** The user opens `Dave` and sends `Hello from a closed server`. Expected: the message is shown as `Pending`; unsent count 1; the list has an entry `dave`. (CORE-SEND-001, CORE-SEND-005, CORE-SEND-010, CORE-VISIBLE-002)
4. **Relaunch.** The client is closed and launched again. Expected: no login screen; header `carol`; list entry `dave`; opening it shows the message as `Pending`; unsent count 1; switch off. (CORE-LOGIN-005, CORE-OFFLINE-004, CORE-OFFLINE-001)
5. **Server starts.** The test starts a fresh server. Completion: the client's indicator is `Online` and the message is `Sent` with server order 1, unsent count 0, with no user action. Expected on the server: counter 1; mailbox `dave` = [1: `Hello from a closed server`]. (CORE-OFFLINE-005, CORE-FLUSH-001, CORE-FLUSH-005)

## SX-2: The acknowledgement is lost, the message is sent again

Pins BR-3: a message that reached the server but was never confirmed is shown once and takes its original server order.

1. **Set-up.** As the end of SC-2 in the main scenario (Alice and Bob online, A1 and B1 delivered, server counter 2).
2. **Queue.** On Alice's client the user switches `Offline mode` on and sends A2 (`Queued by Alice while offline`); it is `Pending`, unsent count 1.
3. **Simulate the lost acknowledgement.** The test reads A2's identity and fields from Alice's snapshot and sends exactly the same message to the server on her behalf. Expected on the server: counter 3; mailbox `bob` = [1: A1, 3: A2].
4. **Reconnect.** The user switches `Offline mode` off. Completion: Alice's indicator is `Online` and A2 is `Sent` with server order 3 (the original one), unsent count 0. Expected: Alice's view is A1 (sent, 1), B1 (received, 2), A2 (sent, 3), with A2 present once; the server counter is still 3; Bob (online) shows A2 once as `Received`, order 3. (CORE-FLUSH-005, CORE-RECEIVE-004; wire: CORE-MSG-001, CORE-DEDUPE-003)

## SX-3: The server is restarted

Pins the user's view of a new server lifetime (CORE-VISIBLE-008; assumed default Q2).

1. **Set-up.** As the end of SC-2 (Alice and Bob online; both views A1, B1).
2. **Stop the server.** The test stops it. Completion: both indicators show `Connecting`. Both views are unchanged.
3. **Queue.** On Alice's client the user sends `Sent while the server was down` (call it A3): it is `Pending`.
4. **Start a new server** (empty, new server epoch) on the same address. Completion: Alice's indicator is `Online` and A3 is `Sent` with server order 1. Expected on Alice's client: the list has one entry `bob`; the view is A3 (sent, 1) only. A1 and B1 are gone; no notice or error is shown. (CORE-VISIBLE-008, CORE-FLUSH-001, CORE-LOGIN-005; wire: CORE-EPOCH-004)
5. **Bob.** Completion: Bob's indicator is `Online` and A3 is shown as `Received` with server order 1. Expected on Bob's client: the list has one entry `alice`; the view is A3 (received, 1) only. (CORE-VISIBLE-008, CORE-RECEIVE-002)

## SX-4: Edge inputs for names and texts

Pins BR-1 + BR-2 input rules and the lowercase display.

1. **Invalid login names.** On a fresh client the user tries `` (empty), `bad name`, ` alice` (leading space), `al!ce`, and a 33-character name. For each: the login screen stays, `Names use 1 to 32 letters, digits, underscores or hyphens.` is shown, the typed text stays. (CORE-LOGIN-002, CORE-LOGIN-003)
2. **Case.** The user enters `ALICE`. Expected: logged in; the header shows `alice`. A 32-character name is accepted. (CORE-LOGIN-004)
3. **Invalid recipient.** The user enters `bob smith` as the recipient: no conversation opens, the same invalid-name text is shown, the typed text stays. Then `Bob`: the conversation with `bob` opens, the recipient field is empty. (CORE-SEND-001, CORE-SEND-002)
4. **Invalid texts.** In the conversation the user sends: an empty text; a text of spaces and line breaks only. Expected each time: `Type a message first.`, no message added, typed text stays. A text of 4097 bytes (for example 4097 letters `a`): `Message is too long. The limit is 4096 bytes.`, no message added. A text of exactly 4096 bytes is accepted as `Pending` or `Sent`. (CORE-SEND-004)
5. **Exact text.** The user sends `  Mixed CASE,  two  spaces` followed by a line break and `ünïcode ✓`. Expected: shown with the same characters, spaces and line break. (CORE-SEND-006)
6. **Note to self.** The user opens the conversation `alice` (their own name) and sends `note`. Expected: once, written by `alice`, with `Sent` once acknowledged; the list entry `alice` exists; the message never shows `Received`. (CORE-SEND-011)

## SX-5: A message of an unknown kind is invisible

Pins CORE-RECEIVE-005 (the groundwork for extensions).

1. **Set-up.** Bob's client is online and logged in as `bob`; the test has registered `alice` on the server through the protocol.
2. **Inject.** The test sends from `alice` to `bob` one message of the kind `demo.unknown` with an arbitrary payload. Expected: server order 1; completion: Bob's stored position in his mailbox is 1 (snapshot cursor). On Bob's screen: nothing changes, the list is still empty (`No conversations yet.`), no error is shown. (CORE-RECEIVE-005; wire: CORE-EXT-002)
3. **Follow-up.** The test sends from `alice` to `bob` the text message `After the unknown one`. Expected: it appears on Bob's screen as `Received` in a new conversation `alice`, server order 2; the conversation contains only this message. (CORE-RECEIVE-001, CORE-RECEIVE-005, CORE-ORDER-006)

## Acceptance criteria

- **AC-F3-13** — Given no server is running, When a new user logs in as `Carol`, sends a message to `Dave`, relaunches the client and the server then starts, Then the user is logged in without the login screen after the relaunch, the message stays `Pending` until the server is available, and then it turns `Sent` by itself, once. (SX-1; CORE-LOGIN-002, CORE-OFFLINE-004, CORE-FLUSH-005)
- **AC-F3-14** — Given a `Pending` message that the server has in fact already accepted, When the client connects, Then the message turns `Sent` once with its original server order and the peer sees it once. (SX-2; CORE-FLUSH-005, CORE-RECEIVE-004)
- **AC-F3-15** — Given online users with history, When the server is restarted and they reconnect, Then their `Sent` and `Received` messages disappear, messages sent while the server was down are delivered, and the recipient sees only those. (SX-3; CORE-VISIBLE-008)
- **AC-F2-15** — Given the login screen or a conversation, When the user enters invalid names or texts, a valid name in capitals, texts at the size limit, or a note to oneself, Then the screens show exactly the outcomes in SX-4. (SX-4; CORE-LOGIN-003, CORE-LOGIN-004, CORE-SEND-002, CORE-SEND-004, CORE-SEND-006, CORE-SEND-011)
- **AC-F2-16** — Given a message of a kind the client does not know arrives, When the client processes it, Then the screen does not change and shows no error, and the next ordinary message appears normally. (SX-5; CORE-RECEIVE-005)
