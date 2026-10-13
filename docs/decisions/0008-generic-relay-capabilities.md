# 0008 — Generic relay and capability negotiation
- Status: proposed (awaiting G0)
- Date: 2026-10-13
- Author: TL (agent, claude-opus-5-5); relay principle decided by operator (gap-analysis Q21, decision 0002)
- Spec ids driven: `CORE-ENV-*`, `CORE-TEXT-*`, `CORE-CAP-*`, `CORE-EXT-*`, `CORE-SRV-040`..`CORE-SRV-042` — in [`spec/core/protocol.md`](../../spec/core/protocol.md) and [`spec/core/server-behavior.md`](../../spec/core/server-behavior.md)

## Context
The brief grades "Evolution": attachments, reactions, group conversations, protocol extensions must be addable by writing spec, not by rewriting the harness. The operator chose a generic relay so that client-only extensions need no server change (Q21). This record fixes the envelope shape, the core type, unknown-type handling and how clients learn about capabilities.

## Decision
1. **Envelope** = `{id, from, to, type, payload, created_at}` on send; the server adds `seq` and `accepted_at` on delivery. The envelope is **closed**: no other top-level fields. Extensions put everything inside `type` + `payload`.
2. **Core defines one type: `text`**, payload `{ "text": <string> }`. The server validates payloads of core types only. Every other `type` is relayed opaquely: stored, sequenced and delivered through the same mailbox and cursor, never inspected.
3. **Type names:** `^[a-z][a-z0-9_.-]{0,63}$`. Core types have no dot. Extension types are `<capability-id>.<name>` (for example `reactions.add`).
4. **Unknown types on clients:** a client that does not implement a `type` ignores it (not displayed, not an error) but still advances its cursor past it. A client sends only types it implements.
5. **Capabilities.** A client declares the extension capability ids it implements in `POST /v1/session` (`capabilities`; `[]` for a core-only client). `GET /v1/users` returns each user's last declared list; `GET /v1/info` returns the server's own `server_capabilities` (`[]` in v1) and limits. Clients may use peer capabilities to hide UI for features the peer lacks; senders never need to (unknown types are ignored).
6. **Requests strict, responses tolerant:** the server rejects unknown fields in requests; clients ignore unknown fields in responses, so the server can add response fields without breaking old clients.

## Alternatives considered
- **Open envelope (extensions add top-level fields).** The server would have to preserve unknown fields and clients would have to agree on where they go; two places to evolve. Rejected.
- **Typed server (server knows every message type).** Every extension becomes a server change and a server test change. Rejected by the operator.
- **Fallback text for unknown types.** Useful for attachments ("[photo]"), noisy for reactions. Rejected for core; an extension may define its own fallback by also sending a `text` envelope if it wants old clients to see something.
- **Per-request capability negotiation headers.** More moving parts than one list per user.

## Consequences
- Reactions, receipts, typing indicators, edits: **client-only** extensions; zero server change.
- Group conversations and attachments **do** need server capabilities (fan-out by group membership; blob storage). They extend the server under a new `server_capabilities` id without changing the core envelope. The spec README says so honestly.
- Malicious or buggy payloads of unknown types are delivered as-is; clients must parse defensively (`CORE-EXT-004`).

## Brief constraint affected
"Evolution" signal: this is the mechanism that answers it.
