# Sub-agents

Role definitions for the delivery pipeline (`/pipeline`, see `generator/WORKFLOW.md` §2). ORC (the main session) launches them with a prompt rendered from `generator/prompts/<role>.md` and picks the model per launch (`generator/scripts/state.py model`).

| File | Role | Default model | Stages |
|---|---|---|---|
| `pm.md` | PM | sonnet | S0 (behavior), S1, S6 on failure |
| `tech-lead.md` | TL | opus (always) | S0 (protocol/platform), S2 |
| `developer.md` | DEV | sonnet (ORC overrides to opus for first generation) | S3 |
| `reviewer.md` | REV | sonnet (ORC overrides to opus above the changed-line threshold) | S4 |
| `qa.md` | QA | sonnet (ORC overrides to opus for a new suite) | S5 |

Every agent: checks its diff snapshot first (`check_snapshot.py`), ends with one `OUTCOME:` line (a `state.py` event) and one final `RETURN:` line (§5.1).
