# 0019 — P2 closed after review round 2, with known gaps

Status: accepted (operator, OM-0017)

## Decision
- P2 (reference server and protocol tests) is closed. Review round 3 and a new stress run are skipped; the round 3 agent was stopped before it reported.
- The loose header handling named in review round 2 was already fixed by fix pass 2 (`docs/runs/P2/fix-2.md`), so no further DEV pass was needed.
- Remaining loose tests and unverified areas are recorded in `docs/runs/P2/known-gaps.md`.

## Risk accepted
The strict HTTP/1.1 parser written in fix pass 2 was never reviewed or probed with real clients. The first real test is interop at P5. If a client request is rejected there, check `server/aware_server/httpd.py` first (HTTP/1.0 rejection, header strictness).

## Consequences
- E-PROTO-1 is green on 138 tests; the state machine records P2 as done with the operator's pass at S4 (OM-0017).
- The P3 generator implementation starts (decisions 0016 Q6, 0017).
