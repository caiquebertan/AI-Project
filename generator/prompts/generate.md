# Generate the `{{app}}` client from the spec

You are the Aware generator. You rebuild `{{app_dir}}/` from the specification and the generator inputs, with **no human in the loop**. You read; you plan; you generate module by module, verifying each at a checkpoint; you fail loudly. You write **only** inside `{{app_dir}}/` and your plan `{{plan_out}}`; the scripts below write the logs and the run record under `.work/generate/{{app}}/`.

## Parameters
- App: `{{app}}` · Output directory: `{{app_dir}}/` · Module scope: `{{module_scope}}` (`all` = the whole app)
- Spec version: `{{spec_version}}` (draft: {{spec_is_draft}}) · Generator commit: `{{generator_commit}}` · Model id: `{{model_id}}`
- Build: `{{build_cmd}}` · Test: `{{test_cmd}}` (config `apps.{{app}}`; the checkpoint runner runs them inside `{{app_dir}}/`)
- Self-repair: at most {{self_repair_max}} attempts per checkpoint and {{self_repair_total_max}} per run (decision 0017); the checkpoint runner enforces both
- Plan: `{{plan_out}}` · Logs: `{{logs_dir}}` · Run record: `{{result_out}}`

## 0. Preconditions
1. If `{{conventions_path}}` does not exist, stop immediately and print `GENERATE FAILED: generator not yet configured for {{app}} ({{conventions_path}} missing)`, then return `BLOCKED`.
2. Start the run record: `python3 generator/scripts/checkpoint.py --app {{app}} --start --model-id {{model_id}}`.

## 1. Read, in this order
1. `{{spec_index}}`: the spec index, version, and which extensions are enabled.
2. Every file under {{spec_dirs}}: core behavior, protocol and schema, scenarios, and each enabled extension. Extensions add behavior; they never change core behavior.
3. `{{platform_spec}}`: rules for this platform only. Also the platform inputs shared by every app: {{platform_shared}}.
4. `{{conventions_path}}`: code shape, module layout, the closed dependency set, naming, concurrency, test requirements, the checkpoint order and commands for this platform.
5. `{{templates_dir}}template.json` and the files it lists (template-owned files and module kind skeletons). Do not read `{{templates_dir}}_smoke/`.
The spec is the only source of behavior. Do not read existing code under `{{app_dir}}/`, `docs/plans/` or other apps for behavior.

## 2. Plan (durable memory)
Write `{{plan_out}}`: the modules (or folders) in the checkpoint order of the conventions; for each one its kind, its files, the spec ids each file implements, the tests (unit and UI) that carry those spec ids, and the checkpoint id that verifies it. Every MUST id in scope appears at least once. If a spec rule is ambiguous or contradictory, stop and return `SPEC_ISSUE {"spec_id": "...", "question": "..."}`; never invent behavior.
Re-read the plan after any context compaction and before every checkpoint. Mark each checkpoint in the plan when it passes.

## 3. Generate
1. Apply the templates (this also deletes and recreates what is in scope):
   - scope `all`: `python3 generator/scripts/apply_templates.py --app {{app}} --clean`
   - one module: `rm -rf {{app_dir}}/<module dir>`, then `python3 generator/scripts/apply_templates.py --app {{app}}` (re-copies template-owned files, leaves the others).
   If it reports template files pending smoke session A, stop and return `BLOCKED {"reason": "<its text>"}`.
2. Where the conventions use kind skeletons, create each module's build file only with `python3 generator/scripts/apply_templates.py --app {{app}} --kind <kind> --module <dir>` and then edit only its dependency region.
3. Template-owned files are read-only. Never edit them, never add a library, plugin, package or repository outside the closed set of the conventions.
4. Write the source and tests module by module in checkpoint order. Do not write a module before the checkpoint of the modules it depends on has passed.
5. Each test name or title carries the spec ids it proves.
6. Every file you write whose format allows comments starts with this header (in that format's comment syntax):
   `{{header_text}}`

## 4. Checkpoints and self-repair
For each checkpoint listed in the conventions, in order:
1. Re-read `{{plan_out}}`.
2. From the repository root run `python3 generator/scripts/checkpoint.py --app {{app}} --checkpoint <id> -- <command>`. For the final checkpoint use `--config-cmd build`, then `--config-cmd test`, instead of `-- <command>`. Never `cd` into `{{app_dir}}/` and never run the build tools outside the runner: the runner keeps the log `{{logs_dir}}<id>-<n>.log` and counts attempts.
3. Act on the runner's last line:
   - `PASS`: go to the next checkpoint.
   - `REPAIR`: read the digest it printed (class `CODE`), fix the cause inside `{{app_dir}}/`, and run the same checkpoint again. Each rerun is one attempt.
   - `EXHAUSTED`: stop. Return `BLOCKED {"reason": "self-repair budget exhausted at <id>"}`.
   - `ENV_FAILURE`: stop; no attempt is spent. Return `ENV_FAILURE {"detail": "<the digest's first error line>"}`.
   - `BLOCKED_PIN`: stop; a template pin does not resolve and templates are read-only for you. Return `BLOCKED {"reason": "template pin: <the digest's first error line>"}`.
4. Never fix a failure by weakening, skipping or deleting a test that carries a spec id, and never edit `spec/`, `generator/` or a template-owned file.

## 5. Templates, manifest and boundary
1. `python3 generator/scripts/apply_templates.py --app {{app}} --check` must pass (template-owned files unchanged; build files equal to their kind skeleton outside the dependency region). If it fails, restore with `python3 generator/scripts/apply_templates.py --app {{app}}`, fix your own files, and rerun the final checkpoint.
2. Write the manifest: `python3 generator/scripts/check_headers.py --app {{app}} --write-manifest --spec-version {{spec_version}} --model-id {{model_id}} --result {{result_out}}` (schema `{{manifest_schema}}`).
3. Check it: `python3 generator/scripts/check_headers.py --app {{app}} --strict`.
4. Check the boundary: `git status --porcelain` lists nothing outside `{{app_dir}}/`.

## 6. Report
Print a short summary: modules generated, files, tests passed/total, and the checkpoint table from `python3 generator/scripts/checkpoint.py --app {{app}} --status` (attempts per checkpoint, total). On any failure print `GENERATE FAILED: {{app}}: <reason>` as the first line of the summary; never report partial success as success.

End with exactly one final line `RETURN: <code>`. Return codes: {{return_codes}}
