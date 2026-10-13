# 0004 — Transport: HTTP + long-poll, per-recipient cursor, server epoch
> **Amended by 0014:** long-poll is replaced by plain polling. `GET /v1/mailboxes/{name}/messages` answers at once and has no `wait` parameter; `POLL_WAIT_S` and `POLL_WAIT_MAX_S` are gone, and the client polls once per cycle every `CYCLE_INTERVAL_MS` (1000 ms). Going offline no longer aborts the in-flight request. Decision point 3 and the long-poll consequences below are history.
- Status: proposed (awaiting G0)
- Date: 2026-10-13
- Author: TL (agent, claude-opus-5-5); decided-in-principle by operator (gap-analysis Q20, decision 0002)
- Spec ids driven: `CORE-HTTP-*`, `CORE-POLL-*`, `CORE-CURSOR-*`, `CORE-EPOCH-*`, `CORE-CONST-001`, `CORE-SRV-010`..`CORE-SRV-016` — in [`spec/core/protocol.md`](../../spec/core/protocol.md) and [`spec/core/server-behavior.md`](../../spec/core/server-behavior.md)

## Context
The operator chose HTTP REST with polling / long-poll and a per-recipient cursor (Q20): it maps directly onto Retrofit + coroutines (Android) and `fetch` + `AbortController` (web), needs no extra library, and is trivial to drive from Python tests. What remained open: exact endpoints, what the cursor is, who stores it, how long a poll waits, and what happens when the in-memory server restarts (every test run restarts it while clients keep local storage).

## Decision
1. JSON over HTTP/1.1, all paths under `/v1`. Five endpoints: `GET /v1/info`, `POST /v1/session`, `POST /v1/messages`, `GET /v1/mailboxes/{name}/messages`, `GET /v1/users`.
2. Every recipient has a **mailbox**: the ordered list of envelopes addressed to them. The **cursor** is the `seq` (see 0006) of the last envelope the client has durably stored from its own mailbox. The cursor is **held by the client**, persisted locally, and sent as `after=<cursor>` on each poll. The server keeps no per-client read state and never deletes envelopes; reading is side-effect free.
3. Long-poll: the client asks with `wait=POLL_WAIT_S` (20 s); the server answers at once when anything with `seq > after` exists, otherwise holds the request until an envelope arrives or `wait` elapses (clamped to `POLL_WAIT_MAX_S` = 30 s), then answers `200` with an empty list. `wait=0` is a plain poll (used for catch-up).
4. The server generates a random **epoch** at start. `POST /v1/session` returns it; every later request carries `epoch=<value>` as a query parameter; a mismatch is `409 epoch_mismatch`. A client that sees a new epoch discards its server-derived local state (cursor, sequenced messages) and keeps its identity and outbox.
5. All timing numbers are named constants in one table (`spec/core/protocol.md` §13, mirrored in `spec/core/schema/constants.json`).

## Alternatives considered
- **WebSocket push.** Lower latency, but adds a second state machine (socket lifecycle) to specify for two clients and complicates the offline toggle. Rejected by the operator for core; possible later as an extension that reuses the same cursor.
- **Server-held cursor (server marks envelopes delivered/acked).** Requires an ack endpoint and per-device state; breaks when two devices use the same name; makes reads destructive, so tests cannot inspect mailboxes. Rejected.
- **Short polling only.** Simpler, but either slow (seconds of latency in interop tests) or chatty. Long-poll costs one extra rule.
- **No epoch.** A restarted server restarts `seq` at 1; a client holding cursor 7 would silently miss envelopes 1–7. Rejected: the epoch costs one field and one rule.

## Consequences
- The client owns delivery progress; at-least-once receive follows from "advance the cursor only after storing" (0007).
- Long-polls hold a server thread each: the server must serve requests concurrently (`CORE-SRV-003`).
- Going offline must abort the in-flight long-poll (0009).
- A server restart visibly clears conversation history on clients (the server is the source of history). The PM must reflect this in behavior.

## Brief constraint affected
None. Local only, no third-party services; general HTTP/JSON libraries only.
