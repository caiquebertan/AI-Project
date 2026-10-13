# 0013 — Operator approvals and MVP cuts
- Status: accepted (operator, 2026-10-13 17:00, OM-0011)
- Context: After the P1 drafts (spec 0.1.0-draft, backlog) the operator asked for a cost review focused on time (OM-0009). ORC proposed ten cuts; the operator accepted all of them, approved the backlog and the spec, and fixed the time rules (OM-0011).

## Approvals
| Item | Decision |
|---|---|
| Backlog (WORKFLOW decision 0002, Q24: approved once at P1) | **Approved**, with the cuts below applied by the PM before use |
| Spec core (gate G0) | **Approved as version 0.1.0 with the cuts and the time fix applied.** ORC sets `0.1.0` and the tag `spec-v0.1.0` only after the cuts are merged and verified. Any change after the tag counts against `spec_reopen` |
| TL open questions Q1-Q7 | Defaults accepted: unknown recipient accepted into a lazy mailbox (Q1); history cleared on server restart, unsent kept (Q2); names shown lowercase (Q3); order = server acceptance order (Q4); Android is exercised by a JVM command-line driver, no emulator requirement (Q5); web test hook always present (Q6); notes to self allowed (Q7) |
| PM open questions P1-P8 | Defaults accepted: names-only conversation list (P1); start a conversation by typing a name (P2); offline switch not remembered (P3); no notice after server restart (P4); no `Failed` look (P5, now moot: the state is withdrawn); **message times shown (P6), see below**; connection indicator semantics (P7); fixed English texts (P8). Refusal text for forbidden characters: the PM's proposed sentence |
| Message times (OM-0010, OM-0011) | The server expects and validates UTC; **no hardcoded local time zone anywhere**; clients send `created_at` in UTC; each client converts the server's UTC `accepted_at` to the device's local time only to display it |

## The ten cuts
| # | Cut | Where it lands |
|---|---|---|
| 1 | Acceptance is gated by the acceptance criteria; rule coverage is reported, not gated | `check_trace.py`, WORKFLOW E-QA-1, `spec/README.md` conventions |
| 2 | One core delivery (F1+F2+F3 generated and reviewed as one unit per app) instead of three loops | WORKFLOW P4, BACKLOG |
| 3 | Plain polling every 1 s with a fixed retry interval instead of long-poll and backoff | protocol, server behavior, constants, Appendix A |
| 4 | The `failed` message state is withdrawn | protocol, behavior, hooks, snapshot schema |
| 5 | No counting proxy and no Android debug state provider; offline-makes-no-requests is proven in the clients' own tests with a fake transport (web externally with the test framework's request events) | decision 0010 superseded, platform rules |
| 6 | Interop: web with web through the UI, and the Android JVM driver (Alice) with web (Bob); other pairings optional | scenarios, BACKLOG F4, WORKFLOW P5 |
| 7 | Server uses a light chain: DEV, one review, protocol tests; no TL plan, no QA agent | WORKFLOW P2, BACKLOG E2 |
| 8 | The delete-and-regenerate check runs once at the end (P7), not after every feature | `generator.json` `regen.per_feature=false`, WORKFLOW |
| 9 | The reactions demo (P6) is the first thing cut if time is short, and only starts after interop passes | WORKFLOW, BACKLOG |
| 10 | Retrospectives per milestone, not per feature stage; the run log stays script-written | WORKFLOW §10, retro template |

Second on the cut line, after reactions: **message-time display**. It is not in the brief; it was added at the operator's request (OM-0010) and is kept modular (`CORE-TIME-*` rules, the time hook, its scenario) so it can be withdrawn without touching other rules.

## Consequences
- Technical details of cuts 3, 4 and 5 are in decision 0014; the workflow changes are in `generator/WORKFLOW.md` v0.3.0.
- Because the `failed` state is gone, a message the server permanently rejects is discarded and logged (unreachable in a correct client, since the client validates first). A defective client could therefore drop a message silently; accepted for the MVP.
- Rule ids are never reused: withdrawn rules stay as one-line tombstones.
- Client builds and tests still run on the operator's machine (decision 0011).
