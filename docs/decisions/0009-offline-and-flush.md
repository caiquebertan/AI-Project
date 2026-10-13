# 0009 — Offline definition, connection cycle and flush order
> **Amended by 0014:** the connection cycle is session (when needed) → polls until `has_more` is false → flush → end. Cycles repeat every `CYCLE_INTERVAL_MS` (1000 ms), with no live long-poll step and no backoff: any failure ends the cycle and the next one starts after the same interval. Going offline starts no new request, and an in-flight request completes and is applied instead of being aborted. `online` now requires a session and a poll. Decision points 2 and 4, the jitter alternative and the abort consequence below are history.
- Status: proposed (awaiting G0)
- Date: 2026-10-13
- Author: TL (agent, claude-opus-5-5); app-controlled offline decided by operator (gap-analysis Q19, decision 0002)
- Spec ids driven: `CORE-CONN-*`, `CORE-OUTBOX-*`, `CORE-CONST-001` — in [`spec/core/protocol.md`](../../spec/core/protocol.md) and [`spec/core/server-behavior.md`](../../spec/core/server-behavior.md)

## Context
Brief steps 3–7 require each user to "go offline" and "reconnect" on demand. Real airplane mode is not scriptable identically on an emulator, a browser and a JVM test. The operator decided that offline is app-controlled: an explicit toggle sets it and real connectivity loss also triggers it, through a swappable connectivity abstraction. This record fixes the states, what may happen in each, and the exact order of requests on reconnect.

## Decision
1. **Inputs:** `offline_toggle` (user/test control, default off) and `network_available` (from a `ConnectivityMonitor` port; tests substitute a fake). The client is **allowed** to talk to the server iff the toggle is off and the network is available.
2. **Connection states:** `offline` (not allowed: zero HTTP requests; in-flight ones aborted and their results discarded), `connecting` (allowed, connection cycle not yet established or retrying after a failure), `online` (session succeeded in this cycle and no request has failed since).
3. **Every outgoing message goes through the persistent outbox**, online or not: one code path. The outbox is FIFO; at most one send is in flight; the next entry is sent only after the previous one is acked or failed (head-of-line).
4. **Connection cycle**, started whenever the client becomes allowed: (1) `POST /v1/session`; (2) catch-up polls with `wait=0` until `has_more` is false; (3) flush the outbox until empty; (4) long-poll loop, while new outbox entries are flushed as they appear. Any retryable failure aborts the cycle, sets `connecting`, waits the backoff (500 ms doubling to 8 s, no jitter) and restarts at (1).
5. Receive-before-flush (step 2 before 3) mirrors the brief's step 7 wording ("receives Alice's message ... and delivers his own queued message"). Final order does not depend on it (0006), but transient UI states become deterministic.

## Alternatives considered
- **Only real connectivity (no toggle).** Not reproducible on web (DevTools offline is not app-observable in the same way) or JVM; rejected by the operator.
- **Toggle only (ignore real connectivity).** Brief says "when offline"; real loss must also queue. Rejected.
- **Send directly when online, outbox only when offline.** Two code paths and a race at the transition. Rejected.
- **Parallel flush.** Faster, but `seq` order of one sender's messages could differ from compose order. Rejected.
- **Flush before catch-up.** Equally correct; chosen order matches the brief's wording.
- **Jittered backoff.** Irrelevant locally and non-deterministic in tests.

## Consequences
- Scenario steps 3–7 are drivable identically through the toggle (UI) or the test hook on both clients and in JVM/Vitest tests.
- A send aborted by going offline may already be accepted; the retry after reconnect returns `200` with the original `seq` (0007).
- The connection state is observable (`offline` / `connecting` / `online`) through the test hooks on both platforms.

## Brief constraint affected
Required behavior 3 ("Messages queue locally when offline and flush when the client reconnects").
