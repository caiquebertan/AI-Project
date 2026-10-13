# Android platform rules

- **Status:** draft for G0 (spec 0.1.0-draft). Owner: TL. Stack source: `docs/PROJECT_CONTEXT.md` (Android), decision 0002 Q19.
- **Scope:** how the Android client is built, structured, configured and tested. **No behavior here.** What the app does is in `spec/core/` (protocol obligations: [`protocol.md`](../core/protocol.md); visible behavior: [`client-behavior.md`](../core/client-behavior.md)). If a rule below seems to decide behavior, the core rule it cites wins.
- **Ids:** `PLAT-ANDROID-NNN`; a withdrawn rule stays as a one-line tombstone without a keyword (decision 0014). Shared hook names: [`test-hooks.md`](test-hooks.md).

## 1. Stack

- **PLAT-ANDROID-001** — The client MUST be Kotlin with Jetpack Compose (Material 3) UI, coroutines and Flow for asynchrony, Hilt for dependency injection, Retrofit + OkHttp for HTTP, kotlinx.serialization for JSON and Room for local storage; exact versions MUST be pinned in `gradle/libs.versions.toml` from the generator templates (P3), not chosen per generation.
- **PLAT-ANDROID-002** — The client MUST NOT depend on any messaging, chat, sync or push SDK (brief constraint); Firebase and Google Play services MUST NOT be used.
- **PLAT-ANDROID-003** — `applicationId` MUST be `app.aware.android`, `minSdk` 26; one Activity hosts all screens through Compose navigation.

## 2. Modules

- **PLAT-ANDROID-004** — The Gradle project MUST have exactly these modules and dependency directions (arrows = "may depend on"):

| Module | Kind | Contains | May depend on |
|---|---|---|---|
| `:core:protocol` | pure Kotlin/JVM | wire models, validation (CORE-NAME, CORE-TEXT), constants (§13 of protocol), ordering (CORE-SEQ), the protocol engine (connection cycle, outbox, cursor, epoch, dedupe), port interfaces (PLAT-HOOK-009), JVM default `Clock`, `TimeZone`, `IdGenerator` and `Scheduler` (PLAT-ANDROID-031), snapshot model | kotlinx-coroutines-core, kotlinx-serialization-json only |
| `:core:network` | pure Kotlin/JVM | `Transport` implementation with Retrofit + OkHttp; maps HTTP outcomes to the classes of CORE-ERR-003 | `:core:protocol` |
| `:core:data` | Android library | Room `LocalStore`, `ConnectivityMonitor` over `ConnectivityManager`, Logcat `DiagnosticLog` (PLAT-ANDROID-035), Hilt modules binding all ports | `:core:protocol`, `:core:network` |
| `:feature:login` | Android library (Compose) | login screen + ViewModel | `:core:protocol` |
| `:feature:chat` | Android library (Compose) | conversation list, conversation screen, composer, connection status, offline toggle + ViewModels | `:core:protocol` |
| `:app` | Android application | `Application`, `MainActivity`, navigation, Hilt entry point | all modules except `:tools:driver` |
| `:tools:driver` | pure Kotlin/JVM application | command-line interop driver for external tests (PLAT-ANDROID-031..034); never shipped | `:core:protocol`, `:core:network` |

- **PLAT-ANDROID-005** — Feature modules MUST NOT depend on each other, on `:core:network` or on `:core:data`; they see only interfaces from `:core:protocol`, injected by Hilt. No module depends on `:tools:driver`.
- **PLAT-ANDROID-006** — All protocol logic (every client-side `CORE-*` rule except rendering) MUST live in `:core:protocol` so it runs in plain JVM unit tests; Android modules hold only adapters and UI.
- **PLAT-ANDROID-007** — The protocol engine MUST be a process-wide singleton running in an application-scoped coroutine scope (not tied to an Activity); there is no background service, WorkManager job or push in v1, so polling stops when the process ends.

## 3. Adapters

- **PLAT-ANDROID-008** — JSON MUST be configured to ignore unknown keys on decode (CORE-HTTP-005) and to always encode every field of a request (no omitted defaults), so requests match the schemas exactly.
- **PLAT-ANDROID-009** — The `Transport` MUST enforce the CORE-CONN-009 timeout on every call (OkHttp `Call.timeout` of `REQUEST_TIMEOUT_MS`, with no longer client-wide timeout). Going offline MUST NOT cancel an in-flight call (CORE-CONN-004): the engine stops starting calls but lets the current one finish and applies its result. A call is cancelled only when its coroutine is cancelled because the engine itself is discarded (relaunch, process end).
- **PLAT-ANDROID-010** — `IdGenerator` MUST use `java.util.UUID.randomUUID().toString()`; UTF-8 byte length (CORE-TEXT-003) MUST be computed on the encoded bytes, and unpaired surrogates MUST be detected before encoding.
- **PLAT-ANDROID-011** — `ConnectivityMonitor` MUST report `network_available = true` iff the default network has `NET_CAPABILITY_INTERNET` (not `VALIDATED`, because the emulator reaches the local server without internet).

## 4. Local storage

- **PLAT-ANDROID-012** — Identity, epoch, cursor, messages and outbox MUST be stored in one Room database `aware.db`; writes that CORE-CURSOR-002 orders (store envelopes, then cursor) MUST run in one Room transaction, and the outbox order MUST be an explicit monotonically increasing column, never row id or time.
  - Why Room: one transactional store for everything the engine persists; ordered queries for the outbox; in-memory Room for Robolectric tests. DataStore/SharedPreferences were rejected because splitting identity and cursor from messages loses atomicity.

## 5. Server address and networking

- **PLAT-ANDROID-013** — The server base URL MUST come from `BuildConfig.SERVER_BASE_URL`, default `http://10.0.2.2:8080` (the emulator's alias for the host loopback), overridable at build time by the Gradle property `aware.serverUrl`; no other host may appear in the code (E-LOCAL-1).
- **PLAT-ANDROID-014** — Cleartext HTTP MUST be allowed only for `10.0.2.2`, `localhost` and `127.0.0.1` through `res/xml/network_security_config.xml` (base config denies cleartext); `android:usesCleartextTraffic="true"` MUST NOT be used.
- **PLAT-ANDROID-015** — The manifest MUST request `INTERNET` and `ACCESS_NETWORK_STATE` and no other permission.

## 6. Test hooks

- **PLAT-ANDROID-016** — Every hook of PLAT-HOOK-001 MUST be applied with `Modifier.testTag(<hook id>)`, the root composable MUST set `testTagsAsResourceId = true` (so UI Automator sees tags as resource ids), and machine values (PLAT-HOOK-004) MUST be exposed as `stateDescription` (`connection-status` uses the state name; `message-<id>` uses exactly three `;`-separated fields `"<state>;<seq>;<from>"` with `<seq>` empty when it has none, e.g. `"sent;3;alice"`, `"pending;;alice"`); `offline-toggle` MUST be a toggleable (`Switch`) whose checked state is `offline_toggle`.
- **PLAT-ANDROID-017** — Withdrawn (decision 0014).
- **PLAT-ANDROID-025** — The relaunch control (PLAT-HOOK-011) MUST discard the engine and build a new one over the same `LocalStore` instance (or the same on-disk Room file): in JVM and Robolectric tests, and in the driver's `relaunch` command (PLAT-ANDROID-032). It MUST NOT be implemented with `Activity.recreate()`, which keeps the process. (A manual emulator run can relaunch with `adb shell am force-stop app.aware.android` and a normal launch; no test depends on it.)
- **PLAT-ANDROID-026** — The default `TimeZone` provider MUST use `java.time`: `zoneId()` = `ZoneId.systemDefault().id` and `offsetMinutesAt(t)` = `ZoneId.systemDefault().rules.getOffset(Instant.ofEpochMilli(t)).totalSeconds / 60`, read on every call (never cached), and the default `Clock` MUST read `Instant.now()`; parsing of the stored UTC strings MUST use `Instant.parse`.
- **PLAT-ANDROID-027** — The `HH:mm` / `YYYY-MM-DD HH:mm` text (CORE-TIME-002) MUST be built by hand in `:core:protocol` from the local wall-time fields (`LocalDateTime` from the instant and offset), zero-padded with ASCII digits; `DateTimeFormatter` with a locale or localized style, `SimpleDateFormat`, `java.text.DateFormat` and `android.text.format.DateFormat` MUST NOT be used for it. In-project tests use a fake `TimeZone`; external tests that run the driver set its zone with the JVM option `-Duser.timezone=<IANA id>` (a test-runner option outside `clients/android/`, CORE-TIME-003).
- **PLAT-ANDROID-018** — `:core:protocol` MUST expose the snapshot as a `StateFlow` so JVM tests read the same shape without Android.

## 7. Tests the generator MUST produce (inside `clients/android/`)

- **PLAT-ANDROID-019** — JVM unit tests in `:core:protocol` MUST cover every client-side `MUST` rule of `spec/core/` (protocol obligations and client behavior) with at least one test each, using fakes for all ports (PLAT-HOOK-009), including a fake server that implements `spec/core/server-behavior.md` in memory and a test that replays protocol Appendix A step by step and asserts the snapshot after each step.
- **PLAT-ANDROID-020** — `:core:network` MUST have JVM tests against OkHttp `MockWebServer` for each endpoint E1–E5: request method, path, query and body, and the CORE-ERR-003 class of each status.
- **PLAT-ANDROID-021** — A JVM test MUST decode every file in `spec/core/schema/examples/` into the wire models and re-encode it to an equal JSON value, and a JVM test MUST assert the constants equal `spec/core/schema/constants.json` (read relative to the repository root).
- **PLAT-ANDROID-022** — Robolectric Compose tests in each feature module MUST check that every hook of that feature exists with its PLAT-ANDROID-016 semantics and that the screen's flows in `client-behavior.md` work against fake ports; visible texts are asserted exactly as listed in `client-behavior.md` §8.1 (this file defines no texts).
- **PLAT-ANDROID-028** — JVM tests in `:core:protocol` MUST check the time text with fake `Clock` and `TimeZone`: the Appendix A "Displayed times" table (both zones, N1 and N2); the local-midnight boundary (`23:59:59.999` local shows the date prefix when "now" is the next local day, `00:00:00.000` shows `00:00`); truncation (`12:00:59.999` → `12:00`); a message date later than "now"'s date also gets the prefix; a zone whose offset differs between the message instant and "now" (DST-like change, using fixed fake offsets, so results do not depend on the tz database); a zone change between two renders takes effect on the second; identical output under `Locale.setDefault` with `ar-EG` and `th-TH-u-nu-thai` (ASCII digits); no time for `pending`. A Robolectric test MUST check that `message-time-<id>` exists for `sent`/`received` and not for `pending`.
- **PLAT-ANDROID-023** — Every test name MUST start with the spec id it covers (Kotlin backtick names, e.g. `` `CORE-OUTBOX-003 sends entries one at a time in order` ``) so `check_trace.py` can match it; one test may name several ids.
- **PLAT-ANDROID-024** — The gate MUST be `./gradlew testDebugUnitTest` plus `test` on the three JVM modules (`:core:protocol`, `:core:network`, `:tools:driver`) and `:tools:driver:installDist`, run without an emulator; reports are the default JUnit XML under `build/test-results/`. Instrumented emulator tests are optional and never part of the gate.
- **PLAT-ANDROID-029** — JVM tests in `:core:protocol` MUST implement every case of PLAT-HOOK-014 against the protocol engine with fake ports; each test name starts with the `CORE-CONN-*` ids it proves (PLAT-ANDROID-023).
- **PLAT-ANDROID-030** — A JVM test in `:core:protocol` named for `CORE-TIME-003` MUST implement PLAT-HOOK-015 over these paths under `clients/android/`: every module's `src/main/` tree, every `build.gradle.kts`, `settings.gradle.kts`, `gradle.properties` and `gradle/libs.versions.toml` (`src/test/` and `src/androidTest/` are not scanned). It adds these patterns: `ZoneId\.of\(`, `ZoneId\.SHORT_IDS`, `ZoneOffset\.of(Hours|HoursMinutes|HoursMinutesSeconds)?\(`, `TimeZone\.getTimeZone\(`, `TimeZone\.setDefault\(`. Allowed and not matched: `ZoneId.systemDefault()`, `ZoneOffset.ofTotalSeconds(<computed value>)`, `ZoneOffset.UTC`, `Instant`.

## 8. Interop driver (`:tools:driver`)

External interop tests (`tests/interop`, QA) drive the Android client's generated protocol code through this driver, with no emulator and no UI (decision 0014; TL G0 question Q5). It runs the same engine as the app; only the adapters differ.

- **PLAT-ANDROID-031** — The module `:tools:driver` MUST be a pure Kotlin/JVM application (Gradle `application` plugin, main class `app.aware.driver.MainKt`) that depends only on `:core:protocol`, `:core:network`, kotlinx-coroutines-core and kotlinx-serialization-json, and on no Android framework class. `./gradlew :tools:driver:installDist` MUST produce the launcher `clients/android/tools/driver/build/install/driver/bin/driver`. It MUST build the protocol engine of `:core:protocol` with: the `:core:network` `Transport` (wrapped per PLAT-ANDROID-033); an in-memory `LocalStore` defined in the driver; a `ConnectivityMonitor` that always reports `true`; the JVM default `Clock`, `TimeZone` (PLAT-ANDROID-026), `IdGenerator` (PLAT-ANDROID-010) and `Scheduler`, which therefore MUST live in `:core:protocol` so that `:app` and the driver use the same code; and a `DiagnosticLog` writing to standard error.
- **PLAT-ANDROID-032** — The driver MUST be invoked as `driver --server <base-url> --user <name>`. On start it MUST check `<name>` against CORE-NAME-001 (exit code `2` with one line on standard error if invalid; also for a missing or unknown option), log in with it (CORE-NAME-004) and start the engine as on an app launch (`offline_toggle` = `false`). It MUST then read commands from standard input, one per line, run them in order, and write exactly one JSON line to standard output per command (`quit` excepted); standard output carries nothing else:

| Command | Effect | Output line |
|---|---|---|
| `snapshot` | none | the snapshot (PLAT-HOOK-006, `client-snapshot.schema.json`) |
| `offline` / `online` | set `offline_toggle` to `true` / `false` (CORE-CONN-001) | snapshot after the change |
| `send <to> <json-string>` | the user sends the decoded JSON string as text to `<to>`, with the same local checks and outbox path as the UI (CORE-NAME-005, CORE-TEXT-004, CORE-OUTBOX-001) | snapshot after enqueueing, or an error line |
| `wait <condition> <timeout-ms>` | block until the condition holds on the snapshot | snapshot when it holds, or error `timeout` |
| `relaunch` | PLAT-HOOK-011 per PLAT-ANDROID-025 | snapshot after the new engine started |
| `requests` | none | `{"requests":<n>}` (PLAT-ANDROID-033) |
| `quit` | stop the engine and exit `0`; end of input does the same | none |

  Conditions: `connection <offline|connecting|online>`; `message <json-string> <pending|sent|received>` (a stored message with exactly that text is in that state); `cursor <n>`; `outbox <n>` (outbox length). An error line is `{"error":{"code":"<code>","message":"<text>"}}` with `code` one of `invalid_name`, `invalid_text`, `timeout`, `bad_command`; the driver continues with the next command after an error.
- **PLAT-ANDROID-033** — The driver MUST wrap the `Transport` it gives the engine in a counter that adds one for every call started (any endpoint, whatever its outcome), outside the engine; `requests` reports that count since the driver process started (it survives `relaunch`). External tests use the difference between two `requests` outputs to check that no request is made while offline (CORE-CONN-004).
- **PLAT-ANDROID-034** — JVM tests in `:tools:driver` MUST run the driver's command loop in-process, with a scripted fake `Transport` behind the counter, and check: every command and condition of PLAT-ANDROID-032; that every output line is one JSON value whose snapshot fields match `client-snapshot.schema.json`; the error lines and exit code `2`; that `requests` counts every call and does not change while offline after an in-flight call has ended; and that `relaunch` keeps identity, cursor, messages and outbox.
- **PLAT-ANDROID-035** — The default `DiagnosticLog` (PLAT-HOOK-009) of the app MUST write with `android.util.Log.w` and tag `Aware`, and live in `:core:data`; the driver's writes one line to standard error (PLAT-ANDROID-031).
