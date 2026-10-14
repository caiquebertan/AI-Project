# Running the harness without slash commands

Fallback for environments where `.claude/commands/` is not picked up, for CI, and for operators who want to drive steps by hand. The slash commands are thin wrappers over the same files, so both paths behave the same.

## Prerequisites
```bash
python3 generator/scripts/setup_env.py --check  # exit 0 if the build environment is complete (/generate runs this first)
python3 generator/scripts/setup_env.py          # if not: dry-run plan with the install commands for your OS; then add --install
python3 generator/scripts/preflight.py          # versions of python, git, node, java, gradle, Android SDK, claude
python3 -m unittest discover -s generator/tests  # harness self-test (stdlib only)
```
The pinned generator model id (`generate_model`), the per-app build/test commands and the headless flags (`generate.claude_flags`: turn and cost limits, tool allowlist, unanswerable prompts denied) are in `generator/config/generator.json` (set at P3, decision 0017).

Before the first `/generate` on a machine, run the token-free smoke session A once (generator design §5; `docs/runs/P3/operator-checklist.md`):
```bash
python3 generator/scripts/smoke_build.py --app all --dry-run   # the steps
python3 generator/scripts/smoke_build.py --app all             # build + test the templates; bundle in .work/smoke/send-back.zip
```

## Generator (`/generate`)
With slash commands (what graders run), `<flags>` being `generate.claude_flags` from the config:
```bash
claude -p "/generate web" --model claude-opus-5-5 <flags>
```
Without slash commands, render the same prompt and pass it directly:
```bash
python3 generator/scripts/render_prompt.py --generate web --out .work/generate/web/prompt.md
claude -p "$(cat .work/generate/web/prompt.md)" --model claude-opus-5-5 <flags>
```
The fallback model (`generate_model_fallback`, Sonnet) is used only by hand, by replacing `--model`; never pass `--fallback-model` (one run never mixes models, decision 0017). If the allowlist blocks a command the run needs, the documented fallback is `--dangerously-skip-permissions` in a throwaway clone only.

A run writes its plan, checkpoint logs and run record under `.work/generate/<app>/` (`plan.md`, `logs/<checkpoint>-<n>.log`, `result.json`); `python3 generator/scripts/checkpoint.py --app <app> --status` prints the checkpoint table. After the gate, collect the JUnit reports for the acceptance check:
```bash
python3 generator/scripts/collect_reports.py --feature D1 --trace-features F1,F2,F3   # copies to docs/runs/D1/reports/<app>/, prints the check_trace command
```

Clean regeneration check (E-PIPE-1), once at P7 by default (S6b only when `regen.per_feature` is true in the config), from a fresh worktree or clone; `--app all` runs android, then web, each in its own checkout, and prints a combined result:
```bash
python3 generator/scripts/regen_check.py --app all --dry-run   # show the steps
python3 generator/scripts/regen_check.py --app all [--clone]   # run them (generate, build, test, template check, headers)
python3 generator/scripts/check_headers.py --app all --strict  # manifest == tree, GENERATED headers
```

## Delivery pipeline (`/pipeline`)
Interactive (stops at gates G0, G1, G2):
```bash
claude "Read .claude/commands/pipeline.md and execute it as ORC with arguments: F1"
```
Autonomous (halts a feature at G0/G2 and continues with independent ones; G1 auto-approves only when E-TL-1 passes):
```bash
claude -p "Read .claude/commands/pipeline.md and execute it as ORC with arguments: F1 --autonomous"
```

## Driving the state machine by hand
Every ORC step is a script call, so an operator can walk a feature manually:
```bash
S="python3 generator/scripts"
$S/state.py init
$S/state.py start-feature F1 --title "<title>" --apps android,web --chain full
$S/state.py status                                              # next actions per app
$S/snapshot_diff.py --feature F1 --app web --stage S4           # after committing
$S/check_snapshot.py --feature F1 --app web                     # agent self-check
$S/state.py model --role REV --changed-lines 512                # -> opus / sonnet + reason
$S/render_prompt.py --template generator/prompts/reviewer.md --stage S4 \
    --snapshot .work/F1/web/diff.meta.json --var ... --out .work/F1/web/prompt-S4.md
$S/run_log.py append --feature F1 --app web --stage S4 --event launch --agent REV --model sonnet
$S/state.py transition --app web --event blockers --expect-stage S4
$S/state.py transition --event approve --decided-by operator    # at a gate
$S/check_trace.py --feature F1,F2,F3 --junit <dir> --playwright <json> --write --acceptance docs/runs/D1/acceptance.md   # D1 = F1+F2+F3
$S/render_retro.py --feature D1 --update-index   # retros are per milestone: D1, F4, F5, phases
$S/lint_commits.py --range main..HEAD
$S/lint_prompts.py
```
Event names per stage are listed by `state.py status` and in `generator/scripts/state.py` (`FEATURE_EVENTS`, `APP_EVENTS`); return codes (`SPEC_ISSUE`, `PLAN_DEVIATION`, `STALE_DIFF`, `ENV_FAILURE`, `BLOCKED`) are events too.

## Exit codes (all scripts)
`0` ok · `1` check failed · `2` usage error · `3` stale snapshot (`STALE_DIFF`) · `4` illegal state transition.
