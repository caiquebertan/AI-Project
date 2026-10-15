# FUTURE

What we would do next. We stopped when the Claude Pro token budget ran out (decision 0020). Items are in the order we would do them; the plan for each is in [`docs/PLAN.md`](docs/PLAN.md).

## Unfinished plan phases
1. **Regeneration check for Android (P7).** `python3 generator/scripts/regen_check.py --app android --clone` (about 41 minutes, $15 list price). Then a second web run to measure determinism, and a run by someone who only follows the README. Web passed once ([`docs/runs/P7/`](docs/runs/P7/)).
2. **Acceptance and traceability (P4).** A QA-designed browser suite (`tests/web-e2e/`) and an Android conformance suite. Make generated tests carry AC ids (today `check_trace.py --feature F1,F2,F3` reports 0/172 met because the ids differ from `docs/product/TRACEABILITY.md`; 71.5% of the 239 rules are mentioned by some test). Independent review (REV) of both generated clients.
3. **Automated interop through the real server (P5).** Done by hand and recorded (web Bob in Chrome, Android Alice in the emulator, including Offline mode and Pending delivery; human-validated, [`docs/demo/`](docs/demo/)). Still to do: script it as `tests/interop/run.sh` (web to web through the UI, Android driver to web UI), three green runs in a row. First thing to look at if it fails: the hand-written HTTP parser in `server/aware_server/httpd.py` (known gaps in `docs/runs/P2/known-gaps.md`).
4. **Evolution demo (P6).** Add reactions as `spec/extensions/reactions.md`, run `/generate` with no prompt changes, and check mixed web/Android pairs. This is the test of "the harness is not hard-coded to this spec".
5. **Signed history (P8).** Re-sign the commits with the operator's own key, re-create the `spec-v0.1.x` tags, force-push.

## Known gaps to close
- The Android UI was run on the emulator and validated by hand ([`docs/demo/`](docs/demo/)); there is no automated emulator or Playwright suite yet.
- Allowlist in `generator.claude_flags` denies `for` loops and `; echo` variants; the run recovers but wastes turns.
- Spec gaps raised by PM and left open: no AC for CORE-VISIBLE-005/006; a refused text with forbidden characters has no defined on-screen message.
- Backlog cut-order wording: withdrawing time display must not remove the UTC wire rules (`docs/PLAN.md` §8, item 6).
- Server: parser and stress run not re-checked after review fix 2.

## Ideas
- Spec extensions: attachments, group conversations, protocol extensions.
- A third client (iOS/Swift) to stress the generic-versus-platform split.
- Regeneration check in CI.
- Durable server storage and auth (out of scope for this exercise).
- Cost control: record cost per checkpoint, and let `/generate` resume from the last passing checkpoint after a limit hit.
