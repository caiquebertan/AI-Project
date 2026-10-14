# Web generator conventions

> Code shape for `clients/web/`. Read by `/generate web` after the spec (`generator/prompts/generate.md` §1). Design: `docs/planning/p3-generator-design.md` §1.2, §2.2, §3.2 (approved at G1, decision 0017).
> These conventions name no product behavior and no product nouns (E-EVOL-1). Every behavior comes from `spec/`.

## 1. Scope and precedence
1. The spec wins: `spec/core/` > `spec/extensions/` > `spec/platform/` > this file. If this file seems to contradict the spec, follow the spec and say so in the final report; if the spec contradicts itself, return `SPEC_ISSUE`.
2. This file only says **how code is shaped**. It cites spec ids and never restates a rule.
3. Template-owned files (§3.1) are read-only for the generator. A failure that needs a template change is `BLOCKED` (generator gap), never a local edit.

## 2. Folder mapping
1. Folders, their contents and the import direction come from the table of `PLAT-WEB-003`. Imports flow only downward in that table; a folder never imports from a folder above it, and `src/features/*` never import each other.
2. The entry point is `src/app/main.tsx` (named by the template `index.html`); it mounts the root component into `#root`.
3. Shared test fakes (fake ports, the in-memory fake server of `PLAT-WEB-013`) live in `src/test/`. Nothing outside test files imports from `src/test/`.
4. File names: components `PascalCase.tsx`; everything else `camelCase.ts`; tests next to their source as `<name>.test.ts(x)`.

## 3. Build files and dependencies
1. **Template-owned** (copied by `apply_templates.py`, never edited): `package.json`, `package-lock.json`, `tsconfig.json`, `vite.config.ts`, `index.html`, `src/vite-env.d.ts`, `.gitignore`, `README.md`.
2. **The dependency set is closed.** Runtime dependencies are exactly those of `PLAT-WEB-002`; dev dependencies are those in the template `package.json`. Never run `npm install <pkg>` and never edit `package.json`. A missing package is `BLOCKED {"reason": "package set lacks <name>"}`.
3. Never write `package-lock.json`; `npm ci` uses the template lockfile.

## 4. TypeScript shape
1. `strict` mode (template `tsconfig.json`). No `any`, no `as unknown as`, no non-null `!` on values that can be absent, no `@ts-ignore`/`@ts-expect-error` in production code.
2. Wire types are `type` aliases whose field names match the schema field names; parsing validates shape by hand and ignores unknown fields (`PLAT-WEB-006`).
3. One discriminated union per transport outcome, with one variant per class of `CORE-ERR-003`; callers switch exhaustively (a `never` check in the default branch).
4. All protocol constants in one module whose values equal `spec/core/schema/constants.json`.
5. Hook ids of `PLAT-HOOK-001` are constants in one module under `src/core/`; fixed visible texts in one module that copies the text table of `spec/core/client-behavior.md` exactly.
6. No default exports except where a tool needs one; one main export per file. Keep files under about 300 lines.

## 5. Concurrency and state
1. One engine instance, created in the composition root (`src/app/`), with every port injected through its constructor (`PLAT-HOOK-009`). No module-level mutable state.
2. The engine exposes `subscribe` / `getSnapshot` (`PLAT-WEB-005`); React reads it only with `useSyncExternalStore`. `getSnapshot` returns the same object until state changes.
3. Time and waiting only through the injected `Clock` and `Scheduler`; no `setTimeout`/`setInterval`/`Date.now()` in `src/core/` outside the default port implementations.
4. One `fetch` per request; an `AbortController` per request used only for the timeout (`PLAT-WEB-006`).
5. Persistence: one `localStorage.setItem` per state change, of the whole document (`PLAT-WEB-009`).

## 6. React
1. Function components and hooks only. Hook ids applied as `data-testid`, machine values as `data-*` attributes per `PLAT-WEB-012`.
2. Components receive the engine (or narrow callbacks) through props or one React context created in `src/app/`; components never touch `Transport` or `LocalStore`.
3. No CSS framework; inline styles or one plain CSS file imported by `src/app/main.tsx`.

## 7. Tests
1. Vitest with explicit imports (`import { describe, it, expect, vi } from 'vitest'`); no globals.
2. The default environment is `node` (template `vite.config.ts`), so `src/core/` tests run without a DOM. Component tests start with the docblock `// @vitest-environment jsdom` on the first line after the GENERATED header.
3. Component tests use `@testing-library/react` and query by `data-testid` (`getByTestId`), never by CSS selectors.
4. Every test title starts with the spec ids it proves (`PLAT-WEB-016`); nest with `describe` only if the id stays in the `it` title. The id must appear in the JUnit `name` so `check_trace.py` can read it.
5. Tests read spec files (schema examples, constants) from `process.env.AWARE_REPO_ROOT`, which the template `vite.config.ts` sets for every test (default: two levels above `clients/web/`), using `node:fs` and `node:path`.
6. Fake time: inject the fake `Clock`/`Scheduler`; use `vi.useFakeTimers()` only in tests of the default port implementations.
7. Never weaken, skip (`it.skip`, `it.todo`) or delete a test that carries a spec id to make a checkpoint pass.
8. The tests the client must contain are listed in `PLAT-WEB-013`..`016`, `-021`..`-023` and `PLAT-HOOK-014`/`-015`.

## 8. Checkpoints (generation order) and commands
Generate and verify folder by folder, in this order. Run every command through the checkpoint runner from the repository root, which runs it inside `clients/web/`, keeps the log and counts attempts:
`python3 generator/scripts/checkpoint.py --app web --checkpoint <id> -- <command>`

| Id | What exists after it | Command |
|---|---|---|
| `C0` | templates applied | `npm ci` |
| `C1` | `src/core/` and `src/test/` (fakes, fake server) | `npx tsc --noEmit` then `npx vitest run src/core` (two runner calls, same checkpoint id) |
| `C2` | `src/data/` | `npx vitest run src/data` |
| `C3` | `src/testing/` | `npx vitest run src/testing` |
| `C4` | every `src/features/<x>/` | `npx vitest run src/features` |
| `C5` | `src/app/`; then the final gate | the app's build command, then its test command (config `apps.web.build` / `.test`; the prompt's Parameters list them) |

Self-repair (decision 0017): on a failed checkpoint the runner prints a digest and one class.
- `CODE`: fix inside `clients/web/` and rerun the same checkpoint. At most 3 attempts per checkpoint and 12 per run (the runner refuses more).
- `ENV`: stop with `ENV_FAILURE`; no attempt is spent.
- `PIN`: stop with `BLOCKED` "template pin"; templates are read-only for the generator.

## 9. Pre-gate self-check (before `C5`)
1. `package.json` and `package-lock.json` are unchanged (`apply_templates.py --check`).
2. No host other than those allowed by `PLAT-WEB-011` in model-written files (E-LOCAL-1).
3. Every model-written file with a comment syntax starts with the GENERATED header.
4. No production file matches the patterns of `PLAT-HOOK-015` and `PLAT-WEB-023` (the generated test enforces it; check before running it).
5. No import goes upward in the `PLAT-WEB-003` table.

## 10. Known pitfalls
(Empty at P3. Pattern nits from review are added here, decision 0002 Q11.)
