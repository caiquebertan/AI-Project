# Fix pass 1 for P2 / server (review round 1)

Branch `fix/p2-review1`, based on `main` 09bf4dc. Findings are those of `docs/runs/P2/review-1.md`. `spec/` is unchanged.

| Id | Status | What was done |
|---|---|---|
| B1 (500 and consumed seq) | fixed | `jsonvalue.dumps` is now iterative (no stack limit, cannot raise for a parsed value). `api.send` serializes the payload once, before the lock, and `ServerState.accept` takes the text. `_seq` is assigned only after the envelope exists (clock read and `Delivered` built first), so nothing that can fail runs after the counter moves. The pre-check that disagreed with the store is removed. |
| B2 (unread body corrupts keep-alive) | fixed | `Handler._serve` sets `close_connection` whenever the request declares a body (`Content-Length` other than 0, or any `Transfer-Encoding`) that `_read_body` did not consume. The existing `_drain` then runs. |
| M1 (no connection-reuse test) | fixed | `ConnectionReuse` in `test_transport.py`: ten error and no-read paths (405, 404, GET/OPTIONS/PUT with body, 415, 413, 400 after a read body), each followed by a valid request on the same `HTTPConnection` that must get `200`. Plus a pipelined raw-socket test. |
| M2 (no boundary-depth test) | fixed | `test_send.py`: sweep of depths (including 485..499, 5000, 20000) asserting no 5xx, only `201` or `400 malformed_request`, contiguous seqs and an unharmed next seq; explicit 491/492/493 test; precedence test for CORE-ERR-002. |
| m1 (nesting order, rule not in spec) | fixed (kept bound) | The only bound left is the parser's own failure, raised inside step (2) (`parse` maps `RecursionError` to `ValueError`), so it is `malformed_request` with the CORE-ERR-002 precedence (tested with a wrong epoch and a bad `from`). With dumps iterative, depth 491..493 are now stored (previously 492 gave 500). The limit is interpreter dependent (about 5000 to 10000 on 3.13); S-10 stays open for TL. |
| m2 (listen backlog) | fixed | `request_queue_size = 128` on `AwareServer`. No dedicated test: a backlog overflow is not reproducible deterministically. |
| m3 (408 mapping) | fixed | Branch removed. |
| m4 (ambiguous framing) | fixed | In `_read_body`, after the 415 check: `Transfer-Encoding` with `Content-Length`, or differing `Content-Length` values, is `400 malformed_request` and closes. Identical repeated values are accepted (RFC 9112 allows them). Tests added. |
| m5 (`>= 400` asserts) | fixed | Exact `(status, code)` pairs in the CORE-SEQ-001 test. |
| m6 (two concurrency races untested) | fixed | `test_runtime.py`: one id with four different bodies sent concurrently (exactly one `201`, rest `200` or `409`, one stored); polls alongside sends (each poll sequence is a prefix of the final mailbox, no gap filled later). |
| n1 (`_s` private import, two JSON styles) | partly fixed | `_s` moved to `jsonvalue.quote`; `api` and `state` import it. `info` and `users` keep `json.dumps` (deterministic, no payload); left as is. |
| n2 (partition twice) | fixed | |
| n3 (`\s` accepts NBSP) | fixed | `CONTENT_TYPE_RE` uses `[ \t]`; test added. |
| n4 (comment S-3 vs S-1) | fixed | |
| n5 (denylist misses ctime, asctime, 1-arg strftime) | fixed | Patterns and self-test samples added. |
| n6 (`check_schema_examples.py` `$` before newline) | deferred | Outside the server boundary (generator). Fix is `re.search("(?:%s)\\Z" % pattern, ...)`; propose as a separate generator change. |
| n7 (OPTIONS outside /v1 untested) | fixed | `test_CORE_SRV_005_options_outside_v1_is_404`. |

Not touched: the S-3 cursor 15-digit cap (waits for operator approval of decision 0018, spec 0.1.1).

Checks: `python3 tests/protocol/run.py` 132 tests OK in five consecutive runs (121 before, 11 added); `python3 -m unittest discover -s generator/tests` 98 OK; `lint_prompts.py` clean. Against the pre-fix server, six of the new tests fail (both blockers, NBSP, both framing cases), so they catch the defects.
