---
description: Regenerate a client (android|web|all) from the spec. Headless, no human gates.
argument-hint: <android|web|all>
---
Placeholder (to be built in Phase 3, see `generator/WORKFLOW.md` §1 and §4).
Reads `spec/` (core, schema, scenarios, extensions, platform/$ARGUMENTS) and `generator/` (conventions, templates, config), builds a plan, writes `clients/$ARGUMENTS/` (code + unit/UI tests + `.generated` manifest), builds and tests, self-repairs at most 3 times, fails loudly otherwise. Writes nothing outside `clients/$ARGUMENTS/`.
