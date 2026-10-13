# Task: TL — {{stage}} for {{feature}} ({{feature_title}})

You are the **tech-lead** sub-agent (`.claude/agents/tech-lead.md`). Follow that file's rules; this prompt gives the concrete inputs for this launch.

## Context
- Feature: `{{feature}}` — {{feature_title}}
- Stage: `{{stage}}` · Apps affected: `{{app}}` · Spec version in: `{{spec_version}}`
- Model: {{model}} ({{model_reason}})
- Diff snapshot: `{{diff_meta}}` (patch: `{{diff_patch}}`)

## Inputs
{{inputs}}

## Do
1. Run `python3 generator/scripts/check_snapshot.py --meta {{diff_meta}}`. On `STALE_DIFF`, stop and return it.
2. Read the brief, `docs/PROJECT_CONTEXT.md`, `docs/decisions/`, the spec index and the inputs above.
3. Stage S0: write the protocol, schema and platform delta this feature needs; record each core protocol decision as a decision record.
   Stage S2: write one plan per affected app at `docs/plans/{{feature}}/<app>.md` citing spec ids for every decision, plus the proposed changes to `generator/conventions/`, `generator/templates/`, `generator/prompts/` and `spec/platform/`.
4. Keep generator prompts generic: feature knowledge belongs in `spec/`, never in `generator/prompts/`.
5. Write the outputs to: {{output_path}}

## Boundaries
{{boundaries}}

## Exit criteria
{{exit_criteria}}

## Finish
End your reply with `OUTCOME: <one of {{outcomes}}>` and then the final line `RETURN: <code>`.
Return codes: {{return_codes}}
