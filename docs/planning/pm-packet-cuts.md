# PM packet: changes after the MVP cuts (spec 0.1.0, OM-0011)

> **Author:** PM agent (sonnet), stage S0 (behavior half of the cuts), ref OM-0011. AI-written; the operator accepted the cuts in decision 0013, the TL covered the technical half in decision 0014. ORC sets the version and tag and recomputes the counts in `spec/README.md` after merging both deltas.
> **Files changed:** `spec/core/client-behavior.md`, `spec/scenarios/alice-bob-offline.md`, `spec/scenarios/additional-scenarios.md`, `docs/product/BACKLOG.md`, `docs/product/TRACEABILITY.md`, this packet. Nothing under `spec/core/protocol.md`, `server-behavior.md`, `schema/`, `spec/platform/`, `clients/` or `generator/` was touched.

## 1. What a user sees now (differences)

- **No `Failed` look.** Message labels are `Pending`, `Sent`, `Received`. A message the server rejects for good is discarded and written to the diagnostic log (CORE-OUTBOX-005); it leaves every view, and a conversation whose only message it was leaves the list. A correct client never reaches this because it validates first (CORE-SEND-004).
- **Offline starts no new request.** A request already running may finish and its result shows (for example a message turns `Sent` just after the switch was turned on). Nothing further is started until the client is allowed again.
- **`Online` means a session and then a poll have succeeded** since the client became allowed or since the last failed request. Queued messages are delivered in the same round, so `Online` can show a moment before the first `Pending` message turns `Sent`.
- **Retry is fixed**, one second after a failed attempt, every second while it keeps failing; no growth.
- **Delivery of a new message** happens in the next round, up to about one second plus the request time; it shows `Pending` until then. Messages from the other user reach a client within the same bound.
- **Times** are unchanged in behavior (server `accepted_at` in UTC shown in the device's local time, CORE-TIME-001..003, CORE-VISIBLE-009..012); the backlog now states UTC everywhere and that no time zone is hardcoded.

## 2. Ids

### Withdrawn ids

| Id | Where | Now |
|---|---|---|
| `CORE-SEND-009` | `client-behavior.md` section 4.2 | one-line tombstone (the `Failed` look and its rules) |
| `AC-F2-12` | `client-behavior.md` section 9, F2 | tombstone (labels incl. `Failed`; also carried the no-receipts check, see open point 1) |
| `AC-F2-13` | `client-behavior.md` section 9, F2 | tombstone (the `Failed` message look) |

All other withdrawn ids of decision 0014 (`CORE-EPOCH-006`, `CORE-SRV-012..014`, `PLAT-HOOK-012`, `PLAT-ANDROID-017`) are TL-owned; no PM-owned file cited any of them (checked). The PM-owned `Failed` mentions that were not ids are gone: section 1 (unsent message), section 8.1 (label list and mapping), `CORE-SEND-008`, `CORE-ORDER-002`, `CORE-VISIBLE-002`, `-008`, `-009`, `AC-F2-20`, backlog story S-F2-7 (marked withdrawn, id kept).

### Reworded rules (same id, changed meaning)

| Id | Change |
|---|---|
| CORE-SEND-008 | going offline or a timeout never marks `Sent`; no `Failed` |
| CORE-OFFLINE-002 | no new request while not allowed; a request in flight is not cancelled, may finish, result applied |
| CORE-OFFLINE-003 | sending offline starts no request, only joins the queue |
| CORE-OFFLINE-005 | `Connecting` at once, first contact starts at once (CORE-CONN-005); `Online` after session then poll (CORE-CONN-003) |
| CORE-OFFLINE-006 | `Online` and `Connecting` defined as CORE-CONN-003; fixed one second retry |
| CORE-OFFLINE-007 | delivery under way is not cancelled: `Sent` if its ack arrives, else `Pending`; no further delivery |
| CORE-FLUSH-005 | retry one second after the failed attempt, then every second |
| CORE-FLUSH-006 | delivered in the next round, up to about one second (`CYCLE_INTERVAL_MS`) plus request time |
| CORE-ORDER-002 | only `Pending` is unsent |
| CORE-VISIBLE-002 | list entries count `Pending` only; a discarded message no longer counts |
| CORE-VISIBLE-008 | only `Pending` messages stay after a server restart (basis CORE-EPOCH-004; the withdrawn epoch rule was never cited) |
| CORE-VISIBLE-009 | only `Pending` shows no time |
| Section 1, 8.1 | unsent message = `pending`; labels and state mapping without `Failed` |

### Reworded and new acceptance criteria

`AC-F2-20` (no `Failed` sentence), `AC-F3-1` (no new request; a running one may finish), `AC-F3-4` (`Online` after registration and reading waiting messages), `AC-F3-11` (in-flight delivery may still finish), `AC-F3-12` (delivery within about a second), `AC-F4-3` (no new request since the switch), `AC-F4-5` (`Online` after session and poll), `AC-F4-9` (the two required pairings). No new AC id was added.

## 3. Scenarios

- **Pairings** (main scenario section 3): web with web through the UI, and Android JVM driver (Alice) with web UI (Bob), citing PLAT-ANDROID-031..033 and PLAT-WEB-024; others optional. P-1..P-4 and the emulator note are gone. Android screens are checked only by Robolectric tests (PLAT-ANDROID-022).
- **Hook mentions:** PLAT-HOOK-006 is described by both mechanisms (web `window.__AWARE__`, Android driver `snapshot`).
- **SC-3:** "starts no new request"; how it is counted externally (driver request count, Playwright request events) is stated.
- **SC-5:** `Online` timing and the order `Online` then `Sent`.
- **SX-4:** a UI edge-case scenario; Android only in Robolectric, the driver covers its own name and text checks.
- Additional-scenarios pairing line rewritten the same way. SC-1..SC-8, SX-1..SX-6 expected tables are unchanged.

## 4. Backlog

D1 = F1+F2+F3 as one delivery per app (full chain), F4 and F5 as in decision 0013; cut order stated at the top (F5 first, message-time display second); acceptance gated by ACs, rule coverage informational; regeneration check once at P7; E2 light chain; F4 required pairings; times UTC everywhere with local display; statuses `optional` and `withdrawn` added; stale risks (20 second waits, Q5 dependency) replaced.

## 5. Traceability

Nine rows of the two withdrawn ACs removed (224 rows before, 215 now). No row cites a withdrawn id. The column table and the duplicated `## F1` block at the top, which were damaged on main, were restored. The F4 intro names the required pairings.

## 6. Numbers for the README (ORC recounts)

By script on this branch: `client-behavior.md` 53 rule ids (was 54; its tombstone is not counted), 37 acceptance criteria there (was 39); scenarios 9 + 6; total 52 acceptance criteria (was 54). Rows of `check_trace.py`: 210 AC-scope rows.

## 7. Checks run

- `.work/pm-scratch/check_ids.py` (throwaway, outside the worktree): every id cited in the six files exists and is not withdrawn, except in tombstones and the "Withdrawn ids" table above: 0 problems (303 ids defined, 9 withdrawn).
- `python3 -m unittest discover -s generator/tests`: 82 tests OK. `generator/scripts/lint_prompts.py`: 0 findings. `check_trace.py --feature F1,F2,F3,F4`: parses 210 AC rows; all `unmet: no test found` because no test exists yet (expected before D1).

## 8. Open points

1. **No AC checks "no receipts, typing or unread indicator" any more.** The withdrawn label criterion (second row of the table in section 2) carried `CORE-VISIBLE-006` and `CORE-VISIBLE-005`. Both rules stay, covered only by rule-level tests (informational). Suggest a new AC id if the operator wants them gated; I did not add one (outside the cut list).
2. **`Online` before `Sent`.** Because `Online` now needs session then poll, and flush follows in the same round, the scenarios wait on the full completion condition; a test that expects `Sent` the instant `Online` appears will be flaky. Written into SC-5.
3. **Android UI behavior is not externally testable.** With no emulator, the validation texts, composer messages and on-screen times of Android are proven only by Robolectric and JVM tests. This weakens AC-F2-2, -4, -15 and -17..23 for Android; accepted by decision 0013 cut 6 but worth knowing at grading.
4. **A silently dropped message** (class P) has no user-visible trace; accepted in decision 0013.
