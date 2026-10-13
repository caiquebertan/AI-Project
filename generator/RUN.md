# Running the harness without slash commands

Fallback for environments where `.claude/commands/` is not picked up, for CI, and for operators who want to drive steps by hand. The slash commands are thin wrappers over the same files, so both paths behave the same.

## Prerequisites
```bash
python3 generator/scripts/preflight.py          # versions of python, git, node, java, gradle, Android SDK, claude
python3 -m unittest discover -s generator/tests  # harness self-test (stdlib only)
```
The pinned generator model id, the per-app build/test commands and the headless permission flags are set in `generator/config/generator.json` at **P3** (now `TBD-at-P3`).

## Generator (`/generate`)
With slash commands (what graders run):
```bash
claude -p "/generate web" --model <generate_model from config>
```
Without slash commands, render the same prompt and pass it directly:
```bash
python3 generator/scripts/render_prompt.py --generate web --out .work/generate/web/prompt.md
claude -p "$(cat .work/generate/web/prompt.md)" --model <generate_model from config>
```
`render_prompt.py` exits non-zero with `generator not yet configured for <app>` until `generator/conventions/<app>.md` exists (P3). Headless runs need edit and shell permissions inside the repo; the exact flags are pinned with the model at P3.

Clean regeneration check (E-PIPE-1), once at P7 by default (S6b only when `regen.per_feature` is true in the config), from a fresh worktree or clone; `--app all` runs android, then web, each in its own checkout, and prints a combined result:
```bash
python3 generator/scripts/regen_check.py --app all --dry-run   # show the steps
python3 generator/scripts/regen_check.py --app all [--clone]   # run them (needs P3 config)
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
