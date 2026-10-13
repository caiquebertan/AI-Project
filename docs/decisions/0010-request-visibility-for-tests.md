# 0010 — Request visibility for tests: per-client counting proxy
> **Superseded by 0014:** no counting proxy. In-project tests use a recording fake `Transport` (PLAT-HOOK-014), external web tests count with Playwright request events, and Android is driven by the JVM driver `:tools:driver`. PLAT-HOOK-012 is withdrawn.
- Status: superseded by 0014
- Date: 2026-10-13
- Author: TL (agent, claude-opus-5-5), on PM request (d.4) in `docs/planning/g0-review-pm.md`
- Spec ids driven: `PLAT-HOOK-012`, `CORE-SRV-007` (unchanged, stays `SHOULD`); checks `CORE-CONN-004`, `CORE-OFFLINE-002` (AC-F4-3)

## Context
AC-F4-3 and CORE-OFFLINE-002 assert that an offline client makes **no** request. An external test needs a dependable count of the requests made by each client. CORE-SRV-007 (a request log) is only a `SHOULD`, and the coordinator suggested promoting it to `MUST` with a test-only endpoint that returns counts per client name.

## Decision
Tests count requests with a **per-client counting proxy** owned by `tests/` (QA): a small HTTP pass-through between one client and the server that records every request (method, path, time) and exposes the count to the test. Each client under test is pointed at its own proxy through its normal base-URL configuration (PLAT-ANDROID-013, PLAT-WEB-011). PLAT-HOOK-012 requires that every client request goes to that single base URL. The server gets no test-only endpoint; CORE-SRV-007 stays `SHOULD`, ids unchanged.

## Alternatives considered
- **Promote CORE-SRV-007 to `MUST` plus a server endpoint with counts per name.** Rejected. The server can attribute a request to a user only when the request names one (session body, `from`, mailbox path). `GET /v1/info`, `GET /v1/users`, and requests rejected before parsing (`413`, `415`, bad JSON) carry no name, yet they are exactly the requests a buggy offline client might make. "No request" would be checked with blind spots. It would also add a test-only surface to the server contract.
- **Clients send an identifying header.** It would change the core client contract for test purposes only. Rejected.
- **Count from client-side hooks (snapshot counter).** The client would be counting its own violations. A buggy client would under-report.

## Consequences
- QA writes about 40 lines of stdlib proxy in `tests/` (P2/P5). It also works against any server.
- Web: the proxy URL is passed as `?server=`, which a relaunch (page reload) keeps. Android: the proxy URL is the build-time `aware.serverUrl`, or `adb reverse` maps to it; the JVM interop driver (G0 Q5) takes it as an argument.
- The proxy must pass long-polls through without buffering, and closing its upstream must not count as a client request.

## Brief constraint affected
None (local only).
