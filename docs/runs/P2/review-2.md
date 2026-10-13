---
feature: P2
app: server
round: 2
head_sha: d723d3c
changed_lines: 686
model: sonnet
blockers: 1
majors: 2
minors: 4
nits: 4
design_concerns: 0
---
# Review P2 / server — round 2

Scope: `server/` (686 lines) and `tests/protocol/` at `main` d723d3c (round-1 fix pass merged, spec 0.1.1 and the S-3 server change merged),
reviewed against `spec/core/protocol.md`, `spec/core/server-behavior.md` (0.1.1), `spec/core/schema/` and decision 0018. REV runs on Sonnet here by operator override
(OM-0016), although the 686 lines are above the 400-line Opus threshold. The launch named no `diff.meta.json`, so I did not run `check_snapshot.py`;
I reviewed the whole tree at the SHA above.

Severity scale (same as round 1): **blocker** breaks spec behavior or correctness. **major** must be fixed in this round (a spec gap that needs a rule decision or a test gap that hides a defect).
**minor** should be fixed and can follow. **nit** is cosmetic. Front-matter counts equal the tagged lines.

How I checked: `python3 tests/protocol/run.py` passes (135 tests) on Python 3.11, 3.12 and 3.13. All probes ran against a real `server/start.sh --port 0` process
(throwaway scripts under `/home/claude/aware/.work/rev-p2-r2/`, not committed): raw sockets for framing, request-line and header cases; a depth sweep and bisection; the S-1..S-13 behaviors from decision 0018;
a 128-thread stress run; 20000 random payloads against Python's `json`.

## Round-1 findings: verified

| Round 1 | Result | Evidence |
|---|---|---|
| B1 (500 and lost seq) | **fixed** | `jsonvalue.py:42-82` is iterative; `api.py:109` serializes once before the lock; `state.py:79-83` moves `_seq` only after `Delivered` exists. Probe: depths 480-519, 1000, 3000, 5000, 6000, 8000 give `201` (never 500). Seqs stayed contiguous (46 accepted, next new envelope got 47, the expected value). Bisection: first rejection at depth 9995 (arrays) and 9989 (objects) on 3.13, ~9991/9985 on 3.12, ~980 on 3.11, always `400 malformed_request` raised at parse time, never 5xx and no seq used. Depth 491/492/493 are stored and returned intact. A deep payload resent three times gets `200`. |
| B2 (unread body desyncs keep-alive) | **fixed for well-formed requests**, but see M1 (malformed header names still desync) | `httpd.py:54-56` closes when a declared body was not read. Probe, one socket, request then `GET /v1/info`: POST /v1/info with body, GET with body, GET with chunked, POST /nowhere, PUT /v1/session, OPTIONS with body, HEAD with body, 415, 413: each gets its status and the connection then closes (no bogus 405). Valid POST then GET on the same socket: `200, 200`. |
| M1 (no reuse test) | fixed | `test_transport.py:68-97`, ten paths on one `HTTPConnection`. See M2 for what it does not cover. |
| M2 (no depth test) | fixed | `test_send.py:144-160`, `162-170`, `171-180`. A recursive `dumps` would fail the 485-499 sweep with a 500, so it is not vacuous. |
| m1 (nesting order) | fixed | `api.py:27-36`, `jsonvalue.py:31-32`. Probe: 20000-deep payload with a wrong epoch, and with a bad `from`, both give `400 malformed_request`. |
| m2 (listen backlog) | fixed | `httpd.py:187`. 128 client threads, 4200 requests, 0 resets. |
| m3 (408 mapping) | fixed | `httpd.py:159-169`, branch gone. |
| m4 (ambiguous framing) | fixed | `httpd.py:97-101`. TE with Content-Length: `400`, closes. `Content-Length: 5` plus `Content-Length: 34`: `400`, closes. Identical repeats accepted (RFC 9112 allows it). |
| m5, m6, n1-n5, n7 | fixed | `test_send.py:134-137` exact pairs; `test_runtime.py:118,131` races (I measured 357 of 800 poll pages were partial while sends ran, so the poll test does interleave); `httpd.py:18,72`; `jsonvalue.quote`; `test_time.py` denylist; `test_runtime.py:160`. n6 (generator script) deferred as DEV proposed, outside the server boundary. |

## S-1..S-13 against the server (decision 0018)

| Id | Result |
|---|---|
| S-1 | Conforming. Array, string, null, number, bool payload: `400 invalid_payload` for `x` and `text`. Order held: epoch, invalid_name, invalid_id, invalid_type all beat it; it beats `unknown_sender`. Missing `payload` is `malformed_request`. |
| S-2 | Conforming. Same id with `created_at` differing by 1 ms is `409`; identical resend is `200`. Invalid `created_at` forms are `400`. |
| S-3 | Conforming. 15 digits accepted for `after` and `limit` (`next_cursor` echoes 999999999999999); 16 digits, leading zeros, `-1`, `+1`, `1.0`, fullwidth and Arabic-Indic digits, empty, `limit=0|00` all `400`; `%31` decodes to `1` and is accepted. |
| S-4 | Conforming except the leniency in m3. Case-insensitive media type, `charset` case-insensitive, quoted accepted, `latin-1`, `utf8`, `x=1`, `;` alone, `application/jsonx`, NBSP all `415`. |
| S-5 | Conforming. Repeated `epoch`, `after`, `limit` on E3 and E4: `400`; repeated unknown names ignored; E1 ignores the query. |
| S-6 | Conforming. Trailing slash, `//`, `/V1`, `%69nfo`, extra segment: `404`. `%62ob` and `BOB` resolve to `bob`; empty segment, `%2F`, `%00`, `%ff`, `%0A`: `400 invalid_name`. |
| S-7 | Conforming. `OPTIONS` `204` on `/v1`, `/v1/`, `/v1/anything`; `404` on `/`, `/v1x`, `/other`, `*`, `/V1/info`. |
| S-8 | Conforming. `HEAD` on known path `405`, unknown `404`, no body, `Content-Length` of the error body kept; unknown method names `405`/`404`; no `Allow` header (the substring "Allow" in my first check came from `Access-Control-Allow-Origin`). |
| S-9 | **Not conforming** in four of the listed cases. See B1, M1 and m1. Garbage request line, `HTTP/2.0`, `HTTP/1.1 extra`, oversize request line, 150 headers, one 70 KB header: `400` with the error body and `Connection: close` as specified. |
| S-10 | Conforming. Last duplicate wins (position of the first, value of the last, same as Python); 64+ levels accepted. |
| S-11 | Conforming. `--host localhost` prints `localhost`; the bound port is printed. |
| S-12 | Conforming. The E2 and E4 orders hold (`test_session.py:105`, `test_errors.py:142`). |
| S-13 | Conforming. The `ServerState(epoch, clock)` seam is unreachable from the CLI and the environment. |

## Findings

- [blocker] server/aware_server/httpd.py:54, 60-63 — **an HTTP/0.9-style request (no version token) crashes the handler: no response, a traceback on stderr, the connection dropped.** `_declares_body` calls `self.headers.get_all(...)`, but for a request line with only two words `http.server` leaves `self.headers` as a plain `dict`, so `AttributeError` escapes `_serve` (the call at line 54 is outside the `try`). Evidence (probe): `GET /v1/info\r\n\r\n` and `GET /v1/users\r\n` return zero bytes and the server prints `AttributeError: 'dict' object has no attribute 'get_all'` from `httpd.py:63`. The same family without a crash: `GET /v1/info HTTP/0.9\r\n...` is answered **without a status line** (`{"protocol":"aware",...` straight away), because `http.server` skips the status line and headers for `HTTP/0.9`. Decision 0018 S-9 and the §12 row `malformed_request` say a request that is not valid HTTP/1.1 (request line, version) is `400 malformed_request` with the error body, then close, and CORE-ERR-001 says every non-2xx carries the error body. The crash is a regression of the round-1 B2 fix (commit 4ad45b6 added `_declares_body`); before it the two-word form got a raw body, which also broke S-9. Fix in: server/aware_server/httpd.py. Override `parse_request` (or check at the top of `_serve`) so that any `request_version` other than `HTTP/1.1` (TL to say whether `HTTP/1.0` stays tolerated; today it is served with `Connection: close`) goes through `send_error(400)`; make `_declares_body` safe when `headers` is not a `Message`; keep the whole post-route block inside the `try`.
- [major] server/aware_server/httpd.py:43-63, 95-114 (inherited `http.server` header parsing) — **malformed header syntax is accepted, and one form re-opens the B2 desync.** S-9 and the §12 row name "header syntax" as a `400` plus close. Probes (each got `200` or was served): a header line without a colon (`Bad Header`); a non-ASCII header name (`\xff: y`); an obs-fold continuation line; bare-LF line endings; two spaces in the request line; NUL inside a header value; HTTP/1.1 with no `Host` or two `Host` headers (RFC 9112 §3.2 requires `400`). The serious one: **`Content-Length : 5` (space before the colon) is not matched by `headers.get_all("Content-Length")`**, so `_declares_body` is false, the connection stays open, and the five body bytes become the next request line. Probe (`GET /v1/info` with that header and body `hello`, then `GET /v1/users`): `200`, then `405 method_not_allowed` "Unsupported method ('helloGET')" in the server log. That is the round-1 B2 symptom again (a valid request answered with a bogus status), reachable by a request that RFC 9112 §5.1 says to reject. Fix in: server/aware_server/httpd.py. After the headers are parsed, reject (`400 malformed_request`, close): any raw header name that is not an RFC token or has whitespace before the colon (`self.headers.raw_items()` / `defects`), a line without a colon, a missing or repeated `Host`, and a bare LF if feasible. If TL prefers a lenient server for the rest, the minimum is: name with trailing whitespace, no-colon line, and `Content-Length`/`Transfer-Encoding` obs-fold are `400`.
- [major] tests/protocol/test_errors.py:42-48 — `test_CORE_ERR_001_garbage_request_lines_still_get_a_json_error_body` asserts only `400 <= status < 500` and that `"error"` appears in the body, on three inputs. Decision 0018 asked for `400 malformed_request` exactly ("Should tighten" item 4); that was not done, and the three samples do not include a version-less line, `HTTP/0.9`, a header without a colon, or a space before the colon. This is why B1 and the major above shipped green. `ConnectionReuse` (`test_transport.py:68-97`) likewise has no malformed-header case. Fix in: tests/protocol/test_errors.py and test_transport.py. Parametrize over the S-9 list (garbage line, 2-word line, `HTTP/0.9`, `HTTP/2.0`, no-colon header, `Content-Length :`, oversize line and header) asserting `(400, "malformed_request")`, `Content-Type`, `Connection: close`, and that a following request on a new connection works; add one pipelined case for the `Content-Length :` desync.
- [minor] server/aware_server/httpd.py (inherited `handle_one_request`) — an empty request line (`\r\n\r\n`) or a single leading blank line before a valid request is closed with **no response at all** (`b''`). S-9 says a garbage request line is `400`; RFC 9112 §2.2 says a server SHOULD ignore at least one leading empty line. Either is acceptable, silence is not. Fix in: server/aware_server/httpd.py (answer `400`, or skip one empty line), with a case in the S-9 test.
- [minor] server/aware_server/jsonvalue.py:33-34 — a valid JSON number whose exponent Decimal cannot hold (`{"a":1e999999999999999999999}`) gives `400 malformed_request`. CORE-HTTP-001 permits rejecting only deep nesting, and CORE-SRV-040 says the server does not interpret payloads. `1e999999999` is stored fine, so the cut-off is arbitrary. Fix in: server/aware_server/jsonvalue.py. Keep the raw text and compare numbers by (sign, digits, exponent) without `Decimal`, or ask TL to add a number-range allowance to S-10.
- [minor] server/aware_server/httpd.py:18 — `CONTENT_TYPE_RE` accepts what S-4 excludes: an unbalanced quote (`charset="utf-8` and `charset=utf-8"` give `200`), spaces around `=` (`charset = utf-8`, `200`), and a second `Content-Type` header is ignored (`application/json` then `text/plain`, `200`). Fix in: server/aware_server/httpd.py. Use `"utf-8"|utf-8` as one alternative, no whitespace around `=`, and reject more than one `Content-Type`. Add the cases to `test_transport.py:27-31`.
- [minor] tests/protocol/test_runtime.py:118-129 — the comment says "every 200 repeats the stored envelope" but nothing asserts it (the loop at 127-128 repeats the `assertIn` of line 123 and checks nothing new). Fix in: tests/protocol/test_runtime.py. Assert each non-`201` success has `seq == winner.seq` and the winner's `accepted_at`, and delete the redundant loop.
- [nit] server/aware_server/cli.py:46 — a bind failure (port in use, `--host ::1`) prints a full traceback and exits with 1. A one-line message is friendlier for the QA harness. Fix in: server/aware_server/cli.py (catch `OSError` around `make_server`).
- [nit] server/aware_server/httpd.py:72-75 — an absolute-form target (`GET http://x/v1/info HTTP/1.1`) is `404`; RFC 9112 §3.2.2 says a server MUST accept it. Not covered by S-6; no client sends it. Fix in: spec (S-6 note) or ignore.
- [nit] tests/protocol/test_send.py:144-160 — the sweep is tied to the old window 485-499; the real parse limit is about 9990 on 3.12/3.13 and about 980 on 3.11, and no case lands next to it. The behavior there is clean (probed), so this is only for the record. Fix in: tests/protocol/test_send.py (bisect the limit at run time and test it plus or minus one).
- [nit] generator/scripts/check_schema_examples.py:86 — round-1 n6 (`re.search` `$` before trailing newline) stays open by design. Fix in: generator/scripts/ (separate change).

## Concurrency, serializer, tests

- **Stress (128, 48 and 32 threads, ~4200 requests each run):** unique ids and ids shared by many threads, 30% immediate resends, polls with `limit` 1, 3 and 100 in between. Result every time: no client errors or resets, 201 count equals unique ids, seqs contiguous from 1, each duplicate accepted once with identical `seq`, every poll strictly ascending and a prefix of the final mailbox (no gap filled later), no `Traceback` on stderr. One probe run hung only because my script piped stderr and never read it; the server blocks on a full stderr pipe, which is expected and not a defect.
- **Serializer (`jsonvalue.dumps`):** 20000 random payloads (all control characters, ` `, `\ud800`/`\udc00` lone surrogates, surrogate pairs, U+10FFFF, BOM, NBSP, big and tiny numbers, `-0`, `1E+2`, 60000-digit numbers, nested and empty containers, escaped and raw input) were compared byte for byte with `json.dumps(..., ensure_ascii=True, separators=(",",":"))` after substituting numbers by their source text: **0 mismatches**. Output is always ASCII; duplicate keys keep the first position and the last value, like Python. `equal()` gives the expected answers (1 == 1.0 == 1e0, 0 == -0, true != 1, null != false, key order ignored, `1e400 != 1e401`).
- **Test quality:** the new tests are not vacuous except the points above. Verified by reading: the reuse, framing, boundary, precedence and race tests would each fail on the pre-fix behavior. The loosest remaining are test_errors.py:42-48 (major) and test_runtime.py:127-128 (minor).

## Notes

- B1 and the second major share one cause: the server trusts `http.server`'s request parsing, which is lenient. One validation step after `parse_request` (version, token-valid header names, `Host`, no obs-fold) closes S-9 for good and makes `_declares_body` safe.
- Convention proposal for later suites (extends round 1): every transport rule that says "then close" gets a test that sends the next request on the same socket and asserts it is not answered with a bogus status.

VERDICT: blockers
