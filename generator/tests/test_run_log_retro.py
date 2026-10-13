"""run_log.py CLI and render_retro.py over a stub feature's run log."""
import json
import tempfile
import unittest
from pathlib import Path

from _util import CAPS, SCRIPTS, run_script
import awarelib as lib
import render_retro
from state import Machine, default_state_path

OP = "operator"
TEMPLATE = (SCRIPTS.parents[1] / "docs" / "retros" / "TEMPLATE.md").read_text()


class RunLogAndRetro(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        m = Machine(Machine.new_state(), CAPS, self.root, regen_per_feature=True)
        m.start_feature("F9", "stub", ["web"], "light")
        m.transition("F9", "no_delta", log_extra={"spec_version": "0.1.0", "agent": "PM+TL"})
        m.transition("F9", "ok", app="web")
        m.transition("F9", "ok", app="web", log_extra={"model": "opus", "model_reason": "first generation",
                                                        "outputs": ["clients/web/src/app.ts"], "tokens": 1000})
        m.transition("F9", "blockers", app="web", log_extra={"model": "sonnet", "tokens": 500, "commit": "abc1234def"})
        for ev in ("ok", "pass", "green"):
            m.transition("F9", ev, app="web")
        m.transition("F9", "met", app="web", log_extra={"result": {"met": ["AC-1"], "unmet": []}})
        m.transition("F9", "green", app="web", log_extra={"spec_version": "0.1.1"})
        m.transition("F9", "ok", log_extra={"outputs": ["docs/retros/F9.md"], "operator_msg_ref": "OM-0042"})
        m.save(default_state_path(self.root))

    def test_cli_append_with_prompt_and_snapshot(self):
        prompt = self.root / "prompt.md"
        prompt.write_text("rendered prompt")
        meta = self.root / "meta.json"
        meta.write_text(json.dumps({"base_sha": "a" * 40, "head_sha": "b" * 40, "changed_lines": 12}))
        res = run_script("run_log.py", "--root", self.root, "append", "--feature", "F9", "--event", "launch",
                         "--agent", "REV", "--model", "sonnet", "--prompt", prompt, "--snapshot", meta,
                         "--findings", '{"blockers": 1}', "--input", "spec/README.md")
        self.assertEqual(res.returncode, 0, res.stderr)
        ev = lib.read_run_events(self.root, "F9")[-1]
        self.assertEqual(ev["prompt_sha256"], lib.sha256_bytes(b"rendered prompt"))
        self.assertEqual((ev["changed_lines"], ev["findings"]), (12, {"blockers": 1}))
        self.assertEqual(run_script("run_log.py", "--root", self.root, "validate", "--feature", "F9").returncode, 0)

    def test_invalid_event_rejected(self):
        res = run_script("run_log.py", "--root", self.root, "append", "--feature", "F9", "--event", "x",
                         "--agent", "NOBODY")
        self.assertEqual(res.returncode, lib.EXIT_USAGE)

    def test_render_retro_tables_and_narrative(self):
        res = run_script("render_retro.py", "--root", self.root, "--feature", "F9", "--update-index")
        self.assertEqual(res.returncode, 0, res.stderr)
        text = (self.root / "docs" / "retros" / "F9.md").read_text()
        self.assertIn("# Retro — F9: stub", text)
        self.assertIn("- Chain: light", text)
        self.assertIn("- Spec version: in 0.1.0 → out 0.1.1", text)
        self.assertIn("- Regen-check (S6b): pass (1 attempt(s))", text)
        self.assertIn("- Operator interventions: OM-0042", text)
        self.assertIn("- ACs met (ids): AC-1", text)
        self.assertIn("| S4 → S3 [web] | blockers |", text)  # backward transition
        self.assertIn("| S4 [web] | REV | sonnet | 1 | blockers → S3 | abc1234def |", text)
        self.assertIn("| clients/web/src/app.ts | generated |", text)
        self.assertIn("| Tokens |  | 1500 |", text)
        self.assertIn("## Gaps found\n<!-- ORC: fill in -->", text)
        # ORC fills a narrative section; a re-render keeps it
        out = self.root / "docs" / "retros" / "F9.md"
        out.write_text(text.replace("## Gaps found\n<!-- ORC: fill in -->\n-", "## Gaps found\n- a real gap"))
        run_script("render_retro.py", "--root", self.root, "--feature", "F9", "--update-index")
        self.assertIn("- a real gap", out.read_text())
        index = (self.root / "docs" / "runs" / "INDEX.md").read_text()
        self.assertEqual(index.count("| F9 |"), 1)
        self.assertIn("| F9 | stub | done |", index)

    def test_render_needs_a_log(self):
        res = run_script("render_retro.py", "--root", self.root, "--feature", "NOPE")
        self.assertEqual(res.returncode, lib.EXIT_USAGE)

    def test_template_sections_all_present(self):
        events = lib.read_run_events(self.root, "F9")
        text = render_retro.render(TEMPLATE, "F9", "stub", events, None)
        for heading, _ in render_retro.split_sections(TEMPLATE)[1]:
            self.assertIn(heading.replace("<feature-id>", "F9"), text)


if __name__ == "__main__":
    unittest.main()
