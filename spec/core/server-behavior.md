# Core server behavior

- **Status:** draft for G0 (spec 0.1.0-draft). Owner: TL. Decisions: [`docs/decisions/0004`–`0009`, `0012`, `0014`](../../docs/decisions/).
- **Scope:** what the reference server in `server/` does internally to satisfy [`protocol.md`](protocol.md). Wire formats, status codes and error precedence are defined there and only referenced here. The server is hand-maintained (not generated) and intentionally trivial: one process, in memory, no security (brief).
- **Ids:** `CORE-SRV-NNN`, grouped by tens (001 runtime, 010 epoch and transport, 020 registry, 030 accepting envelopes, 040 relay and info). Gaps are deliberate; ids are never reused. A withdrawn rule stays as a one-line tombstone without a keyword.

## 1. Runtime

- **CORE-SRV-001** — The server MUST run as a single process holding all state in memory; it MUST NOT write state to disk, and all state MUST be lost when the process exits.
- **CORE-SRV-002** — The server MUST listen on host `127.0.0.1` and port `SERVER_DEFAULT_PORT` (8080) by default; both MUST be overridable by command-line options `--host` and `--port` and by environment variables `AWARE_HOST` and `AWARE_PORT` (options win). Port `0` MUST select a free port. The host is an IPv4 address or a host name that resolves to one; IPv6 is not required.
- **CORE-SRV-003** — The server MUST serve requests concurrently: a slow or stalled connection MUST NOT delay any other request. No request is ever held on purpose (CORE-POLL-005).
- **CORE-SRV-004** — Every read-modify-write of server state (registration, duplicate check, `seq` assignment, storing, appending to a mailbox, reading a mailbox for E4) MUST happen under one mutual-exclusion lock, so each accepted envelope is observed atomically with its `seq`.
- **CORE-SRV-005** — Every response, including errors, MUST carry `Access-Control-Allow-Origin: *`; an `OPTIONS` request to `/v1` or to any path starting with `/v1/`, known or not, MUST be answered `204` with `Access-Control-Allow-Methods: GET, POST, OPTIONS`, `Access-Control-Allow-Headers: Content-Type` and `Access-Control-Max-Age: 600` (the web client runs on another local origin).
- **CORE-SRV-006** — When ready to accept connections, the server MUST print exactly one line `aware-server listening on http://<host>:<port> epoch=<epoch>` to standard output and flush it, where `<host>` is the host string as configured (option, environment variable or default, not resolved) and `<port>` the port actually bound (test harnesses wait for this line and read the actual port from it).
- **CORE-SRV-007** — The server SHOULD log one line per request to standard error: method, path without query, status, duration in ms.

Request visibility for tests (non-normative): tests that must prove a client made **no** request (CORE-CONN-004) do not use the server. In-project tests record the calls of a fake `Transport` (PLAT-HOOK-014), external web tests count with the browser test framework's request events (PLAT-WEB-024), and the Android driver reports its own `Transport` calls (PLAT-ANDROID-033); decision 0014. The server therefore has no test-only endpoint, and CORE-SRV-007 stays a debugging aid (`SHOULD`).

## 2. Epoch and transport

- **CORE-SRV-010** — At start the server MUST create the epoch (CORE-EPOCH-001), an empty user registry, an empty id index, no mailboxes, and the `seq` counter at `0`.
- **CORE-SRV-011** — For a POST, the server MUST check `Content-Type` (CORE-HTTP-003, else `415`), then `Content-Length` (missing → `400 malformed_request`; larger than `BODY_MAX_BYTES` → `413`, without reading the body), before parsing JSON.
- **CORE-SRV-012** — Withdrawn (decision 0014).
- **CORE-SRV-013** — Withdrawn (decision 0014).
- **CORE-SRV-014** — Withdrawn (decision 0014).
- **CORE-SRV-015** — Every E3 and E4 success response MUST carry the server's current epoch.
- **CORE-SRV-016** — E4 MUST NOT require the mailbox owner to be registered (CORE-POLL-007); only the epoch and parameters are validated, and the response is computed from the mailbox at that moment and sent at once (CORE-POLL-005); a `wait` parameter is ignored like any unknown parameter (CORE-HTTP-006).

Testing note (non-normative, decision 0018): CORE-EPOCH-001 (random epoch) and CORE-SRV-031 (real clock) describe every normal start. To replay Appendix A exactly, the server's own tests can build the server state in-process with a fixed epoch and a fake UTC clock. That seam is reachable from test code only: no command-line option, environment variable, configuration file or endpoint sets the epoch or the clock, and a server started normally always uses a random epoch and the real clock. This is not a runtime option and adds no wire behavior.

## 3. User registry

- **CORE-SRV-020** — The registry MUST map canonical names to the last declared capability list; an entry is created by the first E2 for that name in the epoch and never removed.
- **CORE-SRV-021** — E2 MUST return `new_user: true` exactly when it created the registry entry, `false` otherwise.
- **CORE-SRV-022** — E2 MUST replace the stored capability list with the request's list (order preserved as sent).
- **CORE-SRV-023** — E5 MUST return all registry entries sorted by canonical name in ascending byte order; E3's sender check (CORE-MSG-002) MUST use the same registry.

## 4. Accepting envelopes (E3)

- **CORE-SRV-030** — The server MUST process E3 in this order and stop at the first failure: (1) checks of CORE-SRV-011; (2) parse JSON; reject missing or unknown fields, fields of the wrong JSON type (`payload` excepted, step 4), and a `created_at` that is not the exact UTC form of CORE-HTTP-007 or not a real calendar instant (month outside `01`–`12`, a day that does not exist in that month and year, such as `02-29` in a non-leap year, hour above `23`, minute or second above `59` including a leap second `60`, a numeric offset, a lowercase `z`, or not exactly three fraction digits) (`400 malformed_request`; cases: [`schema/cases/timestamp.json`](schema/cases/timestamp.json)); (3) `epoch` query parameter (CORE-EPOCH-002); (4) validate `from` then `to` (`invalid_name`), `id` (`invalid_id`), `type` (`invalid_type`), payload (`invalid_payload`: not a JSON object for any `type` (CORE-ENV-005), or a core type's payload failing §6); (5) canonicalize `from` and `to`; (6) sender registered (`403 unknown_sender`); (7) duplicate check (CORE-SRV-034); (8) accept (CORE-SRV-031..033).
- **CORE-SRV-031** — Accepting MUST increment the `seq` counter by one and assign the new value as the envelope's `seq` (CORE-SEQ-001), and set `accepted_at` to the current UTC time of the server clock in the form of CORE-HTTP-007 (milliseconds truncated).
- **CORE-SRV-032** — Accepting MUST store the delivered form in an index keyed by `id` and append it to the mailbox of `to`, creating the mailbox if absent (CORE-MSG-003); a note to self (`to` = `from`) is appended once.
- **CORE-SRV-033** — Accepting MUST respond `201` with `{id, seq, accepted_at, epoch}`; the envelope is visible to every E4 processed after it (CORE-SRV-004).
- **CORE-SRV-034** — If `id` is already in the index, the server MUST compare `from`, `to` (canonical), `type`, `payload` (JSON value equality: same keys and equal values, numbers compared by value, key order ignored) and `created_at`; all equal → `200` with the stored `seq` and `accepted_at` and no state change; any difference → `409 id_conflict`.
- **CORE-SRV-035** — The server MUST NOT modify a stored envelope after acceptance, and MUST return byte-for-byte equal JSON values for `payload` in every delivery.
- **CORE-SRV-036** — The server MUST keep every accepted envelope for its whole lifetime; there is no deletion, expiry or acknowledgement of receipt (the cursor is client-held, decision 0004).
- **CORE-SRV-037** — The server MUST have no notion of a time zone: it reads only a UTC clock (for `accepted_at`), MUST NOT convert any instant to or from a local time, and MUST NOT read the host's local zone or hold a zone in code or configuration (CORE-TIME-003). After the format check of CORE-SRV-030 it treats `created_at` as an opaque string: it is compared for equality in CORE-SRV-034 and returned unchanged, never interpreted.

## 5. Relay and info

- **CORE-SRV-040** — For a `type` not in `core_types`, the server MUST store and deliver `payload` unchanged and MUST NOT read it for any purpose (CORE-EXT-001).
- **CORE-SRV-041** — E1 MUST return the values of CORE-CAP-001 with `core_types` = `["text"]` and `server_capabilities` = `[]` in this version.
- **CORE-SRV-042** — Adding a client-only extension MUST NOT require any change to the server; a server change is required only for an extension that declares a new `server_capabilities` id (decision 0008).

## 6. What the server does NOT do (non-normative summary)

No authentication, tokens or name ownership (CORE-NAME-006). No persistence across restarts (CORE-SRV-001; clients detect restarts by epoch). No push channel (WebSocket, SSE) and no held or long poll (decision 0014). No time zone (CORE-SRV-037). No per-client delivery state, read receipts or ack endpoint. No validation that a recipient exists (CORE-MSG-003). No payload inspection for non-core types. No reordering, editing or deleting of messages. No rate limiting, TLS, multi-process or production hardening. No group fan-out (would be a server capability of a groups extension).

## 7. Mailbox state in the Alice/Bob scenario

The per-step server state (registry, counter, mailboxes) is listed in [`protocol.md` Appendix A](protocol.md#appendix-a--worked-trace-of-the-alicebob-scenario-normative-example). Final after step 7: counter `4`; mailbox `bob` = [1 A1, 3 A2]; mailbox `alice` = [2 B1, 4 B2].
