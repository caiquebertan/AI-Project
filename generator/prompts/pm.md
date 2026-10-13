# Task: PM — {{stage}} for {{feature}} ({{feature_title}})

You are the **pm** sub-agent (`.claude/agents/pm.md`). Follow that file's rules; this prompt gives the concrete inputs for this launch.

## Context
- Feature: `{{feature}}` — {{feature_title}}
- Stage: `{{stage}}` · App scope: `{{app}}` · Spec version in: `{{spec_version}}`
- Model: {{model}} ({{model_reason}})
- Diff snapshot: `{{diff_meta}}` (patch: `{{diff_patch}}`)

## Inputs (read these, nothing else is authoritative)
{{inputs}}

## Do
1. Run `python3 generator/scripts/check_snapshot.py --meta {{diff_meta}}`. On `STALE_DIFF`, stop and return it.
2. Read the brief, the spec index (`spec/README.md`) and the inputs above.
3. Stage S0: write the behavior and scenario delta for this feature only; give every new MUST an id; bump the spec version.
   Stage S1: add one row per acceptance criterion per scope under `## {{feature}}` in `docs/product/TRACEABILITY.md`; each row references a spec id and a test id; Status `pending`.
   Stage S6: classify each unmet acceptance criterion listed in the inputs (code defect / spec gap / invalid AC / new work).
4. Write the outputs to: {{output_path}}

## Boundaries
{{boundaries}}

## Exit criteria
{{exit_criteria}}

## Finish
End your reply with `OUTCOME: <one of {{outcomes}}>` and then the final line `RETURN: <code>`.
Return codes: {{return_codes}}
