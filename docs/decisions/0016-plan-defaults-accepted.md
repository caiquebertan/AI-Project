# 0016 — Final plan accepted with the recommended defaults

Status: accepted (operator, OM-0014)
Plan: `docs/PLAN.md` (P2 to P8).

## Decisions (all recommended defaults of PLAN §6)
- Q1 One informal, non-gating regen check after D1 is accepted; the gating check stays at P7 (cut 8).
- Q2 No PM/QA acceptance for the server; protocol tests are acceptance, ORC sends `green`/`met`.
- Q3 F4 is one delivery run entirely in P5 (not in P4).
- Q4 No cycle trigger on enqueue; ~1 s send latency stays (decision 0014).
- Q5 No new AC for `CORE-VISIBLE-005/006`; bundle into the first spec reopen if one happens.
- Q6 The TL designs the generator (P3) in parallel with P2; DEV implementation and first generation wait for P2.
- Q7 P3's G1 is D1's G1, and the first `/generate` is D1's generation (S3).

## Also accepted
- P2 starts now in the cloud (light chain).
- An environment helper script that diagnoses missing tools and offers install commands (operator request, OM-0014).

## Consequences
- The document contradictions listed in PLAN §8 are fixed in one docs commit at the start of P2.
- Decision 0002 Q6, Q16 and the S6b wording are superseded by decisions 0013 and 0016.
