# Specification

**Version:** 0.1.1 (patch: clarification) — P2 spec questions S-1..S-13 answered in decision 0018 (accepted by the operator, OM-0016); no rule id added, withdrawn or renumbered. Base 0.1.0 approved by the operator at G0 (OM-0011, decision 0013) and tagged `spec-v0.1.0` by ORC after the cuts were merged and verified. Bump on every behavioral change (semver: major = wire-incompatible, minor = new rules or extensions, patch = clarification).

The spec is the single source of truth for behavior: questions are answered here, never from client or server code. It is platform-neutral in `core/` and `scenarios/`; platform rules live only in `platform/`; new capabilities go in `extensions/`.

## Index

| Path | Purpose | Owner | Status | Rules (MUST) / ACs |
|---|---|---|---|---|
| [`core/protocol.md`](core/protocol.md) | Wire protocol: transport, endpoints, identity, envelope, time, send/ack, poll/cursor, epoch, order, polling cycle and outbox, capabilities, errors, constants; Appendix A Alice/Bob protocol trace and displayed times | TL | approved 0.1.1 | 90 / — |
| [`core/server-behavior.md`](core/server-behavior.md) | Server internals: registry, mailboxes, `seq`, immediate polls, strict timestamps, dedupe, relay, no time zone, what it does not do | TL | approved 0.1.1 | 26 / — |
| [`core/schema/`](core/schema/) | JSON Schemas per request/response, [`index.json`](core/schema/index.json) (endpoint → schema), [`constants.json`](core/schema/constants.json), examples and value cases (`cases/`, valid and invalid values; all checked by `generator/scripts/check_schema_examples.py`) | TL | approved 0.1.1 | — |
| [`core/client-behavior.md`](core/client-behavior.md) | Observable client behavior: screens, login, send, offline queue, flush, receive, order, fixed texts; acceptance criteria | PM | approved 0.1.1 | 53 / 37 ACs |
| [`scenarios/alice-bob-offline.md`](scenarios/alice-bob-offline.md) | The brief's 7-step scenario (SC-1..SC-7, plus SC-8 beyond the brief) with exact expected states per step | PM | approved 0.1.1 | 9 ACs |
| [`scenarios/additional-scenarios.md`](scenarios/additional-scenarios.md) | Extra scenarios SX-1..SX-6 (no server at login, lost ack, server restart, input edge cases, unknown type, message times and time zones) | PM | approved 0.1.1 | 6 ACs |
| [`platform/test-hooks.md`](platform/test-hooks.md) | Hook ids, readable values and state snapshot shared by all clients ([`client-snapshot.schema.json`](platform/client-snapshot.schema.json)), relaunch control, time hook, injected ports, tests every client generates (offline = zero requests, time-zone denylist) | TL | approved 0.1.1 | 14 / — |
| [`platform/android.md`](platform/android.md) | Android stack, modules, storage, networking, hooks, generated tests, JVM interop driver `:tools:driver` | TL | approved 0.1.1 | 34 / — |
| [`platform/web.md`](platform/web.md) | Web stack, structure, storage, configuration, hooks, generated tests, request visibility for browser tests | TL | approved 0.1.1 | 25 / — |
| [`extensions/`](extensions/) | Optional capabilities (reactions, attachments, groups, …); template in its README | TL + PM | template only | — |

Totals: 242 rule ids (239 on `MUST` lines, the ones `check_trace.py` counts) and 52 acceptance criteria, counted by script on 2026-10-13 (main, after merging the TL and PM cuts) from the `- **<id>** —` definition lines; recount after every spec change, including after merging parallel PM and TL deltas. Tombstone lines (below) are not rules and are not counted.

Decision records behind the core choices: `docs/decisions/0004`–`0009`, `0012` (time representation, amended by OM-0011) and `0014` (plain polling, withdrawn rules, test visibility; supersedes `0010`). MVP cuts: `0013`.

## Rule ids

- Every normative rule has an id on the **same line** as its RFC 2119 keyword (`MUST`, `MUST NOT`, `SHOULD`, `MAY`). `generator/scripts/check_trace.py` collects ids on `MUST` lines (regex in `generator/config/generator.json` → `trace.spec_id_regex`). **Acceptance criteria gate acceptance** (S6: every AC needs passing tests); **rule coverage is reported, not gated**: the share of those ids carried by a passing test is listed in the report and tests are still named by the ids they cover, but an uncovered id does not block a feature (operator OM-0011, decision 0013).
- Forms: `CORE-<AREA>-NNN` (core), `PLAT-<PLATFORM>-NNN` (platform, `PLAT-HOOK` for the shared hooks), `EXT-<CAPABILITY>-NNN` (extensions; capability id uppercased without dashes, e.g. `EXT-REACTIONS-001`).
- Ids are **never reused or renumbered**. A withdrawn rule stays in place as one tombstone line, `- **CORE-XXX-nnn** — Withdrawn (decision NNNN).`, with no RFC 2119 keyword, so tooling does not count it as a rule; a citation of a withdrawn id is a defect to fix. A reworded rule keeps its id; the decision that changed it lists the id. Withdrawn constant names are listed under the constants table and are not reused either.
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
