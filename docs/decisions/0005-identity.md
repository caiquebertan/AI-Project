# 0005 — Identity: names, case rules, re-login
- Status: proposed (awaiting G0)
- Date: 2026-10-13
- Author: TL (agent, claude-opus-5-5)
- Spec ids driven: `CORE-NAME-*`, `CORE-SESSION-*`, `CORE-SRV-020`..`CORE-SRV-023` — in [`spec/core/protocol.md`](../../spec/core/protocol.md) and [`spec/core/server-behavior.md`](../../spec/core/server-behavior.md)

## Context
Brief: "A user identifies themselves by name on first launch (i.e. login)". No security is required. Both clients must treat names identically, including case, and must be able to log in while offline (the offline queue would otherwise be useless on first launch).

## Decision
1. A name matches `^[A-Za-z0-9_-]{1,32}$` (ASCII only). Clients do not trim or alter input beyond rejecting it if it does not match.
2. Names are **case-insensitive**. The **canonical form** is the ASCII-lowercase of the name. Everything on the wire after login, all comparisons, local storage keys and all displayed user names use the canonical form. The server canonicalizes every name it receives and emits only canonical names.
3. **Login is local**: a client accepts a syntactically valid name, stores the canonical form as its identity, and is logged in even while offline. Registration with the server happens through `POST /v1/session` at the start of every connection cycle (0009).
4. `POST /v1/session` is **idempotent and non-exclusive**: claiming an existing name returns `200` and the same identity (`new_user: false`). Any client claiming a name *is* that user. Two devices with the same name share one mailbox and keep their own cursors.
5. Each session call replaces the user's advertised capability list (last writer wins).

## Alternatives considered
- **Unicode names with case folding.** Kotlin, JavaScript and Python fold differently (e.g. `ß`, Turkish `İ`); identical behavior could not be guaranteed. Rejected.
- **Case-sensitive names.** "Alice" and "alice" would be two users; error-prone in manual demos. Rejected.
- **Preserve display casing (store first-seen casing).** Adds a lookup to every rendered message and a rule for conflicting casings. Rejected for v1; possible extension.
- **Exclusive names (second claim rejected) / tokens.** Requires auth or secrets; out of scope by the brief.
- **Login requires the server.** Simpler server, but first launch while offline would block. Rejected.

## Consequences
- The UI shows `alice`, not `Alice`. The PM must state this in visible behavior.
- No user can be "taken"; demo users can always log back in.
- Sends from a name that has not called `/v1/session` in the current epoch are rejected (`403 unknown_sender`), which also forces re-registration after a server restart.

## Brief constraint affected
None.
