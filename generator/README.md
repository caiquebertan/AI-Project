# Generator and agentic harness

Full design: [`WORKFLOW.md`](WORKFLOW.md) (v0.2).

| Entry point | Tool | Purpose |
|---|---|---|
| `/generate <android\|web\|all>` | Claude Code | **The generator.** Spec → `clients/<app>/`. Headless, no gates. What graders run. ☐ |
| `/pipeline [feature] [--autonomous]` | Claude Code | Gated delivery pipeline (PM, TL, DEV, REV, QA) that evolves spec and generator and calls `/generate`. ☐ |

Planned layout (built in Phase 0 / Phase 3):
- `prompts/` — role prompt templates (variables only, no feature names)
- `conventions/` — per-platform code-shape rules the generator follows (incl. test requirements)
- `templates/` — copied build infra and module skeletons (Gradle wrapper, Vite config, …)
- `config/` — pinned model IDs, self-repair limit
- `scripts/` — snapshot-diff, count-lines, run-log, check-headers, check-trace, regen-check, lint-commits, preflight
- `RUN.md` — manual fallback for running without slash commands
