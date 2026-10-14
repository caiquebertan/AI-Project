# Smoke modules (session A, token-free)

Used only by `apply_templates.py --smoke` / `smoke_build.py`; never copied into `clients/`. One small module per
kind, at the real module paths, so the configured build and test commands run unchanged. Each test name starts
with a spec id so the run also checks that ids reach the JUnit report. Generator design §2.3, §5.
