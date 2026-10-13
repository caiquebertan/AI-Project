# Task: QA — {{stage}} for {{feature}} / {{app}}

You are the **qa** sub-agent (`.claude/agents/qa.md`). Follow that file's rules; this prompt gives the concrete inputs for this launch.

## Context
- Feature: `{{feature}}` — {{feature_title}}
- App: `{{app}}` · Spec version: `{{spec_version}}`
- Model: {{model}} ({{model_reason}})
- Acceptance criteria: rows under `## {{feature}}` in `docs/product/TRACEABILITY.md`
- Diff snapshot: `{{diff_meta}}` (patch: `{{diff_patch}}`)
- Review report: {{findings}}
- Conventions (test requirements section): `{{conventions_path}}`

## Inputs
{{inputs}}

## Do
1. Run `python3 generator/scripts/check_snapshot.py --meta {{diff_meta}}`. On `STALE_DIFF`, stop and return it.
2. For every acceptance criterion in scope, write or extend an external check under `tests/`. Name or tag each test with its test id and spec ids.
3. State the in-project unit/UI tests the generator must produce as requirements in the conventions file; never edit `clients/`.
4. Run the full suite (regression), writing JUnit XML or Playwright JSON reports to: {{report_paths}}
5. Classify every failure and write `qa.md` to: {{output_path}}

## Boundaries
{{boundaries}}

## Exit criteria
{{exit_criteria}}

## Finish
End your reply with `OUTCOME: <one of {{outcomes}}>` and then the final line `RETURN: <code>`.
Return codes: {{return_codes}}
