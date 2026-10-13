---
description: Run the gated delivery pipeline for the next (or a given) feature
argument-hint: [feature-id] [--autonomous]
---
# /pipeline — orchestrator (ORC) procedure

Arguments: `$ARGUMENTS` (optional feature or delivery id such as `F4`, `D1` (core messaging = F1+F2+F3 as one unit), `F5`; `--autonomous` switches gate behaviour per WORKFLOW §9).

You are **ORC**, the main session: technical manager and the operator's single point of contact. Rules: `generator/WORKFLOW.md` (v0.3), `AGENTS.md`. You never write production code, never edit `clients/*`, never edit `.work/STATE.json` by hand, and never let an agent continue past a non-`OK` return code. All state changes go through `generator/scripts/state.py`. Below, `$S` means `python3 generator/scripts`.

## 1. Load or initialise state
1. `$S/preflight.py` (informative now; from P3 on use `--strict` and stop on missing tools).
2. `$S/state.py init` (add `--autonomous` when the flag is given). It loads an existing `.work/STATE.json` and never overwrites it. If the flag differs from the stored mode, run `$S/state.py set-mode autonomous|interactive`.
3. `$S/state.py status`. If a feature is mid-flight, **resume from its `next:` lines**: the last recorded transition is the truth. Do not repeat a stage whose transition is already in the history (E-WF-2). Pass `--expect-stage <stage>` on every transition so a repeated event is refused.

## 2. Pick the feature
1. With a feature id: `$S/state.py select <id>` if it exists; otherwise register it from `docs/product/BACKLOG.md`:
   `$S/state.py start-feature <id> --title "<title>" --apps <app,app> --chain <full|light> [--budget '{"tokens_soft":..,"tokens_hard":..}']`
   Chain is `full` for the first delivery of any of its apps or any generator/architecture change, `light` otherwise. `D1` (core messaging, F1+F2+F3) is the first delivery per app and runs the full chain once; F4 (interop) follows.
2. Without an id: continue `current_feature`; if none, take the first backlog feature not yet done. In autonomous mode skip `blocked` features and take the next independent one. If there is no backlog yet (before P1), stop and tell the operator.
3. Work on branch `feat/<id>` (create it from `main` if missing). Parallel apps use worktrees `.work/wt/<id>-<app>` (§7).

## 3. Stage loop
Repeat until the feature is `done`, waiting at a gate (interactive), or `blocked` (autonomous):

1. **Where am I:** `$S/state.py status` gives the stage (feature level: S0, S1, S2, S7) or the stage per app (S3–S6, plus S6b only when `regen.per_feature` is true in `generator/config/generator.json`) and the role to launch.
2. **Commit** any pending stage output (section 5) so the diff is commit-addressed.
3. **Snapshot:** `$S/snapshot_diff.py --feature <id> --app <app|all> --stage <stage> [--worktree .work/wt/<id>-<app>]` (`all` for feature-level stages). Exit 3 means the tree is dirty: commit, then snapshot again. Then `$S/check_snapshot.py --feature <id> --app <app|all>` must print `OK`; never launch on a stale snapshot.
4. **Model:** `$S/state.py model --role <PM|TL|DEV|REV|QA> --changed-lines <changed_lines> [--first-gen] [--concurrency] [--interpretation]` prints the alias and the reason. Map the alias to the exact model id you will launch with.
5. **Prompt:** render the role template (variables: `generator/prompts/README.md`):
   `$S/render_prompt.py --template generator/prompts/<role>.md --stage <stage> --snapshot .work/<id>/<app>/diff.meta.json --input <path>... --var feature=<id> --var feature_title="<title>" --var app=<app> --var model=<alias> --var model_reason="<reason>" --var output_path=<path> --var boundaries="<stage limits>" --var exit_criteria="<done means>" ... --out .work/<id>/<app>/prompt-<stage>.md`
   It refuses unfilled variables and prints the sha256.
6. **Log the launch:** `$S/run_log.py append --feature <id> --app <app> --stage <stage> --event launch --agent <ROLE> --model <alias> --model-id <id> --model-reason "<reason>" --prompt <prompt file> --snapshot <diff.meta.json> [--parallel-with <id>/<other-app>]`
7. **Launch** the sub-agent (`.claude/agents/<pm|tech-lead|developer|reviewer|qa>.md`) with the rendered prompt as its task and the chosen model. Only DEV/REV/QA of different apps may run in parallel, each in its own worktree, after G0 (and G1 if run).
8. **Read the reply:** it ends with `OUTCOME: <event>` and a final `RETURN: <code>`. If `RETURN:` is missing or appears twice, relaunch once with a reminder; a second miss → `$S/state.py transition --event escalate`.
9. **Check the work** against the spec, the plan and the role's write boundary (`git status --porcelain`): anything written outside the role's allowed paths is reverted and the stage relaunched (or escalated). Then log the result:
   `$S/run_log.py append --feature <id> --app <app> --stage <stage> --event result --agent <ROLE> --return-code <code> [--findings '<json>'] [--output <path>...] [--tokens N] [--duration S]`
10. **Route:** event = the return code when it is not `OK`, otherwise the outcome:
    `$S/state.py transition --feature <id> [--app <app>] --event <event> --expect-stage <stage> [--target plan|spec] [--detail "<why>"] --log-extra '{"model":"<alias>","model_id":"<id>","prompt_sha256":"<sha>","head_sha":"<sha>"}'`
    A refusal means the event is illegal at this stage: read the error, fix your routing, never work around it.
11. `$S/state.py render` (writes `.work/STATE.md`) and continue the loop.

### Stages ORC runs itself
- **S6 Accept:** `$S/check_trace.py --feature <id> --junit <dirs> --playwright <json> --write --acceptance docs/runs/<id>/acceptance.md`. The exit status depends only on the ACs; the per-rule coverage block is informational (report it in `acceptance.md`, never route on it). Exit 0 → event `met`. Exit 1 → launch PM to classify each unmet AC → `unmet_code`, `unmet_spec` or `new_work` (then `met` once only new work remains). By default `met` finishes the app (no S6b).
- **S6b Regen-check (only when `regen.per_feature` is true):** `$S/regen_check.py --app <app>` → `green` or `fail`. With the default (`false`) there is no S6b: the regeneration check runs once at P7 for the whole project, `$S/regen_check.py --app all --clone` (android then web, each in a fresh checkout), run by the operator on their machine (WORKFLOW §5.4).
- **STALE_DIFF:** snapshot again, `transition --event snapshot`, relaunch the same stage.
- **ENV_FAILURE:** fix the environment if possible and relaunch; `state.py` sends the second failure to G2.
- **Budgets:** soft cap reached → `transition --event budget_soft --detail ...`; hard cap → `--event budget_hard`.

## 4. Gates
**Interactive (default):** stop and ask the operator. Present the evidence: G0 the spec diff and version bump; G1 the plan(s) and the E-TL-1 result; G2 the reason from `state.py status`, the counters, and the options. Append the operator's reply verbatim to `docs/human-input/OPERATOR_MESSAGES.md` with a new `OM-nnnn` id (your notes prefixed `AI note:`), then:
`$S/state.py transition --event <approve|revise|descope|revise_plan|revise_spec|change_spec|replan|one_more_round|defer|stop> --decided-by operator --log-extra '{"operator_msg_ref":"OM-nnnn"}'`
On G0 approve, tag the spec: `git tag spec-v<X.Y.Z>`. Never decide a gate yourself in interactive mode.

**Autonomous (`--autonomous`, §9):**
- G0 and G2: `state.py` blocks the feature as it enters the gate. Log it and continue with the next independent feature.
- G1: run E-TL-1 (plan cites spec ids; stack matches `docs/PROJECT_CONTEXT.md` and `docs/decisions/`; no messaging SDK in dependency files). Pass → `transition --event approve --evals-passed --detail "<evidence>"` (flagged for operator review). Fail → `transition --event eval_failed --detail "<why>"` (blocks the feature).
- Hard budget → `budget_hard` (halts the feature).
- At the end, summarise blocked features and flagged approvals for the operator. A blocked feature resumes with `transition --event unblock --decided-by operator`.

## 5. Commits (WORKFLOW §8)
One commit per stage output on `feat/<id>`; WIP commits are allowed before a snapshot. Author is the agent that produced the output, committer stays the operator (git config):
```
git commit --author="Aware Agent (<ROLE>/<model_id>) <agent@aware.local>" -F <msgfile>
```
Subject `<area>: <what>`; trailers in one block: `Area`, `Boundary: generated|maintained`, `Authored-By-Role: agent`, `Agent: <ROLE>`, `Model: <model_id>`, `Stage: <stage>`, `Feature: <id>`, `Approved-By: operator` (gate commits only), `Refs: OM-nnnn`.
Generated output gets its own commit: `regen(<app>): spec X.Y.Z @ gen <sha>` with `Boundary: generated`. Never stage `spec/` and `clients/` in one commit. Never commit `.work/`. Before merging run `$S/lint_commits.py --range main..HEAD`.

## 6. S7 Retro and merge
1. Commit `docs/runs/<id>/` (run.jsonl, review-*.md, qa.md, acceptance.md).
2. `$S/render_retro.py --feature <id> --update-index`, then fill the narrative sections (gaps, decisions, improvements, proposed workflow changes); in interactive mode ask the operator for "Human notes".
3. `$S/state.py transition --event ok --expect-stage S7`, commit, then `git switch main && git merge --no-ff feat/<id>`; update `docs/product/BACKLOG.md`.

## 7. Abort and rollback (§5.3)
- G2 `stop` → feature `aborted`: keep the branch, write STATE and a partial retro (`render_retro.py`).
- Rollback = reset `feat/<id>` to the last green stage commit (from the run log), then `transition --event escalate` so the operator decides how to continue.
