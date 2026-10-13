# Extensions

Each extension is one file `<capability-id>.md` (plus optional `<capability-id>/schema/*.schema.json`). Extensions add capabilities on top of `spec/core/` through the generic relay (`spec/README.md`, "Extensions and the generic relay"; `core/protocol.md` §11 and Appendix B). Planned: `reactions` (phase P6). Candidates: `receipts`, `attachments`, `groups`.

Rules for every extension:
- It MUST NOT change, override or reinterpret any rule in `spec/core/` (CORE-EXT-005); if it cannot work without a core change, that core change is a separate spec delta with its own decision record.
- Its types are named `<capability-id>.<name>`; its rule ids are `EXT-<CAPABILITY>-NNN`.
- A client-only extension states "Server behavior: none" and must work against an unchanged server.
- Clients that do not implement it must keep working (they ignore its types, CORE-EXT-002); scenarios must include one mixed pair (capable ↔ core-only client).

## Template

Copy into `spec/extensions/<capability-id>.md`:

```markdown
# Extension: <name>

- Capability id: `<capability-id>` (matches ^[a-z][a-z0-9-]{0,31}$; declared in E2 `capabilities`)
- Status: draft (G0) · Spec version introduced: X.Y.Z
- Kind: client-only | server-capability (`server_capabilities` id: `<id>`)
- Depends on: core (and other capability ids, if any)

## 1. Purpose
One paragraph: what users can do, and why it fits the relay.

## 2. Types and payloads
| type | direction | payload schema | meaning |
|---|---|---|---|
| `<capability-id>.<name>` | sender → recipient | `<capability-id>/schema/<name>.schema.json` | ... |
- EXT-<CAP>-001 — <payload rules: required fields, limits, references to message ids>.

## 3. Client behavior
- EXT-<CAP>-0NN — <what a capable client does on send and on receive; how it renders; ordering relative to CORE-SEQ-002>.
- Behavior towards peers without the capability (from E5 `capabilities`): <hide UI / still send>.
- Invalid or dangling payloads (e.g. reference to an unknown message id): <skip | keep pending until target arrives>.

## 4. Server behavior
"None (relayed opaquely, CORE-EXT-001)." — or, for server-capability extensions, the new endpoints and EXT rules.

## 5. Test hooks and platform notes
New hook ids (added to `platform/test-hooks.md` naming style) and snapshot fields, if any. No behavior here.

## 6. Scenarios
Given/When/Then scenarios with fixed ids and texts, including one capable ↔ core-only pairing.
```
