# P7 — Regeneration check (partial)

| App | Result | Evidence |
|---|---|---|
| web | **PASS** (2026-10-15, 01:14Z) | `regen-web.json`, `regen-web.log` |
| android | **not run** (token budget; decision 0020) | first generation only: `docs/runs/D1/android/` |

Command (operator's Mac): `python3 generator/scripts/regen_check.py --app web --clone`.
It cloned the repo at HEAD (`4f50ad9`), deleted `clients/web`, ran `claude -p "/generate web"` with the pinned model `claude-opus-5-5` (about 23 minutes), then `npm ci && npm run build`, `npm test`, `apply_templates --check` and `check_headers --strict`. Every step exited 0 and no file changed outside `clients/web/` (boundary check).

Not shown by this run: a second regeneration to measure determinism (E-DET-1), and a README-only run by someone else (S-E6-2).
