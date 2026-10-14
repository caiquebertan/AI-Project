# Android generator conventions

> Code shape for `clients/android/`. Read by `/generate android` after the spec (`generator/prompts/generate.md` §1). Design: `docs/planning/p3-generator-design.md` §1.1, §2.1, §3.2 (approved at G1, decision 0017).
> These conventions name no product behavior and no product nouns (E-EVOL-1). Every behavior comes from `spec/`.

## 1. Scope and precedence
1. The spec wins: `spec/core/` > `spec/extensions/` > `spec/platform/` > this file. If this file seems to contradict the spec, follow the spec and say so in the final report; if the spec contradicts itself, return `SPEC_ISSUE`.
2. This file only says **how code is shaped**. It cites spec ids and never restates a rule. Where a rule is cited, read it in the spec.
3. Template-owned files (§3.1) are read-only for the generator. A failure that needs a template change is `BLOCKED` (generator gap), never a local edit.

## 2. Module mapping
1. The module list, each module's *Kind* and its *May depend on* column come from the module table of `PLAT-ANDROID-004` (and `PLAT-ANDROID-005`). Do not add, rename or merge modules.
2. Directory = module path with `:` → `/` (`:core:protocol` → `core/protocol/`). `settings.gradle.kts` includes every directory that has a `build.gradle.kts` (depth ≤ 2), so no settings edit is ever needed.
3. *Kind* → skeleton in `generator/templates/android/kinds/`:

| Spec *Kind* | Skeleton |
|---|---|
| pure Kotlin/JVM | `jvm-lib` |
| pure Kotlin/JVM application | `jvm-app` |
| Android library | `android-lib` |
| Android library (Compose) | `android-compose-lib` |
| Android application | `android-app` |

4. Package and Android namespace: `app.aware.<module path with dots>` (`core/protocol` → `app.aware.core.protocol`). Where a spec rule fixes a package or class name, the spec wins (the driver main class of `PLAT-ANDROID-031`).
5. Instantiate each module's `build.gradle.kts` with the script, never by hand:
   `python3 generator/scripts/apply_templates.py --app android --kind <kind> --module <dir> [--main-class <fqcn>]`
   It writes the skeleton with the namespace filled and an empty `// BEGIN deps` … `// END deps` region. **Edit only that region.** `apply_templates.py --check` fails if anything else differs from the skeleton.
6. The application module's manifest and network security config are template-owned (`PLAT-ANDROID-013`..`015`). The manifest names `.AwareApplication` (a `@HiltAndroidApp` `Application`) and `.MainActivity` (a `@AndroidEntryPoint` `ComponentActivity`) relative to the module namespace; create exactly those two classes.

## 3. Build files and dependencies
1. **Template-owned** (copied by `apply_templates.py`, never edited): `settings.gradle.kts`, root `build.gradle.kts`, `gradle.properties`, `gradle/libs.versions.toml`, the Gradle wrapper (`gradlew`, `gradlew.bat`, `gradle/wrapper/*`), `.gitignore`, `README.md`, and the application module's `src/main/AndroidManifest.xml` and `src/main/res/xml/network_security_config.xml`.
2. In the deps region use catalog aliases only (`implementation(libs.x.y)`, `testImplementation(...)`, `ksp(...)`, `implementation(project(":core:protocol"))`). Never write a version literal or a `group:artifact:version` string.
3. **The catalog is closed.** If a library the spec requires is missing from `gradle/libs.versions.toml`, stop with `BLOCKED {"reason": "catalog lacks <library>"}`. Never add a library, plugin or repository.
4. Project dependencies follow the *May depend on* column exactly; nothing depends on the driver module.
5. Shared test fakes (fake ports, the in-memory fake server of `PLAT-ANDROID-019`) live in `core/protocol/src/testFixtures/kotlin/` (the `jvm-lib` skeleton applies `java-test-fixtures`). Other modules use them with `testImplementation(testFixtures(project(":core:protocol")))`. Fakes never go in `src/main/`, which the `PLAT-ANDROID-030` scan reads.

## 4. Kotlin shape
1. Wire models are `@Serializable` data classes whose property names match the schema field names (use `@SerialName` for snake_case). One `Json` instance configured per `PLAT-ANDROID-008`.
2. One sealed result type per transport outcome, with one subclass per class of `CORE-ERR-003`; callers branch with exhaustive `when`.
3. All protocol constants in one `object` whose values equal `spec/core/schema/constants.json`.
4. Forbidden: `!!`, `GlobalScope`, `runBlocking` in production code, `Thread.sleep`, `lateinit` on state the engine reads, platform types leaking into `:core:protocol`.
5. Text sizes and validation per `PLAT-ANDROID-010`; ids from the injected `IdGenerator`.
6. One public type per file; file name = type name. Keep files under about 300 lines; split by responsibility, not by layer.

## 5. Concurrency
1. One engine, one `CoroutineScope` owned by the engine (`PLAT-ANDROID-007`); dispatchers are injected, never `Dispatchers.*` inside `:core:protocol` logic.
2. Engine state is mutated in one place only: under one `Mutex` or on a single-thread dispatcher. Readers see an immutable snapshot through a `StateFlow` (`PLAT-ANDROID-018`).
3. Time and waiting only through the injected `Clock` and `Scheduler` ports (`PLAT-HOOK-009`); no `delay` on wall time outside the default `Scheduler`, no `System.currentTimeMillis()` outside the default `Clock`.
4. Never cancel an in-flight transport call when the engine stops starting calls (`PLAT-ANDROID-009`).

## 6. Persistence
1. One Room database per `PLAT-ANDROID-012`; `exportSchema = false`; schema version 1; no migrations.
2. "Store, then cursor" writes run in one `withTransaction` block.
3. An explicit monotonically increasing order column where the spec asks for an order.
4. Tests use `Room.inMemoryDatabaseBuilder` (with `allowMainThreadQueries()` only in tests).

## 7. Dependency injection and UI
1. Hilt modules (`@Module @InstallIn(SingletonComponent::class)`) live only in the `android-lib` kind module; it binds every port. Other modules only consume constructor-injected interfaces.
2. The server base URL is `BuildConfig.SERVER_BASE_URL` (`PLAT-ANDROID-013`), which the `android-lib` and `android-app` skeletons define from the Gradle property `aware.serverUrl`.
3. ViewModels are `@HiltViewModel` with `@Inject constructor`; screens collect state with `collectAsStateWithLifecycle()`; Compose Material 3 only.
4. Hook ids of `PLAT-HOOK-001` are constants in one Kotlin `object` in `:core:protocol` and are applied with `Modifier.testTag(...)` plus the semantics of `PLAT-ANDROID-016`.
5. Fixed visible texts live in one Kotlin `object` that copies the text table of `spec/core/client-behavior.md` exactly; no Android string resources for them (texts are fixed English).
6. Navigation: one Activity and Compose navigation (`PLAT-ANDROID-003`).

## 8. Tests
1. JUnit 4 everywhere (one XML report format; Robolectric needs it). Coroutine tests use `runTest` with virtual time and the fake `Scheduler`/`Clock`.
2. Robolectric tests: `@RunWith(AndroidJUnit4::class)` and `@Config(sdk = [35])`; Compose UI tests use `createComposeRule()`.
3. Every test name starts with the spec ids it proves (`PLAT-ANDROID-023`), in Kotlin backtick names; one test may name several ids. The id must appear in the JUnit `name` so `check_trace.py` can read it.
4. Tests read spec files (schema examples, constants) through `System.getProperty("aware.repoRoot")`, which every skeleton sets for test tasks (default: two levels above `clients/android/`).
5. Never weaken, skip (`@Ignore`) or delete a test that carries a spec id to make a checkpoint pass.
6. The tests each module must contain are listed in `PLAT-ANDROID-019`..`022`, `-028`..`-030`, `-034` and `PLAT-HOOK-014`/`-015`.

## 9. Checkpoints (generation order) and commands
Generate and verify module by module, in this order. Run every command through the checkpoint runner from the repository root, which runs it inside `clients/android/`, keeps the log and counts attempts:
`python3 generator/scripts/checkpoint.py --app android --checkpoint <id> -- <command>`

| Id | What exists after it | Command |
|---|---|---|
| `C0` | templates applied; every module's `build.gradle.kts` instantiated from its kind; empty source dirs | `./gradlew --console=plain help` |
| `C1` | `:core:protocol` with its test fixtures (fakes, in-memory fake server) and tests | `./gradlew --console=plain :core:protocol:test` |
| `C2` | `:core:network` | `./gradlew --console=plain :core:network:test` |
| `C3` | the driver module (`jvm-app`) | `./gradlew --console=plain :tools:driver:test :tools:driver:installDist` |
| `C4` | the `android-lib` module | `./gradlew --console=plain :core:data:testDebugUnitTest` |
| `C5-<x>` | each `:feature:<x>` module, one checkpoint per module | `./gradlew --console=plain :feature:<x>:testDebugUnitTest` |
| `C6` | the application module; then the final gate | the app's build command, then its test command (config `apps.android.build` / `.test`; the prompt's Parameters list them) |

Self-repair (decision 0017): on a failed checkpoint the runner prints a digest and one class.
- `CODE`: fix inside `clients/android/` and rerun the same checkpoint. At most 3 attempts per checkpoint and 12 per run (the runner refuses more).
- `ENV`: stop with `ENV_FAILURE`; no attempt is spent.
- `PIN`: stop with `BLOCKED` "template pin"; templates are read-only for the generator.

## 10. Pre-gate self-check (before `C6`)
1. No version literal in any module `build.gradle.kts` (only `libs.*` aliases and `project(...)`).
2. No host other than those allowed by `PLAT-ANDROID-013`/`014` in model-written files (E-LOCAL-1). Template-owned files (the wrapper's distribution URL) are exempt.
3. Every model-written file with a comment syntax starts with the GENERATED header.
4. No file under `src/main/` matches the patterns of `PLAT-HOOK-015` and `PLAT-ANDROID-030` (the generated test enforces it; check before running it).
5. `python3 generator/scripts/apply_templates.py --app android --check` passes.

## 11. Known pitfalls
(Empty at P3. Pattern nits from review are added here, decision 0002 Q11.)
