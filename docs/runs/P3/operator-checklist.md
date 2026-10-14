# P3 operator checklist: smoke session A (token-free)

> Written by DEV (agent, claude-opus-5-5), stage S3, ref OM-0019. Design: `docs/planning/p3-generator-design.md` §5–§6 (decision 0017 Q10).
> **Why:** the cloud cannot reach Maven, Google Maven, the Gradle portal or npm (decision 0011). Every version pin, the Gradle wrapper and the npm lockfile had to be verified on the operator's machine first. It costs no tokens, about 30 minutes.

## Status: smoke session A DONE (2026-10-14)
| App | Result | Notes |
|---|---|---|
| android | PASS (2026-10-14) | Gradle 8.14.3 verified; build, Robolectric unit tests and Room passed with the pins in `libs.versions.toml` |
| web | PASS (2026-10-14) | `package-lock.json` produced and committed; `npm ci`, build and tests green |

- The wrapper jar was produced by the operator's Gradle 9.8.1 (`gradle wrapper`), so its sha256 differs from the published 8.14.3 jar (`wrapper_jar_verified: false` in `summary.json`). This is expected and harmless: the wrapper runs the pinned 8.14.3 distribution, whose `distributionSha256Sum` is in `gradle-wrapper.properties`.
- Templates are now complete (`apply_templates.py --app android --list` shows no `PENDING`). `smoke_build.py` skips the wrapper bootstrap and `npm install` when those files exist; it still bootstraps them if they are missing.
- Sections 1 to 4 below are kept as the record and as the recipe for a re-run (for example after a pin change). Section 5 (session B and the unverified items) is still open.

## 1. Before (once)
| Check | Command | Expect |
|---|---|---|
| Python ≥ 3.10 (you had 3.9.6) | `python3 --version` | 3.10 or newer |
| JDK 21 | `java -version` | `21.x` (Robolectric on SDK 35 needs it) |
| Android SDK | `echo $ANDROID_HOME`; `sdkmanager --list_installed` | `platforms;android-35`, `build-tools;35.0.0`, `platform-tools` |
| Node ≥ 22, npm | `node -v`; `npm -v` | v22 or newer (your v26 is accepted, Q7) |
| Gradle, for the wrapper only | `gradle --version` | any recent version (`brew install gradle`) |
| Claude Code ≥ v2.1.259, logged in | `claude --version`; `claude auth status` | needed for session B, not for A |
| All of the above | `python3 generator/scripts/preflight.py --strict` | exit 0 (missing pieces: `python3 generator/scripts/setup_env.py`) |

## 2. Run (from the repository root, on branch `gen/p3-generator` or `main` after merge)
```bash
python3 generator/scripts/smoke_build.py --app all --dry-run   # read the steps
python3 generator/scripts/smoke_build.py --app all             # run them
```
What it does, without touching `clients/` or the templates: builds `.work/smoke/android` and `.work/smoke/web` from the templates plus one tiny module per kind; runs `gradle wrapper --gradle-version 8.14.3` once in `.work/smoke/wrapper-bootstrap`; runs `npm install` (creates the lockfile); then runs the exact build and test commands from `generator/config/generator.json`; checks that every test's spec id appears in the JUnit reports; fetches the published Gradle sha256 sums.
Last lines: `smoke PASS|FAIL: android ..., web ...` and `send back: .work/smoke/send-back.zip`.

## 3. Send back
- `.work/smoke/send-back.zip` (whether it passed or failed). It contains `summary.json` (step exits, failure class and first error per step, testcase names, tool versions incl. `java -version`, `sdkmanager --list_installed`, `node -v`, `claude --version`, Gradle sha256 sums), all logs, and the produced files: `android/gradlew`, `android/gradlew.bat`, `android/gradle/wrapper/gradle-wrapper.jar`, `web/package-lock.json`.
- If a step failed with class `ENV`: fix the environment and rerun once (`env_retry: 1`), then send the zip anyway.

## 4. What DEV does with it (cloud), then you confirm
1. Committed the wrapper files and `package-lock.json` to `generator/templates/{android,web}/`, added `distributionSha256Sum` to `gradle-wrapper.properties`, and fixes any pin that failed (class `PIN` or a `CODE` failure in the smoke modules). Repeat sections 2 and 3 until `smoke PASS`.
2. Replaced "TBD-verify-on-operator-machine" with the verified versions in `libs.versions.toml`, `gradle-wrapper.properties`, `generator.json` (`$comment_claude_flags`) and this file.
3. You confirm with one more `smoke_build.py --app all` → `smoke PASS`, and `python3 generator/scripts/apply_templates.py --app android --list` shows no `PENDING` line.

## 5. Still unverified after session A (confirmed in session B, the first `/generate`)
| # | Item | How it is confirmed |
|---|---|---|
| 1 | `claude -p "/generate <app>"` picks up the slash command in `-p` mode | session B runs at all |
| 2 | `--effort high` is accepted for `claude-opus-5-5`; `--permission-prompts none`, `--max-budget-usd`, `--max-turns` on your CLI version | session B starts; if a flag is rejected, send the error text |
| 3 | The `--allowedTools` patterns cover every command the run needs (`python3 generator/scripts/*`, `./gradlew *`, `npm *`, `npx *`, `rm -rf clients/*`) | no "permission denied" lines in the output; if blocked, send the denied command (fallback: `--dangerously-skip-permissions` in a throwaway clone only, Q5) |
| 4 | Turn and cost limits (400 turns, $75 per app) fit one run; compaction does not lose the plan | the final JSON (`--output-format json`) shows turns and cost; send it |
| 5 | `checkpoint.py`, `build_digest.py`, `apply_templates.py --check` on real tool output | `.work/generate/<app>/{plan.md,logs/,result.json}` zipped and sent back |
| 6 | Vitest `junit` `classname`/`name` shape and Kotlin backtick names carry ids for `check_trace.py` | section 2 checks this on the smoke tests; session B: `collect_reports.py --feature D1 --trace-features F1,F2,F3` |

Session B command (ORC hands over the exact commit command and trailers):
```bash
claude -p "/generate android" --model claude-opus-5-5 <generate.claude_flags from generator/config/generator.json>
```
