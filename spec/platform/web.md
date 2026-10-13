# Web platform rules

- **Status:** draft for G0 (spec 0.1.0-draft). Owner: TL. Stack source: decision 0001 (React + TypeScript + Vite; Vitest, Playwright).
- **Scope:** how the web client is built, structured, configured and tested. **No behavior here.** What the app does is in `spec/core/` (protocol obligations: [`protocol.md`](../core/protocol.md); visible behavior: [`client-behavior.md`](../core/client-behavior.md)). If a rule below seems to decide behavior, the core rule it cites wins.
- **Ids:** `PLAT-WEB-NNN`. Shared hook names: [`test-hooks.md`](test-hooks.md).

## 1. Stack

- **PLAT-WEB-001** — The client MUST be React + TypeScript (`strict: true`) built with Vite, tested with Vitest; exact versions MUST be pinned in `package.json` + `package-lock.json` from the generator templates (P3).
- **PLAT-WEB-002** — Runtime dependencies MUST be exactly `react` and `react-dom`: HTTP uses `fetch`, state uses React built-ins, there is no router, state library, UI kit, or messaging/chat/sync SDK (brief constraint). Adding a runtime dependency is a spec change.

## 2. Structure

- **PLAT-WEB-003** — Source MUST be organised as below; imports flow only downward in the table (a folder may import from folders listed below it, never above):

| Folder | Contains | Must not import |
|---|---|---|
| `src/app/` | entry point, composition root (wires ports to the engine), top-level screen switch | — |
| `src/features/login/` | login screen | `src/data/`, other features |
| `src/features/chat/` | conversation list, conversation view, composer, connection status, offline toggle | `src/data/`, other features |
| `src/testing/` | `window.__AWARE__` hook (PLAT-WEB-012) | features |
| `src/data/` | `fetch` `Transport`, `localStorage` `LocalStore`, browser `ConnectivityMonitor` | React, features |
| `src/core/` | wire types, validation (CORE-NAME, CORE-TEXT), constants, ordering (CORE-SEQ), the protocol engine (connection cycle, outbox, cursor, epoch, dedupe), port interfaces (PLAT-HOOK-009), snapshot | React, DOM, `fetch`, `localStorage`, anything outside `src/core/` |

- **PLAT-WEB-004** — All protocol logic (every client-side `CORE-*` rule except rendering) MUST live in `src/core/`, so it runs in Vitest without a DOM; it mirrors Android `:core:protocol` responsibility for responsibility.
- **PLAT-WEB-005** — The engine MUST expose `subscribe(listener)` and `getSnapshot()` and React MUST read it through `useSyncExternalStore`; components never call `Transport` or `LocalStore` directly.

## 3. Adapters

- **PLAT-WEB-006** — The `Transport` MUST use `fetch` with an `AbortController` per request, enforce CORE-CONN-009 timeouts by aborting, and abort every in-flight request when the engine goes `offline` (CORE-CONN-004); JSON parsing MUST ignore unknown response fields (CORE-HTTP-005).
- **PLAT-WEB-007** — `IdGenerator` MUST use `crypto.randomUUID()`; UTF-8 byte length (CORE-TEXT-003) MUST be computed with `TextEncoder`, and unpaired surrogates MUST be detected by an explicit check (not by relying on `TextEncoder`, which replaces them).
- **PLAT-WEB-008** — `ConnectivityMonitor` MUST report `network_available` from `navigator.onLine` and update it on the window `online` / `offline` events.

## 4. Local storage

- **PLAT-WEB-009** — Identity, epoch, cursor, messages, outbox and the next outbox order number MUST be stored as one JSON document under the `localStorage` key `aware.v1`, rewritten with a single `setItem` per state change (so CORE-CURSOR-002's "store, then cursor" is one atomic write).
  - Why `localStorage`: synchronous, one atomic write per change, trivially inspectable by Playwright; demo data stays far below the quota. IndexedDB was rejected: asynchronous transactions add code and ordering hazards with no benefit at this size.
- **PLAT-WEB-010** — The client MAY assume one open tab per browser profile; a second tab is not coordinated (duplicate sends are harmless by CORE-MSG-001, but views may diverge until reload).

## 5. Server address

- **PLAT-WEB-011** — The server base URL MUST default to the build-time variable `VITE_AWARE_SERVER_URL`, or `http://localhost:8080` when unset, and MUST be overridable at runtime by the page query parameter `server` (read once at start-up, not persisted); only `http://localhost:<port>` and `http://127.0.0.1:<port>` values are accepted, others are ignored (E-LOCAL-1). The Vite dev server MUST use port `5173` with `strictPort`. Cross-origin access relies on the server's CORS headers (CORE-SRV-005); no dev proxy.

## 6. Test hooks

- **PLAT-WEB-012** — Every hook of PLAT-HOOK-001 MUST be a `data-testid` attribute; machine values (PLAT-HOOK-004) MUST be `data-state` (and on `message-<id>` also `data-seq`, empty string when none, and `data-from`) on the same element; `offline-toggle` MUST be an `<input type="checkbox">` whose `checked` is `offline_toggle`. Every build MUST define `window.__AWARE__ = { snapshot(): ClientSnapshot, setOffline(on: boolean): void, setNetworkAvailable(on: boolean): void, relaunch(): void }` (PLAT-HOOK-006; the app is local-only, so the hook is not stripped from production builds).

- **PLAT-WEB-018** — The relaunch control (PLAT-HOOK-011) MUST be a reload of the page at the same URL (Playwright `page.reload()`, or `window.__AWARE__.relaunch()`, which MUST call `location.reload()`); the `server` query parameter is part of the URL and therefore kept. Vitest tests relaunch by discarding the engine and building a new one over the same `LocalStore` data.

## 7. Tests the generator MUST produce (inside `clients/web/`)

- **PLAT-WEB-013** — Vitest unit tests for `src/core/` MUST cover every client-side `MUST` rule of `spec/core/` with at least one test each, using fakes for all ports, including an in-memory fake server implementing `spec/core/server-behavior.md` and a test that replays protocol Appendix A step by step and asserts the snapshot after each step.
- **PLAT-WEB-014** — Vitest tests MUST check the `fetch` `Transport` (mocked `fetch`) for each endpoint E1–E5 and each CORE-ERR-003 class; a test MUST parse every file in `spec/core/schema/examples/` into the wire types and re-serialize it to an equal JSON value; a test MUST assert the constants equal `spec/core/schema/constants.json`.
- **PLAT-WEB-015** — Component tests (Vitest + `@testing-library/react`, `jsdom`) MUST check every hook of PLAT-HOOK-001 with its PLAT-WEB-012 attributes and the screens' flows in `client-behavior.md` against fake ports; visible texts are asserted exactly as listed in `client-behavior.md` §8.1 (this file defines no texts).
- **PLAT-WEB-016** — Every test title MUST start with the spec id it covers (e.g. `it('CORE-OUTBOX-003 sends entries one at a time in order', …)`); `npm test` MUST run `vitest run` with both the default reporter and the `junit` reporter writing `test-results/junit.xml`.
- **PLAT-WEB-017** — The gate MUST be `npm ci && npm run build && npm test`, where `build` runs `tsc --noEmit` then `vite build`. Browser end-to-end tests (Playwright) live outside the client in `tests/web-e2e/` (QA) and MUST NOT be generated into `clients/web/`.
