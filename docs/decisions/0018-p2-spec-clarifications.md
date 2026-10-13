# 0018 — P2 spec clarifications (S-1..S-13)
- Status: proposed (needs operator G0 approval)
- Date: 2026-10-13
- Author: TL (agent, claude-opus-5-5)
- Input: the P2 DEV agent's questions in [`docs/runs/P2/spec-issues.md`](../runs/P2/spec-issues.md).
- Spec version: 0.1.0 → **0.1.1** (patch: clarification). No rule id is added, withdrawn or renumbered; rule counts are unchanged (242 rule ids, 52 ACs).
- Spec ids driven (reworded, same id): `CORE-HTTP-001`, `CORE-HTTP-003`, `CORE-HTTP-006`, `CORE-ENV-005`, `CORE-ENV-006`, `CORE-MSG-001`, `CORE-POLL-001`, `CORE-ERR-001`, `CORE-ERR-002`, `CORE-SRV-002`, `CORE-SRV-005`, `CORE-SRV-006`, `CORE-SRV-011`, `CORE-SRV-030`. Non-id text: `protocol.md` §1 "Path and method matching", §12 table row `malformed_request`, Appendix A fixed-data note; `server-behavior.md` §2 testing note. Schema: `common.schema.json` (`seq`, `cursor` maximum; new `$defs/cursor_param`), `index.json` (`after`/`limit` pattern, two `value_cases`), new `cases/cursor.json` and `cases/cursor-param.json`.

## Context
While building the reference server (P2), DEV found 13 places where the spec is silent or two texts disagree. DEV did the smallest valid thing for each one and recorded it. The rule for each answer: make the smallest spec change that removes the ambiguity, and keep what the server already does unless there is a strong reason to change it.

## Decision

| # | Decision | Ids / text changed |
|---|---|---|
| S-1 | A `payload` that is not a JSON object is **`400 invalid_payload`** for every `type`, reported at its `invalid_payload` position in CORE-ERR-002 (after names, `id` and `type`). The section 12 table already said so. CORE-SRV-030 step 2 and CORE-ERR-002 now exclude `payload` from "wrong JSON type". The server keeps its behavior. | CORE-ENV-005, CORE-ERR-002, CORE-SRV-030 |
| S-2 | `created_at` **takes part in duplicate equality**, as an opaque string and never as a time. A resend with another `created_at` is `409 id_conflict`. CORE-ENV-006 no longer says it "MUST NOT influence dedupe". CORE-MSG-001 points to CORE-SRV-034 for what "all fields equal" means. The server keeps its behavior. | CORE-ENV-006, CORE-MSG-001 |
| S-3 | `after` and `limit` are capped at **15 digits**, `^(0|[1-9][0-9]{0,14})$`. The schema maximum for `seq` and `cursor` becomes 999999999999999, so every `after` the server accepts can come back as `next_cursor` and still validate. A 16-digit value is `400 malformed_request`. Rejected alternative: keep 16 digits and reject values above 2^53−1 with a numeric check. That leaves a pattern that admits invalid values and needs a second check in every implementation. A `seq` near 10^15 cannot happen in an in-memory demo. **Server change.** | CORE-POLL-001; schema `seq`, `cursor`, new `cursor_param`, `index.json` patterns, `cases/cursor.json`, `cases/cursor-param.json` |
| S-4 | The media type `application/json` is compared case-insensitively. The only parameter allowed is `charset=utf-8`, with name and value case-insensitive and the value optionally quoted. A missing header, another media type, another charset (for example `latin-1`) or any other parameter is `415`. The server keeps its behavior. | CORE-HTTP-003, CORE-SRV-011 |
| S-5 | On E3 or E4, `epoch`, `after` or `limit` given more than once is `400 malformed_request`. Unknown parameters are ignored, also when repeated. The server keeps its behavior. | CORE-HTTP-006; §12 row `malformed_request` |
| S-6 | Fixed paths are compared exactly as written, with no percent-decoding. A trailing slash or an extra segment makes a path unknown (`404`). The E4 `<name>` segment is percent-decoded first and then validated. An empty segment is a known path with `400 invalid_name`. The server keeps its behavior. | §1 "Path and method matching" (text, no id) |
| S-7 | `OPTIONS` gets `204` for `/v1` and for every path under `/v1/`, known or not. Outside `/v1` it gets `404`. The server keeps its behavior. | CORE-SRV-005 |
| S-8 | A method not listed for a path, including `HEAD` and unknown method names, is `405` on a known path and `404` elsewhere. No `Allow` header is sent. A `HEAD` response carries the status and headers but no body, because HTTP/1.1 forbids one. CORE-ERR-001 states that exception. The server keeps its behavior. | CORE-ERR-001; §1 "Path and method matching" |
| S-9 | A request that is not valid HTTP/1.1 is `400 malformed_request` with the error body, and the server then closes the connection. This covers a garbage request line, an unsupported version, and bad header syntax or size. The server keeps its behavior; see the 408 note below. | §12 row `malformed_request` |
| S-10 | Senders use unique member names. A server that receives a repeated name uses the **last** occurrence. A server **accepts at least 64 levels** of nesting and **may** reject deeper nesting with `400 malformed_request`. The server keeps its behavior: last wins, and its limit is about 1000 levels. | CORE-HTTP-001 |
| S-11 | IPv6 is not required. `--host` takes an IPv4 address or a host name that resolves to one. The listening line prints the host string as configured (not resolved) and the port actually bound. The server keeps its behavior. | CORE-SRV-002, CORE-SRV-006 |
| S-12 | CORE-ERR-002 applies to **every** endpoint. Its text now spells out the E2 order (`415`, `413`, `malformed_request` including `capabilities` format, then `invalid_name`) and the E4 order (`malformed_request` for query parameters, `epoch_mismatch`, `invalid_name`). DEV's order matches it. The server keeps its behavior. | CORE-ERR-002 |
| S-13 | The server's own tests may build server state in-process with a fixed epoch and a fake UTC clock. This is a **testing note, not a runtime option**: no command-line option, environment variable, configuration file or endpoint can set either value, and a normal start always uses a random epoch (CORE-EPOCH-001) and the real clock (CORE-SRV-031). The current `ServerState(epoch=..., clock=...)` seam already does this. The server keeps its behavior. | `server-behavior.md` §2 testing note; Appendix A fixed-data note |

## Changes for DEV (server and `tests/protocol`)
Only **S-3** changes server behavior. Everything else confirms what the server already does. Some tests can be tightened now that the code is fixed.

**Must change** (the suite fails on this branch until done):
1. `server/aware_server/validation.py`: change `CURSOR_RE` from `0|[1-9][0-9]{0,15}` to `0|[1-9][0-9]{0,14}`. It is used for both `after` and `limit`.
2. `tests/protocol/test_poll.py::test_CORE_POLL_001_after_and_limit_must_be_canonical_decimal_integers`:
   - move `&after=1234567890123456&limit=3` to the rejected list and add `&after=1234567890123456`, `&after=9999999999999999` and `&after=0&limit=1234567890123456` there;
   - add `&after=999999999999999` and `&after=123456789012345&limit=3` to the accepted list;
   - delete the "16 digits above 2**53-1" block that ran with schema validation off.
   The harness validates every response against the schema, so today this test fails with `$.next_cursor: above 999999999999999`. TL tried exactly these edits on a scratch copy and the suite went back to 121/121 green.

**Should tighten** (passes today and is still correct, but looser than the spec):
3. `test_send.py::test_CORE_ENV_005_payload_must_be_a_json_object`: assert `invalid_payload` exactly. Also fix the comment, which cites S-3 instead of S-1.
4. `test_errors.py::test_CORE_ERR_001_garbage_request_lines_still_get_a_json_error_body`: assert `400 malformed_request`, not "any 4xx".
5. S-5: add a test that a repeated `epoch`, `after` or `limit` is `400 malformed_request` and a repeated unknown parameter is ignored.
6. S-10: add a test that a payload nested 64 levels deep is accepted, and one that a repeated member name keeps the last value.
7. Optional, for consistency: in `httpd.py` `send_error`, the `408` branch returns status `408` with code `malformed_request`. That violates CORE-ERR-001's "matching status". It cannot be reached today because the handler sets no read timeout. Map it to `400` if it is kept.

**Clients:** no change. They never send a 16-digit cursor, a non-object payload or duplicate keys.

## Alternatives considered
- S-1 `malformed_request` (the "wrong JSON type" reading). It would mean changing the server and the §12 table, and it splits payload errors over two codes. Rejected.
- S-2 drop `created_at` from duplicate equality. A conflicting resend would then be silently accepted as a duplicate, and the server would need a behavior change. CORE-MSG-005 already obliges clients to resend identical values. Rejected.
- S-10 reject duplicate keys. Stricter, but it needs a custom parser on every platform for a case a correct client never produces. Rejected.
- S-13 a `--epoch` or `AWARE_CLOCK` option. It would be a runtime option that could make production non-random. Rejected.

## Consequences
- Prose and schema agree again on cursors, payload errors and `created_at`.
- After DEV's S-3 change, `tests/protocol` is green against spec 0.1.1.
- PM files need no change. CORE-VISIBLE-009 cites CORE-ENV-006 for "never the sender's clock", and that part is unchanged.

## Brief constraint affected
None.
