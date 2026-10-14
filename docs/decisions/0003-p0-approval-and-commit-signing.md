# 0003 — Phase 0 approval and commit signing
- **Superseded in part by [decision 0015](0015-operator-authored-commits.md):** the author convention in the signing note below ("authors stay `Aware Agent (...)`") no longer applies; history is operator-authored and agents appear only in trailers. The signing command itself still works.
- Status: accepted (operator, 2026-10-13, OM-0008)
- **Phase 0 (harness) approved** by the operator at the P0 gate. Open items from the P0 review stay open: review-report schema check, README checklist script, two-run determinism comparison, E-TL-1 checker.
- **Commit signing:** the operator will sign with their own key. Agents run in a cloud workspace and cannot reach that key, so signing is done **once, at packaging (P8), from the operator's own terminal**, because it rewrites commit hashes:
  `git rebase --root --exec 'git commit --amend --no-edit -S'` (authors stay `Aware Agent (...)`; the committer becomes the signing operator). Verify with `git log --show-signature`. Do this before building the archive and after the final regen-check, then re-run `lint_commits.py`.
- Until then, commits are unsigned and GitHub-style "Unverified" warnings are expected.
