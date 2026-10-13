# 0014 — Plain polling, no `failed` state, tests without proxy or Android provider
- Status: accepted (operator, OM-0011)
- Date: 2026-10-13
- Author: TL (agent, claude-opus-5-5). The operator accepted the MVP cuts in OM-0011; the cut list is decision 0013 (ORC). This record covers how the technical cuts change the protocol and platform rules.
- Amends: 0004 (long-poll), 0006 and 0007 (`failed` state), 0009 (connection cycle, backoff, abort on offline). Supersedes: 0010 (counting proxy).
- Spec ids driven: `CORE-HTTP-007`, `CORE-SESSION-003`, `CORE-EPOCH-005`, `CORE-ENV-006`, `CORE-TIME-003`, `CORE-MSG-006`, `CORE-POLL-001`, `-002`, `-005`, `CORE-SEQ-002`, `CORE-CONN-003`..`-009`, `CORE-OUTBOX-003`..`-006`, `CORE-CAP-001`, `CORE-ERR-002`, `CORE-ERR-003`, `CORE-CONST-001`, `CORE-SRV-003`, `-004`, `-030`, `-031`, `-033`, `-037`, `PLAT-HOOK-006`, `-009`, `-014`, `-015`, `PLAT-ANDROID-004`, `-009`, `-025`, `-027`, `-029`..`-035`, `PLAT-WEB-006`, `-022`..`-025`

## Context
The operator wants the smallest MVP that still meets the brief, and each client build needs the operator at the keyboard (decision 0011). Four parts of the G0 spec cost a lot of generated code and test effort for little value in a local demo:
- **Long-poll with backoff.** Held requests, a server waiter list, request timeouts that depend on `wait`, exponential backoff, and cancelling in-flight requests on going offline. Generated concurrency code goes wrong first in exactly these places (TL G0 packet, risks).
- **The `failed` message state.** Clients validate names and texts before queueing, so a correct client never reaches it. It still needed a visible look, an order rule, an epoch-reset rule and tests on both clients.
- **The counting proxy (0010) and the Android debug `ContentProvider`.** Both exist only for external tests. Android external tests also needed an emulator, which is optional (decision 0002 Q19).
- **Rule coverage as a gate.** A passing test for every `MUST` id on two platforms is a large test volume with no extra product value over the acceptance criteria.

## Decision
1. **Plain polling.** `GET /v1/mailboxes/{name}/messages` answers at once with what qualifies at that moment. The `wait` parameter, held polls, `POLL_WAIT_S`, `POLL_WAIT_MAX_S`, `POLL_TIMEOUT_MARGIN_MS` and the server waiter rules are gone. Every request uses `REQUEST_TIMEOUT_MS`.
2. **One fixed loop on the client.** One constant, `CYCLE_INTERVAL_MS = 1000`. While allowed, the client runs cycles: session if needed → poll until `has_more` is false → flush the outbox FIFO with one send in flight → cycle ends. The next cycle starts `CYCLE_INTERVAL_MS` after the previous one ended, so requests never overlap. Any failed request ends the cycle; the next one starts after the same interval and begins with a session. There is no backoff growth and no jitter. A cycle also starts at once when the client becomes allowed.
3. **Connection state.** `online` = allowed, and a session followed by a poll has succeeded since the client last became allowed or since the last failed request, whichever is later. `connecting` = allowed and not `online`. `offline` = not allowed. When the indicator shows `online`, the client has caught up at least once in the current period.
4. **Offline means no new request.** While not allowed, the client starts no request and no cycle. A request already in flight is not cancelled. It completes or times out, and its result is applied as usual (store, then cursor; ack by id). This is safe because every result is idempotent by `id` and `seq`. It replaces "abort and discard".
5. **No `failed` state.** Message states are `pending`, `sent`, `received`. A permanent rejection of a queued message (class P) removes it from the outbox and from local storage, writes one diagnostic log line (id, code), and the flush continues with the next entry. The outbox never blocks.
6. **Tests without proxy or provider.** In-project tests prove "offline = zero requests" with a recording fake `Transport` (PLAT-HOOK-014). External web tests count requests with Playwright's own request events. Android is driven externally by a generated JVM command-line driver, `:tools:driver`, over `:core:protocol` + `:core:network`. It prints the same snapshot JSON as the UI hook. This settles TL G0 question Q5 with option (b), without an emulator. The web `window.__AWARE__` hook and the Android test tags stay; they serve in-project UI tests and Playwright.
7. **Rule coverage is reported, not gated.** Acceptance criteria gate acceptance (`spec/README.md`).
8. **Withdrawn rules stay as tombstones.** Ids are never reused or renumbered. A withdrawn rule keeps one line, `- **<id>** — Withdrawn (decision 0014).`, with no RFC 2119 keyword.

### Withdrawn ids
`CORE-EPOCH-006` (epoch reset keeps `failed` messages) · `CORE-SRV-012`, `CORE-SRV-013`, `CORE-SRV-014` (held polls) · `PLAT-HOOK-012` (single base URL for a counting proxy) · `PLAT-ANDROID-017` (debug `ContentProvider`).

### Reworded ids (same id, changed meaning)
`CORE-SESSION-003` (session only when needed) · `CORE-EPOCH-005` (`409` handled like any failure) · `CORE-MSG-006` (three states) · `CORE-POLL-001`, `-002` (no `wait`) · `CORE-POLL-005` (answer at once, never hold) · `CORE-SEQ-002` (no `failed`) · `CORE-CONN-003` (`online` after session and poll) · `CORE-CONN-004` (no new request; in-flight request completes and is applied) · `CORE-CONN-005` · `CORE-CONN-006` (cycle steps, no live step) · `CORE-CONN-007` (fixed interval, never overlapping) · `CORE-CONN-008` (fixed retry, no backoff) · `CORE-CONN-009` (one timeout) · `CORE-OUTBOX-003`, `-004`, `-005` (class P removes and logs), `-006` · `CORE-CAP-001` (no `poll_wait_max_s`) · `CORE-ERR-003` (two classes: R and P) · `CORE-SRV-003`, `-004`, `-033` (no waiters) · `PLAT-HOOK-001` (no `failed` value), `-006` (Android mechanism), `-009` (`Scheduler` for the interval; new `DiagnosticLog` port) · `PLAT-ANDROID-004` (module list adds `:tools:driver`), `-009`, `-025`, `-027`, `-028` · `PLAT-WEB-006`, `-021`.

## Alternatives considered
- **Keep long-poll, drop only backoff.** Latency would stay near zero, but held requests, waiters and the abort rule would stay too, and those are the expensive parts. Rejected.
- **Exponential backoff with plain polling.** It protects a server under load. A local single-user server needs no protection, and a fixed interval keeps tests and clients identical. Rejected.
- **Trigger a cycle as soon as a message is queued.** It saves up to one second of latency but adds a second trigger and timing races between triggers. Rejected; the user sees `Pending` for at most about one interval.
- **Abort in-flight requests on going offline (as before).** Both clients would need cancellation plumbing, and discarded responses would make "sent or not" depend on timing. Letting the request finish is simpler and safe by idempotency. Rejected.
- **Keep `failed` as a visible dead letter.** It needs a look, an order rule, an epoch rule and tests on two platforms, for a path a correct client never reaches. Rejected.
- **Keep the counting proxy for Android.** Without an emulator there is no Android UI to put behind it, and the driver can count its own `Transport` calls at the boundary. Rejected.
- **Emulator plus UI Automator for Android interop.** It needs an emulator on every grading machine and adds flaky timing. Rejected for the gate; it can still be run manually.

## Consequences
- Latency is up to about one `CYCLE_INTERVAL_MS` plus request time for receiving and for sending a message queued while online. An idle client makes one poll per second. Both are fine for a local demo.
- The server is simpler: no waiter list and no concurrency needed for held requests. It still serves requests concurrently, so one slow connection cannot stall the others.
- The request sequence depends on timing. Tests wait on states (snapshot) instead of counting cycles. Appendix A shows the cycles that change state; idle cycles are summarised.
- **A defective client can silently drop a message:** a permanent rejection removes the message without any visible trace. The only trace is one diagnostic log line. This is accepted because local validation makes the path unreachable for a correct client against a correct server. The in-project tests cover the removal and the log line.
- "Offline = zero requests" is proven in-project on both platforms and externally on web. On Android the driver reports its own `Transport` call count; this is weaker than an independent proxy (0010 rejected client-side counting for that reason), but it counts at the `Transport` boundary, outside the engine.
- External interop pairings shrink to web↔web through the UI and Android driver (Alice) ↔ web UI (Bob). The PM lists them.
- PM-owned rules and scenarios that cite the withdrawn or reworded ids must follow (TL report for this delta).

## Brief constraint affected
Required behavior 3 (queue and flush) is unchanged in effect. The brief's scenario is still fully specified (Appendix A).
