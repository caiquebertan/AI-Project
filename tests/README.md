# Tests

- `protocol/` — server conformance against `spec/core/`: stdlib unittest, `python3 tests/protocol/run.py [--junit report.xml]` (P2). Test names carry the rule ids they cover (`test_CORE_SRV_030_...`; the JUnit report writes `CORE-SRV-030`).
- `interop/` — drive the Alice/Bob scenario through the server with both clients. ☐
- Regeneration check: delete `clients/`, regenerate, rerun the above. ☐
