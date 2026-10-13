# Task: DEV — {{stage}} for {{feature}} / {{app}}

You are the **developer** sub-agent (`.claude/agents/developer.md`). Follow that file's rules; this prompt gives the concrete inputs for this launch.

## Context
- Feature: `{{feature}}` — {{feature_title}}
- App: `{{app}}` · Module scope: `{{module_scope}}` · Spec version: `{{spec_version}}`
- Model: {{model}} ({{model_reason}})
- Plan: `{{plan_path}}`
- Findings to address (review / QA / acceptance), if any: {{findings}}
- Diff snapshot: `{{diff_meta}}` (patch: `{{diff_patch}}`)

## Inputs
{{inputs}}

## Do
1. Run `python3 generator/scripts/check_snapshot.py --meta {{diff_meta}}`. On `STALE_DIFF`, stop and return it.
2. Read the plan, the findings and the inputs. Address every blocker; turn pattern nits into conventions.
3. Generated app: change only the generator inputs the plan names (conventions, templates, prompts), then run the generator for `{{app}}` (scope `{{module_scope}}`) as described in `generator/RUN.md`. Never edit files under `clients/` by hand.
   Maintained component: edit its code and simple unit tests directly.
4. Build and run the in-project tests: `{{build_cmd}}` then `{{test_cmd}}`.
5. Do not commit. Write any notes to: {{output_path}}

## Boundaries
{{boundaries}}

## Exit criteria
{{exit_criteria}}

## Finish
End your reply with `OUTCOME: <one of {{outcomes}}>` and then the final line `RETURN: <code>`.
Return codes: {{return_codes}}
