# P2 server: known gaps at close

P2 closed by the operator after review round 2 and fix pass 2, without round 3 and without a new stress run (OM-0017, decision 0019). All blockers and majors of rounds 1 and 2 are fixed (see `fix-1.md`, `fix-2.md`). Protocol suite: 138 tests green.

## Not verified (no review or probe happened after fix pass 2)
- The new hand-written strict HTTP/1.1 parser (`server/aware_server/httpd.py`) was tested by DEV's own tests only. Not probed: real clients (curl, OkHttp, browser fetch) with unusual but valid headers, `Expect: 100-continue`, chunked request bodies, slow or split sends, header and request-line size limits, abrupt disconnects mid-body, idle connection and thread cleanup.
- The concurrency stress run (up to 64 threads) was done on the round 1 code and on round 2's code, not on the code after fix pass 2.
- The Decimal-free JSON number type got no independent review.
- The interop run at P5 (web UI and Android driver against this server) is the first test with real clients. A failure there that points at the server is expected to be a parser strictness problem; look at `httpd.py` first.

## Known behavior and small defects, deliberately left
- HTTP/1.0 requests are rejected with 400 (spec S-9: not valid HTTP/1.1). TL may relax this.
- Absolute-form request targets (`GET http://host/v1/info HTTP/1.1`) answer 404; not covered by S-6.
- An exponent of more than 4300 digits (Python's int-string limit) still returns 400.
- The JSON nesting limit depends on the interpreter (about 5000 to 10000 levels on Python 3.13); spec S-10 only requires 64.
- `info` and `users` responses still use `json.dumps` instead of the shared serializer.
- No test for listen-backlog overflow (not reproducible deterministically).
- `generator/scripts/check_schema_examples.py`: a `$` before a trailing newline can let a pattern match a value with a newline at the end (fix suggested in `fix-1.md`; generator code, not server).
- 46 rule ids bind clients only and have no server test by design (list in the P2 report).
