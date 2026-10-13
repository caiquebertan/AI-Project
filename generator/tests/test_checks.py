"""check_trace, check_headers, regen_check (dry run), lint_commits and preflight."""
import json
import tempfile
import unittest
from pathlib import Path

from _util import CONFIG, SCRIPTS, commit_file, make_repo, run_script
import awarelib as lib
import check_headers
import check_trace
import lint_commits
import regen_check

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class CheckTrace(unittest.TestCase):
    def run_trace(self, *extra):
        return run_script("check_trace.py", "--trace", FIXTURES / "trace" / "TRACEABILITY.md",
                          "--spec-dir", FIXTURES / "trace" / "spec",
                          "--junit", FIXTURES / "trace" / "junit.xml",
                          "--playwright", FIXTURES / "trace" / "playwright.json", "--json", *extra)

    def test_ac_status_and_spec_coverage(self):
        res = self.run_trace()
        self.assertEqual(res.returncode, lib.EXIT_FAIL, res.stderr)
        out = json.loads(res.stdout)
        status = {r["ac"]: (r["status"], r["reason"]) for r in out["rows"]}
        self.assertEqual(status["AC-F1-1"][0], "met")         # junit pass
        self.assertEqual(status["AC-F1-2"][0], "met")         # playwright pass via tag
        self.assertIn("failed", status["AC-F1-3"][1])         # junit failure
        self.assertIn("no test found", status["AC-F2-1"][1])
        self.assertIn("skipped", status["AC-F2-2"][1])
        self.assertIn("bad scope", status["AC-F2-3"][1])
        cov = out["spec_coverage"]
        # MUST definitions only: CORE-003 is SHOULD, CORE-099 is a reference, CORE-04 is mistyped.
        self.assertEqual(cov["total"], 6)
        self.assertEqual(cov["missing"], ["CORE-010", "CORE-011", "CORE-SRV-001", "CORE-SRV-002"])
        self.assertEqual(cov["covered"], ["CORE-001", "CORE-002"])   # untagged reports count for every app

    def test_rules_are_definitions_not_references(self):
        rules = check_trace.spec_rules(FIXTURES / "trace" / "spec", CONFIG["trace"])
        ids = [r["id"] for r in rules]
        self.assertEqual(ids, ["CORE-001", "CORE-002", "CORE-010", "CORE-011", "CORE-SRV-001", "CORE-SRV-002"])
        self.assertNotIn("CORE-099", ids)
        self.assertNotIn("CORE-003", ids)
        self.assertIn("CORE-003", check_trace.defined_ids(FIXTURES / "trace" / "spec", CONFIG["trace"]["spec_id_regex"]))

    def test_apps_per_rule(self):
        rules = {r["id"]: r["apps"] for r in check_trace.spec_rules(FIXTURES / "trace" / "spec", CONFIG["trace"])}
        self.assertEqual(rules["CORE-001"], ["android", "web", "server"])   # default
        self.assertEqual(rules["CORE-SRV-001"], ["server"])                 # server-behavior.md
        self.assertEqual(rules["CORE-SRV-002"], ["server", "web"])          # [apps: ...] marker wins

    def test_per_app_coverage_with_tagged_reports(self):
        rules = [{"id": "CORE-A-001", "apps": ["android", "web"]}, {"id": "CORE-SRV-001", "apps": ["server"]},
                 {"id": "CORE-P-001", "apps": ["android", "web", "server"]}]

        def t(name, app=None):
            return {"name": name, "status": "passed", "apps": None if app is None else [app]}

        tests = [t("CORE-A-001", "android"), t("CORE-SRV-001", "web"), t("CORE-P-001", "android"),
                 t("CORE-P-001", "web"), t("CORE-P-001", "server")]
        cov = check_trace.spec_coverage(rules, tests)
        self.assertEqual(cov["uncovered"], [["CORE-A-001", "web"], ["CORE-SRV-001", "server"]])
        self.assertEqual((cov["pairs_total"], cov["pairs_covered"]), (6, 4))
        self.assertEqual(cov["covered"], ["CORE-P-001"])
        # an untagged passing test covers every app
        self.assertEqual(check_trace.spec_coverage(rules, [t("CORE-A-001 CORE-SRV-001 CORE-P-001")])["uncovered"], [])

    def test_cli_tagged_reports(self):
        res = run_script("check_trace.py", "--trace", FIXTURES / "trace" / "TRACEABILITY.md",
                         "--spec-dir", FIXTURES / "trace" / "spec", "--junit", f"server={FIXTURES / 'trace' / 'junit.xml'}",
                         "--json")
        cov = json.loads(res.stdout)["spec_coverage"]
        self.assertIn(["CORE-001", "android"], cov["uncovered"])   # only the server saw CORE-001
        self.assertNotIn(["CORE-001", "server"], cov["uncovered"])

    def test_feature_filter_and_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            trace = Path(tmp) / "T.md"
            trace.write_text((FIXTURES / "trace" / "TRACEABILITY.md").read_text())
            acc = Path(tmp) / "acceptance.md"
            res = run_script("check_trace.py", "--trace", trace, "--spec-dir", FIXTURES / "trace" / "spec",
                             "--junit", FIXTURES / "trace", "--playwright", FIXTURES / "trace" / "playwright.json",
                             "--feature", "F1", "--write", "--acceptance", acc)
            self.assertEqual(res.returncode, lib.EXIT_FAIL)  # AC-F1-3 fails
            text = trace.read_text()
            self.assertIn("| BR-1 | CORE-001 | AC-F1-1 | core | T-F1-1 | met |", text)
            self.assertIn("| SC-3 | CORE-010 | AC-F2-1 | core | T-F2-1 | pending |", text)  # F2 untouched
            self.assertIn("| AC-F1-3 |", acc.read_text())

    def test_coverage_is_informational_unless_strict(self):
        """OM-0011: exit status follows the AC rows only; --strict-coverage restores the coverage gate."""
        with tempfile.TemporaryDirectory() as tmp:
            trace = Path(tmp) / "T.md"
            trace.write_text("## F1\n| BR/SC id | Spec id | AC id | Scope | Test id | Status |\n|---|---|---|---|---|---|\n"
                             "| BR-1 | CORE-001 | AC-F1-1 | core | T-F1-1 | pending |\n")
            args = ("check_trace.py", "--trace", trace, "--spec-dir", FIXTURES / "trace" / "spec",
                    "--junit", FIXTURES / "trace" / "junit.xml")
            res = run_script(*args)
            self.assertEqual(res.returncode, lib.EXIT_OK, res.stderr)   # all ACs met, rules uncovered
            self.assertIn("ACs: 1/1 met", res.stdout)
            self.assertIn("informational", res.stdout)
            self.assertIn("uncovered (spec id, app) pairs", res.stdout)
            strict = run_script(*args, "--strict-coverage")
            self.assertEqual(strict.returncode, lib.EXIT_FAIL)
            self.assertIn("gated by --strict-coverage", strict.stdout)
            self.assertEqual(run_script(*args, "--strict-spec").returncode, lib.EXIT_FAIL)   # old spelling

    def test_unmet_ac_still_fails_without_strict(self):
        res = self.run_trace()
        self.assertEqual(res.returncode, lib.EXIT_FAIL)

    def test_empty_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = run_script("check_trace.py", "--root", tmp)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertIn("ACs: 0/0 met", res.stdout)

    def test_repo_traceability_parses_and_refers_to_defined_spec_ids(self):
        root = SCRIPTS.parents[1]
        cfg = CONFIG["trace"]
        rows = check_trace.parse_trace((root / cfg["file"]).read_text())
        self.assertTrue(rows, "TRACEABILITY.md has no rows")
        defined = check_trace.defined_ids(root / cfg["spec_dir"], cfg["spec_id_regex"])
        for row in rows:
            self.assertRegex(row["scope"], cfg["scope_regex"], f"line {row['line']}")
            self.assertIn(row["spec"], defined, f"line {row['line']}: {row['spec']} is not defined in spec/")


class CheckHeaders(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = Path(self.tmp.name) / "clients" / "web"

    def write_generated(self, files):
        self.app.mkdir(parents=True, exist_ok=True)
        entries = []
        for rel, content in files.items():
            p = self.app / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
            entries.append({"path": rel, "sha256": lib.sha256_file(p)})
        manifest = {"app": "web", "spec_version": "0.1.0", "generator_commit": "abc1234", "model_id": "m",
                    "generated_at": "2026-10-13T00:00:00Z", "files": entries}
        (self.app / CONFIG["headers"]["manifest"]).write_text(json.dumps(manifest))

    def test_missing_dir_and_placeholder_are_graceful(self):
        self.assertEqual(check_headers.check_app(self.app, CONFIG), ("absent", []))
        res = run_script("check_headers.py", "--root", self.tmp.name, "--app", "web")
        self.assertEqual(res.returncode, 0)
        self.assertIn("SKIP web", res.stdout)
        self.app.mkdir(parents=True)
        (self.app / ".generated").write_text("Generated by the Aware harness. placeholder\n")
        self.assertEqual(check_headers.check_app(self.app, CONFIG)[0], "placeholder")
        strict = run_script("check_headers.py", "--root", self.tmp.name, "--app", "web", "--strict")
        self.assertEqual(strict.returncode, lib.EXIT_FAIL)

    def test_clean_tree_passes(self):
        marker = CONFIG["headers"]["marker"]
        self.write_generated({"src/a.ts": f"// {marker} from spec 0.1.0\nexport {{}}\n", "package.json": "{}\n"})
        (self.app / "node_modules").mkdir()
        (self.app / "node_modules" / "x.js").write_text("ignored")
        self.assertEqual(check_headers.check_app(self.app, CONFIG), ("checked", []))

    def test_mismatches_reported(self):
        self.write_generated({"src/a.ts": "export {}\n", "src/b.ts": f"// {CONFIG['headers']['marker']}\n"})
        (self.app / "src" / "b.ts").write_text("edited by hand\n")
        (self.app / "src" / "extra.ts").write_text("x")
        _, problems = check_headers.check_app(self.app, CONFIG)
        text = "\n".join(problems)
        self.assertIn("missing GENERATED header: src/a.ts", text)
        self.assertIn("sha256 mismatch: src/b.ts", text)
        self.assertIn("not in manifest: src/extra.ts", text)


class RegenCheck(unittest.TestCase):
    def test_dry_run_prints_steps_and_touches_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = run_script("regen_check.py", "--root", tmp, "--app", "all", "--dry-run")
            self.assertEqual(res.returncode, 0, res.stderr)
            for word in ("git worktree add", "rm -rf clients/android", "/generate web", "boundary", "cleanup"):
                self.assertIn(word, res.stdout)
            self.assertFalse((Path(tmp) / ".work").exists())

    def test_all_apps_run_in_order_each_in_a_fresh_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            res = run_script("regen_check.py", "--root", tmp, "--app", "all", "--dry-run")
            out = res.stdout
            self.assertLess(out.index("# regen-check android"), out.index("# regen-check web"))
            adds = [ln for ln in out.splitlines() if "git worktree add" in ln]
            self.assertEqual(len(adds), 2)
            self.assertNotEqual(adds[0].split()[-2], adds[1].split()[-2])   # distinct worktrees

    def test_combined_summary_names_every_app(self):
        reports = [{"app": "android", "ok": True, "steps": []},
                   {"app": "web", "ok": False, "steps": [{"step": "generate"}]}]
        self.assertEqual(regen_check.summary(reports), "android PASS, web FAIL (generate)")

    def test_real_run_fails_loudly_while_unconfigured(self):
        if not CONFIG["generate_model"].startswith("TBD"):
            self.skipTest("model pinned; covered by P3 regen runs")
        with tempfile.TemporaryDirectory() as tmp:
            res = run_script("regen_check.py", "--root", tmp, "--app", "web")
            self.assertEqual(res.returncode, lib.EXIT_FAIL)
            self.assertIn("not configured", res.stderr)
            self.assertFalse((Path(tmp) / ".work").exists())


AGENT = {"GIT_AUTHOR_NAME": "Aware Agent (DEV/test-model)", "GIT_AUTHOR_EMAIL": "agent@aware.local"}
GOOD = """generator: add thing

Body.

Area: generator
Boundary: maintained
Authored-By-Role: agent
Agent: DEV
Model: test-model
Stage: P0
Refs: OM-0007

Co-Authored-By: Someone <x@example.invalid>
"""


class LintCommits(unittest.TestCase):
    def setUp(self):
        self.tmp, self.repo = make_repo()
        self.addCleanup(self.tmp.cleanup)

    def test_trailers_across_paragraphs(self):
        t = lint_commits.parse_trailers(GOOD)
        self.assertEqual(t["Agent"], ["DEV"])
        self.assertIn("Co-Authored-By", t)

    def test_good_and_bad_commits(self):
        commit_file(self.repo, "generator/a.txt", "1", GOOD, env=AGENT)
        res = run_script("lint_commits.py", "--cwd", self.repo)
        self.assertEqual(res.returncode, 0, res.stdout)
        self.assertIn("1/1 commit(s) OK", res.stdout)

        commit_file(self.repo, "generator/b.txt", "2", "generator: no trailers\n\nBody only.", env=AGENT)
        bad_agent = GOOD.replace("Agent: DEV", "Agent: REV").replace("Stage: P0\n", "")
        commit_file(self.repo, "generator/c.txt", "3", bad_agent, env=AGENT)
        res = run_script("lint_commits.py", "--cwd", self.repo)
        self.assertEqual(res.returncode, lib.EXIT_FAIL)
        self.assertIn("missing trailer Area", res.stdout)
        self.assertIn("Agent trailer REV != author role DEV", res.stdout)

    def test_spec_and_clients_in_one_commit(self):
        (self.repo / "spec").mkdir()
        (self.repo / "spec" / "x.md").write_text("x")
        commit_file(self.repo, "clients/web/a.ts", "y", "regen(web): spec 0.1.0 @ gen abc\n\n"
                    + GOOD.split("\n\n", 2)[2].replace("maintained", "generated"), env=AGENT)
        res = run_script("lint_commits.py", "--cwd", self.repo, "--range", "main~1..main")
        self.assertEqual(res.returncode, lib.EXIT_FAIL)
        self.assertIn("touches both spec/ and clients/", res.stdout)

    def test_clients_commit_needs_regen_subject(self):
        sha = commit_file(self.repo, "clients/web/a.ts", "y", GOOD, env=AGENT)
        problems = lint_commits.lint(lint_commits.load_commits(self.repo, f"{sha}~1..{sha}", "Aware")[0],
                                     CONFIG["commits"])
        self.assertTrue(any("regen(<app>)" in p for p in problems))
        self.assertTrue(any("Boundary is not generated" in p for p in problems))

    def lint_one(self, msg, name="Aware Agent (PM/test-model)", path="spec/x.md", strict=False):
        env = {**AGENT, "GIT_AUTHOR_NAME": name}
        sha = commit_file(self.repo, path, msg, msg, env=env)
        commit = lint_commits.load_commits(self.repo, f"{sha}~1..{sha}", "Aware")[0]
        return lint_commits.lint(commit, CONFIG["commits"], strict)

    def test_gate_and_feature_stage_rules(self):
        msg = GOOD.replace("Stage: P0", "Stage: G0").replace("Agent: DEV", "Agent: PM")
        self.assertEqual(self.lint_one(msg), ["gate stage G0 needs Approved-By: operator"])
        stage = GOOD.replace("Stage: P0", "Stage: S1").replace("Agent: DEV", "Agent: PM")
        self.assertIn("missing trailer Feature (stage S1)", self.lint_one(stage, path="spec/y.md"))

    def test_phase_level_gate_needs_no_feature(self):
        gate = (GOOD.replace("Stage: P0", "Stage: G1\nApproved-By: operator").replace("Agent: DEV", "Agent: PM"))
        self.assertEqual(self.lint_one(gate), [])
        for feature in ("F3", "D1", "P2"):
            self.assertEqual(self.lint_one(gate.replace("Refs:", f"Feature: {feature}\nRefs:"), path="spec/z.md"), [])
        self.assertIn("Feature 'X9' is neither a feature id nor a phase id",
                      self.lint_one(gate.replace("Refs:", "Feature: X9\nRefs:"), path="spec/w.md"))

    def test_trailer_blocks_single_canonical_split_tolerated(self):
        single = GOOD.replace("\n\nCo-Authored-By", "\nCo-Authored-By")
        self.assertEqual(lint_commits.trailer_blocks(single), 1)
        self.assertEqual(lint_commits.trailer_blocks(GOOD), 2)
        self.assertEqual(self.lint_one(GOOD, name="Aware Agent (DEV/test-model)", path="generator/s.txt"), [])
        strict = self.lint_one(GOOD, name="Aware Agent (DEV/test-model)", path="generator/t.txt", strict=True)
        self.assertEqual(strict, ["trailers are split over several paragraphs (use one final block)"])
        self.assertEqual(self.lint_one(single, name="Aware Agent (DEV/test-model)", path="generator/u.txt",
                                       strict=True), [])

    def test_human_commits_skip_trailer_rules(self):
        commit_file(self.repo, "docs/x.md", "x", "docs: human note")
        res = run_script("lint_commits.py", "--cwd", self.repo, "--range", "main~1..main")
        self.assertEqual(res.returncode, 0, res.stdout)


class Preflight(unittest.TestCase):
    def test_reports_and_exits_zero(self):
        res = run_script("preflight.py", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        tools = {r["tool"]: r["version"] for r in json.loads(res.stdout)}
        self.assertTrue(tools["python"])
        self.assertIn("android-sdk", tools)

    def test_strict_ignores_optional_gradle(self):
        import preflight
        self.assertIn("gradle", preflight.OPTIONAL)
        self.assertNotIn("python", preflight.OPTIONAL)


class HelpFlags(unittest.TestCase):
    def test_every_script_has_help(self):
        for script in sorted(SCRIPTS.glob("*.py")):
            if script.name == "awarelib.py":
                continue
            res = run_script(script.name, "--help")
            self.assertEqual(res.returncode, 0, f"{script.name}: {res.stderr}")


if __name__ == "__main__":
    unittest.main()
