# 0017 — G1: P3 generator design (and D1 plan) approved

Status: accepted (operator, OM-0015)
Document: `docs/planning/p3-generator-design.md`. Per decision 0016 Q7, this G1 is also D1's G1.

## Decisions (the recommended defaults of the design's §7)
1. Android module names stay as in `PLAT-ANDROID-004`.
2. Module build files come from per-kind skeletons; the model fills only package name and dependency lines.
3. Self-repair budget: up to 3 attempts per checkpoint and 12 per run. This amends WORKFLOW (previously 3 per run) when the generator is implemented.
4. Pinned model Opus (`claude-opus-5-5`); Sonnet is a manual-only fallback, never mixed in one run.
5. Headless permissions: explicit allowlist, unanswerable prompts denied (no skip-all).
6. Cost limits per app run: 400 turns and $75, recalibrated after the first real run.
7. Node 22 or newer is accepted.
8. Android Gradle plugin: latest 8.x.
9. Test reports are committed under `docs/runs/D1/reports/`.
10. A token-free smoke session (templates only) runs before the first `/generate`.

## Consequences
- DEV may implement conventions, templates and generator config after P2 is merged (decision 0016 Q6).
- All version pins stay TBD-verify-on-operator-machine until smoke session A.
