# Test hooks (shared by all client platforms)

- **Status:** draft for G0 (spec 0.1.0-draft). Owner: TL.
- **Why a shared file:** in-project UI tests on both platforms and the external checks in `tests/` (web through the browser, Android through the JVM driver of PLAT-ANDROID-031) must find the **same hook names and the same state shape**. This file fixes those names, the snapshot, and the test cases both platforms must generate once; [`android.md`](android.md) and [`web.md`](web.md) say only how each platform exposes them.
- **Ids:** `PLAT-HOOK-NNN`; a withdrawn rule stays as a one-line tombstone without a keyword (decision 0014).
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
| `message-<id>` | one message, `<id>` = its message id | state: `pending` \| `sent` \| `received`; seq; author (`from`) |
| `message-time-<id>` | the displayed time of message `<id>` (CORE-TIME-002); present only while the message has a `seq` | text (equals snapshot `time_text`) |
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

- **PLAT-HOOK-006** — Each client MUST provide a test-only way to (a) read a snapshot of its client state as JSON matching [`client-snapshot.schema.json`](client-snapshot.schema.json), (b) set `offline_toggle`, and (c) set the value its connectivity monitor reports as `network_available`, without UI interaction. Platform files define the mechanism (web: `window.__AWARE__`, PLAT-WEB-012, used by in-project and Playwright tests; Android: the engine API in `:core:protocol`, PLAT-ANDROID-018, used by JVM and Robolectric tests, and the JVM driver, PLAT-ANDROID-032, used by external tests).
- **PLAT-HOOK-007** — The snapshot MUST reflect persisted state: after a step completes, the values in the snapshot are the ones a restart would reload (identity, epoch, cursor, outbox, messages).
- **PLAT-HOOK-008** — The snapshot's `messages` MUST list every stored `text` message of all conversations in CORE-SEQ-002 order; its `outbox` MUST list the ids of `pending` messages in outbox order.
- **PLAT-HOOK-013** — Each snapshot message MUST carry `accepted_at` (the stored UTC instant, CORE-TIME-001; `null` without `seq`) and `time_text` (exactly the text shown by `message-time-<id>` when the snapshot is taken, produced by the same code with the same `Clock` and `TimeZone`; `null` when no time is shown); `message-time-<id>` MUST be absent while the message has no `seq`.

Snapshot shape (abridged; the schema is normative):

```json
{"user":"bob","connection":"online","offline_toggle":false,"network_available":true,
 "epoch":"3f9a1c7e5b2d4086","cursor":3,"outbox":[],
 "messages":[{"id":"00000000-0000-4000-8000-0000000000a1","seq":1,"from":"alice","to":"bob","text":"Hi Bob, I have something important to tell you","state":"received","created_at":"2026-10-13T15:00:01.000Z",
   "accepted_at":"2026-10-13T15:00:01.010Z","time_text":"00:00"}]}
```

- **PLAT-HOOK-011** — Each client MUST support a test-only **relaunch** control (mechanism per platform file) equivalent to the user closing and launching the app again: all in-memory state is discarded, persisted storage (identity, epoch, cursor, messages with their enqueue order, outbox) is kept untouched, and the client starts as on a normal launch (`offline_toggle` back to `false` per CORE-OFFLINE-001; any `setNetworkAvailable` override is dropped and the real monitor is read again).
- **PLAT-HOOK-012** — Withdrawn (decision 0014).

## 4. Injected ports (for in-project tests)

- **PLAT-HOOK-009** — The client's protocol engine MUST receive these dependencies through constructor injection, never by global lookup, so generated unit tests can replace them with fakes: `Transport` (the five endpoints), `LocalStore` (identity, epoch, cursor, messages, outbox), `ConnectivityMonitor` (`network_available` as an observable value), `Clock` (UTC now), `TimeZone` (the device's current zone: `zoneId()` returning an IANA id or a fixed offset `±HH:MM`, and `offsetMinutesAt(utcInstant)` returning the zone's UTC offset in minutes at that instant), `Scheduler` (the `CYCLE_INTERVAL_MS` pause between cycles, CORE-CONN-007, and request timeouts), `IdGenerator` (UUID v4), `DiagnosticLog` (`warn(line)`: one line per call, used by CORE-OUTBOX-005).

## 5. Tests every client MUST generate

- **PLAT-HOOK-014** — Each client's in-project tests MUST prove CORE-CONN-004, CORE-CONN-005, CORE-CONN-007 and CORE-CONN-008 against the protocol engine with a recording fake `Transport` (every call logged with its endpoint, start and end), a fake `Scheduler` and a fake `Clock`, with at least these cases: (a) online and idle, then `setOffline(true)`: after fake time advances by `10 × CYCLE_INTERVAL_MS` and a message is queued, no call has started since the switch; (b) the same with `setNetworkAvailable(false)`; (c) an E3 in flight, and in a separate test an E4 in flight, when `setOffline(true)` is called: that call is not cancelled, its response is applied (the message becomes `sent`; the polled envelopes are stored and the cursor advances) and no further call starts; (d) after `setOffline(false)` the next call is E2 and starts without waiting for the interval; (e) at most one call is in flight at any time, and the next cycle's first call starts exactly `CYCLE_INTERVAL_MS` after the previous cycle's last call ended, including after a failed call (no growth). These tests replace any request-counting proxy (decision 0014).
- **PLAT-HOOK-015** — Each client's in-project tests MUST include one test that enforces CORE-TIME-003: it reads every file in the client's production sources and build configuration (paths per platform file; test sources and fixtures are outside them) and fails, naming file and line, on any match of the patterns below plus the platform patterns of the platform file. No match is exempted by a comment or an allowlist.

| Pattern (regular expression) | Catches |
|---|---|
| `\b(Africa\|America\|Antarctica\|Arctic\|Asia\|Atlantic\|Australia\|Europe\|Indian\|Pacific\|Etc)/[A-Za-z_+-]+` | IANA zone ids, e.g. `America/Sao_Paulo` |
| `\b(UTC\|GMT)\s*[+-]\s*[0-9]` | offset names, e.g. `UTC-3`, `GMT+9` |
| `["'\x60][+-](0[0-9]\|1[0-4]):?[0-5][0-9]["'\x60]` | quoted offset literals, e.g. `"+09:00"`, `'-0300'` |
| `["'\x60](BRT\|JST\|PST\|PDT\|EST\|EDT\|CST\|CDT\|MST\|MDT\|CET\|CEST\|EET\|BST\|IST)["'\x60]` | quoted zone abbreviations |
| `\bTZ\s*=` | `TZ=` settings in scripts and configuration |
| `user\.timezone` | JVM default-zone settings |

In the table, `\|` stands for the regex alternation `|` (escaped for Markdown) and `\x60` for a backtick. UTC itself is allowed: the `Z` designator, `ZoneOffset.UTC`, `Instant`, `Date.UTC` and `getUTC*` do not match any pattern.
