# Generator / agentic harness

**Tool:** Claude Code (or Codex). **Input:** `spec/`. **Output:** `clients/<platform>/`.

_To be defined._ Intended shape:
- `.claude/commands/generate-client.md` — `/generate-client <platform>`: regenerates one client from the spec.
- `.claude/commands/verify-client.md` — `/verify-client <platform>`: runs conformance scenarios.
- `generator/prompts/` — reusable prompt fragments, parameterised by platform and spec version.
- `generator/WORKFLOW.md` — orchestrator + specialist agent pipeline.

The harness must stay generic: it reads whatever is in `spec/` (including new `extensions/`) and does not hard-code the messaging scenario.
