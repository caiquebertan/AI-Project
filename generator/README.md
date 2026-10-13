# Generator and agentic harness

Full design: [`WORKFLOW.md`](WORKFLOW.md) (v0.3). Manual / CI usage: [`RUN.md`](RUN.md).

| Entry point | Tool | Purpose | Status |
|---|---|---|---|
| `/generate <android\|web\|all> [--module <m>]` | Claude Code | **The generator.** Spec → `clients/<app>/`. Headless, no gates. What graders run. | procedure ✔ (P0); stops with "generator not yet configured" until conventions/templates exist ☐ P3 |
| `/pipeline [feature] [--autonomous]` | Claude Code | Gated delivery pipeline (PM, TL, DEV, REV, QA) that evolves spec and generator and calls `/generate`. | ✔ (P0) |

## What exists now (Phase 0 harness)

| Path | What | Status |
|---|---|---|
| `prompts/` | Role templates (`pm`, `tech-lead`, `developer`, `reviewer`, `qa`) and `generate.md`, the generator's base prompt. Variables only, listed in `prompts/README.md`. | ✔ |
| `config/generator.json` | Single source of caps, thresholds, app paths, commands, lint rules ([`config/README.md`](config/README.md)) | ✔ (model ids, build/test commands `TBD-at-P3`) |
| `schemas/` | `state.schema.json` (`.work/STATE.json`), `run-event.schema.json` (run log lines), `manifest.schema.json` (`clients/<app>/.generated`, proposed; confirmed at P3) | ✔ |
| `scripts/` | Stdlib-only Python, each with `--help`; shared code in `awarelib.py` | ✔ |
| `tests/` | `python3 -m unittest discover -s generator/tests` (E-WF-1 dry run, E-WF-2 resume, script unit tests) | ✔ |
| `conventions/` | Per-platform code-shape rules incl. in-project test requirements | ☐ P3 |
| `templates/` | Build infra and module skeletons copied verbatim | ☐ P3 |

Sub-agents: [`../.claude/agents/`](../.claude/agents/). Commands: [`../.claude/commands/`](../.claude/commands/).

## Scripts

| Script | WORKFLOW | Does |
|---|---|---|
| `state.py` | §5, §5.1, §5.2, §9 | The state machine: `init`, `start-feature` (ids like `F4`, `D1`, `P3`), `transition --event`, `status`, `render`, `select`, `set-mode`, `model` (§2 model rules). Refuses illegal transitions; checkpoints STATE.json and logs every transition. |
| `snapshot_diff.py` | §6.1, §6.4 | Commit-addressed `diff.patch` + `diff.meta.json`; per-file patches above the split threshold |
| `count_lines.py` | §6.2 | `changed_lines` without lockfiles, wrapper, binaries, manifests |
| `check_snapshot.py` | §6.3 | Agent self-check; prints `STALE_DIFF`, exit 3 |
| `render_prompt.py` | §8 | Fills `{{var}}` templates, refuses unfilled ones, prints sha256; `--generate <app>` for the generator |
| `run_log.py` | §8 | Append / show / validate `docs/runs/<feature>/run.jsonl` |
| `render_retro.py` | §10 | Retro tables from the run log (per milestone: D1, F4, F5, phases); `--update-index` for `docs/runs/INDEX.md` |
| `check_trace.py` | S6, E-PM-1/3, E-QA-1 | AC met/unmet from JUnit XML + Playwright JSON; the exit status depends on the AC rows only. Spec-id coverage per app is reported as informational (`--strict-coverage` makes it fail the run again): a rule is a defined bold id (not a citation); client rules need a passing test per app, `server-behavior.md` rules one from the server report. Tag reports `--junit android=<p> --junit web=<p> --junit server=<p> --playwright web=<p>`; untagged paths count for all apps. Uncovered is listed as `(spec id, app)` pairs; `protocol.md` rules default to all three apps unless a rule carries `[apps: ...]` |
| `check_headers.py` | E-DEV-1 | Manifest vs tree, GENERATED headers; `--write-manifest` for `/generate` |
| `regen_check.py` | P7 (S6b if `regen.per_feature`), E-PIPE-1, E-BOUND-1 | Fresh worktree/clone → delete → generate → build → test → boundary, per app (`--app all`: android then web, combined result); `--dry-run` |
| `lint_commits.py` | §8, E-PIPE-3 | Trailer rules for commits with an `Agent` trailer (operator is author of all commits, decision 0015; one final trailer block is canonical, split blocks tolerated, `--strict-trailers` rejects them; `Feature` optional at gates, F-id or P-id), no commit touching `spec/` and `clients/` |
| `lint_prompts.py` | E-EVOL-1 | Feature-noun denylist over generator prompts |
| `preflight.py` | §5.3 | Toolchain versions; `--strict` to gate |

All scripts share exit codes: `0` ok, `1` check failed, `2` usage, `3` stale snapshot, `4` illegal transition.

## Requirements
Harness scripts and tests use only the Python standard library and need **Python 3.10 or newer** (tested on 3.10 and 3.13). Run the tests with `python3 -m unittest discover -s generator/tests`.
