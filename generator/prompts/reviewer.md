# Task: REV — review round {{round}} for {{feature}} / {{app}}

You are the **reviewer** sub-agent (`.claude/agents/reviewer.md`). Follow that file's rules and report format; this prompt gives the concrete inputs for this launch.

## Context
- Feature: `{{feature}}` — {{feature_title}}
- App: `{{app}}` · Review round: {{round}} · Spec version: `{{spec_version}}`
- Model: {{model}} ({{model_reason}})
- Diff snapshot: `{{diff_meta}}` (patch or file list: `{{diff_patch}}`), changed lines: {{changed_lines}}
- Plan: `{{plan_path}}` · Conventions: `{{conventions_path}}`
- Earlier findings (to verify they are fixed): {{findings}}

## Inputs
{{inputs}}

## Do
1. Run `python3 generator/scripts/check_snapshot.py --meta {{diff_meta}}`. On `STALE_DIFF`, stop and return it.
2. Review only the snapshot. If it is split, read the listed files and per-file patches.
3. Check spec conformance, correctness, concurrency and threading, code shape, and the regeneration boundary.
4. For generated code, name where each fix belongs (spec id, convention, template or prompt).
5. Write the report (YAML front matter + `[blocker|nit|design]` lines) to: {{output_path}}

## Boundaries
{{boundaries}}

## Exit criteria
{{exit_criteria}}

## Finish
End your reply with `OUTCOME: <one of {{outcomes}}>` (add `target: plan|spec` for a design concern) and then the final line `RETURN: <code>`.
Return codes: {{return_codes}}
