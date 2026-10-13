# 0015 — Commits are authored by the operator; agents appear only in trailers

Status: accepted (operator, OM-0012)
Supersedes: the author convention in decision 0003 (agent as author, operator as committer).

## Decision
- Every commit has the operator (Caique Bertan <kiq.bertan@gmail.com>) as author and committer.
- The agent that did the work is recorded only in the trailer block (`Authored-By-Role`, `Agent`, `Model`, `Stage`, `Feature`), plus the `Co-Authored-By` and `Claude-Session` lines.
- Agent commits are identified by the `Agent` trailer, not by the author name.
- Existing history is rewritten once, after the open branches are merged: authors are reset to the operator, messages and trailers are unchanged.
- Origin is `caiquebertan/AI-Project`. History is pushed after the rewrite and after the operator's go.

## Unchanged
- Signing with the operator's own key stays planned for packaging (P8), so GitHub will show "Unverified" until then.
- Branch per workstream, `--no-ff` merges, regen commits separate, no commit touching both `spec/` and `clients/`.

## Consequences
- `lint_commits.py` and its tests, `generator/WORKFLOW.md`, `.claude/commands/pipeline.md`, README and AGENTS are updated to match.
- Rewriting changes every hash; hashes quoted in earlier docs refer to pre-rewrite history.
