# AGENTS.md

Instructions for any coding agent (Claude Code, Codex) working in this repo. `CLAUDE.md` imports this file.

## Read first
1. `docs/brief/aware-test-brief.md` — authoritative brief and constraints.
2. `docs/PROJECT_CONTEXT.md` — objective and preferred directions.
3. `spec/README.md` — the current specification index.
4. `generator/WORKFLOW.md` — the pipeline, your role, return codes and limits.

## Rules
- **The spec is the source of truth.** Resolve behavior questions from `spec/`, never from client or server code. If the spec is silent or ambiguous, propose a spec change first.
- **Never hand-edit generated code** (`clients/*/`, anything with a `GENERATED` header). Change the spec or the generator, then regenerate. Only `/generate` writes `clients/*`.
- Only stage S0 (spec delta, approved at G0) may change `spec/`.
- **Never edit the spec to match code** without recording the reason in `docs/decisions/`.
- Do not use messaging/chat SDKs. HTTP, WebSocket, JSON and local-storage libraries are fine.
- Everything must run locally with no cloud or third-party services.
- **Agents cannot build or test the clients** in their sandbox (no Android SDK, no npm/Maven/Gradle access; `docs/ENVIRONMENT.md`). Never claim a client builds or passes unless a log from the operator's machine says so. Python-only work (harness, server, protocol tests) can be run and verified in the sandbox.
- Keep the server small; invest in protocol clarity and generation reliability.
- One commit per stage output; generated output in its own `regen(<app>)` commit; never one commit touching both `spec/` and `clients/`. Commit conventions: `generator/WORKFLOW.md` §8 and decision 0015 (operator is author and committer; agents only in trailers).
- End every agent task with one return code: `OK`, `SPEC_ISSUE`, `PLAN_DEVIATION`, `STALE_DIFF`, `ENV_FAILURE`, `BLOCKED`. Never fill a spec gap in code; return `SPEC_ISSUE`.
- Read the diff snapshot ORC gives you; check it isn't stale before starting (`python3 generator/scripts/check_snapshot.py --meta <diff.meta.json>`).
- Sub-agents end their reply with `OUTCOME: <event>` and a final `RETURN: <code>` line (formats in `.claude/agents/`). ORC routes them only through `generator/scripts/state.py`.
- Harness self-test: `python3 -m unittest discover -s generator/tests`; prompt genericity: `python3 generator/scripts/lint_prompts.py`.

## Roles (orchestration)
The main orchestrator (ORC) is the technical manager and the operator's single point of contact: it keeps the plan and state, launches PM, Tech Lead, Developer, Reviewer and QA agents from prompt templates, and reviews results against the spec. Two entry points: `/pipeline` (gated delivery) and `/generate` (headless generator). Roles, gates, loops and limits: `generator/WORKFLOW.md`. Agent definitions: `.claude/agents/`.

## Definition of done for a change
- Spec updated (if behavior changed) and versioned.
- Affected clients regenerated, not hand-patched.
- In-project tests and external AC checks (`tests/`) pass.
- Clean delete-and-regenerate check passes (S6b).
