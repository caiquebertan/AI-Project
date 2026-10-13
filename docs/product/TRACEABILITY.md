# Traceability

Brief requirement → spec id → acceptance criterion → test → status (WORKFLOW §3, evals E-PM-1, E-PM-3, E-QA-1).

- **Writers:** PM adds rows at S1 (Trace); `generator/scripts/check_trace.py --write` sets the `Status` column at S6. Nobody else edits this file.
- **Rows** are grouped under one `## <feature-id>` heading per feature (for example `## F1`). Each row is one AC for one scope.
- **Columns** (fixed order, parsed by position):

| Column | Meaning | Example |
|---|---|---|
| BR/SC id | Brief requirement (`BR-n`) or brief scenario step (`SC-n`) | `BR-1` |
| Spec id | The spec rule the AC checks (`CORE-xxx`, extension or platform id) | `CORE-001` |
| AC id | Acceptance criterion id, `AC-<feature>-<n>`; the AC text lives in the spec, not here | `AC-F1-1` |
| Scope | `core`, `platform:android` or `platform:web` | `core` |
| Test id | One or more test ids (comma separated). A test carries its id in its name. | `T-F1-1` |
| Status | `pending` → `met` / `unmet` (written by `check_trace.py`) | `pending` |

A row is `met` when every listed test id matches at least one test in the reports and all matching tests passed.

<!-- Rows start below (P1). Keep the header row; add `## <feature-id>` sections with their own copy of the table. -->

| BR/SC id | Spec id | AC id | Scope | Test id | Status |
|---|---|---|---|---|---|
