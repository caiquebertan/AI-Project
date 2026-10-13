# Specification

**Version:** 0.0.1 (skeleton) — bump on every behavioral change.

The spec is the single source of truth. It is platform-neutral in `core/` and `scenarios/`; platform-specific rules live only in `platform/`; new capabilities go in `extensions/`.

| Path | Purpose | Status |
|---|---|---|
| [`core/protocol.md`](core/protocol.md) | Wire protocol: transport, message envelope, IDs, ordering, delivery | ☐ |
| [`core/client-behavior.md`](core/client-behavior.md) | Observable client behavior: login, send, offline queue, flush, display | ☐ |
| [`core/server-behavior.md`](core/server-behavior.md) | Server rules: routing, per-recipient mailbox, redelivery | ☐ |
| [`scenarios/alice-bob-offline.md`](scenarios/alice-bob-offline.md) | The brief's 7-step scenario with exact expected states | ☐ expected states |
| [`extensions/`](extensions/) | Attachments, reactions, groups, etc. | empty |
| [`platform/android.md`](platform/android.md) | Android-specific requirements | ☐ |
| [`platform/web.md`](platform/web.md) | Web-specific requirements | ☐ |

## Conventions
- Use RFC 2119 keywords (MUST / SHOULD / MAY).
- Every MUST has an ID (`CORE-xxx`) and is covered by at least one scenario.
- Extensions MUST NOT change core behavior; they add fields/messages and declare themselves in a capability list.
