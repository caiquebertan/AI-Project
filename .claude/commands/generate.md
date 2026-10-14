---
description: Regenerate a client (android|web|all) from the spec. Headless, no human gates.
argument-hint: <android|web|all> [--module <name>]
---
# /generate — headless generator

Arguments: `$ARGUMENTS` — an app name from `generator/config/generator.json` (`apps`), or `all`; optional `--module <name>` (default `all`, the whole app).

There are no human gates: do not ask questions, do not wait for approval. Write only inside `clients/<app>/` and `.work/generate/<app>/` (git-ignored scratch: plan, logs, run record).

How it runs (generator design `docs/planning/p3-generator-design.md` §3, decision 0017):
- One headless session per app, e.g. `claude -p "/generate android" --model <generate_model> <generate.claude_flags>` (both from the config). The flags bound turns and cost and give an explicit tool allowlist; a prompt nobody can answer is denied, never waited on.
- Templates are copied by `generator/scripts/apply_templates.py`; module build files come from kind skeletons; the model writes sources, tests and the dependency region only.
- The model writes a plan file first and re-reads it after context compaction and before each checkpoint.
- Modules are built and tested at checkpoints (order and commands in `generator/conventions/<app>.md`) through `generator/scripts/checkpoint.py`, which keeps logs, prints a failure digest with a class (`CODE`, `ENV`, `PIN`) and enforces the self-repair budget (per checkpoint and per run).

Step 0, once, before any app: run `python3 generator/scripts/setup_env.py --check`. If it exits non-zero, stop: print `GENERATE FAILED: build environment incomplete. Run python3 generator/scripts/setup_env.py (dry run: shows what is missing and the install commands), then python3 generator/scripts/setup_env.py --install, and retry.` and end with `RETURN: ENV_FAILURE`. Never install anything from this command.

For each app (for `all`: every app in the config, one after another):

1. Render the base prompt from config:
   `python3 generator/scripts/render_prompt.py --generate <app> --module <module> --out .work/generate/<app>/prompt.md`
   If it exits non-zero, print its error text verbatim (for example `generator not yet configured for <app>: generator/conventions/<app>.md is missing`), stop, and end with `RETURN: BLOCKED {"reason": "<that text>"}`.
2. Read `.work/generate/<app>/prompt.md` and follow it exactly: it is `generator/prompts/generate.md` with this app's paths, commands, model id, spec version, plan path and self-repair budget filled in.
3. If any app fails, stop: print `GENERATE FAILED: <app>: <reason>` and end with its return code. Do not continue with the next app.

End with exactly one final line `RETURN: <code>` (`OK`, `SPEC_ISSUE`, `ENV_FAILURE`, `BLOCKED`).
