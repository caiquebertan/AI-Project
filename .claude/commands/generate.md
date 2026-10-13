---
description: Regenerate a client (android|web|all) from the spec. Headless, no human gates.
argument-hint: <android|web|all> [--module <name>]
---
# /generate — headless generator

Arguments: `$ARGUMENTS` — an app name from `generator/config/generator.json` (`apps`), or `all`; optional `--module <name>` (default `all`, the whole app).

> **Status:** the procedure is in place (P0); per-app conventions and templates arrive in **P3**. Until `generator/conventions/<app>.md` exists, this command stops with `generator not yet configured for <app>`.

There are no human gates: do not ask questions, do not wait for approval. Write only inside `clients/<app>/`.

For each app (for `all`: every app in the config, one after another):

1. Render the base prompt from config:
   `python3 generator/scripts/render_prompt.py --generate <app> --module <module> --out .work/generate/<app>/prompt.md`
   If it exits non-zero, print its error text verbatim (for example `generator not yet configured for <app>: generator/conventions/<app>.md is missing`), stop, and end with `RETURN: BLOCKED {"reason": "<that text>"}`.
2. Read `.work/generate/<app>/prompt.md` and follow it exactly: it is `generator/prompts/generate.md` with this app's paths, commands, model id, spec version and self-repair bound filled in.
3. If any app fails, stop: print `GENERATE FAILED: <app>: <reason>` and end with its return code. Do not continue with the next app.

End with exactly one final line `RETURN: <code>` (`OK`, `SPEC_ISSUE`, `ENV_FAILURE`, `BLOCKED`).
