# DESIGN

Draft design principles. Refine as the spec and generator take shape.

## Principles
1. **Generator over output.** The generator is the deliverable; the clients are reproducible artifacts.
2. **Spec is authoritative and platform-neutral.** Core protocol and behavior are separated from platform-specific extensions (`spec/core/` vs `spec/platform/`).
3. **Testable contracts.** Every behavior in the spec is backed by a scenario that can be executed against any client (`spec/scenarios/`, `tests/`).
4. **Explicit regeneration boundary.** Generated vs hand-written is visible in the file tree, in file headers, and in the README.
5. **Evolvable.** New capabilities (attachments, reactions, groups) are added as spec extensions (`spec/extensions/`) without changing the harness.
6. **Proportionate engineering.** SOLID and clean architecture scaled to component size; the server stays trivially small.

## Components
- **Spec** → input to the generator.
- **Generator/harness** → prompts, commands and sub-agents that drive Claude Code to produce clients and verify them against scenarios.
- **Server** → in-memory Python, hand-written.
- **Clients** → Android (Kotlin, Compose, Hilt, Retrofit, multi-module) and web (stack TBD, see decision log), both generated.

## Open design questions
- Transport: HTTP polling, long-poll, or WebSocket? (decide in `spec/core/protocol.md`)
- Message identity and ordering (client-generated IDs, server sequence numbers?).
- Delivery semantics on reconnect (at-least-once + dedupe by ID?).
- How scenarios are encoded so both clients can be driven by the same test script.
