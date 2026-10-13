"""Prompt templates: rendering, genericity lint (E-EVOL-1), generator preconditions, manifest round-trip."""
import tempfile
import unittest
from pathlib import Path

from _util import CONFIG, SCRIPTS, commit_file, make_repo, run_script
import awarelib as lib
import check_headers
import lint_prompts
import render_prompt

PROMPTS = SCRIPTS.parent / "prompts"
ROLES = ("pm", "tech-lead", "developer", "reviewer", "qa")
RULES = CONFIG["prompt_lint"]
ROLE_VARS = {k: f"<{k}>" for k in (
    "feature", "feature_title", "app", "stage", "round", "spec_version", "model", "model_reason", "diff_meta",
    "diff_patch", "changed_lines", "inputs", "output_path", "boundaries", "exit_criteria", "outcomes",
    "plan_path", "findings", "module_scope", "build_cmd", "test_cmd", "conventions_path", "report_paths")}


class PromptLint(unittest.TestCase):
    def test_repo_prompts_are_generic(self):
        res = run_script("lint_prompts.py")
        self.assertEqual(res.returncode, 0, res.stdout)

    def test_denylist_and_example_fences(self):
        pattern = lint_prompts.build_pattern(RULES)
        text = "\n".join([
            "Generate the Login screen.",          # 1 hit
            "```example",
            "the chat view shows messages",        # ignored
            "```",
            "```text",
            "queued items",                         # 5 hit (not an example fence)
            "```",
            "Messages and messaging",               # 8 two hits
            "a message-free contactless line",      # 9: 'message' hit; 'contactless' is not 'contact'
        ])
        hits = lint_prompts.lint_text(text, pattern, RULES["example_fence_word"])
        self.assertEqual([h[0] for h in hits], [1, 6, 8, 8, 9])

    def test_cli_reports_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "p.md"
            bad.write_text("Flush the outbox.\n")
            res = run_script("lint_prompts.py", tmp)
            self.assertEqual(res.returncode, lib.EXIT_FAIL)
            self.assertIn("p.md:1", res.stdout)


class RenderRolePrompts(unittest.TestCase):
    def test_every_role_template_renders_with_documented_vars(self):
        readme = (PROMPTS / "README.md").read_text()
        for role in ROLES:
            text = (PROMPTS / f"{role}.md").read_text()
            used = set(render_prompt.PLACEHOLDER.findall(text))
            for var in used:
                self.assertIn(f"`{{{{{var}}}}}`", readme, f"{role}.md uses undocumented {var}")
            out = render_prompt.render(text, {**ROLE_VARS, "return_codes": render_prompt.RETURN_CODES_TEXT})
            self.assertNotIn("{{", out)

    def test_unfilled_variables_fail(self):
        with self.assertRaises(render_prompt.RenderError):
            render_prompt.render("Hi {{feature}} {{app}}", {"feature": "x"})

    def test_cli_stage_outcomes_snapshot_and_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta = Path(tmp) / "diff.meta.json"
            lib.write_json_atomic(meta, {"changed_lines": 7, "patch": "diff.patch"})
            out = Path(tmp) / "prompt.md"
            args = ["--template", PROMPTS / "reviewer.md", "--stage", "S4", "--snapshot", meta, "--out", out,
                    "--input", "spec/README.md"]
            for k, v in ROLE_VARS.items():
                if k not in ("stage", "outcomes", "diff_meta", "diff_patch", "changed_lines", "inputs"):
                    args += ["--var", f"{k}={v}"]
            res = run_script("render_prompt.py", *args)
            self.assertEqual(res.returncode, 0, res.stderr)
            text = out.read_text()
            self.assertIn("`pass`, `blockers`, `design_concern`", text)
            self.assertIn("changed lines: 7", text)
            self.assertIn(lib.sha256_file(out), res.stdout)


class GeneratePrompt(unittest.TestCase):
    def test_not_configured_without_conventions(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = run_script("render_prompt.py", "--generate", "web", "--root", tmp, "--print")
            self.assertEqual(res.returncode, lib.EXIT_FAIL)
            self.assertIn("generator not yet configured for web", res.stderr)

    def test_renders_from_config_when_conventions_exist(self):
        tmp, repo = make_repo()
        self.addCleanup(tmp.cleanup)
        (repo / "spec").mkdir()
        (repo / "spec" / "README.md").write_text("**Version:** 1.2.3 (test)\n")
        commit_file(repo, CONFIG["apps"]["web"]["conventions"], "# conventions\n")
        res = run_script("render_prompt.py", "--generate", "web", "--root", repo, "--print")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertNotIn("{{", res.stdout)
        self.assertIn("Spec version: `1.2.3`", res.stdout)
        self.assertIn(CONFIG["headers"]["marker"] + " from spec 1.2.3", res.stdout)


    def render_with_version(self, version_line):
        tmp, repo = make_repo()
        self.addCleanup(tmp.cleanup)
        (repo / "spec").mkdir()
        (repo / "spec" / "README.md").write_text(version_line + "\n")
        commit_file(repo, CONFIG["apps"]["web"]["conventions"], "# conventions\n")
        return run_script("render_prompt.py", "--generate", "web", "--root", repo, "--print")

    def test_shared_platform_inputs_are_listed(self):
        res = self.render_with_version("**Version:** 1.2.3")
        self.assertGreater(len(CONFIG["generate"]["platform_shared"]), 1)
        for path in CONFIG["generate"]["platform_shared"]:
            self.assertTrue((SCRIPTS.parents[1] / path).exists(), path)
            self.assertIn(f"`{path}`", res.stdout)
        self.assertIn("test-hooks.md", res.stdout)
        self.assertIn("client-snapshot.schema.json", res.stdout)

    def test_draft_version_is_stamped_in_full_and_warned(self):
        res = self.render_with_version("**Version:** 0.1.0-draft (test)")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Spec version: `0.1.0-draft` (draft: yes)", res.stdout)
        self.assertIn(CONFIG["headers"]["marker"] + " from spec 0.1.0-draft", res.stdout)
        self.assertIn("WARNING: spec 0.1.0-draft is a draft", res.stderr)
        final = self.render_with_version("**Version:** 1.0.0")
        self.assertIn("(draft: no)", final.stdout)
        self.assertNotIn("WARNING", final.stderr)

    def test_draft_version_passes_manifest_schema_pattern(self):
        import re
        pattern = lib.read_json(lib.SCHEMA_DIR / "manifest.schema.json")["properties"]["spec_version"]["pattern"]
        self.assertTrue(re.match(pattern, "0.1.0-draft"))
        self.assertTrue(re.match(pattern, "0.1.0"))
        self.assertFalse(re.match(pattern, "0.1"))


class ManifestRoundTrip(unittest.TestCase):
    def test_written_manifest_passes_check(self):
        tmp, repo = make_repo()
        self.addCleanup(tmp.cleanup)
        app_dir = repo / CONFIG["apps"]["web"]["dir"]
        (app_dir / "src").mkdir(parents=True)
        (app_dir / "src" / "a.ts").write_text(f"// {CONFIG['headers']['marker']} from spec 0.1.0\n")
        res = run_script("check_headers.py", "--root", repo, "--app", "web", "--write-manifest",
                         "--spec-version", "0.1.0", "--model-id", "test-model")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(check_headers.check_app(app_dir, CONFIG), ("checked", []))
        self.assertEqual(run_script("check_headers.py", "--root", repo, "--app", "web", "--strict").returncode, 0)


if __name__ == "__main__":
    unittest.main()
