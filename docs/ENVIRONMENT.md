# Build environment (required on the operator's machine)

> **Read this before running `/generate` or any client build.** Decision: [`docs/decisions/0011-build-environment.md`](decisions/0011-build-environment.md).

## Why this exists

On 2026-10-13 we checked the two places agents run and found that **neither can build the clients**:

| Where | Result |
|---|---|
| Agent cloud workspace | No Android SDK. npm, PyPI, Maven Central, Google Maven and the Gradle plugin portal are unreachable (some are blocked by organization policy). Python standard library works. |
| Shell on the operator's computer, reached through the desktop app (`device_bash`) | Same: no Android SDK, no access to those registries. |

So agents can write and verify everything that is pure Python (the harness, the **server**, the **protocol tests**), but they **cannot compile, test or run the Android or web client**. Building and testing generated clients happens on a machine that has the toolchain and network access: the operator's own terminal, and later the graders' machine.

## Required tools (the list grows if we find we need more; record additions in `docs/decisions/`)

| Tool | Needed for | Notes |
|---|---|---|
| Python 3.10+ | harness scripts, server, protocol tests | standard library only |
| Git | history, worktrees, regen-check | |
| Claude Code CLI (`claude`) | `/generate`, `/pipeline` | logged in |
| JDK 21 (Temurin recommended) | Android build | Gradle host JDK; Robolectric tests for SDK 35 need a JDK 21 runtime; bytecode targets 17 (generator design §2.5, P3) |
| Android SDK | Android build and JVM tests | `ANDROID_HOME` set; `platforms;android-35` and `build-tools;35.0.0` (compileSdk 35, P3; TBD-verify in smoke session A); command-line tools or Android Studio |
| Node.js 22 or newer, and npm | web build, Vitest, Playwright | `engines >=22` (decision 0017 Q7); the actual version is recorded by smoke session A |
| Network access to: npm registry, Maven Central, Google Maven, Gradle plugin portal | dependency download on first build | an offline cache is out of scope |
| Gradle | once, for smoke session A | produces the Gradle wrapper (`gradle wrapper`) the templates ship afterwards (`brew install gradle`); not needed after that |
| Playwright browsers | web UI/e2e tests | installed with `npx playwright install` |

Not required: an Android emulator (decision 0002 Q19). Emulator runs are an optional extra.

## Check it

```
python3 generator/scripts/preflight.py            # report
python3 generator/scripts/preflight.py --strict   # exit 1 if a required tool is missing
```

`--strict` must pass on the operator's machine before Phase 3 (generator) starts. It checks tool presence and versions only: it does **not** check registry access (npm, Maven Central, Google Maven, Gradle plugin portal) and does **not** check that the Playwright browsers are installed. The real network check is the token-free smoke session A (`python3 generator/scripts/smoke_build.py --app all`; steps in `docs/runs/P3/operator-checklist.md`), which builds the templates before the first `/generate`; dependency download errors there and in `/generate` are classified `ENV` (`ENV_FAILURE`), not a generator bug. `setup_env.py` (below) adds a best-effort Playwright cache check.

## Set it up

`generator/scripts/setup_env.py` exists to diagnose and install the missing tools:

```
python3 generator/scripts/setup_env.py             # dry run: what is missing or too old, exact install commands for your OS
python3 generator/scripts/setup_env.py --install   # runs them one by one, asking before each (--yes skips the questions)
python3 generator/scripts/setup_env.py --check     # quiet, exit code only; /generate runs this first and stops on failure
```

Supported: macOS with Homebrew, Debian/Ubuntu with apt, Windows with winget; any other OS gets link hints only. Rules: `sudo` commands are always confirmed by hand, even with `--yes`; shell profiles are never edited (the script prints the `ANDROID_HOME`/`PATH` lines to add); the checks are the ones in `preflight.py`, plus a best-effort Playwright browser cache check that is reported but does not fail `--check`. After `--install`, open a new terminal so PATH changes apply.

## What runs where

| Step | Where it runs |
|---|---|
| Spec, backlog, decisions, generator design, prompts, docs | agents (cloud) |
| Server and `tests/protocol` | agents (cloud); Python only |
| `/generate android`, `/generate web`; Gradle and npm builds; in-project unit/UI tests; Playwright; Android core driver; E-INTEROP-1; the delete-and-regenerate check (once, at P7, decision 0013 cut 8) | **operator's machine**, running Claude Code locally; results committed with the run log |
| Review (S4) | agents read the generated code from the repository; they do not need to build it |

When a stage needs a build, the orchestrator stops and hands the operator an exact command and the files to send back (or commit). This is recorded as a normal human step in the run log (`decided_by: operator`).
