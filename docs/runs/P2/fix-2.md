# Fix pass 2 for P2 / server (review round 2)

Branch `fix/p2-review2`, based on `main` d30c1c5. Findings are those of `docs/runs/P2/review-2.md`. `spec/` is unchanged.

| Id | Status | What was done |
|---|---|---|
| B1 (version-less request line crashes the handler) | fixed | `Handler.parse_request` is replaced by a small strict parser (stdlib only). The request line must be `METHOD SP target SP HTTP/1.1` with CRLF; anything else (two-word line, empty line, HTTP/0.9, HTTP/1.0, HTTP/2.0, bad token, double space, bare LF, control characters in the target) goes through `send_error(400)`: `400 malformed_request`, error body, `Connection: close`, no traceback (checked on a real process). `self.headers` is always an `HTTPMessage`, so `_declares_body` is safe. HTTP/1.0 is no longer served (S-9 says not valid HTTP/1.1 is 400; TL may relax). |
| M1 (header syntax accepted, `Content-Length :` desync) | fixed | The same parser reads the headers itself: a name must be an RFC token (rejects `Name :`, spaces, non-ASCII names), a colon is required (no-colon lines), obs-fold, bare LF and EOF inside the header block are 400, control characters (NUL) in a value are 400, at most 100 headers, line limit 65536, exactly one `Host`. A body declaration the server cannot see is now impossible; `_declares_body` stays as the second line of defense. |
| M2 (weak garbage-request test) | fixed | `test_errors.py`: 25 cases (the S-9 list plus the review's probes) each assert exactly `(400, malformed_request)`, error `Content-Type`, `Connection: close`, a schema-valid error body, that a valid request pipelined on the same connection is not answered (exactly one response), and that a new connection works. `test_transport.py` adds the dedicated `Content-Length :` pipelined case. |
| m1 (empty request line or leading blank line closed silently) | fixed | Answered with 400 (RFC 9112 2.2 allows either); in the S-9 test (`empty request line`, `leading blank line`). |
| m2 (exponent beyond Decimal) | fixed | `Num` no longer uses `Decimal`: value is (negative, digits, exponent) with zeros stripped, compared as ints; `1e999999999999999999999` is stored and returned verbatim, `0.50 == 5e-1` by value. Remaining limit: an exponent of more than 4300 digits (Python's int-string limit) is still 400. |
| m3 (Content-Type strictness, S-4) | fixed | Regex accepts `charset=utf-8` or `charset="utf-8"` only as one alternative, no blanks around `=`; a repeated `Content-Type` is 415. Cases added to `test_transport.py`. |
| m4 (race test asserts nothing) | fixed | Every non-409 response must carry the winner's `seq` and `accepted_at`; redundant loop removed. |
| n1 (bind failure traceback) | fixed | `cli.main` catches `OSError` around `make_server`: one stderr line, exit 1; test added (port in use). |
| n2 (absolute-form target is 404) | deferred | Not covered by S-6, no client sends it; for TL as a spec note (S-6) or ignore. |
| n3 (sweep tied to the 485-499 window) | fixed | The nesting test bisects the parser limit at run time (64 accepted, 20000 rejected) and tests limit-1, limit and limit+1 for 5xx, seq and contiguity; the fixed-window 491..493 test is removed. |
| n4 (`check_schema_examples.py` `$` before newline) | deferred | Outside the server boundary; separate generator change, as in round 1 (fix-1 n6). |

Checks: `python3 tests/protocol/run.py` 138 tests OK in five consecutive runs (135 before); generator unit tests 98 OK; `lint_prompts.py` clean. Against the pre-fix server six of the new tests fail.
