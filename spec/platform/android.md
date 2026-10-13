# Android platform notes (skeleton)

Platform-specific only; behavior lives in `core/`.
- Kotlin, Jetpack Compose, coroutines, Hilt, Retrofit (follow current Google Android guidance).
- Multi-module: at minimum `:feature:login`, `:feature:chat`, `:core:network` / data API (names TBD); shared data boundary clearly separated.
- Local storage for identity and outbox: ☐ choose (Room / DataStore).
- Emulator reaches the host server at `10.0.2.2`.
