# AGENTS.md

Instructions for any coding agent (Claude Code, Codex) working in this repo. `CLAUDE.md` imports this file.

## Read first
1. `docs/brief/aware-test-brief.md` — authoritative brief and constraints.
2. `docs/PROJECT_CONTEXT.md` — objective and preferred directions.
3. `spec/README.md` — the current specification index.

## Rules
- **The spec is the source of truth.** Resolve behavior questions from `spec/`, never from client or server code. If the spec is silent or ambiguous, propose a spec change first.
- **Never hand-edit generated code** (`clients/*/`, anything with a `GENERATED` header). Change the spec or the generator, then regenerate.
- **Never edit the spec to match code** without recording the reason in `docs/decisions/`.
- Do not use messaging/chat SDKs. HTTP, WebSocket, JSON and local-storage libraries are fine.
- Everything must run locally with no cloud or third-party services.
- Keep the server small; invest in protocol clarity and generation reliability.
- Small, meaningful commits; the message states which area changed (spec / generator / server / clients / tests / docs).

## Roles (orchestration)
The main orchestrator acts as technical manager: keeps the plan, launches specialized agents with scoped context, and reviews results against the spec. Agent definitions live in `.claude/agents/`; detailed handoffs will be defined in `generator/WORKFLOW.md`.

## Definition of done for a change
- Spec updated (if behavior changed) and versioned.
- Affected clients regenerated, not hand-patched.
- Conformance and interop tests pass (`tests/`).
