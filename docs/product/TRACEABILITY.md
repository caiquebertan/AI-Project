# Traceability

Brief requirement → spec id → acceptance criterion → test → status (WORKFLOW §3, evals E-PM-1, E-PM-3, E-QA-1).

- **Writers:** PM adds rows at S1 (Trace); `generator/scripts/check_trace.py --write` sets the `Status` column at S6. Nobody else edits this file.
- **Rows** are grouped under one `## <feature-id>` heading per feature (for example `## F1`). Each row is one AC for one scope.
- **Columns** (fixed order, parsed by position):

| Column | Meaning | Example |
|---|---|---|

## F1

F1 — Identity and login.

Test ids for `AC-F1-<n>`: core (external checks in `tests/`) `T-F1-<n>`, android in-project `T-F1-<100+n>`, web in-project `T-F1-<200+n>`.

| BR/SC id | Spec id | AC id | Scope | Test id | Status |
|---|---|---|---|---|---|
| BR-1 | CORE-LOGIN-001 | AC-F1-1 | core | T-F1-1 | pending |
| BR-1 | CORE-LOGIN-001 | AC-F1-1 | platform:android | T-F1-101 | pending |
| BR-1 | CORE-LOGIN-001 | AC-F1-1 | platform:web | T-F1-201 | pending |
| BR-1 | CORE-LOGIN-004 | AC-F1-2 | core | T-F1-2 | pending |
| BR-1 | CORE-VISIBLE-001 | AC-F1-2 | core | T-F1-2 | pending |
| BR-2 | CORE-VISIBLE-002 | AC-F1-2 | core | T-F1-2 | pending |
| BR-1 | CORE-LOGIN-004 | AC-F1-2 | platform:android | T-F1-102 | pending |
| BR-1 | CORE-LOGIN-004 | AC-F1-2 | platform:web | T-F1-202 | pending |
| BR-1 | CORE-LOGIN-002 | AC-F1-3 | core | T-F1-3 | pending |
| BR-1 | CORE-LOGIN-003 | AC-F1-3 | core | T-F1-3 | pending |
| BR-1 | CORE-LOGIN-002 | AC-F1-3 | platform:android | T-F1-103 | pending |
| BR-1 | CORE-LOGIN-002 | AC-F1-3 | platform:web | T-F1-203 | pending |
| BR-1 | CORE-LOGIN-002 | AC-F1-4 | core | T-F1-4 | pending |
| BR-1 | CORE-LOGIN-004 | AC-F1-4 | core | T-F1-4 | pending |
| BR-3 | CORE-OFFLINE-006 | AC-F1-4 | core | T-F1-4 | pending |
| BR-1 | CORE-LOGIN-002 | AC-F1-4 | platform:android | T-F1-104 | pending |
| BR-1 | CORE-LOGIN-002 | AC-F1-4 | platform:web | T-F1-204 | pending |
| BR-1 | CORE-LOGIN-005 | AC-F1-5 | core | T-F1-5 | pending |
| BR-4 | CORE-VISIBLE-004 | AC-F1-5 | core | T-F1-5 | pending |
| BR-1 | CORE-LOGIN-005 | AC-F1-5 | platform:android | T-F1-105 | pending |
| BR-1 | CORE-LOGIN-005 | AC-F1-5 | platform:web | T-F1-205 | pending |
| BR-1 | CORE-VISIBLE-001 | AC-F1-6 | core | T-F1-6 | pending |
| BR-3 | CORE-OFFLINE-001 | AC-F1-6 | core | T-F1-6 | pending |
| BR-1 | CORE-VISIBLE-001 | AC-F1-6 | platform:android | T-F1-106 | pending |
| BR-1 | CORE-VISIBLE-001 | AC-F1-6 | platform:web | T-F1-206 | pending |
| BR-1 | CORE-LOGIN-006 | AC-F1-7 | core | T-F1-7 | pending |
| BR-1 | CORE-LOGIN-006 | AC-F1-7 | platform:android | T-F1-107 | pending |
| BR-1 | CORE-LOGIN-006 | AC-F1-7 | platform:web | T-F1-207 | pending |

## F2

F2 — Send and receive.

Test ids for `AC-F2-<n>`: core (external checks in `tests/`) `T-F2-<n>`, android in-project `T-F2-<100+n>`, web in-project `T-F2-<200+n>`.

| BR/SC id | Spec id | AC id | Scope | Test id | Status |
|---|---|---|---|---|---|
| BR-2 | CORE-SEND-001 | AC-F2-1 | core | T-F2-1 | pending |
| BR-2 | CORE-SEND-003 | AC-F2-1 | core | T-F2-1 | pending |
| BR-2 | CORE-VISIBLE-002 | AC-F2-1 | core | T-F2-1 | pending |
| BR-2 | CORE-SEND-001 | AC-F2-1 | platform:android | T-F2-101 | pending |
| BR-2 | CORE-SEND-001 | AC-F2-1 | platform:web | T-F2-201 | pending |
| BR-2 | CORE-SEND-002 | AC-F2-2 | core | T-F2-2 | pending |
| BR-2 | CORE-SEND-002 | AC-F2-2 | platform:android | T-F2-102 | pending |
| BR-2 | CORE-SEND-002 | AC-F2-2 | platform:web | T-F2-202 | pending |
| BR-2 | CORE-SEND-005 | AC-F2-3 | core | T-F2-3 | pending |
| BR-2 | CORE-SEND-007 | AC-F2-3 | core | T-F2-3 | pending |
| BR-2 | CORE-SEND-008 | AC-F2-3 | core | T-F2-3 | pending |
| BR-2 | CORE-SEND-005 | AC-F2-3 | platform:android | T-F2-103 | pending |
| BR-2 | CORE-SEND-005 | AC-F2-3 | platform:web | T-F2-203 | pending |
| BR-2 | CORE-SEND-004 | AC-F2-4 | core | T-F2-4 | pending |
| BR-2 | CORE-SEND-004 | AC-F2-4 | platform:android | T-F2-104 | pending |
| BR-2 | CORE-SEND-004 | AC-F2-4 | platform:web | T-F2-204 | pending |
| BR-2 | CORE-SEND-006 | AC-F2-5 | core | T-F2-5 | pending |
| BR-4 | CORE-RECEIVE-006 | AC-F2-5 | core | T-F2-5 | pending |
| BR-2 | CORE-SEND-006 | AC-F2-5 | platform:android | T-F2-105 | pending |
| BR-2 | CORE-SEND-006 | AC-F2-5 | platform:web | T-F2-205 | pending |
| BR-4 | CORE-RECEIVE-001 | AC-F2-6 | core | T-F2-6 | pending |
| BR-4 | CORE-RECEIVE-003 | AC-F2-6 | core | T-F2-6 | pending |
| BR-2 | CORE-VISIBLE-002 | AC-F2-6 | core | T-F2-6 | pending |
| BR-4 | CORE-VISIBLE-007 | AC-F2-6 | core | T-F2-6 | pending |
| BR-4 | CORE-RECEIVE-001 | AC-F2-6 | platform:android | T-F2-106 | pending |
| BR-4 | CORE-RECEIVE-001 | AC-F2-6 | platform:web | T-F2-206 | pending |
| BR-4 | CORE-ORDER-001 | AC-F2-7 | core | T-F2-7 | pending |
| BR-4 | CORE-ORDER-002 | AC-F2-7 | core | T-F2-7 | pending |
| BR-4 | CORE-ORDER-003 | AC-F2-7 | core | T-F2-7 | pending |
| BR-4 | CORE-ORDER-001 | AC-F2-7 | platform:android | T-F2-107 | pending |
| BR-4 | CORE-ORDER-001 | AC-F2-7 | platform:web | T-F2-207 | pending |
| BR-4 | CORE-VISIBLE-003 | AC-F2-8 | core | T-F2-8 | pending |
| BR-4 | CORE-VISIBLE-003 | AC-F2-8 | platform:android | T-F2-108 | pending |
| BR-4 | CORE-VISIBLE-003 | AC-F2-8 | platform:web | T-F2-208 | pending |
| BR-4 | CORE-RECEIVE-005 | AC-F2-9 | core | T-F2-9 | pending |
| BR-4 | CORE-RECEIVE-005 | AC-F2-9 | platform:android | T-F2-109 | pending |
| BR-4 | CORE-RECEIVE-005 | AC-F2-9 | platform:web | T-F2-209 | pending |
| BR-4 | CORE-RECEIVE-004 | AC-F2-10 | core | T-F2-10 | pending |
| BR-4 | CORE-RECEIVE-004 | AC-F2-10 | platform:android | T-F2-110 | pending |
| BR-4 | CORE-RECEIVE-004 | AC-F2-10 | platform:web | T-F2-210 | pending |
| BR-2 | CORE-SEND-011 | AC-F2-11 | core | T-F2-11 | pending |
| BR-2 | CORE-SEND-011 | AC-F2-11 | platform:android | T-F2-111 | pending |
| BR-2 | CORE-SEND-011 | AC-F2-11 | platform:web | T-F2-211 | pending |
| BR-2 | CORE-SEND-007 | AC-F2-12 | core | T-F2-12 | pending |
| BR-4 | CORE-ORDER-004 | AC-F2-12 | core | T-F2-12 | pending |
| BR-4 | CORE-VISIBLE-005 | AC-F2-12 | core | T-F2-12 | pending |
| BR-4 | CORE-VISIBLE-006 | AC-F2-12 | core | T-F2-12 | pending |
| BR-2 | CORE-SEND-007 | AC-F2-12 | platform:android | T-F2-112 | pending |
| BR-2 | CORE-SEND-007 | AC-F2-12 | platform:web | T-F2-212 | pending |
| BR-2 | CORE-SEND-009 | AC-F2-13 | core | T-F2-13 | pending |
| BR-4 | CORE-ORDER-002 | AC-F2-13 | core | T-F2-13 | pending |
| BR-2 | CORE-SEND-009 | AC-F2-13 | platform:android | T-F2-113 | pending |
| BR-2 | CORE-SEND-009 | AC-F2-13 | platform:web | T-F2-213 | pending |
| BR-4 | CORE-ORDER-005 | AC-F2-14 | core | T-F2-14 | pending |
| BR-4 | CORE-ORDER-006 | AC-F2-14 | core | T-F2-14 | pending |
| BR-4 | CORE-ORDER-005 | AC-F2-14 | platform:android | T-F2-114 | pending |
| BR-4 | CORE-ORDER-005 | AC-F2-14 | platform:web | T-F2-214 | pending |
| BR-1 | CORE-LOGIN-003 | AC-F2-15 | core | T-F2-15 | pending |
| BR-1 | CORE-LOGIN-004 | AC-F2-15 | core | T-F2-15 | pending |
| BR-2 | CORE-SEND-002 | AC-F2-15 | core | T-F2-15 | pending |
| BR-2 | CORE-SEND-004 | AC-F2-15 | core | T-F2-15 | pending |
| BR-2 | CORE-SEND-006 | AC-F2-15 | core | T-F2-15 | pending |
| BR-2 | CORE-SEND-011 | AC-F2-15 | core | T-F2-15 | pending |
| BR-1 | CORE-LOGIN-003 | AC-F2-15 | platform:android | T-F2-115 | pending |
| BR-1 | CORE-LOGIN-003 | AC-F2-15 | platform:web | T-F2-215 | pending |
| BR-4 | CORE-RECEIVE-005 | AC-F2-16 | core | T-F2-16 | pending |
| BR-4 | CORE-RECEIVE-005 | AC-F2-16 | platform:android | T-F2-116 | pending |
| BR-4 | CORE-RECEIVE-005 | AC-F2-16 | platform:web | T-F2-216 | pending |

## F3

F3 — Offline queue and flush.

Test ids for `AC-F3-<n>`: core (external checks in `tests/`) `T-F3-<n>`, android in-project `T-F3-<100+n>`, web in-project `T-F3-<200+n>`.

| BR/SC id | Spec id | AC id | Scope | Test id | Status |
|---|---|---|---|---|---|
| BR-3 | CORE-OFFLINE-001 | AC-F3-1 | core | T-F3-1 | pending |
| BR-3 | CORE-OFFLINE-002 | AC-F3-1 | core | T-F3-1 | pending |
| BR-3 | CORE-OFFLINE-001 | AC-F3-1 | platform:android | T-F3-101 | pending |
| BR-3 | CORE-OFFLINE-001 | AC-F3-1 | platform:web | T-F3-201 | pending |
| BR-3 | CORE-OFFLINE-003 | AC-F3-2 | core | T-F3-2 | pending |
| BR-2 | CORE-SEND-010 | AC-F3-2 | core | T-F3-2 | pending |
| BR-4 | CORE-ORDER-002 | AC-F3-2 | core | T-F3-2 | pending |
| BR-3 | CORE-OFFLINE-003 | AC-F3-2 | platform:android | T-F3-102 | pending |
| BR-3 | CORE-OFFLINE-003 | AC-F3-2 | platform:web | T-F3-202 | pending |
| BR-3 | CORE-OFFLINE-004 | AC-F3-3 | core | T-F3-3 | pending |
| BR-3 | CORE-OFFLINE-001 | AC-F3-3 | core | T-F3-3 | pending |
| BR-3 | CORE-OFFLINE-004 | AC-F3-3 | platform:android | T-F3-103 | pending |
| BR-3 | CORE-OFFLINE-004 | AC-F3-3 | platform:web | T-F3-203 | pending |
| BR-3 | CORE-OFFLINE-005 | AC-F3-4 | core | T-F3-4 | pending |
| BR-3 | CORE-OFFLINE-005 | AC-F3-4 | platform:android | T-F3-104 | pending |
| BR-3 | CORE-OFFLINE-005 | AC-F3-4 | platform:web | T-F3-204 | pending |
| BR-3 | CORE-FLUSH-001 | AC-F3-5 | core | T-F3-5 | pending |
| BR-3 | CORE-FLUSH-002 | AC-F3-5 | core | T-F3-5 | pending |
| BR-3 | CORE-FLUSH-001 | AC-F3-5 | platform:android | T-F3-105 | pending |
| BR-3 | CORE-FLUSH-001 | AC-F3-5 | platform:web | T-F3-205 | pending |
| BR-3 | CORE-FLUSH-004 | AC-F3-6 | core | T-F3-6 | pending |
| BR-4 | CORE-ORDER-003 | AC-F3-6 | core | T-F3-6 | pending |
| BR-3 | CORE-FLUSH-004 | AC-F3-6 | platform:android | T-F3-106 | pending |
| BR-3 | CORE-FLUSH-004 | AC-F3-6 | platform:web | T-F3-206 | pending |
| BR-4 | CORE-RECEIVE-002 | AC-F3-7 | core | T-F3-7 | pending |
| BR-3 | CORE-FLUSH-003 | AC-F3-7 | core | T-F3-7 | pending |
| BR-4 | CORE-RECEIVE-002 | AC-F3-7 | platform:android | T-F3-107 | pending |
| BR-4 | CORE-RECEIVE-002 | AC-F3-7 | platform:web | T-F3-207 | pending |
| BR-3 | CORE-OFFLINE-006 | AC-F3-8 | core | T-F3-8 | pending |
| BR-3 | CORE-FLUSH-005 | AC-F3-8 | core | T-F3-8 | pending |
| BR-3 | CORE-OFFLINE-006 | AC-F3-8 | platform:android | T-F3-108 | pending |
| BR-3 | CORE-OFFLINE-006 | AC-F3-8 | platform:web | T-F3-208 | pending |
| BR-3 | CORE-FLUSH-005 | AC-F3-9 | core | T-F3-9 | pending |
| BR-4 | CORE-RECEIVE-004 | AC-F3-9 | core | T-F3-9 | pending |
| BR-3 | CORE-FLUSH-005 | AC-F3-9 | platform:android | T-F3-109 | pending |
| BR-3 | CORE-FLUSH-005 | AC-F3-9 | platform:web | T-F3-209 | pending |
| BR-3 | CORE-VISIBLE-008 | AC-F3-10 | core | T-F3-10 | pending |
| BR-3 | CORE-FLUSH-001 | AC-F3-10 | core | T-F3-10 | pending |
| BR-3 | CORE-VISIBLE-008 | AC-F3-10 | platform:android | T-F3-110 | pending |
| BR-3 | CORE-VISIBLE-008 | AC-F3-10 | platform:web | T-F3-210 | pending |
| BR-3 | CORE-OFFLINE-007 | AC-F3-11 | core | T-F3-11 | pending |
| BR-3 | CORE-OFFLINE-007 | AC-F3-11 | platform:android | T-F3-111 | pending |
| BR-3 | CORE-OFFLINE-007 | AC-F3-11 | platform:web | T-F3-211 | pending |
| BR-3 | CORE-FLUSH-006 | AC-F3-12 | core | T-F3-12 | pending |
| BR-3 | CORE-FLUSH-006 | AC-F3-12 | platform:android | T-F3-112 | pending |
| BR-3 | CORE-FLUSH-006 | AC-F3-12 | platform:web | T-F3-212 | pending |
| BR-1 | CORE-LOGIN-002 | AC-F3-13 | core | T-F3-13 | pending |
| BR-3 | CORE-OFFLINE-004 | AC-F3-13 | core | T-F3-13 | pending |
| BR-3 | CORE-FLUSH-005 | AC-F3-13 | core | T-F3-13 | pending |
| BR-1 | CORE-LOGIN-002 | AC-F3-13 | platform:android | T-F3-113 | pending |
| BR-1 | CORE-LOGIN-002 | AC-F3-13 | platform:web | T-F3-213 | pending |
| BR-3 | CORE-FLUSH-005 | AC-F3-14 | core | T-F3-14 | pending |
| BR-4 | CORE-RECEIVE-004 | AC-F3-14 | core | T-F3-14 | pending |
| BR-3 | CORE-FLUSH-005 | AC-F3-14 | platform:android | T-F3-114 | pending |
| BR-3 | CORE-FLUSH-005 | AC-F3-14 | platform:web | T-F3-214 | pending |
| BR-3 | CORE-VISIBLE-008 | AC-F3-15 | core | T-F3-15 | pending |
| BR-3 | CORE-VISIBLE-008 | AC-F3-15 | platform:android | T-F3-115 | pending |
| BR-3 | CORE-VISIBLE-008 | AC-F3-15 | platform:web | T-F3-215 | pending |

## F4

F4 — Interoperability (Alice/Bob scenario, android and web).

Core-scope tests (`tests/interop`, `tests/web-e2e`) drive both clients through the scenario; platform-scope tests replay the same steps against each app's fake server (PLAT-ANDROID-019, PLAT-WEB-013). Test ids: core `T-F4-<n>`, android `T-F4-<100+n>`, web `T-F4-<200+n>` for AC `AC-F4-<n>`.

| BR/SC id | Spec id | AC id | Scope | Test id | Status |
|---|---|---|---|---|---|
| SC-1 | CORE-SEND-001 | AC-F4-1 | core | T-F4-1 | pending |
| SC-1 | CORE-SEND-008 | AC-F4-1 | core | T-F4-1 | pending |
| SC-1 | CORE-RECEIVE-001 | AC-F4-1 | core | T-F4-1 | pending |
| SC-1 | CORE-VISIBLE-002 | AC-F4-1 | core | T-F4-1 | pending |
| SC-1 | CORE-SEND-001 | AC-F4-1 | platform:android | T-F4-101 | pending |
| SC-1 | CORE-SEND-001 | AC-F4-1 | platform:web | T-F4-201 | pending |
| SC-2 | CORE-VISIBLE-004 | AC-F4-2 | core | T-F4-2 | pending |
| SC-2 | CORE-ORDER-001 | AC-F4-2 | core | T-F4-2 | pending |
| SC-2 | CORE-ORDER-005 | AC-F4-2 | core | T-F4-2 | pending |
| SC-2 | CORE-VISIBLE-004 | AC-F4-2 | platform:android | T-F4-102 | pending |
| SC-2 | CORE-VISIBLE-004 | AC-F4-2 | platform:web | T-F4-202 | pending |
| SC-3 | CORE-OFFLINE-002 | AC-F4-3 | core | T-F4-3 | pending |
| SC-3 | CORE-OFFLINE-003 | AC-F4-3 | core | T-F4-3 | pending |
| SC-3 | CORE-OFFLINE-002 | AC-F4-3 | platform:android | T-F4-103 | pending |
| SC-3 | CORE-OFFLINE-002 | AC-F4-3 | platform:web | T-F4-203 | pending |
| SC-4 | CORE-OFFLINE-002 | AC-F4-4 | core | T-F4-4 | pending |
| SC-4 | CORE-OFFLINE-003 | AC-F4-4 | core | T-F4-4 | pending |
| SC-4 | CORE-OFFLINE-002 | AC-F4-4 | platform:android | T-F4-104 | pending |
| SC-4 | CORE-OFFLINE-002 | AC-F4-4 | platform:web | T-F4-204 | pending |
| SC-5 | CORE-OFFLINE-005 | AC-F4-5 | core | T-F4-5 | pending |
| SC-5 | CORE-FLUSH-001 | AC-F4-5 | core | T-F4-5 | pending |
| SC-5 | CORE-FLUSH-004 | AC-F4-5 | core | T-F4-5 | pending |
| SC-5 | CORE-OFFLINE-005 | AC-F4-5 | platform:android | T-F4-105 | pending |
| SC-5 | CORE-OFFLINE-005 | AC-F4-5 | platform:web | T-F4-205 | pending |
| SC-6 | CORE-OFFLINE-001 | AC-F4-6 | core | T-F4-6 | pending |
| SC-6 | CORE-OFFLINE-001 | AC-F4-6 | platform:android | T-F4-106 | pending |
| SC-6 | CORE-OFFLINE-001 | AC-F4-6 | platform:web | T-F4-206 | pending |
| SC-7 | CORE-RECEIVE-002 | AC-F4-7 | core | T-F4-7 | pending |
| SC-7 | CORE-FLUSH-003 | AC-F4-7 | core | T-F4-7 | pending |
| SC-7 | CORE-FLUSH-004 | AC-F4-7 | core | T-F4-7 | pending |
| SC-7 | CORE-ORDER-002 | AC-F4-7 | core | T-F4-7 | pending |
| SC-7 | CORE-RECEIVE-002 | AC-F4-7 | platform:android | T-F4-107 | pending |
| SC-7 | CORE-RECEIVE-002 | AC-F4-7 | platform:web | T-F4-207 | pending |
| SC-8 | CORE-RECEIVE-002 | AC-F4-8 | core | T-F4-8 | pending |
| SC-8 | CORE-ORDER-005 | AC-F4-8 | core | T-F4-8 | pending |
| SC-8 | CORE-RECEIVE-002 | AC-F4-8 | platform:android | T-F4-108 | pending |
| SC-8 | CORE-RECEIVE-002 | AC-F4-8 | platform:web | T-F4-208 | pending |
| BR-4 | CORE-ORDER-005 | AC-F4-9 | core | T-F4-9 | pending |

## F5

F5 — Reactions extension (evolution demo).

Rows are added at S1 of F5, after `spec/extensions/reactions.md` (EXT-REACTIONS ids, behavior and scenarios) is approved at G0 in phase P6. Until then this feature has no spec ids to trace. Test id scheme: `T-F5-<n>`.

| BR/SC id | Spec id | AC id | Scope | Test id | Status |
|---|---|---|---|---|---|
