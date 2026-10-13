# Server (hand-written)

Reference server for protocol v1: Python 3.10+, standard library only, one process, all state in memory, one thread per
connection, JSON over HTTP/1.1 under `/v1`. It implements [`spec/core/server-behavior.md`](../spec/core/server-behavior.md)
and the server side of [`spec/core/protocol.md`](../spec/core/protocol.md). It is not generated and has no security
(no authentication, TLS, rate limit or persistence). Questions about behavior are answered by the spec, not by this code.

## Run

```sh
server/start.sh                      # 127.0.0.1:8080
server/start.sh --port 0             # any free port
server/start.sh --host 127.0.0.1 --port 9000
AWARE_HOST=127.0.0.1 AWARE_PORT=9000 server/start.sh
python3 -m aware_server --port 0     # from inside server/ (or with PYTHONPATH=server)
```

| Setting | Option | Environment | Default |
|---|---|---|---|
| Host | `--host` | `AWARE_HOST` | `127.0.0.1` |
| Port | `--port` (`0` = free port) | `AWARE_PORT` | `8080` |

Options win over the environment (CORE-SRV-002). When the server accepts connections it prints exactly one line on
standard output, `aware-server listening on http://<host>:<port> epoch=<epoch>` (CORE-SRV-006); test harnesses read the
real port from it. One line per request goes to standard error: method, path without query, status, duration
(CORE-SRV-007). Stop with Ctrl-C or SIGTERM; everything is lost, and the next start has a new epoch.

## Endpoints

| Id | Request | Success |
|---|---|---|
| E1 | `GET /v1/info` | `200` capabilities, epoch, limits |
| E2 | `POST /v1/session` | `200` `{name, epoch, new_user}` |
| E3 | `POST /v1/messages?epoch=<epoch>` | `201` new, `200` duplicate: `{id, seq, accepted_at, epoch}` |
| E4 | `GET /v1/mailboxes/<name>/messages?epoch=<epoch>&after=<cursor>&limit=<n>` | `200` `{epoch, messages, next_cursor, has_more}`, always answered at once |
| E5 | `GET /v1/users` | `200` `{users: [{name, capabilities}]}` |

Errors use `{"error": {"code", "message"}}` with the codes and statuses of protocol section 12. There is no time zone
anywhere: `accepted_at` is read from a UTC clock and `created_at` is only checked for its exact UTC form (CORE-SRV-037).

## Layout

| File | Content |
|---|---|
| `start.sh` | start script |
| `aware_server/cli.py` | options and environment, the listening line |
| `aware_server/httpd.py` | routing, `Content-Type` and `Content-Length` checks, CORS, request log, error bodies |
| `aware_server/api.py` | endpoint logic and the validation order of CORE-SRV-030 / CORE-ERR-002 |
| `aware_server/state.py` | registry, id index, mailboxes, `seq`; every read-modify-write under one lock (CORE-SRV-004) |
| `aware_server/validation.py`, `jsonvalue.py` | field rules; exact JSON numbers, value equality, verbatim payload text |
| `aware_server/constants.py` | the constants table of protocol section 13 (a test compares it with `spec/core/schema/constants.json`) |

`ServerState(epoch=..., clock=...)` accepts a fixed epoch and a millisecond clock for the Appendix A replay in
`tests/protocol/`; the command line and the environment cannot set them.

## Tests

```sh
python3 tests/protocol/run.py                        # all protocol tests
python3 tests/protocol/run.py --junit report.xml     # plus JUnit XML for check_trace.py
python3 -m unittest discover -s tests/protocol       # plain unittest
```

Open questions about the spec are in [`docs/runs/P2/spec-issues.md`](../docs/runs/P2/spec-issues.md).
