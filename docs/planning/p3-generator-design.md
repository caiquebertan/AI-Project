# P3 generator design (gate G1, also D1's G1)

> **Author:** TL agent (claude-opus-5-5), stage S2, ref OM-0014. AI-written; awaiting the operator at **G1**.
> **Base:** `main` @ `4e45789`, spec `0.1.0`, WORKFLOW v0.3.0, decisions 0002 (Q15–Q17, Q19), 0011, 0013, 0014, 0016.
> **Scope (decision 0016 Q7):** this is P3's design and D1's S2 plan in one. Approving it at G1 approves both. The first `/generate <app>` is **D1's S3** (`state.py start-feature D1 --apps android,web --chain full`). DEV implementation waits for G1 and for P2 to be green (0016 Q6).
> **Not here:** conventions, templates and code. This file lists what they contain; DEV writes them after G1.

## 0. Principles (for reviewers in a hurry)
1. **Copy what can be copied; generate only what the spec decides.** Build infrastructure, version pins, the wrapper and lockfiles are templates copied by a script. The model writes sources, tests and the dependency lines of each module.
2. **Prove the toolchain before spending tokens.** A token-free *smoke build* of the templates runs on the operator's machine before the first `/generate` (PLAN risks 1, 2).
3. **One headless session per app, with module checkpoints.** One `claude -p` run per app. It compiles and tests module by module, so errors surface close to their cause.
4. **The spec names things; the generator stays generic.** Module lists, hook ids and texts are read from `spec/platform/*`. Templates are per *module kind*, not per feature, and prompts and conventions name no features (E-EVOL-1).
5. **Deterministic steps are scripts, not prompts.** Template copy, log digest, manifest, boundary and header checks are Python (stdlib). The model never retypes a lockfile or computes a hash.

## 1. Layout and generation order

### 1.1 Android (`clients/android/`, modules fixed by PLAT-ANDROID-004)
> Note: the TL task named `:core:storage`. The spec says `:core:data` (Room, connectivity, logging, Hilt bindings) and adds `:feature:login` and `:feature:chat`. The spec wins; renaming would be a spec reopen (G1 Q1).

| Order / checkpoint | Module (kind from the spec's *Kind* column) | Checkpoint command (inside `clients/android/`) |
|---|---|---|
| C0 | templates applied, one skeleton per module from its kind | `./gradlew --console=plain help` (configuration phase only) |
| C1 | `:core:protocol` (jvm-lib) + test fixtures (fakes, in-memory fake server) | `./gradlew :core:protocol:test` |
| C2 | `:core:network` (jvm-lib) | `./gradlew :core:network:test` |
| C3 | `:tools:driver` (jvm-app) | `./gradlew :tools:driver:test :tools:driver:installDist` |
| C4 | `:core:data` (android-lib: Room, Hilt) | `./gradlew :core:data:testDebugUnitTest` |
| C5 | each `:feature:*` (android-compose-lib) | `./gradlew :feature:<x>:testDebugUnitTest` |
| C6 | `:app` (android-app) | final gate (§4) |

Package and namespace: `app.aware.<module path, dots>` (e.g. `app.aware.core.protocol`). The driver main class is `app.aware.driver.MainKt` (PLAT-ANDROID-031). Shared fakes live in `:core:protocol` `src/testFixtures/` (java-test-fixtures plugin) and are consumed with `testImplementation(testFixtures(project(":core:protocol")))`. That keeps them out of `src/main/`, which the CORE-TIME-003 scan reads (PLAT-ANDROID-030).

### 1.2 Web (`clients/web/`, structure fixed by PLAT-WEB-003)
| Checkpoint | Folder | Command (inside `clients/web/`) |
|---|---|---|
| C0 | templates applied | `npm ci` |
| C1 | `src/core/` + `src/test/` (fakes, fake server) | `npx tsc --noEmit && npx vitest run src/core` |
| C2 | `src/data/` | `npx vitest run src/data` |
| C3 | `src/testing/` | `npx vitest run src/testing` |
| C4 | each `src/features/<x>/` | `npx vitest run src/features` |
| C5 | `src/app/` | final gate (§4) |

Tests sit next to their sources as `*.test.ts(x)`. Component tests start with `// @vitest-environment jsdom`; the default environment is `node`, so `src/core` really runs without a DOM (PLAT-WEB-004).

### 1.3 Who writes what
| Template-copied by `apply_templates.py` (byte-for-byte; placeholders `{{spec_version}}`, `{{header}}` only) | Model-generated |
|---|---|
| Android: `settings.gradle.kts`, root `build.gradle.kts`, `gradle.properties`, `gradle/libs.versions.toml`, wrapper (`gradlew`, `gradlew.bat`, `gradle/wrapper/*`), `.gitignore`, `README.md` | each module's `build.gradle.kts`, instantiated from its kind skeleton; the model fills only `namespace` and the `// BEGIN deps` … `// END deps` region, using catalog aliases only |
| Android app kind: `AndroidManifest.xml`, `res/xml/network_security_config.xml` (fixed by PLAT-ANDROID-013..015) | all Kotlin sources, resources, all tests |
| Web: `package.json`, `package-lock.json`, `tsconfig.json`, `vite.config.ts`, `index.html`, `src/vite-env.d.ts`, `.gitignore`, `README.md` | everything else under `src/` |

No CI files, no lint configs, no IDE files. `settings.gradle.kts` includes every directory that has a `build.gradle.kts` (depth ≤ 2, `build/` excluded), so a module list that changes in the spec needs no template edit. After the run, `apply_templates.py --check` fails if a template-owned file differs from its rendered template, which stops the model from "fixing" pins.

## 2. Contents of conventions and templates

### 2.1 `generator/conventions/android.md` (code shape only; no behavior, no feature nouns)
1. **Scope and precedence:** spec > conventions; the conventions cite spec ids and never restate rules.
2. **Module mapping:** read the module table in the platform spec, map *Kind* → kind skeleton, take dependencies from the *May depend on* column.
3. **Dependencies:** use `libs.*` aliases only and never a version literal. The catalog is closed: a library the catalog lacks is `BLOCKED` (generator gap), never added.
4. **Kotlin shape:** `@Serializable` data classes for wire models; a sealed result type for each transport outcome class (CORE-ERR-003); constants in one object; no `!!`, no `GlobalScope`, no `Thread.sleep`.
5. **Concurrency:** one engine scope; state is mutated only under one `Mutex` or a single-thread dispatcher; snapshot as `StateFlow`; time and waiting only through the injected `Clock` and `Scheduler`; dispatchers are injected.
6. **Persistence:** store-then-cursor in one Room `withTransaction`; `exportSchema = false`; in-memory Room in tests.
7. **DI and UI:** Hilt modules only in the data-kind module; `@HiltViewModel`; Compose M3; hook ids as constants used with `Modifier.testTag`; fixed texts in one Kotlin object that copies the behavior spec's text table.
8. **Tests:** JUnit 4 everywhere (one XML format, required by Robolectric); `runTest` with virtual time; `@RunWith(AndroidJUnit4::class)` and `@Config(sdk = [<compileSdk>])`; names start with spec ids (PLAT-ANDROID-023); spec files are read through the system property `aware.repoRoot` that the kind skeleton sets.
9. **Checkpoints and commands** (§1.1), and the self-repair rules (§3.2).
10. **Pre-gate self-check:** no version literals in module build files; no host other than the allowed ones (E-LOCAL-1); headers present.
11. **Known pitfalls:** starts empty; pattern nits from REV are added here (0002 Q11).

### 2.2 `generator/conventions/web.md`
Same sections, adapted: `strict` TypeScript and no `any`; imports flow only downward (PLAT-WEB-003); `useSyncExternalStore`; one `fetch` per request plus an `AbortController` used only for the timeout; one `localStorage.setItem` per state change; Vitest with explicit imports (no globals); `@testing-library/react` queries by `data-testid`; fakes in `src/test/`; the jsdom docblock for component tests; checkpoints from §1.2.

### 2.3 `generator/templates/android/`
| File | Purpose |
|---|---|
| `settings.gradle.kts` | repositories (google, mavenCentral, gradlePluginPortal), `FAIL_ON_PROJECT_REPOS`, module auto-include |
| `build.gradle.kts` | plugins via catalog aliases, `apply false` |
| `gradle.properties` | JVM args, AndroidX, non-transitive R, `aware.serverUrl` default; contains nothing the PLAT-ANDROID-030 patterns match |
| `gradle/libs.versions.toml` | **all** pins (§2.5) |
| `gradle/wrapper/gradle-wrapper.properties` | distribution URL + `distributionSha256Sum` |
| `gradle/wrapper/gradle-wrapper.jar`, `gradlew`, `gradlew.bat` | wrapper (binary jar produced on the operator's machine, §5) |
| `kinds/jvm-lib.gradle.kts` | Kotlin JVM, serialization plugin, toolchain 17, `java-test-fixtures` when the module exports fakes, `aware.repoRoot` test property |
| `kinds/jvm-app.gradle.kts` | jvm-lib + `application` (main class placeholder) |
| `kinds/android-lib.gradle.kts` | Android library, KSP, Hilt, Room, Robolectric test options (`isIncludeAndroidResources = true`) |
| `kinds/android-compose-lib.gradle.kts` | android-lib + Compose compiler plugin, Compose BOM, ui-test-junit4, ui-test-manifest |
| `kinds/android-app.gradle.kts`, `kinds/android-app/AndroidManifest.xml`, `kinds/android-app/res/xml/network_security_config.xml` | application id `app.aware.android`, minSdk 26, `BuildConfig.SERVER_BASE_URL` from `aware.serverUrl`, two permissions, cleartext only for local hosts |
| `.gitignore`, `README.md` | build outputs, `.kotlin/`; generated-boundary note |
| `_smoke/` | token-free smoke modules, one per kind (a Room entity + Hilt module, a Compose screen with a Robolectric test, a driver main), used only by `--smoke`, never copied into `clients/` |

### 2.4 `generator/templates/web/`
`package.json` (exact versions; scripts: `dev`, `build` = `tsc --noEmit && vite build`, `test` = `vitest run --reporter=default --reporter=junit --outputFile.junit=test-results/junit.xml`; `engines`), `package-lock.json` (from the smoke run), `tsconfig.json` (`strict`, `jsx: react-jsx`, `moduleResolution: bundler`), `vite.config.ts` (React plugin, port 5173 `strictPort`, Vitest `include: src/**/*.test.{ts,tsx}`, environment `node`), `index.html`, `src/vite-env.d.ts` (types `VITE_AWARE_SERVER_URL`), `.gitignore`, `README.md`, `_smoke/` (a minimal app, one node test, one jsdom component test).

### 2.5 Pins (exact patch versions: **TBD-verify-on-operator-machine**; registries are unreachable from the cloud, probed 2026-10-13)
| Item | Proposed line | Reason |
|---|---|---|
| Host JDK / bytecode | JDK 21 (Temurin) / `jvmToolchain(17)` | 21 is known good in ENVIRONMENT; 17 is the AGP 8 baseline |
| Gradle | 8.14.x | last 8.x line; matches AGP 8.x |
| AGP | latest 8.x (candidate 8.13.x) | the model knows the AGP 8 DSL best; AGP 9 changes Kotlin plugin wiring (G1 Q8) |
| Kotlin / KSP | 2.2.x / the KSP release matching it | K2 with the Compose compiler plugin at the same version |
| compileSdk / targetSdk / minSdk | 35 / 35 / 26 | Robolectric supports 35 well; minSdk from PLAT-ANDROID-003 |
| Compose BOM, activity-compose, navigation-compose, lifecycle | latest stable matching AGP and Kotlin | the BOM pins Compose as a set |
| Hilt / hilt-navigation-compose | 2.5x with KSP | Room and Hilt both on KSP; no kapt |
| Room | 2.7.x+ | KSP, Kotlin codegen, in-memory DB for tests |
| Retrofit / OkHttp / MockWebServer | Retrofit 2.11+ or 3.x (built-in kotlinx-serialization converter) / OkHttp 4.12.x / `mockwebserver` 4.12.x | stable set; MockWebServer is required by PLAT-ANDROID-020 |
| kotlinx-coroutines / -serialization | 1.10.x / 1.8–1.9.x | must match Kotlin |
| Robolectric / JUnit | 4.14+ (SDK 35) / 4.13.2 | JVM UI gate (0002 Q19) |
| Node | ≥ 22 in `engines`; operator has v26.11.1 | ENVIRONMENT says 22 LTS (G1 Q7) |
| React / react-dom (+ `@types`) | 19.x | the only runtime dependencies (PLAT-WEB-002) |
| TypeScript | 5.9.x | stay on 5.x; avoid the TS 6/7 transition |
| Vite / @vitejs/plugin-react | 7.x / the matching major | current line at the knowledge cutoff |
| Vitest / jsdom / @testing-library/react + /dom | the line supporting that Vite / 26.x / 16.x + 10.x | PLAT-WEB-015 |

The real pins are whatever the smoke run (§5) resolves and passes with: `libs.versions.toml` and `package-lock.json` as committed in templates.

## 3. How `/generate` runs

### 3.1 Prompting
- **One pass per app** (`claude -p "/generate <app>"`), following the checkpoint order. `--module <name>` remains for scoped fix loops (0002 Q16). Per-module invocations were rejected: the spec would be reloaded about seven times, and interfaces would drift between sessions.
- **Context, in the order of `generate.md` §1:** spec index → `spec/core/**`, `spec/scenarios/**`, enabled `spec/extensions/**` → the platform spec + `test-hooks.md` + the snapshot schema → conventions → the template file list. About 172 KB (≈ 45k tokens) of spec, read once. The prompt says not to read `clients/`, `docs/plans/` or the other app.
- **Plan as durable memory:** `.work/generate/<app>/plan.md` lists modules, files, spec ids per file and tests. It is re-read after auto-compaction and before each checkpoint.
- **Prompt edits by DEV (P3):** `generate.md` §3.2 becomes "run `apply_templates.py --app {{app}}`"; §4 gains the checkpoint loop and the digest step. Both changes pass `lint_prompts.py`.
- **Bounds (config `generate.claude_flags`):** `--max-turns 400 --max-budget-usd 75` per app, recalibrated after the first run (G1 Q6). `--output-format json` gives the final usage and cost for the run log.

### 3.2 Self-repair (≤ 3, `self_repair_max`)
1. Every checkpoint or gate command writes its full log to `.work/generate/<app>/logs/<checkpoint>-<n>.log`.
2. On failure, `build_digest.py --app <app> --log <file>` (new, stdlib) prints a compact digest: Gradle `What went wrong` blocks and `e:`/`error:` lines, `tsc` `error TS` lines, failing tests from JUnit XML (message + 30 stack lines, at most 20 failures), and the last 80 lines. It also prints one class: `CODE`, `ENV` or `PIN`.
3. `CODE`: the model fixes it inside `clients/<app>/` and reruns the checkpoint. Each rerun is one attempt. Budget: **≤ 3 per checkpoint, ≤ 12 per run** (G1 Q3; today WORKFLOW says ≤ 3 per run). Weakening or deleting an id-named test is forbidden (already in `generate.md`).
4. `ENV` → `ENV_FAILURE`, no attempt spent. Patterns live in config `generate.env_patterns`: `UnknownHostException`, `Could not GET`, `Connection timed out`, `ENOTFOUND`, `EAI_AGAIN`, `ECONNRESET`, proxy `403`/`407`, `SDK location not found`, `ANDROID_HOME`, `Unsupported class file major version`, `EBADENGINE`, `daemon disappeared`. The operator retries once (`env_retry: 1`), then G2.
5. `PIN` (`Could not find <g:a:v>`, npm `ETARGET`/`No matching version`) → `BLOCKED` "template pin". This is a generator defect the model may not touch (templates are read-only to it), so G2.

### 3.3 Manifest `.generated`
`check_headers.py --write-manifest` stays the writer. Optional schema additions (backward-compatible): per file `origin: template|model`; top level `claude_code_version`, `self_repair_attempts`, `checkpoints` (name → attempts, result). `model_id` is the model that actually ran.

### 3.4 Determinism and pinning
- `generate_model = claude-opus-5-5`, `generate_model_fallback = claude-sonnet-5-5` (ids checked against the Anthropic models page 2026-10-13). The fallback is **manual only**: no `--fallback-model` flag, so one run never mixes models. A fallback run is recorded in the manifest and the run log (G1 Q4).
- Also pinned or recorded: Claude Code CLI version (recorded in the manifest; the README names it), `--effort high` (TBD-verify for this model), templates and lockfile, spec tag.
- LLM output is not byte-deterministic. E-DET-1 compares the **file set per module and the test results**, not bytes. The conventions narrow variance with file naming per module, the plan step and closed dependencies.

### 3.5 `regen_check.py`
No logic change. `regen.generate_cmd` becomes `claude -p "/generate {app}" --model {model} {claude_flags}`. It needs the build/test commands below, so `TBD` disappears. Its boundary check already ignores `.work/` (git-ignored). Add `apply_templates.py --check` and `check_headers.py --strict` as steps after `test`.

### 3.6 Headless permissions (config `generate.claude_flags`, TBD-verify)
`--permission-mode acceptEdits --permission-prompts none --allowedTools "Read" "Write" "Edit" "Glob" "Grep" "Bash(./gradlew *)" "Bash(npm *)" "Bash(npx *)" "Bash(python3 generator/scripts/*)" "Bash(git status *)" "Bash(git rev-parse *)" "Bash(rm -rf clients/*)" "Bash(mkdir *)" "Bash(ls *)" "Bash(cd *)"`. With `--permission-prompts none` a missing rule is denied rather than hanging the run. Fallback: `--dangerously-skip-permissions` in a throwaway clone only (G1 Q5).

## 4. Build/test commands (fill `generator.json`) and report feed

| Key | Android | Web |
|---|---|---|
| `build` | `./gradlew --console=plain assembleDebug :tools:driver:installDist` | `npm ci && npm run build` |
| `test` | `./gradlew --console=plain --continue testDebugUnitTest :core:protocol:test :core:network:test :tools:driver:test` | `npm test` |
| Reports | `*/build/test-results/{test,testDebugUnitTest}/TEST-*.xml` (and `core/*`, `feature/*`, `tools/*` below them) | `test-results/junit.xml` |

`--continue` collects every failing module in one run, so one digest can feed one repair. These commands match PLAT-ANDROID-024 and PLAT-WEB-016/017.

**Into `check_trace.py`** (D1 S5/S6, run on the operator's machine or after sending the reports back):
```
find clients/android -path '*/build/test-results/*' -name 'TEST-*.xml' -exec cp {} docs/runs/D1/reports/android/ \;
cp clients/web/test-results/junit.xml docs/runs/D1/reports/web/
python3 generator/scripts/check_trace.py --feature F1,F2,F3 \
  --junit android=docs/runs/D1/reports/android --junit web=docs/runs/D1/reports/web \
  [--playwright web=docs/runs/D1/reports/web-e2e.json] --write --acceptance docs/runs/D1/acceptance.md
```
A test carries an id when the id appears in its JUnit `classname name` (Kotlin backtick name, Vitest `describe > it` title). Playwright JSON comes from QA's `tests/web-e2e/` (reporter `json`, P4), not from P3. The reports are committed under `docs/runs/D1/reports/` because they are small and evidence (G1 Q9).

## 5. First run on the operator's machine (skeleton first)

**Before (environment, OM-0013 showed gaps):** Python ≥ 3.10 (has 3.9.6), JDK 21, Android command-line tools with `platforms;android-35` and build-tools, `ANDROID_HOME`, `claude` logged in. Then `python3 generator/scripts/preflight.py --strict` must exit 0.

| Session | Operator runs | Sends back / commits | Tokens |
|---|---|---|---|
| **A. Smoke** (≈ 30 min) | `python3 generator/scripts/apply_templates.py --app android --smoke --out .work/smoke/android` then, inside it, `gradle wrapper --gradle-version <pin>` (only if the jar is missing; needs `brew install gradle`) and the §4 build + test commands; then the same for web with `npm install` (creates the lockfile), `npm run build`, `npm test` | logs; `package-lock.json`; `gradle-wrapper.jar` + `distributionSha256Sum`; `java -version`, `sdkmanager --list_installed`, `node -v`, `claude --version`. ORC/DEV fix pins in the cloud and repeat until green, then commit them to `generator/templates/` | 0 |
| **B. First generation** (D1 S3) | `claude -p "/generate android" --model claude-opus-5-5 <claude_flags>`; then web (a parallel worktree is allowed) | the `regen(<app>): spec 0.1.0 @ gen <sha>` commit (exact command and trailers handed over by ORC); `.work/generate/<app>/{plan.md,logs/,result.json}` as a zip; test reports (§4) | 1 run per app |
| **C. Fix loop** (only if needed) | after a cloud fix to the generator inputs: `/generate <app> --module <m>`, then the full gate | same as B | ≤ 1 run per loop |

Why this order: session A proves wrapper, pins, SDK, KSP/Hilt/Room, Robolectric artifact download, testFixtures and the Vite/Vitest/jsdom set with zero tokens. In session B a failure is then almost certainly in generated code, which self-repair can fix, or in the conventions, which DEV can fix.

## 6. Not verifiable offline (the first operator run must confirm)
1. Every exact version in §2.5 resolves and the set builds together (AGP↔Gradle↔Kotlin↔KSP↔Hilt↔Room↔Compose; Vite↔Vitest↔jsdom).
2. Gradle wrapper jar and checksum; npm lockfile contents.
3. Robolectric SDK 35 artifact download and Compose tests under Robolectric; `java-test-fixtures` consumed by Android modules.
4. Vitest `junit` reporter flags and its `classname`/`name` shape, so ids are carried in `check_trace`.
5. Claude Code flags on the operator's CLI version: `--allowedTools` patterns for compound `cd … && ./gradlew` commands, `--permission-prompts none` (needs v2.1.259+), `--max-budget-usd`, `--effort high` for `claude-opus-5-5`, `/generate` picked up in `-p` mode.
6. Real token use and wall time per app (calibrate §3.1 bounds); whether one session per app fits without harmful compaction.
7. That Node 26 builds the pinned toolchain (`engines`); `EBADENGINE` warnings.
8. `apply_templates.py`, `build_digest.py` and the new checkpoint loop: written and unit-tested in the cloud, but never run against real tool output.

## 7. DEV deliverables after G1 (for sizing; P3 implementation, cloud)
`generator/conventions/{android,web}.md`; `generator/templates/{android,web}/` (§2.3–2.4); `generator/scripts/apply_templates.py` (copy, `--check`, `--smoke`) and `build_digest.py` with tests in `generator/tests/`; `generator.json` (`generate_model`, fallback, build/test, `generate.claude_flags`, `generate.env_patterns`, `self_repair_total_max`); `generate.md` §3–4 edits; optional manifest schema fields; RUN.md and ENVIRONMENT.md (JDK 21, platform 35, Python ≥ 3.10); WORKFLOW §5.2 only if G1 Q3 = per checkpoint. All must pass `lint_prompts.py` and the 82 harness self-tests.

## 8. G1 questions (recommended default in bold)
| # | Question | Default |
|---|---|---|
| Q1 | Android module names: the spec's `:core:data` + `:feature:*`, or rename to `:core:storage` as in the TL task? | **Keep the spec.** A rename is a spec reopen (`spec_reopen` 1 of 2) for no behavior gain |
| Q2 | Module build files: kind skeletons (template) with the model filling only namespace + deps, or fully model-written? | **Kind skeletons.** Build scripts are where LLM Android builds fail first |
| Q3 | Self-repair budget: ≤ 3 per run (WORKFLOW today) or ≤ 3 per checkpoint with ≤ 12 per run? | **Per checkpoint, ≤ 12 total.** About 7 Android checkpoints on a first generation; 3 in total would send ordinary compile slips to G2 |
| Q4 | Model pin: Opus primary, Sonnet fallback, manual fallback only (no `--fallback-model`)? | **Yes**: `claude-opus-5-5` / `claude-sonnet-5-5`, never mixed in one run |
| Q5 | Headless permissions: explicit allowlist + `--permission-prompts none`, or `--dangerously-skip-permissions`? | **Allowlist**; skip-permissions only in a throwaway clone if the allowlist blocks a needed command |
| Q6 | Cost bounds per app run | **`--max-turns 400`, `--max-budget-usd 75`**, recalibrated after session B |
| Q7 | Node: accept your v26 (`engines >= 22`) or install 22 LTS? | **Accept ≥ 22**, record the actual version; graders may use any LTS ≥ 22 |
| Q8 | AGP line: 8.x (known DSL) or 9.x (current)? | **8.x latest**, revisit in FUTURE.md |
| Q9 | Commit test reports under `docs/runs/D1/reports/<app>/`? | **Yes** (small; evidence for `check_trace` and graders) |
| Q10 | Run the token-free smoke session A before the first `/generate`? | **Yes.** It is the main mitigation for PLAN risks 1 and 2 |
