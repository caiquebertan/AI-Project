# Prompt templates

Templates with `{{var}}` placeholders only. Feature knowledge lives in `spec/`, never here (E-EVOL-1, enforced by `generator/scripts/lint_prompts.py`; fenced blocks tagged `example` are exempt). Render with `generator/scripts/render_prompt.py`, which refuses to leave a placeholder unfilled and prints the sha256 that goes in the run log.

| Template | Used by | Rendered by |
|---|---|---|
| `pm.md`, `tech-lead.md`, `developer.md`, `reviewer.md`, `qa.md` | the matching sub-agent in `.claude/agents/` | ORC at each stage (`/pipeline`) |
| `generate.md` | the headless generator (`/generate <app>`) | `render_prompt.py --generate <app>` from `generator/config/generator.json` |

## Role prompt variables (filled by ORC)

| Variable | Meaning |
|---|---|
| `{{feature}}`, `{{feature_title}}` | Feature id and title from `.work/STATE.json` |
| `{{app}}` | App (or comma list of apps) in scope |
| `{{stage}}` | Pipeline stage (`--stage` also fills `{{outcomes}}`) |
| `{{outcomes}}` | Allowed `OUTCOME:` events for the stage (from `state.py`) |
| `{{round}}` | Review round number (reviewer) |
| `{{spec_version}}` | Spec version at launch |
| `{{model}}`, `{{model_reason}}` | Model alias and the rule that chose it (`state.py model`) |
| `{{diff_meta}}`, `{{diff_patch}}`, `{{changed_lines}}` | Snapshot paths and size (`--snapshot` fills all three) |
| `{{inputs}}` | Bullet list of input paths (`--input`, repeatable) |
| `{{output_path}}` | Where the agent writes its output |
| `{{plan_path}}` | `docs/plans/<feature>/<app>.md` |
| `{{findings}}` | Review / QA / acceptance reports to address or verify |
| `{{module_scope}}` | Module to regenerate, or `all` |
| `{{conventions_path}}` | `generator/conventions/<app>.md` |
| `{{build_cmd}}`, `{{test_cmd}}` | App build and test commands (config) |
| `{{report_paths}}` | Where QA writes JUnit XML / Playwright JSON |
| `{{boundaries}}` | Stage-specific limits on top of the role file |
| `{{exit_criteria}}` | What "done" means for this launch |
| `{{return_codes}}` | Return codes (§5.1); filled by default |

## Generator prompt variables (filled from config by `--generate`)

| Variable | Source |
|---|---|
| `{{app}}`, `{{app_dir}}`, `{{module_scope}}` | `apps.<app>.dir`, `--module` |
| `{{spec_index}}`, `{{spec_dirs}}`, `{{spec_version}}` | `generate.spec_index`, `generate.spec_dirs`, version line of the spec index |
| `{{platform_spec}}`, `{{conventions_path}}`, `{{templates_dir}}` | `apps.<app>.platform_spec`, `apps.<app>.conventions`, `generate.templates_dir` |
| `{{build_cmd}}`, `{{test_cmd}}`, `{{self_repair_max}}` | `apps.<app>.build`, `apps.<app>.test`, `self_repair_max` |
| `{{model_id}}`, `{{generator_commit}}` | `generate_model`, `git rev-parse HEAD` |
| `{{plan_out}}`, `{{manifest_schema}}`, `{{header_text}}` | `generate.plan_out`, `generate.manifest_schema`, `headers.header_text` |
| `{{return_codes}}` | default |
