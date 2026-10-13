# 0007 — Delivery, acknowledgement and dedupe
- Status: proposed (awaiting G0)
- Date: 2026-10-13
- Author: TL (agent, claude-opus-5-5); dedupe principle decided by operator (Phase 1 launch brief)
- Spec ids driven: `CORE-MSG-*`, `CORE-DEDUPE-*`, `CORE-CURSOR-*`, `CORE-SRV-030`..`CORE-SRV-036` — in [`spec/core/protocol.md`](../../spec/core/protocol.md) and [`spec/core/server-behavior.md`](../../spec/core/server-behavior.md)

## Context
Requests can be lost in both directions: the offline toggle aborts in-flight requests, a send may be accepted by the server while its response is lost, and a client may crash between receiving and storing. The operator fixed the principle: client-generated ids, at-least-once delivery, idempotent handling by id. This record fixes the exact semantics, and what the server does with recipients it has never seen.

## Decision
1. **Send ack.** A message is acknowledged (`sent`) only when the client receives `201` or `200` from `POST /v1/messages` with a `seq`. Nothing else (timeouts, aborted requests) counts as an ack.
2. **Retry is identical.** Until acked, the client re-sends the byte-for-byte same envelope field values (same `id`, `created_at`, text).
3. **Server idempotency.** If an envelope with the same `id` was already accepted in this epoch: identical fields → `200` with the **original** `seq` and `accepted_at`, nothing stored again; any field different → `409 id_conflict`.
4. **Receive is at-least-once.** The client stores received envelopes and only then advances its cursor. Re-delivered envelopes are dropped by `id`.
5. **Recipients are not checked.** The server accepts envelopes to any syntactically valid name and creates the mailbox on first use. When the recipient later polls, the envelopes are there. The sender must be registered in the current epoch.
6. **Retention:** the server keeps every accepted envelope for its whole lifetime (in memory); there is no deletion or ack endpoint.
7. **No delivery/read receipts in core.** They are a client-only extension candidate (0008).

## Alternatives considered
- **Reject unknown recipients (`404`).** Catches typos, but creates a permanent-failure path for messages queued offline, and makes test order matter (Bob must log in before Alice's first send). It also fails after a server restart until the recipient re-registers. Kept as an operator open question (G0 packet Q1).
- **Server-side dedupe by content.** Would drop legitimate repeated texts ("ok", "ok"). Rejected.
- **Exactly-once via ack endpoint.** More round-trips and server state; the id makes it unnecessary.
- **Bounded retention.** Not needed for a local in-memory demo; would add an "expired" state.

## Consequences
- The `failed` state is reachable only through client bugs or a server that violates the spec (clients validate name and text before queueing). It is still defined so both clients behave identically if it happens.
- Mailboxes grow for the whole server lifetime: fine for a demo, noted in FUTURE.
- A typo in a recipient name sends into a mailbox nobody reads; the client can warn using `GET /v1/users` (behavior is the PM's call).

## Brief constraint affected
None.
