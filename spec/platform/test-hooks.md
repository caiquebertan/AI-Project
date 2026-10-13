# Test hooks (shared by all client platforms)

- **Status:** draft for G0 (spec 0.1.0-draft). Owner: TL.
- **Why a shared file:** external acceptance checks in `tests/` drive either client as Alice or Bob with one script. That only works if both clients expose the **same hook names and the same state shape**. This file fixes those names once; [`android.md`](android.md) and [`web.md`](web.md) say only how each platform exposes them.
- **Not behavior:** this file says what must be *addressable* and *readable* by tests. When an element is shown, what it says and what it does are in [`../core/client-behavior.md`](../core/client-behavior.md) (PM). If the behavior spec has no element for a hook below, that is a spec gap (`SPEC_ISSUE`), not a reason to drop the hook.

## 1. Element hooks

- **PLAT-HOOK-001** — Each client MUST attach the hook ids below, as exact strings, to the corresponding UI elements whenever they are on screen (Android: test tag; web: `data-testid`).

| Hook id | Element | Readable value (§2) |
|---|---|---|
| `login-name-input` | name text field on the login screen | — |
| `login-submit` | button that submits the name | — |
| `login-error` | validation message for an invalid name | — |
| `current-user` | header: the logged-in canonical name | text |
| `connection-status` | header: indicator of the connection state | state: `offline` \| `connecting` \| `online` |
| `offline-toggle` | header: the user control for `offline_toggle` (CORE-CONN-001) | on = offline |
| `conversation-list` | container of conversations | — |
| `conversation-item-<peer>` | one conversation, `<peer>` = canonical peer name | — |
| `new-conversation-input` | field to type a recipient name | — |
| `new-conversation-submit` | button that opens the conversation with that name | — |
| `new-conversation-error` | validation message for an invalid recipient name (CORE-SEND-002) | — |
| `conversation-back` | the `Back` control of the conversation screen (CORE-SEND-003) | — |
| `conversation-peer` | the open conversation's peer name | text |
| `message-list` | container of the open conversation's messages, in CORE-SEQ-002 order | — |
| `message-<id>` | one message, `<id>` = its message id | state: `pending` \| `sent` \| `received` \| `failed`; seq; author (`from`) |
| `composer-input` | text field for a new message | — |
| `composer-send` | send button | — |
| `composer-error` | validation message for an invalid text | — |

- **PLAT-HOOK-002** — Elements carrying `message-<id>` inside `message-list`, and elements carrying `conversation-item-<peer>` inside `conversation-list`, MUST appear in element order exactly as they are rendered (top to bottom), so a test can read the rendered order of messages (CORE-SEQ-002) and of conversations (CORE-VISIBLE-003) from the element order.
- **PLAT-HOOK-003** — A hook id MUST be unique on screen at any moment.
- **PLAT-HOOK-010** — `current-user`, `connection-status` and `offline-toggle` MUST be inside the header that is present on every screen after login (CORE-VISIBLE-001) and absent from the login screen; because only one screen is shown at a time, each of the three exists exactly once while logged in (PLAT-HOOK-003).

## 2. Readable values

- **PLAT-HOOK-004** — `connection-status` and every `message-<id>` MUST expose their machine value (the state names in the table, lowercase, exactly) independently of the visible label, and `message-<id>` MUST also expose its `seq` (empty when it has none) and its author (the canonical `from`, equal to the snapshot's `from`).
- **PLAT-HOOK-005** — `offline-toggle` MUST expose its on/off state through the platform's standard checked/toggleable state, where on means `offline_toggle = true`.

## 3. State snapshot and control hooks

- **PLAT-HOOK-006** — Each client MUST provide a test-only way to (a) read a snapshot of its client state as JSON matching [`client-snapshot.schema.json`](client-snapshot.schema.json), (b) set `offline_toggle`, and (c) set the value its connectivity monitor reports as `network_available`, without UI interaction. Platform files define the mechanism.
- **PLAT-HOOK-007** — The snapshot MUST reflect persisted state: after a step completes, the values in the snapshot are the ones a restart would reload (identity, epoch, cursor, outbox, messages).
- **PLAT-HOOK-008** — The snapshot's `messages` MUST list every stored `text` message of all conversations in CORE-SEQ-002 order; its `outbox` MUST list the ids of `pending` messages in outbox order.

Snapshot shape (abridged; the schema is normative):

```json
{"user":"bob","connection":"online","offline_toggle":false,"network_available":true,
 "epoch":"3f9a1c7e5b2d4086","cursor":3,"outbox":[],
 "messages":[{"id":"00000000-0000-4000-8000-0000000000a1","seq":1,"from":"alice","to":"bob","text":"Hi Bob, I have something important to tell you","state":"received","created_at":"2026-10-13T15:00:01.000Z"}]}
```

- **PLAT-HOOK-011** — Each client MUST support a test-only **relaunch** control (mechanism per platform file) equivalent to the user closing and launching the app again: all in-memory state is discarded, persisted storage (identity, epoch, cursor, messages with their enqueue order, outbox) is kept untouched, and the client starts as on a normal launch (`offline_toggle` back to `false` per CORE-OFFLINE-001; any `setNetworkAvailable` override is dropped and the real monitor is read again).
- **PLAT-HOOK-012** — Every HTTP request of a client MUST go to its single configured base URL (PLAT-ANDROID-013, PLAT-WEB-011), so a test can place a per-client counting proxy in front of the server and observe every request the client makes (decision 0010; used for "no request while offline", CORE-CONN-004).

## 4. Injected ports (for in-project tests)

- **PLAT-HOOK-009** — The client's protocol engine MUST receive these dependencies through constructor injection, never by global lookup, so generated unit tests can replace them with fakes: `Transport` (the five endpoints), `LocalStore` (identity, epoch, cursor, messages, outbox), `ConnectivityMonitor` (`network_available` as an observable value), `Clock` (UTC now), `Scheduler` (delays for backoff), `IdGenerator` (UUID v4).
