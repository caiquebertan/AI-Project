# Specification

**Version:** 0.1.0-draft — awaiting operator approval at G0 (then `0.1.0` and tag `spec-v0.1.0`, set by the operator/ORC, not by an agent). Bump on every behavioral change (semver: major = wire-incompatible, minor = new rules or extensions, patch = clarification).

The spec is the single source of truth for behavior: questions are answered here, never from client or server code. It is platform-neutral in `core/` and `scenarios/`; platform rules live only in `platform/`; new capabilities go in `extensions/`.

## Index

| Path | Purpose | Owner | Status | Rules (MUST) / ACs |
|---|---|---|---|---|
| [`core/protocol.md`](core/protocol.md) | Wire protocol: transport, endpoints, identity, envelope, send/ack, poll/cursor, epoch, order, connection cycle and outbox, capabilities, errors, constants; Appendix A Alice/Bob protocol trace and displayed times | TL | draft (G0) | 90 (90) |
| [`core/server-behavior.md`](core/server-behavior.md) | Server internals: registry, mailboxes, `seq`, long-poll, dedupe, relay, what it does not do | TL | draft (G0) | 28 (27) |
| [`core/schema/`](core/schema/) | JSON Schemas per request/response, [`index.json`](core/schema/index.json) (endpoint → schema), [`constants.json`](core/schema/constants.json), examples (checked by `generator/scripts/check_schema_examples.py`) | TL | draft (G0) | — |
| [`core/client-behavior.md`](core/client-behavior.md) | Observable client behavior: screens, login, send, offline queue, flush, receive, order, fixed texts; acceptance criteria | PM | draft (G0) | 54 (53) / 39 ACs |
| [`scenarios/alice-bob-offline.md`](scenarios/alice-bob-offline.md) | The brief's 7-step scenario (SC-1..SC-7, plus SC-8 beyond the brief) with exact expected states per step | PM | draft (G0) | 9 ACs |
| [`scenarios/additional-scenarios.md`](scenarios/additional-scenarios.md) | Extra scenarios SX-1..SX-6 (no server at login, lost ack, server restart, input edge cases, unknown type, message times and time zones) | PM | draft (G0) | 6 ACs |
| [`platform/test-hooks.md`](platform/test-hooks.md) | Hook ids, readable values and state snapshot shared by all clients ([`client-snapshot.schema.json`](platform/client-snapshot.schema.json)), relaunch and request-visibility controls, time hook | TL | draft (G0) | 13 (13) |
| [`platform/android.md`](platform/android.md) | Android stack, modules, storage, networking, hooks, generated tests | TL | draft (G0) | 28 (28) |
| [`platform/web.md`](platform/web.md) | Web stack, structure, storage, configuration, hooks, generated tests | TL | draft (G0) | 21 (20) |
| [`extensions/`](extensions/) | Optional capabilities (reactions, attachments, groups, …); template in its README | TL + PM | template only | — |

Totals: 234 rule ids (231 on `MUST` lines, counted by `check_trace.py`) and 54 acceptance criteria, counted by script on 2026-10-13 (main, after merging the PM and TL time deltas) from the `- **<id>** —` definition lines; recount after every spec change, including after merging parallel PM and TL deltas.

Decision records behind the core choices: `docs/decisions/0004`–`0010` and `0012` (time representation).

## Rule ids

- Every normative rule has an id on the **same line** as its RFC 2119 keyword (`MUST`, `MUST NOT`, `SHOULD`, `MAY`). `generator/scripts/check_trace.py` collects ids on `MUST` lines (regex in `generator/config/generator.json` → `trace.spec_id_regex`), and every such id needs at least one passing test whose name carries it (E-QA-1).
- Forms: `CORE-<AREA>-NNN` (core), `PLAT-<PLATFORM>-NNN` (platform, `PLAT-HOOK` for the shared hooks), `EXT-<CAPABILITY>-NNN` (extensions; capability id uppercased without dashes, e.g. `EXT-REACTIONS-001`).
- Ids are **never reused or renumbered**. A removed rule keeps its id, marked `(withdrawn in X.Y.Z)`.
- Area ownership (prevents PM/TL collisions):

| Areas | File | Owner |
|---|---|---|
| `HTTP` `NAME` `SESSION` `EPOCH` `ENV` `TIME` `TEXT` `MSG` `POLL` `CURSOR` `DEDUPE` `SEQ` `CONN` `OUTBOX` `CAP` `EXT` `ERR` `CONST` | `core/protocol.md` | TL |
| `SRV` | `core/server-behavior.md` | TL |
| `LOGIN` `SEND` `OFFLINE` `FLUSH` `RECEIVE` `ORDER` `VISIBLE` (and new areas PM adds); acceptance criteria `AC-F<n>-<m>`; scenario steps `SC-n`, `SX-n` | `core/client-behavior.md`, `scenarios/` | PM |
| `ANDROID` `WEB` `HOOK` | `platform/` | TL |

## Conventions

- **Precedence:** brief > this spec > everything else (plans, prompts, code). Inside the spec, `core/` > `extensions/` > `platform/`: a platform file never changes behavior, an extension never changes core.
- **Generic vs platform:** `core/` and `scenarios/` name no language, library or OS. `platform/` names no behavior (it may only cite core ids). A rule that seems to need both is split into a core rule and a platform rule that cites it.
- **Prose and schema:** both normative; a contradiction is a spec defect (`SPEC_ISSUE`), never resolved in code.
- **Fixed test data** (message texts for scenario steps 3 and 4, fixture ids) is defined in `core/protocol.md` Appendix A and reused by scenarios and tests.

## Extensions and the generic relay

The server is a store-and-forward relay (decision 0008): it validates the envelope, assigns `seq`, stores and delivers through the same mailbox and cursor, and validates payloads **only** for core types (`text`). Any other `type` is opaque to it. Consequently:

- **Client-only extensions** (reactions, receipts, typing, edits) are written as one file in `extensions/` and need **no server change and no core change**: they define new `type`s (`<capability-id>.<name>`) with payload schemas, and clients that do not implement a type ignore it while still advancing their cursor (CORE-EXT-002). See `core/protocol.md` Appendix B.
- **Server-capability extensions** (groups with fan-out, attachments with blob storage) must also declare a `server_capabilities` id and the server rules they add; they still must not change core rules.
- An extension file (template: [`extensions/README.md`](extensions/README.md)) declares: capability id, new types and payload schemas (`extensions/<id>/schema/`), client behavior, server behavior (or "none"), scenarios, and its `EXT-` rules. It MUST NOT edit any file in `core/`.
- The generator reads `extensions/` with `core/` (generator config `spec_dirs`), so an approved extension regenerates into both clients without prompt changes (E-EVOL-1).
