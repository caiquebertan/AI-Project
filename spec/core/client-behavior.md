# Core client behavior

- **Status:** draft for G0 (spec 0.1.0-draft). Owner: PM. Written in plain language; exact enough that two clients on different platforms are indistinguishable to a user.
- **Scope:** what a user sees and can do in a client: screens, texts, message states, connection states, order. How messages travel (requests, retries, cursor, epoch, ordering key) is in [`protocol.md`](protocol.md); this file cites those rules and never restates them. Server internals are in [`server-behavior.md`](server-behavior.md). Which element carries which test hook is in [`../platform/test-hooks.md`](../platform/test-hooks.md).
- **Platform-neutral:** nothing here names a platform, library or input device. "The user enters / selects / activates" covers typing, tapping and clicking alike. Layout, colors, fonts and animation are platform choices unless a rule below says otherwise.
- **Ids:** `CORE-LOGIN`, `CORE-SEND`, `CORE-OFFLINE`, `CORE-FLUSH`, `CORE-RECEIVE`, `CORE-ORDER`, `CORE-VISIBLE` (PM areas, see [`../README.md`](../README.md)). Acceptance criteria `AC-F<n>-<m>` are listed in section 9, next to the rules they check; scenarios are in [`../scenarios/`](../scenarios/).
- **Defaults assumed pending the operator** (G0 questions Q1 to Q7 of the TL packet, TL recommendations): a recipient that has never connected is accepted (messages wait in its mailbox); a server restart clears received and sent history but keeps unsent messages; names are shown in lowercase; conversation order is the server's acceptance order; notes to self are allowed. If an answer changes, the rules named in section 10 change with it.

Contents: 1 Words used · 2 Screens · 3 Login · 4 Conversations and sending · 5 Offline use · 6 Flush · 7 Receiving · 8 Order and what is shown · 9 Acceptance criteria · 10 Decisions behind the defaults · 11 Out of scope

---

## 1. Words used

| Word | Meaning |
|---|---|
| user / peer | The person using this client / the other person in a conversation. Names are the canonical lowercase names of CORE-NAME-002. |
| conversation | All text messages exchanged between the user and one peer, in both directions (CORE-SEQ-005). Opening a conversation with oneself is allowed. |
| unsent message | A message in state `pending` or `failed`, i.e. without a server order number. |
| accepted time | The moment, in UTC, at which the server accepted a message (`accepted_at`, CORE-ENV-007). Unsent messages have none. |
| server order | The position the server gave a message when it accepted it (CORE-SEQ-001). |
| allowed to connect | The client may contact the server (CORE-CONN-002). Not allowed means the connection state is `offline`. |

## 2. Screens

After the one-time login screen, the client has two screens that share one header.

1. **Login screen** (section 3): name field, submit control, validation message. Shown only while no identity is stored.
2. **Conversation list screen** (section 4.1): header, the new-conversation entry, the list of conversations.
3. **Conversation screen** (section 4.2): header, the peer's name, a way back to the list, the messages, the composer.

**Header** (CORE-VISIBLE-001): the user's name, the connection indicator, the offline switch. It is on both screens after login and never on the login screen.

## 3. Login

- **CORE-LOGIN-001** — On launch with no stored identity the client MUST show the login screen and nothing of the main app: a name field, a submit control labelled `Continue`, and no header.
- **CORE-LOGIN-002** — When the user submits, the client MUST check the entered text against CORE-NAME-001 locally, exactly as typed (no trimming; leading or trailing spaces make the name invalid), and MUST NOT contact the server for this (CORE-NAME-005). Login MUST work in every connection state, including when the server is not running.
- **CORE-LOGIN-003** — If the name is invalid (including empty), the client MUST stay on the login screen, MUST show the validation message of section 8.1 next to the name field, MUST keep the typed text in the field, and MUST NOT store anything. The message MUST disappear when the user edits the field or when login succeeds.
- **CORE-LOGIN-004** — If the name is valid, the client MUST store its lowercase form as the user's identity (CORE-NAME-004), persistently, and MUST show the conversation list screen at once, without waiting for the server. Names that differ only in letter case are the same user: entering `Alice`, `ALICE` or `alice` all log in as `alice`, and the header shows `alice`, never the casing typed.
- **CORE-LOGIN-005** — On every later launch with a stored identity the client MUST skip the login screen and show the conversation list screen for the same user, with all stored conversations, messages and unsent messages restored (CORE-OUTBOX-002, CORE-CURSOR-001). The offline switch is not restored: it starts off at every launch (CORE-OFFLINE-001).
- **CORE-LOGIN-006** — The client MUST NOT offer any way to log out, change the name or reset the identity from within the app (v1; section 11).

## 4. Conversations and sending

### 4.1 Conversation list screen

- **CORE-SEND-001** — The conversation list screen MUST offer a recipient field and a control labelled `Open`. When the user activates it with a valid name (CORE-NAME-001, checked locally, exactly as typed), the client MUST open the conversation screen for the lowercase form of that name (`Bob` opens the conversation with `bob`), and MUST clear the recipient field. If a conversation with that peer already exists it MUST open that one, not a second one. No server check of the name's existence is made (CORE-MSG-003).
- **CORE-SEND-002** — With an invalid recipient name (including empty) the client MUST stay on the list screen, MUST show the message of section 8.1 next to the recipient field, MUST keep the typed text, and MUST NOT open a conversation. The message MUST disappear when the user edits the field or opens a conversation.

### 4.2 Conversation screen

- **CORE-SEND-003** — The conversation screen MUST show: the peer's name; a control labelled `Back` that returns to the list screen; the list of messages of this conversation (section 8) or, when there are none, the text `No messages yet.`; the composer (a text field and a control labelled `Send`). Messages that arrive or change state while the screen is open MUST appear without any user action (CORE-VISIBLE-007).
- **CORE-SEND-004** — When the user activates `Send` with text that is blank or longer than 4096 bytes in UTF-8 (CORE-TEXT-002, CORE-TEXT-003, checked locally), the client MUST show the matching message of section 8.1 next to the composer, MUST NOT add any message, MUST keep the typed text in the composer, and MUST NOT contact the server. The message MUST disappear when the user edits the text or sends a valid one.
- **CORE-SEND-005** — When the user activates `Send` with valid text, the client MUST at once add the message to the end of this conversation's list with the state `Pending`, clear the composer, and remove any composer message. This MUST happen in every connection state and the message always goes through the unsent queue (CORE-OUTBOX-001); there is no other way to send.
- **CORE-SEND-006** — A message's text MUST be shown exactly as the user typed it (CORE-TEXT-005): same characters, same case, same leading, trailing and repeated spaces, same line breaks. Long text MUST wrap or scroll; it MUST NOT be cut off or abbreviated.
- **CORE-SEND-007** — Each message in the list MUST show its author's name (`alice`, `bob`), its text, the label of its state (section 8.1) and, when it has one, its time (CORE-VISIBLE-009). Messages written by the user and messages written by the peer MUST be visibly distinguishable beyond the author name (for example by alignment or color); how is a platform choice.
- **CORE-SEND-008** — A message the user wrote MUST change state in place, without leaving the list: `Pending` becomes `Sent` only when the server has acknowledged it (CORE-MSG-004); a timeout, lost connection or going offline MUST NOT mark it `Sent` or `Failed`. Becoming `Sent` may move the message (CORE-ORDER-003).
- **CORE-SEND-009** — A message the server rejects for good (CORE-ERR-003 class P) MUST show the label `Failed`, MUST be visibly marked as an error beyond the label, MUST stay in the list in the place CORE-SEQ-002 gives it, and MUST NOT be resent automatically, edited, resent by the user or removed (CORE-OUTBOX-005). It does not hold back later messages. The client's own checks (CORE-SEND-004) make this state practically unreachable, but its look is fixed here.
- **CORE-SEND-010** — `Send` and the composer MUST be usable in every connection state; the connection state never disables them.
- **CORE-SEND-011** — The user MAY open a conversation with their own name. A message to oneself appears once, as written by the user, and shows `Sent` after acknowledgement, never `Received` (CORE-DEDUPE-004, CORE-ENV-003). Such a conversation appears in the list under the user's own name.

## 5. Offline use

- **CORE-OFFLINE-001** — The header MUST contain an offline switch labelled `Offline mode`. Switching it on makes the client not allowed to connect (CORE-CONN-001, CORE-CONN-002); switching it off makes it allowed again, unless the network is unavailable. The switch is off at every launch and MUST NOT be remembered across launches.
- **CORE-OFFLINE-002** — Whenever the client is not allowed to connect, whether because the switch is on or because the device has no network, the connection indicator MUST show `Offline` and the client MUST NOT contact the server at all (CORE-CONN-004). Messages the peer sent in the meantime are not shown until the client connects again. With the switch off and no network, the indicator shows `Offline` while the switch itself reads off.
- **CORE-OFFLINE-003** — While `Offline`, the user MUST still be able to see all stored conversations and messages, open conversations, start new ones and send messages exactly as when online (CORE-SEND-010). Each message sent offline shows `Pending` and keeps the position of CORE-SEQ-002 relative to the user's other unsent messages (their sending order).
- **CORE-OFFLINE-004** — Unsent messages MUST survive closing and relaunching the client in every connection state (CORE-OUTBOX-002): after relaunch they are still shown as `Pending` in the same relative order.
- **CORE-OFFLINE-005** — When the client becomes allowed to connect again (switch off, network back, or launch), the indicator MUST change at once from `Offline` to `Connecting` and, once the server accepts the client's registration (CORE-CONN-006 step 1), to `Online`. The user does nothing else.
- **CORE-OFFLINE-006** — The indicator MUST show exactly one of: `Offline` (not allowed to connect), `Connecting` (allowed, but no working server connection yet or retrying after a failure, including when the server is not running), `Online` (allowed and the last contact with the server worked). `Online` does not mean the unsent messages are delivered; their labels say that. The states follow CORE-CONN-003 and CORE-CONN-008.
- **CORE-OFFLINE-007** — If the client goes offline while a message is being delivered, that message and every later unsent message MUST still show `Pending`, except a message whose acknowledgement had already been processed (it shows `Sent`). No message is shown twice and none is lost (CORE-CONN-004, CORE-OUTBOX-004).

## 6. Flush

- **CORE-FLUSH-001** — After the client has become `Online`, it MUST deliver all unsent messages on its own, with no user action and no control for it.
- **CORE-FLUSH-002** — Unsent messages MUST become `Sent` one at a time in the order they were sent by the user (CORE-OUTBOX-003): at no moment may a message show `Sent` while an earlier unsent message of the same user still shows `Pending`, across all conversations.
- **CORE-FLUSH-003** — Messages waiting for the user on the server MUST be shown before the user's unsent messages are delivered (CORE-CONN-006 steps 2 and 3). Consequently, on reconnection the received messages appear first and the `Pending` ones turn `Sent` afterwards.
- **CORE-FLUSH-004** — When a message becomes `Sent` the list MUST show it at the place its new server order gives it (CORE-SEQ-004), with the label `Sent`.
- **CORE-FLUSH-005** — If delivery fails for a reason that may pass (server not reachable, timeout, server error), the unsent messages MUST stay `Pending` in unchanged order, the indicator MUST show `Connecting`, and the client MUST try again by itself (CORE-CONN-008). No message appears twice, including when a failed attempt had in fact reached the server (CORE-DEDUPE-001, CORE-DEDUPE-003): the message then becomes `Sent` once, at the place of its original server order.
- **CORE-FLUSH-006** — Once the queue is empty and the indicator shows `Online`, any message the user sends MUST be delivered at once, without waiting for another event or any other action (CORE-CONN-006 step 4).

## 7. Receiving

- **CORE-RECEIVE-001** — While `Online`, a message addressed to the user MUST appear in the conversation with its sender with the label `Received` and the sender's name as author, without any user action, whichever screen is open (it is then visible when that conversation is open, and through the list).
- **CORE-RECEIVE-002** — Messages the server holds for the user from the time the client was not connected (offline, closed or restarting) MUST appear after connecting, all of them, in their order (CORE-SEQ-002), before the user's unsent messages are delivered (CORE-FLUSH-003).
- **CORE-RECEIVE-003** — A received message MUST NOT trigger any pop-up, sound, badge, unread count or automatic opening of a conversation. It only appears in its conversation and, if it starts a new conversation or is the newest, moves that conversation in the list (CORE-VISIBLE-003).
- **CORE-RECEIVE-004** — A message MUST be shown once, however many times it is delivered (CORE-DEDUPE-002).
- **CORE-RECEIVE-005** — A message of a kind this client does not know, or of a known kind with unusable content, MUST be invisible: no entry in any message list, no conversation created for it, no error, no label (CORE-EXT-002, CORE-EXT-004). The next ordinary message still appears.
- **CORE-RECEIVE-006** — A received message's text MUST be shown exactly as sent (CORE-SEND-006 applies to received text too).

## 8. Order and what is shown

### 8.1 Fixed texts

Every client MUST use these texts exactly (no trailing punctuation changes, no translation in v1).

| Where | Text |
|---|---|
| Invalid name (login field and recipient field) | `Names use 1 to 32 letters, digits, underscores or hyphens.` |
| Composer, blank text | `Type a message first.` |
| Composer, text over 4096 bytes | `Message is too long. The limit is 4096 bytes.` |
| Connection indicator | `Offline`, `Connecting`, `Online` |
| Message state labels | `Pending`, `Sent`, `Received`, `Failed` |
| Empty conversation list | `No conversations yet.` |
| Empty conversation | `No messages yet.` |
| Message time | `HH:mm`, or `YYYY-MM-DD HH:mm` when the date differs (CORE-VISIBLE-010) |
| Controls | `Continue` (login), `Open` (new conversation), `Back`, `Send`, `Offline mode` (switch) |

Mapping of machine states to labels: `pending` → `Pending`, `sent` → `Sent`, `received` → `Received`, `failed` → `Failed`; `offline` → `Offline`, `connecting` → `Connecting`, `online` → `Online` (CORE-MSG-006, CORE-CONN-003).

### 8.2 Order in a conversation

- **CORE-ORDER-001** — A conversation's messages MUST be listed from top to bottom in the order of CORE-SEQ-002, oldest first, newest last. A newly added message appears at the bottom.
- **CORE-ORDER-002** — Unsent messages (`Pending`, `Failed`) MUST always be below every `Sent` and `Received` message, in the order the user sent them. Hence a message the user has just written is at the bottom even if received messages with a later server order are shown above it later.
- **CORE-ORDER-003** — When a `Pending` message becomes `Sent`, the list MUST immediately show it at the position of its server order (CORE-SEQ-004). It MAY move up past messages that were received while it was pending, and every other message keeps its relative order.
- **CORE-ORDER-004** — No time of day, date or clock value MUST be used for order (CORE-SEQ-003); the time shown on a message (CORE-VISIBLE-009) is informational only, and an order that disagrees with the shown times stays as it is.
- **CORE-ORDER-005** — Once every message of a conversation is acknowledged and delivered, both users MUST see the same messages in the same order, whichever client each of them uses (CORE-SEQ-005). The labels differ by viewpoint (the author sees `Sent`, the other user `Received`).
- **CORE-ORDER-006** — A conversation MUST list only text messages between the user and that peer (CORE-SEQ-005); nothing else.

### 8.3 Conversation list and general display

- **CORE-VISIBLE-001** — The header MUST show, on every screen after login: the user's name in lowercase; the connection indicator (CORE-OFFLINE-006); the offline switch (CORE-OFFLINE-001). It MUST NOT appear on the login screen.
- **CORE-VISIBLE-002** — The conversation list MUST contain one entry per peer for whom at least one stored text message exists, in either direction, including `Pending` and `Failed` ones. An entry shows the peer's name and nothing else. A conversation that was only opened, with no message in it, MUST NOT appear in the list. With no entries the list area shows `No conversations yet.`
- **CORE-VISIBLE-003** — The list MUST be ordered newest conversation first. A conversation's position is that of its newest message in the order of CORE-SEQ-002 taken over all the user's messages (so a conversation whose newest message is unsent is above every conversation whose newest message is `Sent` or `Received`; among unsent ones, the one written last is first; among the rest, the highest server order is first). Order changes at once when a message arrives, is sent, or becomes `Sent`.
- **CORE-VISIBLE-004** — Activating a list entry MUST open that conversation's screen. After a launch, the client MUST show the conversation list screen, not the conversation that was open before.
- **CORE-VISIBLE-005** — The client MUST show exactly the fixed texts of section 8.1 for the states and conditions listed there.
- **CORE-VISIBLE-006** — The client MUST NOT show delivery or read receipts, typing indicators, unread counts, online status of other users, or error dialogs for network problems; network problems are only visible through the connection indicator and the `Pending` labels.
- **CORE-VISIBLE-007** — Every change of state, order, list content or indicator MUST appear on screen by itself, without refreshing or any user action, and no element may keep showing a state that the client no longer has.
- **CORE-VISIBLE-008** — When the server has been restarted, the client MUST discover it by itself the next time it connects and, per CORE-EPOCH-004, remove every `Sent` and `Received` message from all views; `Pending` and `Failed` messages stay, in their order, and the unsent ones are delivered as usual (CORE-FLUSH-001). A conversation with no remaining message leaves the list; an open conversation with none remaining shows `No messages yet.`. The client shows no notice, dialog or error about this in v1. The indicator may pass through `Connecting` while the server is down.
- **CORE-VISIBLE-009** — Every message that has an accepted time (state `Sent` or `Received`) MUST show that time, the same instant for both users, next to its state label; a `Pending` or `Failed` message MUST show no time. When a `Pending` message becomes `Sent` it gains its time in the same change (CORE-FLUSH-004). The time is the server's accepted time, never the sender's clock (CORE-ENV-006, CORE-ENV-007).
- **CORE-VISIBLE-010** — The time MUST be written as `HH:mm`: hours 00 to 23 and minutes 00 to 59, two ASCII digits each, a colon between, no seconds (the seconds are dropped, not rounded), no AM or PM, whatever the device language or region. If the calendar date of the time in the device's local time zone differs from the current local date, it MUST be written `YYYY-MM-DD HH:mm` instead (four-digit year, two-digit month and day, one space). The client composes this text itself and does not use a language- or region-dependent format.
- **CORE-VISIBLE-011** — The time MUST be converted from UTC (CORE-TIME-001) to the device's current local time zone, and "current local date" taken from the current time, each time the time is displayed (CORE-TIME-002). A change of the device's time zone MUST show in the times the next time they are displayed, without relaunching and without any user action.
- **CORE-VISIBLE-012** — The time MUST NOT change a message's place, a conversation's place in the list, or any state (CORE-ORDER-004).

## 9. Acceptance criteria

Given/When/Then, observable by a user; each cites the rules it checks. Traceability (test ids per scope): [`docs/product/TRACEABILITY.md`](../../docs/product/TRACEABILITY.md). Scenario-level criteria (`AC-F4-*`, `AC-F2-15`, `AC-F2-16`, `AC-F2-21`, `AC-F3-13` to `AC-F3-15`) are in [`../scenarios/`](../scenarios/).

### F1: Identity and login (BR-1)

- **AC-F1-1** — Given a freshly installed client, When it is launched, Then the login screen with a name field and a `Continue` control is shown and no header or conversation list is shown. (CORE-LOGIN-001)
- **AC-F1-2** — Given the login screen, When the user enters `Alice` and activates `Continue`, Then the conversation list screen is shown with `alice` in the header and the text `No conversations yet.`. (CORE-LOGIN-004, CORE-VISIBLE-001, CORE-VISIBLE-002)
- **AC-F1-3** — Given the login screen, When the user enters an empty name, a name with a space, a name with a character other than letters, digits, underscore and hyphen, or a name of 33 characters, Then the text `Names use 1 to 32 letters, digits, underscores or hyphens.` is shown, the typed text stays, and the login screen remains. (CORE-LOGIN-002, CORE-LOGIN-003)
- **AC-F1-4** — Given the login screen and no server running, When the user enters `carol` and activates `Continue`, Then the conversation list screen is shown with `carol` and the indicator `Connecting`. (CORE-LOGIN-002, CORE-LOGIN-004, CORE-OFFLINE-006)
- **AC-F1-5** — Given a client logged in as `alice`, When the client is closed and launched again, Then no login screen is shown, the header shows `alice`, and the conversation list screen is shown with its earlier conversations. (CORE-LOGIN-005, CORE-VISIBLE-004)
- **AC-F1-6** — Given a logged-in client, When any screen after login is shown, Then the header shows the user's name, the connection indicator and the `Offline mode` switch, which is off. (CORE-VISIBLE-001, CORE-OFFLINE-001)
- **AC-F1-7** — Given a logged-in client, When the user looks for a way to log out or change the name, Then there is none. (CORE-LOGIN-006)

### F2: Sending and receiving (BR-2, BR-4)

- **AC-F2-1** — Given the conversation list screen, When the user enters `Bob` in the recipient field and activates `Open`, Then the conversation screen for `bob` is shown with `No messages yet.`, and `Back` returns to a list that does not contain `bob`. (CORE-SEND-001, CORE-SEND-003, CORE-VISIBLE-002)
- **AC-F2-2** — Given the conversation list screen, When the user enters an invalid name (for example `bob smith`) and activates `Open`, Then the invalid-name text is shown, the typed text stays, and no conversation opens. (CORE-SEND-002)
- **AC-F2-3** — Given an open conversation, When the user sends `Hello` while the indicator shows `Online`, Then `Hello` appears at the bottom, written by the user's name, and the field is empty; and when the server acknowledges it, its label reads `Sent`. (CORE-SEND-005, CORE-SEND-007, CORE-SEND-008)
- **AC-F2-4** — Given an open conversation, When the user sends text that is empty, only spaces and line breaks, or 4097 bytes long, Then the matching composer text is shown, no message is added, and the typed text stays; and a text of exactly 4096 bytes is accepted. (CORE-SEND-004)
- **AC-F2-5** — Given an open conversation, When the user sends text with leading and trailing spaces, repeated spaces, upper and lower case, a line break and non-English characters, Then the message shows exactly those characters, and the peer's client shows the same characters for it. (CORE-SEND-006, CORE-RECEIVE-006)
- **AC-F2-6** — Given Bob is online, When Alice sends `Hi Bob` to him, Then Bob's list gains an entry `alice` without any action, and in that conversation `Hi Bob` is shown written by `alice` with the label `Received`. (CORE-RECEIVE-001, CORE-RECEIVE-003, CORE-VISIBLE-002, CORE-VISIBLE-007)
- **AC-F2-7** — Given a conversation with several messages, When messages are sent and received, Then they are listed oldest first, unsent ones below all others, and a message that becomes `Sent` moves to the position of its server order. (CORE-ORDER-001, CORE-ORDER-002, CORE-ORDER-003)
- **AC-F2-8** — Given conversations with `bob` and `carol`, When the newest message is in the one with `carol`, Then `carol` is above `bob` in the list, and when a new message arrives from `bob`, `bob` moves to the top. (CORE-VISIBLE-003)
- **AC-F2-9** — Given an open conversation, When a message of an unknown kind or with unusable content is delivered to the user, Then nothing changes on screen, no error is shown, and the next ordinary message still appears. (CORE-RECEIVE-005)
- **AC-F2-10** — Given any message, When it is delivered more than once to the client, Then it is shown once. (CORE-RECEIVE-004)
- **AC-F2-11** — Given the user is `alice`, When Alice opens a conversation with `Alice` and sends `note`, Then `note` is shown once, written by `alice`, with the label `Sent`, and the list has an entry `alice`. (CORE-SEND-011)
- **AC-F2-12** — Given any screen after login, When a message is shown, Then it shows author, text and one of the labels `Pending`, `Sent`, `Received`, `Failed`, and no receipt, typing or unread indicator is shown anywhere. (CORE-SEND-007, CORE-VISIBLE-005, CORE-VISIBLE-006)
- **AC-F2-13** — Given a message the server rejected for good, When it is shown, Then it reads `Failed`, is marked as an error, sits below all `Sent` and `Received` messages, is not resent and does not stop later messages from being delivered. (CORE-SEND-009, CORE-ORDER-002)
- **AC-F2-14** — Given two users with a settled conversation, When both look at it, Then both see the same messages in the same order, on any pairing of the two clients. (CORE-ORDER-005, CORE-ORDER-006)
- **AC-F2-17** — Given a message the server accepted at 15:00 UTC on 2026-10-13 and a device in the time zone UTC-03:00 whose current date is 2026-10-13, When the message is shown with the label `Sent` or `Received`, Then it shows the time `12:00` next to its label. (CORE-VISIBLE-009, CORE-VISIBLE-010, CORE-VISIBLE-011)
- **AC-F2-18** — Given the same message and a device in the time zone UTC-03:00 whose current date is 2026-10-14, When the message is shown, Then it shows `2026-10-13 12:00`. (CORE-VISIBLE-010)
- **AC-F2-19** — Given a message accepted at 15:00:59.999 UTC on a device in UTC, When it is shown, Then it shows `15:00`, with two digits for hours and minutes and no seconds, whatever the device language and region. (CORE-VISIBLE-010)
- **AC-F2-20** — Given a `Pending` message, When it is shown, Then it shows no time; and When the server acknowledges it, Then the label becomes `Sent` and a time appears. A `Failed` message shows no time. (CORE-VISIBLE-009, CORE-SEND-008)
- **AC-F2-22** — Given a device whose time zone changes from UTC-03:00 to UTC+09:00 while a conversation is open, When the times are displayed again, Then each time shows the new local time without relaunching. (CORE-VISIBLE-011)
- **AC-F2-23** — Given messages whose shown times are not in the same order as their places in the list, When the list is shown, Then the places are unchanged and follow the server's order. (CORE-VISIBLE-012, CORE-ORDER-004)

### F3: Offline queue and flush (BR-3)

- **AC-F3-1** — Given an online client, When the user switches `Offline mode` on, Then the indicator shows `Offline` and the client sends nothing to the server and shows no new messages from others while it stays on. (CORE-OFFLINE-001, CORE-OFFLINE-002)
- **AC-F3-2** — Given the indicator shows `Offline`, When the user opens a conversation and sends `Later`, Then `Later` is shown at the bottom with the label `Pending`, in the order of sending among the user's other `Pending` messages. (CORE-OFFLINE-003, CORE-SEND-010, CORE-ORDER-002)
- **AC-F3-3** — Given `Pending` messages exist, When the client is closed and launched again, Then they are still shown as `Pending` in the same order, and the switch is off. (CORE-OFFLINE-004, CORE-OFFLINE-001)
- **AC-F3-4** — Given the indicator shows `Offline` after the user's switch, When the user switches `Offline mode` off, Then the indicator shows `Connecting` at once and `Online` when the server accepts the client. (CORE-OFFLINE-005)
- **AC-F3-5** — Given several `Pending` messages in different conversations, When the client becomes `Online`, Then they turn `Sent` one at a time in the order the user sent them, with no user action. (CORE-FLUSH-001, CORE-FLUSH-002)
- **AC-F3-6** — Given a `Pending` message and messages received while it was pending, When the message turns `Sent`, Then it is shown at the position of its server order, with the label `Sent`. (CORE-FLUSH-004, CORE-ORDER-003)
- **AC-F3-7** — Given messages waiting on the server for a client that is offline and has `Pending` messages, When the client reconnects, Then the waiting messages appear as `Received` before any `Pending` message turns `Sent`. (CORE-RECEIVE-002, CORE-FLUSH-003)
- **AC-F3-8** — Given a `Pending` message, When the server cannot be reached while the switch is off, Then the indicator shows `Connecting`, the message stays `Pending`, and when the server is reachable again it turns `Sent` once, without user action. (CORE-OFFLINE-006, CORE-FLUSH-005)
- **AC-F3-9** — Given a message the server already accepted whose acknowledgement the client never processed, When the client connects again, Then the message turns `Sent` once, shown once, at the place of its original server order. (CORE-FLUSH-005, CORE-RECEIVE-004)
- **AC-F3-10** — Given an online client with `Sent` and `Received` messages, When the server has been restarted and the client connects to it, Then all `Sent` and `Received` messages disappear from every view, `Pending` messages stay and are delivered, and no notice or error is shown. (CORE-VISIBLE-008, CORE-FLUSH-001)
- **AC-F3-11** — Given several `Pending` messages being delivered, When the user switches `Offline mode` on, Then messages whose acknowledgement was already shown remain `Sent`, all others remain `Pending` in order, and none is shown twice. (CORE-OFFLINE-007)
- **AC-F3-12** — Given the client is `Online` with no `Pending` messages, When the user sends a message, Then it turns `Sent` without further action. (CORE-FLUSH-006)

## 10. Decisions behind the defaults

| Question (TL packet) | Assumed default | Rules that change if the operator decides otherwise |
|---|---|---|
| Q1 unknown recipient | accepted, lazy mailbox | CORE-SEND-001, CORE-SEND-002, (protocol CORE-MSG-003) |
| Q2 history on server restart | cleared, unsent messages kept | CORE-VISIBLE-008, CORE-FLUSH-005 |
| Q3 name display | lowercase everywhere | CORE-LOGIN-004, CORE-SEND-001, CORE-SEND-007, CORE-VISIBLE-001 |
| Q4 order | server acceptance order | CORE-ORDER-001 to -005, CORE-VISIBLE-003 |
| Q7 notes to self | allowed | CORE-SEND-011 |

PM choices not asked of the TL: two screens with a shared header; list shows names only; message times are the server's accepted time in local `HH:mm` (operator decision OM-0010, section 8.3); offline switch not remembered; no notice after a server restart; fixed English texts. They are listed as questions in the PM packet.

## 11. Out of scope in v1

No logout or change of name; no passwords or accounts; no delivery or read receipts; no typing indicators; no groups; no attachments or images; no editing or deleting of messages; no search; no sender-side or seconds-level timestamps; no unread counts or notifications; no contact list or check that a recipient exists; no push delivery while the client is closed; no translation of the fixed texts. Extensions (for example reactions) are specified separately under [`../extensions/`](../extensions/) and add behavior without changing this file.
