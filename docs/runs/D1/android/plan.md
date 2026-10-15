# Plan — /generate android (spec 0.1.1, gen 85db6e3, model claude-opus-5-5)

Scope: all modules. Checkpoint order from generator/conventions/android.md §9.
Re-read before every checkpoint. Mark `[x]` when PASS.

## Checkpoints
- [x] C0 templates + 7 build files instantiated (`help`)  — PASS
- [x] C1 :core:protocol (+ testFixtures) — PASS on attempt 2 (77 tests; repair: two test expectations fixed)
- [x] C2 :core:network — PASS attempt 1 (9 tests)
- [x] C3 :tools:driver — PASS attempt 1 (9 tests, launcher built)
- [x] C4 :core:data — PASS attempt 1 (9 tests)
- [x] C5-login :feature:login — PASS attempt 1 (5 tests)
- [x] C5-chat :feature:chat — PASS attempt 1 (20 tests)
- [ ] C6 :app, then build + test (config)

## Design summary
- Ports (PLAT-HOOK-009) in `app.aware.core.protocol.port`: Transport, LocalStore, ConnectivityMonitor, Clock, TimeZone, Scheduler, IdGenerator, DiagnosticLog. Defaults (PLAT-ANDROID-026/010/031) in `...protocol.defaults`.
- `TransportResult` sealed: Success / Failed (class R) / Rejected (class P); `OutcomeClassifier` maps status+code per CORE-ERR-003 (used by :core:network and fakes).
- `ProtocolEngine` (one lifetime; own SupervisorJob scope from injected context; one Mutex; immutable `EngineState`; loop = await active → cycle → pause CYCLE_INTERVAL_MS or wake). `EngineHost` implements `AwareClient`, owns snapshot StateFlow, relaunch = stop engine + new engine over same LocalStore (PLAT-ANDROID-025).
- Snapshot built by `SnapshotBuilder` (time text computed at build; refreshed every CYCLE_INTERVAL_MS through Scheduler so zone changes show without action).
- `StoredState` reducers shared by in-memory stores and the engine mirror; Room store does same writes in transactions.
- UI: features take `AwareClient` (protocol interface) via @HiltViewModel; app root: ready? → login (no identity) or NavHost(list, conversation/{peer}).
- Spec gap noted (not filled with visible behavior): text refused for U+0000/unpaired surrogate shows no composer text (protocol §6 ownership note) — refused silently, nothing enqueued. E3 outcome outside the CORE-ERR-003 P list (e.g. 409 without valid code, other 2xx) treated as class R.

## Modules, files, spec ids, tests

### C1 :core:protocol (jvm-lib) — package app.aware.core.protocol
Main:
- ProtocolConstants (CORE-CONST-001), FixedTexts (CORE-VISIBLE-005 §8.1), HookIds (PLAT-HOOK-001)
- validation/NameRules, TextRules, TextCheck (CORE-NAME-001/002/004/005, CORE-TEXT-002/003/004/005, PLAT-ANDROID-010)
- time/UtcTime, TimeText (CORE-HTTP-007, CORE-TIME-001/002/003, CORE-VISIBLE-009..012, PLAT-ANDROID-026/027)
- wire/* models + WireJson (CORE-ENV-001, CORE-HTTP-001/004/005, PLAT-ANDROID-008)
- port/* (PLAT-HOOK-009), Endpoint, TransportResult, OutcomeClassifier (CORE-ERR-003, CORE-EPOCH-005)
- defaults/DefaultClock, DefaultTimeZone, DefaultIdGenerator, DefaultScheduler (PLAT-ANDROID-026/010/031, CORE-ENV-002)
- store/MessageState, StoredMessage, SentMark, StoredState (CORE-MSG-006, CORE-OUTBOX-002/006, CORE-EPOCH-003/004, CORE-CURSOR-001)
- engine/ConnectionState, EngineState, EnginePorts, MessageOrder, PollApplier, PollOutcome, SnapshotBuilder, ProtocolEngine, EngineHost
  (CORE-CONN-001..009, CORE-SESSION-003/004, CORE-EPOCH-004/005, CORE-OUTBOX-001..006, CORE-MSG-004/005, CORE-DEDUPE-001..004, CORE-CURSOR-001..003, CORE-SEQ-002..005, CORE-EXT-002..004, CORE-CAP-002, CORE-ENV-002/003/006, PLAT-ANDROID-006/007/018, PLAT-HOOK-006..008/011/013)
- client/AwareClient, LoginResult, SendResult, ConversationList (CORE-LOGIN-002..005, CORE-SEND-001/002/004/005/011, CORE-VISIBLE-002/003, CORE-ORDER-001..006)
- snapshot/ClientSnapshot, SnapshotMessage (PLAT-HOOK-006/008/013)
Fixtures (src/testFixtures, package app.aware.core.protocol.testing): FakeClock, FakeTimeZone, FakeConnectivityMonitor, FakeIdGenerator, FakeDiagnosticLog, FakeScheduler, InMemoryLocalStore, FakeServer (server-behavior in memory), FakeServerTransport (recording, hold, lose-ack, intercepts), CallRecord, TestRig, FakeAwareClient (for feature tests).
Tests: ValidationTest, WireModelTest (PLAT-ANDROID-021, CORE-CONST-001), ClassifierTest, OrderingTest, TimeTextTest (PLAT-ANDROID-028), TimeZoneDenylistTest (CORE-TIME-003, PLAT-HOOK-015, PLAT-ANDROID-030), ConnectionCycleTest (PLAT-HOOK-014 a–e, PLAT-ANDROID-029), OutboxFlushTest, ReceiveTest, EpochTest, LoginSendTest, RelaunchTest, SnapshotTest, AppendixAReplayTest (PLAT-ANDROID-019, SC-1..SC-8 + displayed times), ScenarioTest (SX-1, SX-2, SX-3, SX-5, SX-6).

### C2 :core:network (jvm-lib) — HttpTransport, AwareApi (Retrofit), HttpOutcomes
Ids: CORE-HTTP-001/002/003, CORE-CONN-009, CORE-ERR-003, PLAT-ANDROID-009/013, CORE-EPOCH-002.
Tests: HttpTransportTest with MockWebServer per E1–E5 (PLAT-ANDROID-020).

### C3 :tools:driver (jvm-app) — Main, DriverApp, DriverArgs, CommandLoop, CountingTransport, DriverLocalStore, StderrDiagnosticLog, AlwaysAvailableMonitor
Ids: PLAT-ANDROID-031..034, PLAT-ANDROID-025, PLAT-HOOK-006/011.
Tests: CommandLoopTest, DriverArgsTest (PLAT-ANDROID-034).

### C4 :core:data (android-lib) — AwareDatabase, MessageEntity, MetaEntity, StoreDao, RoomLocalStore, AndroidConnectivityMonitor, LogcatDiagnosticLog, DataModule
Ids: PLAT-ANDROID-012, -011, -035, -007, -013, PLAT-HOOK-009, CORE-CURSOR-002, CORE-OUTBOX-002/006.
Tests (Robolectric): RoomLocalStoreTest, RoomRelaunchTest (PLAT-ANDROID-025, CORE-LOGIN-005, CORE-OFFLINE-004), LogcatDiagnosticLogTest.

### C5-login :feature:login — LoginViewModel, LoginUiState, LoginScreen, LoginRoute
Ids: CORE-LOGIN-001..004/006, CORE-NAME-005, PLAT-HOOK-001, PLAT-ANDROID-016/022.
Tests: LoginScreenTest (Robolectric Compose).

### C5-chat :feature:chat — AppHeader, ConversationListViewModel/State/Screen/Route, ConversationViewModel/State/Screen/Route, MessageRow, Labels
Ids: CORE-VISIBLE-001..012, CORE-SEND-001..011, CORE-OFFLINE-001/002/006, CORE-RECEIVE-001/003/005/006, CORE-ORDER-001..006, PLAT-HOOK-001..005/010/013, PLAT-ANDROID-016/022/028.
Tests: HeaderTest, ConversationListScreenTest, ConversationScreenTest (Robolectric Compose).

### C6 :app — AwareApplication, MainActivity, AwareRoot
Ids: PLAT-ANDROID-003/007/016 (testTagsAsResourceId), CORE-VISIBLE-004, CORE-LOGIN-005.
Gate: build + test commands from config.
