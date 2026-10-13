# Core protocol

- **Status:** draft for G0 (spec 0.1.0-draft). Owner: TL. Decisions: [`docs/decisions/0004`–`0009`, `0012`, `0014`](../../docs/decisions/).
- **Scope:** the wire contract between any client and the server, plus the client obligations that are visible on the wire (request order, retries, cursor, ordering key). Visible UI behavior (screens, labels, what the user sees at each step) is in [`client-behavior.md`](client-behavior.md) (PM). Server internals are in [`server-behavior.md`](server-behavior.md).
- **Platform-neutral:** nothing here names a language, library or OS. Platform rules are in [`../platform/`](../platform/).
- **Machine-readable contract:** [`schema/`](schema/) (JSON Schema per request/response, [`schema/index.json`](schema/index.json) maps endpoints to schemas, [`schema/constants.json`](schema/constants.json) holds §13). Prose and schema are both normative; a contradiction between them is a spec defect (return `SPEC_ISSUE`), not a choice for the implementer.
- **Keywords:** MUST / MUST NOT / SHOULD / MAY as in RFC 2119. Each normative rule has an id `CORE-<AREA>-NNN`; ids are never reused or renumbered. A withdrawn rule stays as a one-line tombstone `Withdrawn (decision NNNN).` without a keyword ([`../README.md`](../README.md#rule-ids)).

Contents: 1 Transport · 2 Names and identity · 3 Session · 4 Epoch · 5 Envelope · 6 Core type `text` · 7 Send and ack · 8 Poll and receive · 9 Order · 10 Connection and outbox (client) · 11 Capabilities and extensions · 12 Errors · 13 Constants · Appendix A: Alice/Bob trace · Appendix B: an extension riding the envelope.

---

## 1. Transport

- **CORE-HTTP-001** — Client and server MUST communicate over HTTP/1.1; every request and response body MUST be a single JSON value encoded as UTF-8.
- **CORE-HTTP-002** — All endpoints MUST live under the path prefix `/v1`; the base URL (scheme, host, port) is configuration, never hard-coded in core (see platform files).
- **CORE-HTTP-003** — Requests with a body MUST carry `Content-Type: application/json` (a `charset=utf-8` parameter is allowed); responses with a body MUST carry `Content-Type: application/json; charset=utf-8`.
- **CORE-HTTP-004** — Request bodies MUST NOT contain fields other than those in their schema; the server MUST reject such requests with `400 malformed_request`.
- **CORE-HTTP-005** — Clients MUST ignore response fields they do not know (so the server may add fields within `/v1`).
- **CORE-HTTP-006** — Unknown query parameters MUST be ignored by the server.
- **CORE-HTTP-007** — Timestamps MUST be UTC strings in the exact form `YYYY-MM-DDTHH:MM:SS.sssZ` (exactly three fraction digits, uppercase literal `Z`, no numeric offset) that denote a real instant of the Gregorian calendar: month `01`–`12`; day valid for that month, with `02-29` only in leap years (year divisible by 4, except years divisible by 100 and not by 400); hour `00`–`23`; minute and second `00`–`59` (no leap second). The schema pattern `common.schema.json#/$defs/timestamp` encodes exactly this; valid and invalid cases are in [`schema/cases/timestamp.json`](schema/cases/timestamp.json).

### Endpoints

| Id | Method and path | Request | Success | Errors (§12) |
|---|---|---|---|---|
| E1 | `GET /v1/info` | none | `200` info-response | `405` |
| E2 | `POST /v1/session` | session-request | `200` session-response | `400` `413` `415` |
| E3 | `POST /v1/messages?epoch=<epoch>` | send-request | `201` send-response (new), `200` send-response (duplicate) | `400` `403` `409` `413` `415` |
| E4 | `GET /v1/mailboxes/<name>/messages?epoch=<epoch>&after=<cursor>&limit=<n>` | none | `200` poll-response | `400` `409` |
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
- **CORE-SESSION-003** — A client MUST call `POST /v1/session` as the first request it starts after it becomes allowed (CORE-CONN-002) and as the first request of the first cycle after a failed request (class R, §12), and MUST NOT send or poll until that session has succeeded. Otherwise a cycle skips the session (§10).
- **CORE-SESSION-004** — The `name` in the response MUST equal the client's stored canonical identity; a client MUST treat any other value as a failed request of class R (§12).

## 4. Epoch

The epoch identifies one lifetime of the in-memory server. `seq` values and mailboxes are only meaningful within one epoch.

- **CORE-EPOCH-001** — The server MUST generate a new epoch at start: 16 lowercase hex characters from a random source (`^[0-9a-f]{16}$`), constant until the process exits.
- **CORE-EPOCH-002** — Every E3 and E4 request MUST carry the client's current epoch as query parameter `epoch`; missing or malformed → `400 malformed_request`; different from the server's → `409 epoch_mismatch`.
- **CORE-EPOCH-003** — A client MUST persist the epoch from its last successful session together with its cursor.
- **CORE-EPOCH-004** — When a session response carries an epoch different from the stored one (or there is none stored), the client MUST perform an epoch reset before any other request: delete all locally stored messages that have a `seq` (states `sent` and `received`), set the cursor to `0`, store the new epoch. Identity and outbox (`pending` messages, the only messages without a `seq`) MUST be kept.
- **CORE-EPOCH-005** — On `409 epoch_mismatch` a client MUST NOT change its stored epoch, cursor or messages; it MUST handle the outcome as a failed request (class R, §12), so the next cycle starts with a session (CORE-SESSION-003) whose epoch triggers CORE-EPOCH-004.
- **CORE-EPOCH-006** — Withdrawn (decision 0014).

## 5. Envelope

Send form (E3 body): `{"id", "from", "to", "type", "payload", "created_at"}`. Delivered form (E4): the same plus `"seq"` and `"accepted_at"`. Schemas: `send-request.schema.json`, `envelope.schema.json`.

- **CORE-ENV-001** — The send form MUST contain exactly the fields `id`, `from`, `to`, `type`, `payload`, `created_at`; the delivered form MUST contain exactly those plus `seq` and `accepted_at`.
- **CORE-ENV-002** — `id` MUST be generated by the sending client at compose time as a random UUID version 4 in lowercase canonical text form, matching `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`; it never changes for that message.
- **CORE-ENV-003** — `from` MUST be the sender's canonical name and `to` the recipient's canonical name (CORE-NAME-001); `to` MAY equal `from` (a note to self).
- **CORE-ENV-004** — `type` MUST match `^[a-z][a-z0-9_.-]{0,63}$`. Core types contain no `.`; extension types MUST be `<capability-id>.<name>` (§11).
- **CORE-ENV-005** — `payload` MUST be a JSON object; its shape is defined by `type` (core: §6; extensions: their own spec).
- **CORE-ENV-006** — `created_at` MUST be the sender's `Clock` reading at compose time, in UTC (CORE-HTTP-007, CORE-TIME-001); it is informational only and MUST NOT influence order, dedupe or validity beyond its format. It is sent, stored and validated but MUST NOT be shown to the user: the displayed instant is `accepted_at`, stored in UTC and converted to local time only at display time (CORE-TIME-002).
- **CORE-ENV-007** — `seq` (integer ≥ 1) and `accepted_at` (server clock in UTC, CORE-HTTP-007, CORE-TIME-001) MUST be assigned by the server when it first accepts the envelope and MUST be identical in every later response or delivery of that envelope.

### 5.1 Time

Operator decisions OM-0010 and OM-0011, decision 0012 (amended): instants are UTC everywhere, on input as well as output; only text produced for the user is in the device's local time zone, and no code holds a fixed zone. Which instant is shown and in what format is client behavior ([`client-behavior.md`](client-behavior.md), PM); the rules below fix the representation and the conversion.

- **CORE-TIME-001** — Every instant on the wire, in the local store, in state snapshots and in test fixtures MUST be a UTC string in the exact form `YYYY-MM-DDTHH:mm:ss.sssZ` (CORE-HTTP-007; never a local time, never a numeric offset such as `+09:00`); a client MUST store `accepted_at` with every message that has a `seq` and MUST convert to a local time zone only when it produces text for display.
- **CORE-TIME-002** — The display conversion MUST obtain the device's time zone from the `TimeZone` provider and "now" from the `Clock` at the moment the text is produced (never cached from an earlier display), so a zone change takes effect at the next display; local wall time = the UTC instant plus the zone's UTC offset at that instant, fields are taken from that wall time with seconds and milliseconds dropped (truncated, not rounded), and the viewer's current local date is the date of "now" plus the zone's offset at "now".
- **CORE-TIME-003** — Production code and configuration of clients and server MUST NOT contain a hardcoded time zone or UTC offset: no zone identifier (such as `America/Sao_Paulo`), no zone abbreviation, and no offset literal (such as `UTC-3`, `GMT+9`, `+09:00`). A client's only source of a zone is its `TimeZone` provider reading the device (PLAT-HOOK-009); the server uses no zone at all (CORE-SRV-037). UTC itself (the `Z` of CORE-HTTP-007 and UTC-based APIs) is the representation, not a zone choice, and is allowed. Zone values appear only in specs, fixtures and tests, as values injected into a fake `TimeZone` or set through a test runner's zone option; generated tests check this with a denylist (PLAT-HOOK-015).

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
- **CORE-MSG-004** — A client MUST treat a message as acknowledged (state `sent`, with `seq`) only on a `200` or `201` E3 response whose `id` equals the sent `id`; a timeout or network error MUST NOT count as an ack.
- **CORE-MSG-005** — A client re-sending an unacknowledged message MUST send identical field values (same `id`, `from`, `to`, `type`, `payload`, `created_at`).

### Message states (client, wire-relevant)

| State | Meaning | Has `seq` |
|---|---|---|
| `pending` | in the outbox, not acknowledged | no |
| `sent` | acknowledged by E3 (or seen in own mailbox, CORE-DEDUPE-004) | yes |
| `received` | delivered by E4 from another user | yes |

- **CORE-MSG-006** — A client MUST give every local message exactly one of the states `pending`, `sent`, `received`, with the meanings in the table above; there is no other message state (a permanently rejected message is removed, CORE-OUTBOX-005). The PM's behavior spec defines how each is shown.

## 8. Poll and receive (E4)

Query: `epoch` (required), `after` (required, cursor), `limit` (default and maximum `POLL_LIMIT_MAX`). There is no `wait` parameter: a poll is always answered at once (decision 0014); a `wait` sent anyway is an unknown parameter and is ignored (CORE-HTTP-006). Response `{"epoch", "messages": [<delivered envelope>...], "next_cursor", "has_more"}` (`poll-response.schema.json`).

- **CORE-POLL-001** — `after` and `limit` MUST be decimal integers matching `^(0|[1-9][0-9]{0,15})$`; otherwise, or if `limit` is `0`, the server MUST answer `400 malformed_request`.
- **CORE-POLL-002** — The server MUST clamp `limit` to `POLL_LIMIT_MAX` (values above are treated as the maximum, not rejected).
- **CORE-POLL-003** — The response MUST list the envelopes in mailbox `<name>` with `seq > after`, in ascending `seq`, at most `limit` of them; `has_more` MUST be true iff more such envelopes exist beyond the returned ones.
- **CORE-POLL-004** — `next_cursor` MUST be the `seq` of the last returned envelope, or `after` unchanged if none is returned.
- **CORE-POLL-005** — The server MUST answer every E4 at once with the envelopes that qualify when the request is processed, `200` with `messages: []` when none does; it MUST NOT hold the request waiting for new envelopes.
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
- **CORE-SEQ-002** — Clients MUST order messages by this key: messages with a `seq` (`sent`, `received`) first, ascending by `seq`; then messages without a `seq` (`pending`), ascending by local enqueue order (CORE-OUTBOX-006).
- **CORE-SEQ-003** — Clients MUST NOT use `created_at`, arrival time or any clock to order messages.
- **CORE-SEQ-004** — When a `pending` message is acknowledged it MUST take its position by its new `seq` (it may move above messages received while it was pending).
- **CORE-SEQ-005** — The conversation between canonical users X and Y MUST consist of exactly the stored `text` messages with {`from`, `to`} = {X, Y} (for X = Y, those with `from` = `to` = X), ordered by CORE-SEQ-002.

Consequence (Appendix A): once all messages are acknowledged and delivered, both participants of a conversation hold the same messages in the same order.

## 10. Connection and outbox (client)

The client's network activity is decided by these rules alone (decisions 0009 and 0014). The client runs one fixed loop of **cycles** separated by `CYCLE_INTERVAL_MS`. It has one request in flight at most, and there is no backoff. The exact request sequence depends on timing (how many idle cycles fall between two user actions); the states it produces do not. The PM's behavior spec defines how states are shown.

### Offline definition

- **CORE-CONN-001** — A client MUST have an `offline_toggle` (boolean, initially `false`) settable by the user and by test hooks, and MUST obtain `network_available` (boolean) from a replaceable connectivity monitor.
- **CORE-CONN-002** — A client MUST consider itself allowed to contact the server iff `offline_toggle` is `false` and `network_available` is `true`.
- **CORE-CONN-003** — A logged-in client MUST be in exactly one connection state: `offline` when not allowed; `online` when allowed and, since the later of (a) the moment it last became allowed and (b) its last failed request (class R, §12), a session (E2) and after it a poll (E4), both started after that moment, have succeeded; `connecting` when allowed and not `online`. A permanent rejection of a send (class P) is not a failed request and does not change the state.
- **CORE-CONN-004** — While not allowed, a client MUST NOT start any HTTP request or cycle. A request already in flight when the client becomes not allowed MUST NOT be cancelled for that reason: it runs until its response or its timeout (CORE-CONN-009), and a response MUST be applied exactly as when allowed (CORE-MSG-004, CORE-CURSOR-002, CORE-EPOCH-004, CORE-DEDUPE-001..004); the cycle then ends without any further request.
- **CORE-CONN-005** — When a logged-in client becomes allowed (start-up, toggle off, network back) it MUST enter `connecting` and start a cycle at once, without waiting for `CYCLE_INTERVAL_MS`; if a request from before is still in flight (CORE-CONN-004), the cycle starts as soon as that request has completed and its result is applied.

### Connection cycle

- **CORE-CONN-006** — A cycle MUST run these steps in order: (1) E2 session, only when CORE-SESSION-003 requires one (apply CORE-EPOCH-004 on success); (2) catch-up: E4 with the current cursor, repeated with the new cursor while `has_more` is true; (3) flush the outbox until it is empty (CORE-OUTBOX-003), including entries added during the cycle; (4) end of cycle. A cycle with nothing to receive or send is one E4 (an idle cycle).
- **CORE-CONN-007** — A client MUST have at most one request in flight at any time and MUST make its E2, E3 and E4 requests only inside a cycle. While allowed, the next cycle MUST start `CYCLE_INTERVAL_MS` after the previous cycle ended (measured from the completion of its last request), whether it ended normally or by a failure. Cycles start only at those moments and on CORE-CONN-005; queuing a message does not start one.
- **CORE-CONN-008** — On a failed request (class R, §12) the client MUST end the cycle at once, with no further request in it, and enter `connecting`. The next cycle starts after the same `CYCLE_INTERVAL_MS` as always (no backoff, no growth, no jitter) and begins with a session (CORE-SESSION-003).
- **CORE-CONN-009** — Every request (E1 to E5) MUST time out after `REQUEST_TIMEOUT_MS`; a timeout is a failed request (class R).

### Outbox and flush

- **CORE-OUTBOX-001** — Every message a user sends MUST first be appended to a persistent outbox as `pending`, whatever the connection state; there is no other send path.
- **CORE-OUTBOX-002** — The outbox MUST survive app restarts and keep insertion order (the local enqueue order of CORE-SEQ-002).
- **CORE-OUTBOX-003** — Flushing MUST send outbox entries in insertion order, one at a time: the next E3 MUST NOT start before the previous one ended with an ack or a class P outcome (§12).
- **CORE-OUTBOX-004** — An entry MUST leave the outbox only when acknowledged (→ `sent`) or rejected with a class P outcome (→ removed, CORE-OUTBOX-005); on a class R outcome it stays at the head and the cycle ends (CORE-CONN-008).
- **CORE-OUTBOX-005** — On a class P outcome for an entry, the client MUST delete that message from the outbox and from local storage (it disappears from every view), MUST write one line to its diagnostic log (PLAT-HOOK-009 `DiagnosticLog`) holding the message `id` and the error `code` (or the HTTP status when the body has no valid error code), and MUST continue the flush with the next entry in the same cycle; the message is never retried. With the local checks of CORE-TEXT-004 and CORE-NAME-005, a correct client never reaches this path against a correct server.
- **CORE-OUTBOX-006** — The local enqueue order (CORE-SEQ-002) MUST be a number assigned once when the message enters the outbox, strictly greater than every number assigned before for that identity, and persisted with the message; it is never reused or reassigned.

## 11. Capabilities and extensions

- **CORE-CAP-001** — `GET /v1/info` MUST return `protocol` = `"aware"`, `protocol_version` = `PROTOCOL_VERSION`, the current `epoch`, `core_types` = `["text"]`, `server_capabilities` (`[]` in v1) and `limits` (`text_max_bytes`, `body_max_bytes`, `poll_limit_max`, equal to §13).
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
- **CORE-ERR-002** — When several errors apply, the server MUST report the first in this order: `415`, `413`, `malformed_request` (JSON parse, missing or unknown fields, a field of the wrong JSON type, `created_at` format including calendar validity (CORE-HTTP-007), `capabilities` format, query parameters, `epoch` format), `epoch_mismatch`, `invalid_name`, `invalid_id`, `invalid_type`, `invalid_payload`, `unknown_sender`, `id_conflict`.
- **CORE-ERR-003** — Clients MUST classify every outcome of a request into exactly one class and act as follows:

| Class | Outcomes | Client action |
|---|---|---|
| R — failed request | network error, timeout, any `5xx`, `403 unknown_sender`, `404`, `405`, `409 epoch_mismatch`, any other `4xx` on E1, E2, E4 or E5 (a client bug), a CORE-SESSION-004 violation | end the cycle; the next cycle starts after `CYCLE_INTERVAL_MS` with a session (CORE-CONN-008, CORE-SESSION-003) |
| P — permanent | on E3 only: `400` (any code), `409 id_conflict`, `413`, `415` | remove the message and log it (CORE-OUTBOX-005); the flush continues with the next entry |

## 13. Constants

Single normative table; [`schema/constants.json`](schema/constants.json) MUST hold the same values (checked by `generator/scripts/check_schema_examples.py`).

- **CORE-CONST-001** — Implementations MUST use exactly these values; a test that needs shorter waits MUST control time through the `Clock` and `Scheduler` ports (PLAT-HOOK-009), never by changing the production values.

| Name | Value | Used by |
|---|---|---|
| `PROTOCOL_VERSION` | `1` | CORE-CAP-001 |
| `NAME_MAX_LENGTH` | `32` | CORE-NAME-001 |
| `TEXT_MAX_BYTES` | `4096` | CORE-TEXT-003 |
| `BODY_MAX_BYTES` | `65536` | §12 `413` |
| `POLL_LIMIT_MAX` | `100` | CORE-POLL-002 |
| `REQUEST_TIMEOUT_MS` | `10000` | CORE-CONN-009 |
| `CYCLE_INTERVAL_MS` | `1000` | CORE-CONN-007, CORE-CONN-008 (fixed pause between cycles, also after a failure) |
| `SERVER_DEFAULT_PORT` | `8080` | server-behavior CORE-SRV-002 |

Withdrawn by decision 0014 (never reuse the names): `POLL_WAIT_S`, `POLL_WAIT_MAX_S`, `POLL_TIMEOUT_MARGIN_MS`, `RETRY_INITIAL_MS`, `RETRY_MAX_MS`.

---

## Appendix A — Worked trace of the Alice/Bob scenario (normative example)

**Fixed test data.** Steps 1 and 2 use the brief's texts. The queued texts of steps 3 and 4 are fixed for test purposes as `Queued by Alice while offline` and `Queued by Bob while offline`. Message ids below are fixed for this trace and the schema examples only (real clients generate random UUIDs, CORE-ENV-002). Epoch `3f9a1c7e5b2d4086`. The `accepted_at` values are fixed test data for displayed times (table "Displayed times" at the end of this appendix): A1 `2026-10-13T15:00:01.010Z`, B1 `2026-10-13T15:00:02.010Z`, A2 `2026-10-13T15:00:05.010Z`, B2 `2026-10-13T15:00:07.010Z`. `created_at` values are illustrative; nothing depends on them.

| Label | id | from → to | text |
|---|---|---|---|
| A1 | `00000000-0000-4000-8000-0000000000a1` | alice → bob | `Hi Bob, I have something important to tell you` |
| B1 | `00000000-0000-4000-8000-0000000000b1` | bob → alice | `What is it?` |
| A2 | `00000000-0000-4000-8000-0000000000a2` | alice → bob | `Queued by Alice while offline` |
| B2 | `00000000-0000-4000-8000-0000000000b2` | bob → alice | `Queued by Bob while offline` |

**Notation.** `E2(u)` = `POST /v1/session` with `{"name":"u","capabilities":[]}`. `E3(X)` = `POST /v1/messages?epoch=3f9a1c7e5b2d4086` with the send form of X. `E4(u, a)` = `GET /v1/mailboxes/u/messages?epoch=3f9a1c7e5b2d4086&after=a` (`limit` omitted = 100). `empty(c)` = the response `200 {"epoch":"3f9a1c7e5b2d4086","messages":[],"next_cursor":c,"has_more":false}`. Views list messages in CORE-SEQ-002 order as `label(state, seq)`.

**Cycles and idle cycles.** Every request below belongs to a cycle (CORE-CONN-006); a cycle ends after its flush step, and the next one starts `CYCLE_INTERVAL_MS` later (CORE-CONN-007). `idle(u, c)` = a cycle that is only `E4(u, c)` → `empty(c)`, with nothing to flush. While a client is allowed and nothing changes, it repeats `idle(u, c)` every `CYCLE_INTERVAL_MS`. How many idle cycles fall between two steps depends on timing; they change no state and are left out of the tables. Only the cycles that change state are listed, with all of their requests. Tests wait on each step's completion condition (snapshot), never on a number of cycles.

### Step 0 — both log in (precondition, fresh server, fresh clients)
Alice types `Alice`, Bob types `Bob`; identities stored as `alice`, `bob` (CORE-NAME-004). Both toggles off, so both clients are allowed and start a cycle at once (CORE-CONN-005).

| # | Client | Request | Response → effect |
|---|---|---|---|
| 0.1 | Alice | `E2(alice)` | `200 {"name":"alice","epoch":"3f9a1c7e5b2d4086","new_user":true}` → epoch reset (none stored): epoch stored, cursor 0; still `connecting` |
| 0.2 | Alice | `E4(alice, 0)` | `empty(0)` → `online` (session and poll succeeded, CORE-CONN-003); outbox empty → cycle ends |
| 0.3 | Bob | `E2(bob)` | `200 {"name":"bob","epoch":"3f9a1c7e5b2d4086","new_user":true}` → epoch stored, cursor 0 |
| 0.4 | Bob | `E4(bob, 0)` | `empty(0)` → `online`; cycle ends |

Then `idle(alice, 0)` and `idle(bob, 0)`. Server: users {alice, bob}; counter 0; mailboxes empty. Cursors: alice 0, bob 0. **Complete when** both clients are `online`.

### Step 1 — Alice → Bob: A1
Alice composes A1 → outbox [A1], A1(pending). Her next cycle to reach its flush step sends it.

| # | Client | Request | Response → effect |
|---|---|---|---|
| 1.1 | Alice | `E4(alice, 0)` | `empty(0)`; cursor 0 |
| 1.2 | Alice | `E3(A1)` body `{"id":"…a1","from":"alice","to":"bob","type":"text","payload":{"text":"Hi Bob, I have something important to tell you"},"created_at":"2026-10-13T15:00:01.000Z"}` | `201 {"id":"…a1","seq":1,"accepted_at":"2026-10-13T15:00:01.010Z","epoch":"3f9a…"}` → A1(sent,1); outbox [] → cycle ends |
| 1.3 | Bob | `E4(bob, 0)` (first poll processed after 1.2) | `200 {"epoch":"3f9a…","messages":[A1 with seq 1],"next_cursor":1,"has_more":false}` → A1 stored as received, then cursor 1; cycle ends |

Then `idle(alice, 0)`, `idle(bob, 1)`. Server: counter 1; mailbox bob [1:A1]; mailbox alice []. Alice view: A1(sent,1). Bob view: A1(received,1). Cursors: alice 0, bob 1. **Complete when** Alice holds A1 `sent` and Bob holds A1 `received`.

### Step 2 — Bob → Alice: B1
Bob composes B1 → outbox [B1].

| # | Client | Request | Response → effect |
|---|---|---|---|
| 2.1 | Bob | `E4(bob, 1)` | `empty(1)`; cursor 1 |
| 2.2 | Bob | `E3(B1)` | `201 {"id":"…b1","seq":2,"accepted_at":"2026-10-13T15:00:02.010Z",…}` → B1(sent,2); outbox [] |
| 2.3 | Alice | `E4(alice, 0)` | `200 {"messages":[B1 with seq 2],"next_cursor":2,"has_more":false}` → B1 stored, cursor 2 |

Then `idle(alice, 2)`, `idle(bob, 1)`. Server: counter 2; bob [1:A1]; alice [2:B1]. Alice view: A1(sent,1), B1(received,2). Bob view: A1(received,1), B1(sent,2). Cursors: alice 2, bob 1. **Complete when** Bob holds B1 `sent` and Alice holds B1 `received`.

### Step 3 — Alice goes offline, queues A2
Alice sets `offline_toggle` → `offline`. If an `idle(alice, 2)` request is in flight, it is not cancelled: it completes with `empty(2)` and nothing follows (CORE-CONN-004). She composes A2 → outbox [A2]. **No new request.**
Server unchanged. Alice view: A1(sent,1), B1(received,2), A2(pending). Bob view unchanged. Cursors: alice 2, bob 1. **Complete when** Alice is `offline` and holds A2 `pending` with outbox [A2].

### Step 4 — Bob goes offline, queues B2
Bob sets `offline_toggle` → `offline`; an in-flight `idle(bob, 1)` completes with `empty(1)`. He composes B2 → outbox [B2]. **No new request.**
Server unchanged. Bob view: A1(received,1), B1(sent,2), B2(pending). Cursors: alice 2, bob 1. **Complete when** Bob is `offline` and holds B2 `pending` with outbox [B2].

### Step 5 — Alice reconnects; A2 reaches the server
Alice clears `offline_toggle` → `connecting`, and a cycle starts at once (CORE-CONN-005); a session is required (CORE-SESSION-003).

| # | Client | Request | Response → effect |
|---|---|---|---|
| 5.1 | Alice | `E2(alice)` | `200 {"name":"alice","epoch":"3f9a…","new_user":false}` (same epoch: no reset); still `connecting` |
| 5.2 | Alice | `E4(alice, 2)` | `empty(2)` (B2 is still in Bob's outbox) → `online` |
| 5.3 | Alice | `E3(A2)` | `201 {"id":"…a2","seq":3,"accepted_at":"2026-10-13T15:00:05.010Z",…}` → A2(sent,3); outbox [] → cycle ends |

Then `idle(alice, 2)`. Server: counter 3; bob [1:A1, 3:A2]; alice [2:B1]. Alice view: A1(sent,1), B1(received,2), A2(sent,3). Bob view unchanged (offline). Cursors: alice 2, bob 1. **Complete when** Alice is `online` and holds A2 `sent` with seq 3 and outbox [].

### Step 6 — Alice goes offline again
Alice sets `offline_toggle` → `offline`; an in-flight `idle(alice, 2)` completes with `empty(2)`. No new request. Server and views unchanged. Cursors: alice 2, bob 1. **Complete when** Alice is `offline`.

### Step 7 — Bob reconnects; receives A2, delivers B2
Bob clears `offline_toggle` → `connecting`; a cycle starts at once with a session.

| # | Client | Request | Response → effect |
|---|---|---|---|
| 7.1 | Bob | `E2(bob)` | `200 {"name":"bob","epoch":"3f9a…","new_user":false}`; still `connecting` |
| 7.2 | Bob | `E4(bob, 1)` | `200 {"epoch":"3f9a…","messages":[A2 with seq 3],"next_cursor":3,"has_more":false}` (example `poll-response.bob-step7.json`) → A2 stored as received, then cursor 3 → `online` |
| 7.3 | Bob | `E3(B2)` | `201 {"id":"…b2","seq":4,"accepted_at":"2026-10-13T15:00:07.010Z",…}` → B2(sent,4); outbox [] → cycle ends |

Then `idle(bob, 3)`. Server: counter 4; bob [1:A1, 3:A2]; alice [2:B1, 4:B2]. Bob view: A1(received,1), B1(sent,2), A2(received,3), B2(sent,4). Alice view (still offline): A1(sent,1), B1(received,2), A2(sent,3). She does **not** see B2 yet. Cursors: alice 2, bob 3. **Complete when** Bob is `online`, holds A2 `received` with seq 3 and B2 `sent` with seq 4, and his outbox is [].

Transient on Bob (deterministic by CORE-CONN-006): after 7.2 and before 7.3 he is `online` and his view is A1, B1, A2(received,3), B2(pending).

### Step 8 (beyond the brief) — Alice reconnects
| # | Client | Request | Response → effect |
|---|---|---|---|
| 8.1 | Alice | `E2(alice)` | `200 {"name":"alice","epoch":"3f9a…","new_user":false}` |
| 8.2 | Alice | `E4(alice, 2)` | `200 {"messages":[B2 with seq 4],"next_cursor":4,"has_more":false}` → B2 stored, cursor 4 → `online`; outbox empty → cycle ends |

Then `idle(alice, 4)` and `idle(bob, 3)`. Server unchanged (counter 4). Alice view: A1(sent,1), B1(received,2), A2(sent,3), B2(received,4), the same order as Bob's. Cursors: alice 4, bob 3. **Complete when** Alice is `online` and holds B2 `received` with seq 4.

### Variant — going offline during a send
If in step 5 Alice sets `offline_toggle` while 5.3 is in flight, the request is not cancelled (CORE-CONN-004). Its `201` is applied: A2 becomes `sent` with seq 3 while Alice is `offline`, and no further request is made. The resulting state equals the end of step 6.

### Variant — lost ack
If 5.3 fails after the server accepted A2 (timeout, or the connection drops before the response arrives), the outcome is class R: A2 stays `pending` at the head of the outbox, the cycle ends and Alice is `connecting` (CORE-CONN-008). `CYCLE_INTERVAL_MS` later the next cycle runs `E2(alice)` → `200`; `E4(alice, 2)` → `empty(2)` → `online`; `E3(A2)` → `200` with seq 3 and the original `accepted_at` (CORE-MSG-001, CORE-DEDUPE-003). The result is identical to the trace above.

### Displayed times (CORE-TIME-001, CORE-TIME-002)

Fixed zones for this example: Alice's device at UTC−03:00 (IANA `America/Sao_Paulo`, no daylight saving time), Bob's device at UTC+09:00 (IANA `Asia/Tokyo`). These are test inputs: they are injected into a fake `TimeZone` or set through a test runner's zone option, never written into production code (CORE-TIME-003). Two values of "now": N1 = `2026-10-13T15:00:10.000Z` (right after step 7 / step 8) and N2 = `2026-10-14T15:00:00.000Z` (one day later). Format per the PM's behavior spec: `HH:mm`, or `YYYY-MM-DD HH:mm` when the message's local date differs from the viewer's current local date. A message without `seq` (`pending`) shows no time.

| Msg | `accepted_at` (UTC) | Alice local | Bob local | Alice at N1 (today 2026-10-13) | Bob at N1 (today 2026-10-14) | Alice at N2 (today 2026-10-14) | Bob at N2 (today 2026-10-15) |
|---|---|---|---|---|---|---|---|
| A1 | `2026-10-13T15:00:01.010Z` | 2026-10-13 12:00:01 | 2026-10-14 00:00:01 | `12:00` | `00:00` | `2026-10-13 12:00` | `2026-10-14 00:00` |
| B1 | `2026-10-13T15:00:02.010Z` | 2026-10-13 12:00:02 | 2026-10-14 00:00:02 | `12:00` | `00:00` | `2026-10-13 12:00` | `2026-10-14 00:00` |
| A2 | `2026-10-13T15:00:05.010Z` | 2026-10-13 12:00:05 | 2026-10-14 00:00:05 | `12:00` | `00:00` | `2026-10-13 12:00` | `2026-10-14 00:00` |
| B2 | `2026-10-13T15:00:07.010Z` | 2026-10-13 12:00:07 | 2026-10-14 00:00:07 | `12:00` (after step 8) | `00:00` | `2026-10-13 12:00` | `2026-10-14 00:00` |

Notes: the same instant shows a different local date for the two users (Bob's 00:00 is on the 14th); before step 8 Alice holds no B2; during steps 3–4 A2 and B2 are `pending` and show no time; order is by `seq` regardless of the times shown (CORE-SEQ-003).

## Appendix B — How an extension rides the envelope (non-normative)

Suppose a future `reactions` extension (phase P6; not specified here) lets Bob react to A1. Bob's client declares `"capabilities":["reactions"]` in E2 and sends through the normal outbox:

```json
{"id":"00000000-0000-4000-8000-0000000000c1","from":"bob","to":"alice","type":"reactions.add",
 "payload":{"target_id":"00000000-0000-4000-8000-0000000000a1","reaction":"+1"},"created_at":"2026-10-13T15:10:00.000Z"}
```

The server validates only the envelope (CORE-EXT-001), assigns the next `seq`, stores it in Alice's mailbox, and delivers it through E4 and the same cursor. A core-only client skips it (CORE-EXT-002) and still advances its cursor; a reactions-capable client applies it. No server code, endpoint or schema in `spec/core/` changes; the extension file adds `reactions.add` and its payload schema.
