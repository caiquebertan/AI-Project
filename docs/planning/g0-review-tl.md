# G0 review packet — TL protocol, server and platform spec (P1, spec 0.1.0-draft)

> **Author:** TL agent (claude-opus-5-5), stage S0, phase P1, ref OM-0008. AI-written; awaiting operator decision at G0.
> **Read with:** `spec/core/protocol.md` (Appendix A is the fastest way to check the design), `spec/core/server-behavior.md`, `spec/platform/*`, decisions `docs/decisions/0004`–`0009`.
> **Not in this packet:** `client-behavior.md`, scenarios, backlog, traceability (PM, next).

## (a) Decisions on one page

| # | Decision | Record | Spec ids |
|---|---|---|---|
| 1 | **Transport:** JSON over HTTP/1.1 under `/v1`; five endpoints: `GET /info`, `POST /session`, `POST /messages`, `GET /mailboxes/{name}/messages` (long-poll), `GET /users`. | 0004 | CORE-HTTP, CORE-POLL |
| 2 | **Cursor:** client-held, persisted, = `seq` of the last stored envelope of its own mailbox; sent as `after`. The server never deletes and keeps no read state; reads are side-effect free. | 0004 | CORE-CURSOR, CORE-POLL-006 |
| 3 | **Long-poll:** client `wait=20 s`, server clamp 30 s, instant answer when anything is newer than `after`; `wait=0` for catch-up. | 0004 | CORE-POLL-005, CORE-CONST-001 |
| 4 | **Epoch:** random id per server start; required on send/poll; mismatch `409` → client re-sessions, clears server-derived history and cursor, keeps identity and outbox. | 0004 | CORE-EPOCH |
| 5 | **Identity:** `^[A-Za-z0-9_-]{1,32}$`, case-insensitive, canonical = ASCII lowercase used everywhere (also displayed). Login is local (works offline); `POST /session` is idempotent and non-exclusive at each connection. | 0005 | CORE-NAME, CORE-SESSION |
| 6 | **Message id:** client-generated lowercase UUID v4. | 0006 | CORE-ENV-002 |
| 7 | **Order:** server assigns one global `seq` per epoch at acceptance. Render order on every client: sequenced messages by `seq`, then unsent ones by local enqueue order. No clocks. | 0006 | CORE-SEQ |
| 8 | **Ack and dedupe:** a message is `sent` only on `201`/`200` with `seq`; retries are byte-identical; server returns the original `seq` for a duplicate id (`200`), `409` if fields differ; receive is at-least-once (store, then advance cursor) with dedupe by id. | 0007 | CORE-MSG, CORE-DEDUPE |
| 9 | **Recipients:** the server accepts any valid recipient name and creates the mailbox lazily (no `404`); the sender must be registered in the epoch. | 0007 | CORE-MSG-002, -003 |
| 10 | **Generic relay:** closed envelope `{id, from, to, type, payload, created_at}` + server `seq`, `accepted_at`. Core type `text` only; the server validates core payloads only; any other type is relayed opaquely. Clients ignore unknown types but advance the cursor. | 0008 | CORE-ENV, CORE-EXT |
| 11 | **Capabilities:** clients declare capability ids at session; `GET /users` exposes them; `GET /info` exposes server capabilities (`[]`) and limits. | 0008 | CORE-CAP |
| 12 | **Offline:** `allowed = !offline_toggle && network_available` (monitor is a replaceable port). States `offline` / `connecting` / `online`. Offline = zero requests; going offline aborts in-flight requests. | 0009 | CORE-CONN-001..005 |
| 13 | **Connection cycle and flush:** session → catch-up polls → flush outbox FIFO, one send in flight → live long-poll (new sends flushed as they come). Any retryable failure: backoff 0.5 s doubling to 8 s, no jitter, restart cycle. Every send goes through the persistent outbox. | 0009 | CORE-CONN-006..009, CORE-OUTBOX |
| 14 | **Errors:** one body shape, 13 codes, a fixed precedence, and three client classes (retry / re-session / permanent). Limits: text ≤ 4096 UTF-8 bytes and not blank; body ≤ 64 KiB. | — | CORE-ERR, CORE-TEXT |
| 15 | **Platform:** Android modules `:core:protocol` + `:core:network` (pure JVM, the test gate), `:core:data` (Room, connectivity), `:feature:login`, `:feature:chat`, `:app`; web `src/core` (pure TS) / `data` / `features` / `app` / `testing`, runtime deps only React. Storage: Room `aware.db`; web `localStorage` key `aware.v1`. | — | PLAT-ANDROID, PLAT-WEB |
| 16 | **Test hooks:** one shared list of hook ids (`test-hooks.md`) used as Android test tags and web `data-testid`, a JSON state snapshot (schema), and test-only controls for the offline toggle and network flag (`window.__AWARE__`; Android debug ContentProvider). | — | PLAT-HOOK |

Rule ids written: CORE 114 (protocol 86, server 28), PLAT 50 (hooks 9, Android 24, web 17); 164 in total. Machine contract: 11 schemas, `index.json`, `constants.json`, 6 examples, checked by `generator/scripts/check_schema_examples.py`.

## (b) Open questions only the operator can decide

| # | Question | Options | Recommendation |
|---|---|---|---|
| Q1 | Should sending to a never-seen recipient fail? | (a) accept and store in a lazy mailbox (current draft); (b) `404 unknown_recipient`, so the message becomes `failed` | **(a).** With (b), an offline-queued message can fail permanently on flush, Bob must log in before Alice's first send, and after a server restart sends fail until the recipient reconnects. A typo warning can be a UI check against `GET /v1/users`. |
| Q2 | What happens to local history when the server restarts (new epoch)? | (a) clear sent/received history and cursor, keep the outbox (current draft); (b) keep the old history above the new one (epoch becomes an ordered timestamp) | **(a).** The server is the source of history; (b) shows history the peer may no longer have and adds an ordering rule. |
| Q3 | How are names shown? | (a) canonical lowercase everywhere (current); (b) keep the casing typed at first registration | **(a)** for v1. (b) is a small later extension. |
| Q4 | Is "server acceptance order" the right conversation order? Bob typed B2 before he saw A2, but A2 renders first because it reached the server first. | (a) accept order (current); (b) compose-time order (needs synchronized clocks, can differ between the two users) | **(a).** It is the only order both users can compute identically. |
| Q5 | How does P5 interop (E-INTEROP-1, android↔web) drive the Android client if the emulator is optional (Q19)? | (a) require an emulator for P5 only; (b) also have the generator produce a small JVM command-line driver over `:core:protocol` + `:core:network` (real protocol code, no UI) for `tests/interop`; (c) Android interop only in the operator's manual demo | **(b) + optional (a).** The driver exercises the generated Android protocol code against the real server in any sandbox; the emulator run stays a documented extra. It needs one platform rule added at P3. |
| Q6 | Test hooks in shipped builds | (a) web hook always present, Android provider debug-only (current); (b) strip both from release/production builds | **(a).** Local-only demo; Playwright can test the production build. |
| Q7 | Notes to self (`to` = `from`) | (a) allowed by the protocol (current); (b) rejected by the server | **(a).** Costs one dedupe rule; the PM may still hide it in the UI. |

## (c) Risks

- **Test volume.** E-QA-1 requires a passing test per `MUST` id: 164 ids, most client-side on two platforms. Mitigation: the platform rules make the generator emit id-named unit tests (one test may name several ids), including a replay of Appendix A against an in-memory fake server.
- **Concurrency in generated code.** Aborting long-polls on going offline, one send in flight, and the cycle restart are where generated code will be wrong first (stale responses applied after going offline, double flushers). REV should run on Opus for the first generation (WORKFLOW §2 already does).
- **Atomic store-then-cursor.** It depends on one Room transaction or one `localStorage` write. A generator that splits them breaks at-least-once silently. It is covered by explicit platform rules; QA should add a crash-between-writes test.
- **Hook list ahead of the UI.** The hooks assume a recipient-entry field and a conversation list before the PM writes the screens. If the PM's design differs, the hook list changes in the same G0.
- **Timing in external tests.** Long-poll and backoff run on real timers: 20 s idle polls and up to 8 s backoff. External tests must wait on states (snapshot or hooks), never on fixed sleeps. In-project tests use the injected `Scheduler`/`Clock`.
- **Spec version string.** `generator/config/generator.json` → `generate.spec_version_regex` captures `0.1.0` out of `0.1.0-draft`, so a generation run on the draft would stamp headers as `0.1.0` (see harness issues below).

## (d) What the PM needs for behavior and scenarios

- **Id areas.** PM ids use `CORE-LOGIN/SEND/OFFLINE/FLUSH/RECEIVE/ORDER/VISIBLE-NNN` (`spec/README.md` area table). Cite TL ids instead of restating wire rules: for example, "order per CORE-SEQ-002", "states per CORE-MSG-006 / CORE-CONN-003".
- **Visible states to name and show.** Message: `pending`, `sent`, `received`, `failed` (failed is practically unreachable but must have a defined look). Connection: `offline`, `connecting`, `online`. Hook values use exactly these strings; labels are the PM's choice.
- **Ordering consequences.** (1) Bob's final view is A1, B1, A2, B2, even though B2 was typed first. (2) Pending messages always sit below all sequenced ones. (3) A message can move when its ack arrives (CORE-SEQ-004). (4) After step 7 Alice does **not** see B2. Seeing it needs a step 8 (Alice reconnects), which the PM may add as an extra scenario step.
- **Step completion conditions** (to make "identically" testable): step 5 ends when A2 is `sent` on Alice (seq 3); step 7 ends when Bob shows A2 `received` (3) and B2 `sent` (4). Transient on Bob between 7.2 and 7.3: A2 above a still-`pending` B2.
- **Fixed texts.** `Queued by Alice while offline` (step 3) and `Queued by Bob while offline` (step 4); fixture ids in protocol Appendix A.
- **Login.** Works offline (local); invalid names never reach the server (CORE-NAME-005); names show in lowercase. Re-login with any casing is the same user. Logout is not in the brief. If the PM adds it, the PM must say what local data is cleared.
- **Composer.** Blank text and text over 4096 UTF-8 bytes are rejected locally and never enter the outbox (CORE-TEXT-004). Text is shown exactly as typed.
- **Server restart.** A new epoch clears sent/received history on clients but keeps pending messages (CORE-EPOCH-004). The PM should state what the user sees.
- **Still the PM's to define:** conversation list contents and order (suggest: one item per peer with any stored message, ordered by its latest message by CORE-SEQ-002, newest first); how a conversation is started (`new-conversation-*` hooks); whether the offline toggle persists across restarts (suggest: not persisted, default off, which keeps tests deterministic); display of `created_at` (informational only).
- **Unknown types** (future extensions) are invisible in core clients (CORE-EXT-002); scenarios for extensions come with P6.

## (e) Changes after PM review

Input: `docs/planning/g0-review-pm.md` §(d) and §(e), `spec/core/client-behavior.md`, `spec/scenarios/*`. Ids are stable; nothing was renumbered. Spec stays `0.1.0-draft`.

| PM item | Change | Where |
|---|---|---|
| d.1a/b: hooks for `Back` and the invalid-recipient message | Added `conversation-back` and `new-conversation-error`. Without them SC-2 navigation and SX-4 step 3 cannot be driven. | `test-hooks.md` PLAT-HOOK-001 table |
| d.1c: conversation order readable | PLAT-HOOK-002 now also covers `conversation-item-<peer>` inside `conversation-list`, in rendered order (CORE-VISIBLE-003). | `test-hooks.md` |
| d.1d: author readable | Included, because the snapshot already has `from`. Web exposes `data-from`; Android `stateDescription` is now `"<state>;<seq>;<from>"`, e.g. `sent;3;alice`. The snapshot schema is unchanged. | PLAT-HOOK-004, PLAT-WEB-012, PLAT-ANDROID-016 |
| d.2: header on both screens | New PLAT-HOOK-010: `current-user`, `connection-status` and `offline-toggle` live in the header on every screen after login and never on the login screen. | `test-hooks.md` |
| d.3: relaunch with storage kept | New PLAT-HOOK-011 (semantics: in-memory state dropped, storage kept, switch back off, network override dropped). Web: page reload or `window.__AWARE__.relaunch()` (PLAT-WEB-018). Android: `am force-stop` + `am start` (PLAT-ANDROID-025). In-project tests: a new engine over the same store. | platform files |
| d.4: count requests per client | **Not done the way the coordinator recommended.** I chose a per-client counting proxy owned by `tests/`; the server gets no test endpoint and CORE-SRV-007 stays `SHOULD`. Reason: the server cannot attribute `/info`, `/users` or requests rejected before parsing to a client, and those are exactly the requests a buggy offline client might make. The new rule PLAT-HOOK-012 (every request goes to the one configured base URL) is what makes the proxy dependable. | decision 0010, PLAT-HOOK-012, note under CORE-SRV-007 |
| d.5: spec index | `client-behavior.md` and both scenario files are listed as draft, with rule and AC counts produced by a script; the id table names AC and scenario ids as PM-owned. | `spec/README.md` |
| d.6: Android interop driver | Unchanged: still G0 Q5, rule to be added at P3 if approved. | — |
| d.8: label texts in platform tests | Confirmed: component tests assert texts exactly as in `client-behavior.md` §8.1; platform files define no texts. | PLAT-ANDROID-022, PLAT-WEB-015 |
| e: enqueue order of failed messages | New CORE-OUTBOX-006: the enqueue number is assigned once, persisted with the message, kept when the message becomes `failed`, and never reused. | `protocol.md` §10 |
| e: failed messages and epoch reset | New CORE-EPOCH-006: an epoch reset keeps `failed` messages and their order; they are not re-sent. This matches CORE-VISIBLE-008. | `protocol.md` §4 |
| d.7 / e: text refused for forbidden characters (CORE-TEXT-003) | Stated in a non-normative note that the visible text is client behavior owned by the PM spec, that none is defined yet, and that no AC covers it until the operator decides. **New operator question Q8:** adopt the PM's proposed text (`Message contains characters that cannot be sent.`) or leave it undefined. Recommendation: adopt it; it costs one row in §8.1 and one AC. | `protocol.md` §6 |

Not changed: "`online` precedes flush" and the unobservable transient in step 7. Both are as designed (CORE-CONN-006); the PM documented them correctly.

## (f) Changes after the operator decision on times (OM-0010)

Branch `spec/tl-time`. The PM writes the visible behavior (format `HH:mm` / `YYYY-MM-DD HH:mm`, nothing shown while pending) in parallel; this delta holds only the technical part. Decision record: 0012.

| Change | Where |
|---|---|
| New CORE-TIME-001: every instant is UTC `…Z` (wire, store, snapshot, fixtures); clients store `accepted_at`; conversion to local time only for display text | `protocol.md` §5.1 |
| New CORE-TIME-002: zone from the `TimeZone` provider and "now" from the `Clock`, read at each display; offset taken at the instant; seconds truncated; "today" = local date of "now" | `protocol.md` §5.1 |
| CORE-ENV-006/007 wording: clocks are explicitly UTC (no change in meaning, ids unchanged) | `protocol.md` §5 |
| Appendix A: fixed `accepted_at` for A1, B1, A2, B2 and a "Displayed times" table for Alice at UTC−03:00 (`America/Sao_Paulo`) and Bob at UTC+09:00 (`Asia/Tokyo`), at N1 = `2026-10-13T15:00:10.000Z` and N2 = one day later. The PM's SX-6 can cite it. | `protocol.md` Appendix A |
| `TimeZone` port added to the injected dependencies | PLAT-HOOK-009 |
| Hook `message-time-<id>` (absent without `seq`); snapshot messages gain `accepted_at` and `time_text` | PLAT-HOOK-001 table, PLAT-HOOK-013, `client-snapshot.schema.json` |
| Android: `java.time` default provider; text built by hand, no locale formatters; emulator `-timezone`; generated tests | PLAT-ANDROID-026..028 |
| Web: `Date#getTimezoneOffset` default provider; text built by hand with `getUTC*`, no `toLocale*`/`Intl` formatting; Playwright `timezoneId` + `page.clock` for external tests; generated tests | PLAT-WEB-019..021 |

Notes for the operator and PM:
- The displayed time is the server's acceptance time, not the time the message was typed. It is the only choice consistent with display order (decision 0012).
- The two users can see different dates for the same message. In Appendix A, Bob's `00:00` falls on the next day.
- Whether the list re-renders on its own at local midnight or when the zone changes is a PM behavior choice. The protocol only guarantees that the next display uses the current zone and "now".
- Schema examples are unchanged: no wire format changed.
