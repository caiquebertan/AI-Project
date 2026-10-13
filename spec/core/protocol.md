# Core protocol (skeleton)

_To be written._ Must define, unambiguously:

1. **Transport** — (decide: WebSocket vs HTTP) and endpoint(s).
2. **Identity** — how a client announces its user name; uniqueness rules; case handling.
3. **Message envelope** — fields (id, from, to, text, client timestamp, server sequence?), JSON schema.
4. **Send / ack** — what the server returns and when a client may treat a message as sent.
5. **Receive / delivery** — how queued messages are delivered to a reconnecting recipient; ordering guarantee.
6. **Idempotency** — duplicate handling (e.g. dedupe by message id).
7. **Capability negotiation** — hook for extensions.
8. **Errors** — unknown recipient, malformed message.
