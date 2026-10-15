# 0020 — Wrap-up: scope cut after the token budget ran out

- Status: accepted by the operator (OM-0023, 2026-10-14)
- Context: both clients were generated on the operator's machine (web 126 tests, Android 129 tests), the web regeneration check passed, and the operator's Claude Pro window can no longer cover the Android check or the remaining phases.
- Decision: package now. Cut (moved to `FUTURE.md`):
  1. P4 acceptance suites (QA-designed `tests/web-e2e/`, `tests/android-conformance/`) and the traceability gate (`check_trace`: 0/172 ACs met because generated tests carry AC ids, not the `T-F…` ids the table expects).
  2. P5 interop through the real server (`tests/interop/`, 3 green runs).
  3. P6 reactions demo (the evolution test).
  4. P7 Android regeneration check (web done: PASS).
  5. P8 signing rebase, re-tagging and force-push.
- Kept: README, DESIGN.md, AGENTS.md, FUTURE.md, D1 retro, one zip containing `.git`.
- Consequence: the README must say plainly what is verified (unit and scenario-replay tests on both clients, 138 server protocol tests, 142 harness tests, web delete-and-regenerate PASS) and what is not (no run against the real server through the UI, no emulator, no Android delete-and-regenerate).
