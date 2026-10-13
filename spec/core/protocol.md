# Core protocol

- **Status:** draft for G0 (spec 0.1.0-draft). Owner: TL. Decisions: [`docs/decisions/0004`–`0009`](../../docs/decisions/).
- **Scope:** the wire contract between any client and the server, plus the client obligations that are visible on the wire (request order, retries, cursor, ordering key). Visible UI behavior (screens, labels, what the user sees at each step) is in [`client-behavior.md`](client-behavior.md) (PM). Server internals are in [`server-behavior.md`](server-behavior.md).
- **Platform-neutral:** nothing here names a language, library or OS. Platform rules are in [`../platform/`](../platform/).
- **Machine-readable contract:** [`schema/`](schema/) (JSON Schema per request/response, [`schema/index.json`](schema/index.json) maps endpoints to schemas, [`schema/constants.json`](schema/constants.json) holds §13). Prose and schema are both normative; a contradiction between them is a spec defect (return `SPEC_ISSUE`), not a choice for the implementer.
- **Keywords:** MUST / MUST NOT / SHOULD / MAY as in RFC 2119. Each normative rule has an id `CORE-<AREA>-NNN`; ids are never reused or renumbered.

Contents: 1 Transport · 2 Names and identity · 3 Session · 4 Epoch · 5 Envelope · 6 Core type `text` · 7 Send and ack · 8 Poll and receive · 9 Order · 10 Connection and outbox (client) · 11 Capabilities and extensions · 12 Errors · 13 Constants · Appendix A: Alice/Bob trace · Appendix B: an extension riding the envelope.

---

## 1. Transport

- **CORE-HTTP-001** — Client and server MUST communicate over HTTP/1.1; every request and response body MUST be a single JSON value encoded as UTF-8.
- **CORE-HTTP-002** — All endpoints MUST live under the path prefix `/v1`; the base URL (scheme, host, port) is configuration, never hard-coded in core (see platform files).
- **CORE-HTTP-003** — Requests with a body MUST carry `Content-Type: application/json` (a `charset=utf-8` parameter is allowed); responses with a body MUST carry `Content-Type: application/json; charset=utf-8`.
- **CORE-HTTP-004** — Request bodies MUST NOT contain fields other than those in their schema; the server MUST reject such requests with `400 malformed_request`.
- **CORE-HTTP-005** — Clients MUST ignore response fields they do not know (so the server may add fields within `/v1`).
- **CORE-HTTP-006** — Unknown query parameters MUST be ignored by the server.
- **CORE-HTTP-007** — Timestamps MUST be UTC strings in the exact form `YYYY-MM-DDTHH:MM:SS.sssZ` (millisecond precision, literal `Z`).

### Endpoints

| Id | Method and path | Request | Success | Errors (§12) |
|---|---|---|---|---|
| E1 | `GET /v1/info` | none | `200` info-response | `405` |
| E2 | `POST /v1/session` | session-request | `200` session-response | `400` `413` `415` |
| E3 | `POST /v1/messages?epoch=<epoch>` | send-request | `201` send-response (new), `200` send-response (duplicate) | `400` `403` `409` `413` `415` |
| E4 | `GET /v1/mailboxes/<name>/messages?epoch=<epoch>&after=<cursor>&wait=<s>&limit=<n>` | none | `200` poll-response | `400` `409` |
| E5 | `GET /v1/users` | none | `200` users-response | `405` |

Any other path returns `404 not_found`; a known path with another method returns `405 method_not_allowed`. Schema file names: [`schema/index.json`](schema/index.json).

## 2. Names and identity

- **CORE-NAME-001** — A user name MUST match `^[A-Za-z0-9_-]{1,32}$` (ASCII letters, digits, `_`, `-`; 1 to 32 characters). Anything else is invalid; there is no trimming or other normalization.
- **CORE-NAME-002** — Names MUST be compared case-insensitively. The canonical form of a name is its ASCII lowercase (`A`–`Z` mapped to `a`–`z`, nothing else changed).
- **CORE-NAME-003** — The server MUST canonicalize every name it receives (body fields and path segments) before using it, and every name it emits MUST be canonical.
- **CORE-NAME-004** — A client MUST store its identity in canonical form and MUST send only canonical names (`from`, `to`, path `<name>`).
- **CORE-NAME-005** — A client MUST validate a name with CORE-NAME-001 locally; logging in MUST NOT require a server round-trip (login works offline; registration happens in the connection cycle, §10).
- **CORE-NAME-006** — Names are not exclusive: any client that claims a name MUST be treated by the server as that user (no authentication, brief "no security").

## 3. Session (E2)

Request `{"name": "<name>", "capabilities": ["<capability-id>", ...]}`; response `{"name": "<canonical>", "epoch": "<epoch>", "new_user": <bool>}`.

- **CORE-SESSION-001** — `POST /v1/session` MUST register the canonical name if unknown in the current epoch (`new_user: true`) and MUST succeed with `200` for a name already registered (`new_user: false`); it is idempotent.
- **CORE-SESSION-002** — `capabilities` MUST be present (possibly empty), contain unique ids matching `^[a-z][a-z0-9-]{0,31}$`, at most 32 entries; each session call MUST replace the user's stored list.
- **CORE-SESSION-003** — A client MUST call `POST /v1/session` as the first request of every connection cycle (§10) and MUST NOT send or poll in that cycle before it succeeds.
- **CORE-SESSION-004** — The `name` in the response MUST equal the client's stored canonical identity; a client MUST treat any other value as a failed request of class R (§12).

## 4. Epoch

The epoch identifies one lifetime of the in-memory server. `seq` values and mailboxes are only meaningful within one epoch.

- **CORE-EPOCH-001** — The server MUST generate a new epoch at start: 16 lowercase hex characters from a random source (`^[0-9a-f]{16}$`), constant until the process exits.
- **CORE-EPOCH-002** — Every E3 and E4 request MUST carry the client's current epoch as query parameter `epoch`; missing or malformed → `400 malformed_request`; different from the server's → `409 epoch_mismatch`.
- **CORE-EPOCH-003** — A client MUST persist the epoch from its last successful session together with its cursor.
- **CORE-EPOCH-004** — When a session response carries an epoch different from the stored one (or there is none stored), the client MUST perform an epoch reset before any other request: delete all locally stored messages that have a `seq` (states `sent` and `received`), set the cursor to `0`, store the new epoch. Identity and outbox (`pending` messages) MUST be kept.
- **CORE-EPOCH-005** — On `409 epoch_mismatch` a client MUST end the current cycle and start a new one at once (session first, no backoff); a second consecutive `409 epoch_mismatch` MUST be handled as retryable (class R, §12).
- **CORE-EPOCH-006** — An epoch reset MUST keep `failed` messages unchanged (they have no `seq`), with their enqueue order (CORE-OUTBOX-006); they are not re-sent (CORE-OUTBOX-005).

## 5. Envelope

Send form (E3 body): `{"id", "from", "to", "type", "payload", "created_at"}`. Delivered form (E4): the same plus `"seq"` and `"accepted_at"`. Schemas: `send-request.schema.json`, `envelope.schema.json`.

- **CORE-ENV-001** — The send form MUST contain exactly the fields `id`, `from`, `to`, `type`, `payload`, `created_at`; the delivered form MUST contain exactly those plus `seq` and `accepted_at`.
- **CORE-ENV-002** — `id` MUST be generated by the sending client at compose time as a random UUID version 4 in lowercase canonical text form, matching `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`; it never changes for that message.
- **CORE-ENV-003** — `from` MUST be the sender's canonical name and `to` the recipient's canonical name (CORE-NAME-001); `to` MAY equal `from` (a note to self).
- **CORE-ENV-004** — `type` MUST match `^[a-z][a-z0-9_.-]{0,63}$`. Core types contain no `.`; extension types MUST be `<capability-id>.<name>` (§11).
- **CORE-ENV-005** — `payload` MUST be a JSON object; its shape is defined by `type` (core: §6; extensions: their own spec).
- **CORE-ENV-006** — `created_at` MUST be the sender's clock at compose time (CORE-HTTP-007); it is informational only and MUST NOT influence order, dedupe or validity beyond its format.
- **CORE-ENV-007** — `seq` (integer ≥ 1) and `accepted_at` (server clock, CORE-HTTP-007) MUST be assigned by the server when it first accepts the envelope and MUST be identical in every later response or delivery of that envelope.

## 6. Core type `text`

- **CORE-TEXT-001** — An envelope with `type` `text` MUST have payload exactly `{"text": <string>}`.
- **CORE-TEXT-002** — `text` MUST contain at least one character outside the set {U+0009, U+000A, U+000D, U+0020}; an empty or blank text is invalid.
- **CORE-TEXT-003** — The UTF-8 encoding of `text` MUST be at most `TEXT_MAX_BYTES` (4096) bytes, and `text` MUST NOT contain U+0000 or unpaired surrogates.
- **CORE-TEXT-004** — Clients MUST validate CORE-TEXT-002 and CORE-TEXT-003 before putting a message in the outbox and MUST NOT enqueue an invalid text.
- **CORE-TEXT-005** — `text` MUST be transmitted, stored and displayed exactly as composed (no trimming, case change or Unicode normalization by client or server).

Ownership note (non-normative): what the user sees when the client refuses a text under CORE-TEXT-003 because of forbidden characters (U+0000, unpaired surrogates) is client behavior, owned by [`client-behavior.md`](client-behavior.md) (PM). No such text is defined yet and no acceptance criterion covers it until the operator decides (TL G0 packet, "Changes after PM review"); the refusal itself (CORE-TEXT-004) applies regardless.

## 7. Send and ack (E3)

Response `{"id", "seq", "accepted_at", "epoch"}` (`send-response.schema.json`).

- **CORE-MSG-001** — The server MUST answer a newly accepted envelope with `201` and a duplicate of an accepted one (same `id`, all fields equal) with `200`, both with the original `seq` and `accepted_at`.
- **CORE-MSG-002** — The server MUST reject a send whose `from` has not called E2 in the current epoch with `403 unknown_sender`.
- **CORE-MSG-003** — The server MUST NOT reject a send because `to` is unknown: it MUST accept any valid `to` and keep the envelope in that name's mailbox (decision 0007).
- **CORE-MSG-004** — A client MUST treat a message as acknowledged (state `sent`, with `seq`) only on a `200` or `201` E3 response whose `id` equals the sent `id`; a timeout, network error or aborted request MUST NOT count as an ack.
- **CORE-MSG-005** — A client re-sending an unacknowledged message MUST send identical field values (same `id`, `from`, `to`, `type`, `payload`, `created_at`).

### Message states (client, wire-relevant)

| State | Meaning | Has `seq` |
|---|---|---|
| `pending` | in the outbox, not acknowledged | no |
| `sent` | acknowledged by E3 (or seen in own mailbox, CORE-DEDUPE-004) | yes |
| `received` | delivered by E4 from another user | yes |
| `failed` | rejected with a non-retryable error (class P, §12) | no |

- **CORE-MSG-006** — A client MUST give every local message exactly one of the states `pending`, `sent`, `received`, `failed`, with the meanings in the table above; the PM's behavior spec defines how each is shown.

## 8. Poll and receive (E4)

Query: `epoch` (required), `after` (required, cursor), `wait` (seconds, default `0`), `limit` (default and maximum `POLL_LIMIT_MAX`). Response `{"epoch", "messages": [<delivered envelope>...], "next_cursor", "has_more"}` (`poll-response.schema.json`).

- **CORE-POLL-001** — `after`, `wait` and `limit` MUST be decimal integers matching `^(0|[1-9][0-9]{0,15})$`; otherwise, or if `limit` is `0`, the server MUST answer `400 malformed_request`.
- **CORE-POLL-002** — The server MUST clamp `wait` to `POLL_WAIT_MAX_S` and `limit` to `POLL_LIMIT_MAX` (values above are treated as the maximum, not rejected).
- **CORE-POLL-003** — The response MUST list the envelopes in mailbox `<name>` with `seq > after`, in ascending `seq`, at most `limit` of them; `has_more` MUST be true iff more such envelopes exist beyond the returned ones.
- **CORE-POLL-004** — `next_cursor` MUST be the `seq` of the last returned envelope, or `after` unchanged if none is returned.
- **CORE-POLL-005** — If at least one envelope qualifies, the server MUST respond immediately; otherwise it MUST hold the request until an envelope with `seq > after` is added to the mailbox (then respond with it at once) or until `wait` seconds pass (then respond `200` with `messages: []`).
- **CORE-POLL-006** — Polling MUST be side-effect free: it MUST NOT change any server state, so any number of clients or tests MAY read the same mailbox.
- **CORE-POLL-007** — Polling a valid name that has no mailbox yet MUST return `200` with no messages (mailboxes exist implicitly for every valid name).

### Cursor (client)

- **CORE-CURSOR-001** — A client MUST keep one cursor per identity, initially `0`, persisted across restarts together with the epoch.
- **CORE-CURSOR-002** — A client MUST durably store (or deliberately skip, CORE-EXT-002 and CORE-EXT-004) every envelope of a poll response before it persists `next_cursor` as its new cursor.
- **CORE-CURSOR-003** — A client MUST send its persisted cursor as `after`; it MUST NOT move the cursor backwards except by an epoch reset (CORE-EPOCH-004).

### Dedupe (client side; server side is CORE-MSG-001)

- **CORE-DEDUPE-001** — A client MUST identify messages by `id` alone; it MUST NOT create a second local message for an `id` it already holds.
- **CORE-DEDUPE-002** — A received envelope whose `id` is already stored as `received` or `sent` MUST be dropped without any change.
- **CORE-DEDUPE-003** — A `200` duplicate response to a send MUST be processed exactly like `201` (CORE-MSG-004).
- **CORE-DEDUPE-004** — A received envelope whose `id` matches a local `pending` message (a note to self delivered before its ack) MUST mark that message `sent` with the envelope's `seq` and remove it from the outbox.

## 9. Order

One rule decides the order of messages in every view of every client (decision 0006).

- **CORE-SEQ-001** — The server MUST assign `seq` from one counter per epoch, shared by all mailboxes: the first accepted envelope gets `1`, each further newly accepted envelope gets the previous value plus `1`. Duplicates (CORE-MSG-001) and rejected requests MUST NOT consume a value.
- **CORE-SEQ-002** — Clients MUST order messages by this key: messages with a `seq` (`sent`, `received`) first, ascending by `seq`; then messages without a `seq` (`pending`, `failed`), ascending by local enqueue order.
- **CORE-SEQ-003** — Clients MUST NOT use `created_at`, arrival time or any clock to order messages.
- **CORE-SEQ-004** — When a `pending` message is acknowledged it MUST take its position by its new `seq` (it may move above messages received while it was pending).
- **CORE-SEQ-005** — The conversation between canonical users X and Y MUST consist of exactly the stored `text` messages with {`from`, `to`} = {X, Y} (for X = Y, those with `from` = `to` = X), ordered by CORE-SEQ-002.

Consequence (Appendix A): once all messages are acknowledged and delivered, both participants of a conversation hold the same messages in the same order.

## 10. Connection and outbox (client)

The client's network activity is decided by these rules alone, so every client produces the same request sequence for the same inputs (decision 0009). The PM's behavior spec defines how states are shown.

### Offline definition

- **CORE-CONN-001** — A client MUST have an `offline_toggle` (boolean, initially `false`) settable by the user and by test hooks, and MUST obtain `network_available` (boolean) from a replaceable connectivity monitor.
- **CORE-CONN-002** — A client MUST consider itself allowed to contact the server iff `offline_toggle` is `false` and `network_available` is `true`.
- **CORE-CONN-003** — A logged-in client MUST be in exactly one connection state: `offline` (not allowed), `connecting` (allowed, no successful session in the current cycle, or retrying), `online` (allowed, the current cycle's session succeeded and no request has failed since).
- **CORE-CONN-004** — In state `offline` a client MUST NOT issue any HTTP request; on becoming not allowed it MUST abort all in-flight requests and timers and MUST discard any response not yet processed.
- **CORE-CONN-005** — When a logged-in client becomes allowed (start-up, toggle off, network back) it MUST enter `connecting` and start a connection cycle immediately, without backoff.

### Connection cycle

- **CORE-CONN-006** — A connection cycle MUST run these steps in order: (1) E2 session; on success set state `online` (and apply CORE-EPOCH-004 if needed); (2) catch-up: E4 with `wait=0`, repeated with the new cursor while `has_more` is true; (3) flush the outbox until empty (CORE-OUTBOX-003); (4) live: E4 with `wait=POLL_WAIT_S` in a loop, while the outbox is flushed whenever it is non-empty.
- **CORE-CONN-007** — In step 4 the client MUST issue the next E4 immediately after processing the previous response (no delay) and MUST have at most one E4 in flight.
- **CORE-CONN-008** — On a retryable failure (class R, §12) of any request in a cycle the client MUST abort the cycle's other requests, enter `connecting`, wait the backoff delay `min(RETRY_MAX_MS, RETRY_INITIAL_MS × 2^(n−1))` for the n-th consecutive failure (no jitter), then start a new cycle at step 1; n resets to 0 after a successful session.
- **CORE-CONN-009** — Request timeouts MUST be `REQUEST_TIMEOUT_MS` for E1, E2, E3, E5 and `wait × 1000 + POLL_TIMEOUT_MARGIN_MS` for E4; a timeout is a retryable failure.

### Outbox and flush

- **CORE-OUTBOX-001** — Every message a user sends MUST first be appended to a persistent outbox as `pending`, whatever the connection state; there is no other send path.
- **CORE-OUTBOX-002** — The outbox MUST survive app restarts and keep insertion order (the local enqueue order of CORE-SEQ-002).
- **CORE-OUTBOX-003** — Flushing MUST send outbox entries in insertion order, one at a time: the next E3 MUST NOT start before the previous one ended with an ack or a non-retryable error.
- **CORE-OUTBOX-004** — An entry MUST leave the outbox only when acknowledged (→ `sent`) or rejected with a class P error (→ `failed`); on a class R error it stays at the head and the cycle restarts (CORE-CONN-008).
- **CORE-OUTBOX-005** — A `failed` message MUST NOT be retried automatically and MUST NOT block later entries.
- **CORE-OUTBOX-006** — The local enqueue order (CORE-SEQ-002) MUST be a number assigned once when the message enters the outbox, strictly greater than every number assigned before for that identity, persisted with the message, and kept after the message leaves the outbox as `failed`; it is never reused or reassigned.

## 11. Capabilities and extensions

- **CORE-CAP-001** — `GET /v1/info` MUST return `protocol` = `"aware"`, `protocol_version` = `PROTOCOL_VERSION`, the current `epoch`, `core_types` = `["text"]`, `server_capabilities` (`[]` in v1) and `limits` (`text_max_bytes`, `body_max_bytes`, `poll_wait_max_s`, `poll_limit_max`, equal to §13).
- **CORE-CAP-002** — A client MUST declare in E2 `capabilities` exactly the extension capability ids it implements; a core-only client MUST send `[]`.
- **CORE-CAP-003** — `GET /v1/users` MUST list every user registered in the current epoch as `{"name", "capabilities"}`, sorted by `name` ascending (byte order).
- **CORE-CAP-004** — A client MAY use peer capabilities (E5) to decide what to offer in its UI; it MUST NOT require them to send core types.
- **CORE-EXT-001** — The server MUST relay envelopes of any valid `type` the same way: validate the envelope, assign `seq`, store, deliver through E4; it MUST validate payloads only for core types (`text`).
- **CORE-EXT-002** — A client receiving an envelope whose `type` it does not implement MUST NOT display it, MUST NOT report an error, and MUST advance its cursor past it.
- **CORE-EXT-003** — A client MUST only send types it implements (core: `text`; others only with their capability declared in CORE-CAP-002).
- **CORE-EXT-004** — A client receiving an envelope of a type it implements but with an invalid payload MUST skip it like an unknown type (CORE-EXT-002) and MUST NOT stall its cursor.
- **CORE-EXT-005** — An extension MUST NOT change any rule in `spec/core/`; it MAY add types, payload schemas, capability ids, client behavior and (declared through `server_capabilities`) server endpoints. Template: [`../extensions/README.md`](../extensions/README.md).

## 12. Errors

Error body (`error.schema.json`): `{"error": {"code": "<code>", "message": "<human text>"}}`. `message` is free text for logs; clients MUST NOT parse it.

| Status | `code` | When |
|---|---|---|
| 400 | `malformed_request` | body not JSON, schema violation not covered below, unknown request field, bad or missing query parameter |
| 400 | `invalid_name` | a name (body or path) fails CORE-NAME-001 |
| 400 | `invalid_id` | `id` fails CORE-ENV-002 |
| 400 | `invalid_type` | `type` fails CORE-ENV-004 |
| 400 | `invalid_payload` | payload of a core type fails §6, or `payload` is not an object |
| 403 | `unknown_sender` | CORE-MSG-002 |
| 404 | `not_found` | unknown path |
| 405 | `method_not_allowed` | known path, other method |
| 409 | `id_conflict` | same `id` already accepted with different fields |
| 409 | `epoch_mismatch` | CORE-EPOCH-002 |
| 413 | `payload_too_large` | body larger than `BODY_MAX_BYTES` |
| 415 | `unsupported_media_type` | POST without `application/json` |
| 500 | `internal_error` | server bug |

- **CORE-ERR-001** — Every non-2xx response MUST carry the error body with one `code` from the table above and the matching status.
- **CORE-ERR-002** — When several errors apply, the server MUST report the first in this order: `415`, `413`, `malformed_request` (JSON parse, missing or unknown fields, a field of the wrong JSON type, `created_at` or `capabilities` format, query parameters, `epoch` format), `epoch_mismatch`, `invalid_name`, `invalid_id`, `invalid_type`, `invalid_payload`, `unknown_sender`, `id_conflict`.
- **CORE-ERR-003** — Clients MUST classify every outcome of a request into exactly one class and act as follows:

| Class | Outcomes | Client action |
|---|---|---|
| R — retryable | network error, timeout, any `5xx`, `404`, `405`, a second consecutive `409 epoch_mismatch`, and any other `4xx` on E2 or E4 (a client bug; it must never loop faster than the backoff), a CORE-SESSION-004 violation | CORE-CONN-008 |
| S — re-session | `403 unknown_sender`, first `409 epoch_mismatch` | end cycle, start a new cycle at once (CORE-EPOCH-005) |
| P — permanent | on E3 only: `400` (any code), `409 id_conflict`, `413`, `415` | message → `failed` (CORE-OUTBOX-004), flush continues with the next entry |

## 13. Constants

Single normative table; [`schema/constants.json`](schema/constants.json) MUST hold the same values (checked by `generator/scripts/check_schema_examples.py`).

- **CORE-CONST-001** — Implementations MUST use exactly these values; a test that needs shorter waits MUST inject them through the clock / delay ports defined in the platform files, never by changing the production values.

| Name | Value | Used by |
|---|---|---|
| `PROTOCOL_VERSION` | `1` | CORE-CAP-001 |
| `NAME_MAX_LENGTH` | `32` | CORE-NAME-001 |
| `TEXT_MAX_BYTES` | `4096` | CORE-TEXT-003 |
| `BODY_MAX_BYTES` | `65536` | §12 `413` |
| `POLL_WAIT_S` | `20` | CORE-CONN-006 (client long-poll `wait`) |
| `POLL_WAIT_MAX_S` | `30` | CORE-POLL-002 (server clamp) |
| `POLL_LIMIT_MAX` | `100` | CORE-POLL-002 |
| `REQUEST_TIMEOUT_MS` | `10000` | CORE-CONN-009 |
| `POLL_TIMEOUT_MARGIN_MS` | `10000` | CORE-CONN-009 |
| `RETRY_INITIAL_MS` | `500` | CORE-CONN-008 |
| `RETRY_MAX_MS` | `8000` | CORE-CONN-008 |
| `SERVER_DEFAULT_PORT` | `8080` | server-behavior CORE-SRV-002 |

---

## Appendix A — Worked trace of the Alice/Bob scenario (normative example)

**Fixed test data.** Steps 1 and 2 use the brief's texts. The queued texts of steps 3 and 4 are fixed for test purposes as `Queued by Alice while offline` and `Queued by Bob while offline`. Message ids below are fixed for this trace and the schema examples only (real clients generate random UUIDs, CORE-ENV-002). Epoch `3f9a1c7e5b2d4086`. Timestamps are illustrative; nothing depends on them.

| Label | id | from → to | text |
|---|---|---|---|
| A1 | `00000000-0000-4000-8000-0000000000a1` | alice → bob | `Hi Bob, I have something important to tell you` |
| B1 | `00000000-0000-4000-8000-0000000000b1` | bob → alice | `What is it?` |
| A2 | `00000000-0000-4000-8000-0000000000a2` | alice → bob | `Queued by Alice while offline` |
| B2 | `00000000-0000-4000-8000-0000000000b2` | bob → alice | `Queued by Bob while offline` |

Notation: `E3(X)` = `POST /v1/messages?epoch=3f9a1c7e5b2d4086` with the send form of X; `E4(u, a, w)` = `GET /v1/mailboxes/u/messages?epoch=3f9a1c7e5b2d4086&after=a&wait=w` (`limit` omitted = 100). Views list messages in CORE-SEQ-002 order as `label(state, seq)`.

### Step 0 — both log in (precondition, fresh server, fresh clients)
Alice types `Alice`, Bob types `Bob`; identities stored as `alice`, `bob` (CORE-NAME-004). Both online, toggles off.

| # | Client | Request | Response |
|---|---|---|---|
| 0.1 | Alice | `POST /v1/session` `{"name":"alice","capabilities":[]}` | `200 {"name":"alice","epoch":"3f9a1c7e5b2d4086","new_user":true}` → epoch reset (none stored): cursor 0 |
| 0.2 | Alice | `E4(alice, 0, 0)` | `200 {"epoch":"3f9a…","messages":[],"next_cursor":0,"has_more":false}`; outbox empty; enters live |
| 0.3 | Alice | `E4(alice, 0, 20)` | held |
| 0.4–0.6 | Bob | same three requests for `bob` | session `new_user:true`; catch-up empty; `E4(bob, 0, 20)` held |

Server: users {alice, bob}; counter 0; mailboxes empty.

### Step 1 — Alice → Bob: A1
| # | Client | Request | Response |
|---|---|---|---|
| 1.1 | Alice | compose → outbox [A1] → `E3(A1)` body `{"id":"…a1","from":"alice","to":"bob","type":"text","payload":{"text":"Hi Bob, I have something important to tell you"},"created_at":"2026-10-13T15:00:01.000Z"}` | `201 {"id":"…a1","seq":1,"accepted_at":"2026-10-13T15:00:01.010Z","epoch":"3f9a…"}` |
| 1.2 | Bob | held `E4(bob, 0, 20)` returns | `200 {"messages":[A1 with seq 1],"next_cursor":1,"has_more":false}`; Bob stores A1, cursor 1, issues `E4(bob, 1, 20)` |

Server: counter 1; mailbox bob [1:A1]; mailbox alice []. Alice view: A1(sent,1). Bob view: A1(received,1). Cursors: alice 0, bob 1.

### Step 2 — Bob → Alice: B1
| # | Client | Request | Response |
|---|---|---|---|
| 2.1 | Bob | `E3(B1)` | `201 {"seq":2,…}` |
| 2.2 | Alice | held `E4(alice, 0, 20)` returns | `200 {"messages":[B1 seq 2],"next_cursor":2}`; cursor 2; `E4(alice, 2, 20)` |

Server: counter 2; bob [1:A1]; alice [2:B1]. Alice view: A1(sent,1), B1(received,2). Bob view: A1(received,1), B1(sent,2). Cursors: alice 2, bob 1.

### Step 3 — Alice goes offline, queues A2
Alice sets `offline_toggle` → state `offline`; her held `E4(alice, 2, 20)` is aborted (CORE-CONN-004). She composes A2 → outbox [A2]. **No request.**
Server unchanged. Alice view: A1(sent,1), B1(received,2), A2(pending). Bob view unchanged.

### Step 4 — Bob goes offline, queues B2
Bob sets `offline_toggle`; `E4(bob, 1, 20)` aborted. Composes B2 → outbox [B2]. **No request.**
Server unchanged. Bob view: A1(received,1), B1(sent,2), B2(pending).

### Step 5 — Alice reconnects; A2 reaches the server
| # | Client | Request | Response |
|---|---|---|---|
| 5.1 | Alice | `POST /v1/session` | `200 {"name":"alice","epoch":"3f9a…","new_user":false}` (same epoch: no reset) → `online` |
| 5.2 | Alice | `E4(alice, 2, 0)` | `200 {"messages":[],"next_cursor":2,"has_more":false}` (B2 is still in Bob's outbox) |
| 5.3 | Alice | `E3(A2)` | `201 {"seq":3,…}`; outbox [] |
| 5.4 | Alice | `E4(alice, 2, 20)` | held |

Server: counter 3; bob [1:A1, 3:A2]; alice [2:B1]. Alice view: A1(sent,1), B1(received,2), A2(sent,3). Bob view unchanged (offline). The step is complete when A2 is `sent` on Alice's client.

### Step 6 — Alice goes offline again
`E4(alice, 2, 20)` aborted. No request. Server and views unchanged; Alice state `offline`, cursor 2.

### Step 7 — Bob reconnects; receives A2, delivers B2
| # | Client | Request | Response |
|---|---|---|---|
| 7.1 | Bob | `POST /v1/session` | `200 {"name":"bob","epoch":"3f9a…","new_user":false}` → `online` |
| 7.2 | Bob | `E4(bob, 1, 0)` | `200 {"messages":[A2 with seq 3],"next_cursor":3,"has_more":false}` (example `poll-response.bob-step7.json`); cursor 3 |
| 7.3 | Bob | `E3(B2)` | `201 {"seq":4,…}`; outbox [] |
| 7.4 | Bob | `E4(bob, 3, 20)` | held |

Server: counter 4; bob [1:A1, 3:A2]; alice [2:B1, 4:B2]. Bob view: A1(received,1), B1(sent,2), A2(received,3), B2(sent,4). Alice view (still offline): A1(sent,1), B1(received,2), A2(sent,3) — she does **not** see B2 yet. Cursors: alice 2, bob 3.

Transient on Bob (deterministic by CORE-CONN-006): after 7.2 and before 7.3 his view is A1, B1, A2(received,3), B2(pending).

### Step 8 (beyond the brief) — Alice reconnects
Session (no reset) → `E4(alice, 2, 0)` returns B2 (seq 4), cursor 4 → outbox empty → live `E4(alice, 4, 20)`. Alice view: A1(sent,1), B1(received,2), A2(sent,3), B2(received,4) — same order as Bob's.

### Variant — lost ack
If in 5.3 Alice goes offline after the server accepted A2 but before the response is processed, A2 stays `pending`; on the next cycle `E3(A2)` returns `200` with `seq` 3 (CORE-MSG-001), and the result is identical to the trace above.

## Appendix B — How an extension rides the envelope (non-normative)

Suppose a future `reactions` extension (phase P6; not specified here) lets Bob react to A1. Bob's client declares `"capabilities":["reactions"]` in E2 and sends through the normal outbox:

```json
{"id":"00000000-0000-4000-8000-0000000000c1","from":"bob","to":"alice","type":"reactions.add",
 "payload":{"target_id":"00000000-0000-4000-8000-0000000000a1","reaction":"+1"},"created_at":"2026-10-13T15:10:00.000Z"}
```

The server validates only the envelope (CORE-EXT-001), assigns the next `seq`, stores it in Alice's mailbox, and delivers it through E4 and the same cursor. A core-only client skips it (CORE-EXT-002) and still advances its cursor; a reactions-capable client applies it. No server code, endpoint or schema in `spec/core/` changes; the extension file adds `reactions.add` and its payload schema.
