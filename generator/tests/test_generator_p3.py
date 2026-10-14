"""P3 generator scripts and inputs: apply_templates, build_digest, checkpoint, smoke_build,
collect_reports, the manifest additions, templates and config (design docs/planning/p3-generator-design.md)."""
import copy
import json
import os
import re
import shlex
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

from _util import CONFIG, SCRIPTS, make_repo, run_script
import apply_templates as at
import awarelib as lib
import build_digest
import check_headers
import check_trace
import checkpoint
import collect_reports
import smoke_build

HARNESS = SCRIPTS.parents[1]
TEMPLATES = HARNESS / "generator" / "templates"
VARS = {"spec_version": "9.9.9", "header": CONFIG["headers"]["header_text"].format(spec_version="9.9.9")}
ID_RE = CONFIG["trace"]["spec_id_regex"]

# CORE-TIME-003 patterns of PLAT-HOOK-015 plus the platform patterns (PLAT-ANDROID-030, PLAT-WEB-023).
TIME_PATTERNS = [
    r"\b(Africa|America|Antarctica|Arctic|Asia|Atlantic|Australia|Europe|Indian|Pacific|Etc)/[A-Za-z_+-]+",
    r"\b(UTC|GMT)\s*[+-]\s*[0-9]", r"[\"'`][+-](0[0-9]|1[0-4]):?[0-5][0-9][\"'`]",
    r"[\"'`](BRT|JST|PST|PDT|EST|EDT|CST|CDT|MST|MDT|CET|CEST|EET|BST|IST)[\"'`]", r"\bTZ\s*=", r"user\.timezone",
    r"ZoneId\.of\(", r"ZoneId\.SHORT_IDS", r"ZoneOffset\.of(Hours|HoursMinutes|HoursMinutesSeconds)?\(",
    r"TimeZone\.getTimeZone\(", r"TimeZone\.setDefault\(", r"timeZone\s*:", r"process\.env\.TZ"]


def tmpdir(test):
    t = tempfile.TemporaryDirectory()
    test.addCleanup(t.cleanup)
    return Path(t.name)


def fake_template(root: Path, operator_present=True) -> tuple[Path, dict]:
    """A tiny template set: one rendered file, one raw file, one operator-produced executable."""
    tdir = root / "tpl"
    (tdir / "kinds").mkdir(parents=True)
    (tdir / "a.kts").write_text("// {{header}}\nval v = \"{{spec_version}}\"\n")
    (tdir / "raw.json").write_text('{"x": "{{not_rendered}}"}\n')
    (tdir / "dot-gitignore").write_text("build/\n")
    if operator_present:
        (tdir / "run.sh").write_text("#!/bin/sh\necho hi\n")
    spec = {"copy": [{"src": "a.kts", "dest": "a.kts"}, {"src": "raw.json", "dest": "raw.json", "raw": True},
                     {"src": "dot-gitignore", "dest": ".gitignore"},
                     {"src": "run.sh", "dest": "run.sh", "raw": True, "operator": True, "executable": True}]}
    return tdir, spec


def android_template():
    return at.load_template("android", CONFIG)


# ------------------------------------------------------------ apply_templates
class ApplyTemplatesCopy(unittest.TestCase):
    def test_copy_renders_raw_renames_and_sets_exec_bit(self):
        root = tmpdir(self)
        tdir, spec = fake_template(root)
        out = root / "clients" / "x"
        written = at.copy_templates(tdir, spec, out, VARS)
        self.assertEqual(sorted(written), sorted([".gitignore", "a.kts", "raw.json", "run.sh"]))
        self.assertIn("from spec 9.9.9", (out / "a.kts").read_text())
        self.assertIn('"9.9.9"', (out / "a.kts").read_text())
        self.assertEqual((out / "raw.json").read_text(), '{"x": "{{not_rendered}}"}\n')
        self.assertTrue(os.access(out / "run.sh", os.X_OK))
        self.assertEqual(at.check(tdir, spec, out, VARS), [])

    def test_missing_operator_file_blocks_unless_allowed(self):
        root = tmpdir(self)
        tdir, spec = fake_template(root, operator_present=False)
        with self.assertRaises(at.TemplateError) as ctx:
            at.copy_templates(tdir, spec, root / "out", VARS)
        self.assertIn("pending: run.sh", str(ctx.exception))
        self.assertIn("smoke session A", str(ctx.exception))
        written = at.copy_templates(tdir, spec, root / "out", VARS, allow_missing=True)
        self.assertNotIn("run.sh", written)
        self.assertTrue(any("pending: run.sh" in p for p in at.check(tdir, spec, root / "out", VARS)))

    def test_unfilled_placeholder_in_rendered_file_is_an_error(self):
        root = tmpdir(self)
        tdir, spec = fake_template(root)
        (tdir / "a.kts").write_text("// {{header}} {{oops}}\n")
        with self.assertRaises(at.TemplateError):
            at.copy_templates(tdir, spec, root / "out", VARS)

    def test_check_reports_changed_missing_and_exec_bit(self):
        root = tmpdir(self)
        tdir, spec = fake_template(root)
        out = root / "out"
        at.copy_templates(tdir, spec, out, VARS)
        (out / "a.kts").write_text("// edited\n")
        (out / "raw.json").unlink()
        (out / "run.sh").chmod(0o644)
        problems = "\n".join(at.check(tdir, spec, out, VARS))
        self.assertIn("changed: a.kts", problems)
        self.assertIn("missing: raw.json", problems)
        self.assertIn("exec bit: run.sh", problems)

    def test_clean_refuses_paths_outside_root(self):
        root = tmpdir(self)
        with self.assertRaises(at.TemplateError):
            at.safe_clean(root.parent, root)
        with self.assertRaises(at.TemplateError):
            at.safe_clean(root, root)
        (root / "clients" / "x").mkdir(parents=True)
        at.safe_clean(root / "clients" / "x", root)
        self.assertFalse((root / "clients" / "x").exists())


class ApplyTemplatesKinds(unittest.TestCase):
    def setUp(self):
        self.tdir, self.spec = android_template()
        self.out = tmpdir(self)

    def kind_problems(self):
        return [p for p in at.check(self.tdir, self.spec, self.out, VARS)
                if "pending" not in p and "template-owned" not in p]

    def test_every_kind_instantiates_and_conforms(self):
        for i, kind in enumerate(self.spec["kinds"]["names"]):
            main = "app.aware.driver.MainKt" if kind == "jvm-app" else None
            dest = at.instantiate(self.tdir, self.spec, kind, f"m{i}/x", self.out, VARS, main_class=main,
                                  deps=["implementation(libs.junit)"])
            text = dest.read_text()
            self.assertNotIn("{{", text)
            self.assertTrue(text.startswith("// " + CONFIG["headers"]["marker"]))
            if "namespace =" in text:
                self.assertIn(f'namespace = "app.aware.m{i}.x"', text)
        self.assertEqual(self.kind_problems(), [])

    def test_edit_outside_deps_region_and_version_literal_are_caught(self):
        dest = at.instantiate(self.tdir, self.spec, "android-lib", "core/data", self.out, VARS)
        text = dest.read_text()
        dest.write_text(text.replace("// END deps", '    implementation("com.x:y:1.2.3")\n    // END deps'))
        self.assertTrue(any("version literal" in p for p in self.kind_problems()))
        dest.write_text(text.replace("minSdk = libs", "minSdk = 21 // libs"))
        self.assertTrue(any("differs from every kind" in p for p in self.kind_problems()))
        dest.write_text(text.replace("// BEGIN deps\n", '// BEGIN deps\n    implementation(project(":core:protocol"))\n'))
        self.assertEqual(self.kind_problems(), [])

    def test_bad_inputs_are_rejected(self):
        with self.assertRaises(at.TemplateError):
            at.instantiate(self.tdir, self.spec, "jvm-app", "tools/driver", self.out, VARS)  # no main class
        with self.assertRaises(at.TemplateError):
            at.instantiate(self.tdir, self.spec, "nope", "a", self.out, VARS)
        with self.assertRaises(at.TemplateError):
            at.instantiate(self.tdir, self.spec, "jvm-lib", "../escape", self.out, VARS)
        with self.assertRaises(at.TemplateError):
            at.instantiate(self.tdir, self.spec, "jvm-lib", "a", self.out, VARS, namespace="Bad.Name")

    def test_module_given_as_gradle_path(self):
        dest = at.instantiate(self.tdir, self.spec, "jvm-lib", ":core:protocol", self.out, VARS)
        self.assertEqual(dest, self.out / "core" / "protocol" / "build.gradle.kts")


class ApplyTemplatesSmokeAndRealTemplates(unittest.TestCase):
    def test_android_smoke_project_is_complete_and_conforms(self):
        tdir, spec = android_template()
        out = tmpdir(self)
        res = at.apply_smoke(tdir, spec, out, VARS)
        self.assertEqual(sorted(res["pending"]), sorted(["gradle/wrapper/gradle-wrapper.jar", "gradlew", "gradlew.bat"]))
        for m in spec["smoke"]["modules"]:
            self.assertTrue((out / m["module"] / "build.gradle.kts").is_file(), m["module"])
        self.assertFalse((out / "README.md").read_text().startswith("# Smoke"))
        problems = [p for p in at.check(tdir, spec, out, VARS) if "pending" not in p]
        self.assertEqual(problems, [])
        for f in out.rglob("*"):
            if f.is_file():
                self.assertNotIn("{{", f.read_text(errors="replace"), f)

    def test_web_smoke_project(self):
        tdir, spec = at.load_template("web", CONFIG)
        out = tmpdir(self)
        res = at.apply_smoke(tdir, spec, out, VARS)
        self.assertEqual(res["pending"], ["package-lock.json"])
        self.assertTrue((out / "src/app/main.tsx").is_file())
        lines = (out / "src/features/probe/Probe.test.tsx").read_text().splitlines()
        self.assertIn(CONFIG["headers"]["marker"], lines[0])
        self.assertEqual(lines[1], "// @vitest-environment jsdom")

    def test_template_sources_exist_and_headers_are_in_place(self):
        exts = set(CONFIG["headers"]["comment_extensions"])
        for app in CONFIG["apps"]:
            tdir, spec = at.load_template(app, CONFIG)
            for e in spec["copy"]:
                src = tdir / e["src"]
                if e.get("operator"):
                    continue
                self.assertTrue(src.is_file(), src)
                if not e.get("raw") and Path(e["dest"]).suffix in exts:
                    head = src.read_text().splitlines()[: CONFIG["headers"]["scan_lines"]]
                    self.assertTrue(any("{{header}}" in ln for ln in head), f"{app}: {e['src']} lacks {{{{header}}}}")

    def test_scanned_template_files_pass_the_time_zone_denylist(self):
        scanned = {"android": ["settings.gradle.kts", "build.gradle.kts", "gradle.properties",
                               "gradle/libs.versions.toml", "kinds/*.gradle.kts"],
                   "web": ["index.html", "vite.config.ts", "package.json", "tsconfig.json", "src/*"]}
        for app, globs in scanned.items():
            tdir = TEMPLATES / app
            for g in globs:
                for f in tdir.glob(g):
                    for n, line in enumerate(f.read_text().splitlines(), 1):
                        for pat in TIME_PATTERNS:
                            self.assertIsNone(re.search(pat, line), f"{f}:{n} matches {pat}")

    def test_web_package_is_exact_and_closed(self):
        pkg = json.loads((TEMPLATES / "web" / "package.json").read_text())
        self.assertEqual(sorted(pkg["dependencies"]), ["react", "react-dom"])            # PLAT-WEB-002
        for name, version in {**pkg["dependencies"], **pkg["devDependencies"]}.items():
            self.assertRegex(version, r"^\d+\.\d+\.\d+$", name)
        self.assertEqual(pkg["scripts"]["build"], "tsc --noEmit && vite build")       # PLAT-WEB-017
        self.assertIn("--reporter=junit", pkg["scripts"]["test"])                       # PLAT-WEB-016
        self.assertIn("test-results/junit.xml", pkg["scripts"]["test"])
        self.assertEqual(pkg["engines"]["node"], ">=22")

    def test_android_pins_are_marked_unverified_and_catalog_has_no_dynamic_versions(self):
        toml = (TEMPLATES / "android" / "gradle" / "libs.versions.toml").read_text()
        self.assertIn("TBD-verify-on-operator-machine", toml)
        self.assertNotRegex(toml, r'version = "[^"]*[+]|latest')
        self.assertIn("TBD-verify-on-operator-machine",
                      (TEMPLATES / "android" / "gradle" / "wrapper" / "gradle-wrapper.properties").read_text())

    def test_cli_kind_and_check(self):
        tmp, repo = make_repo()
        self.addCleanup(tmp.cleanup)
        res = run_script("apply_templates.py", "--root", repo, "--app", "android", "--kind", "jvm-lib",
                         "--module", "core/protocol")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue((repo / "clients/android/core/protocol/build.gradle.kts").is_file())
        res = run_script("apply_templates.py", "--root", repo, "--app", "android")
        self.assertEqual(res.returncode, lib.EXIT_FAIL)           # wrapper still pending in the cloud
        self.assertIn("smoke session A", res.stderr)
        res = run_script("apply_templates.py", "--root", repo, "--app", "web", "--check")
        self.assertEqual(res.returncode, lib.EXIT_FAIL)


# ------------------------------------------------------------- build_digest
GRADLE_COMPILE = """> Task :core:protocol:compileKotlin FAILED
e: file:///x/core/protocol/src/main/kotlin/A.kt:3:5 Unresolved reference 'foo'.

FAILURE: Build failed with an exception.

* What went wrong:
Execution failed for task ':core:protocol:compileKotlin'.
> A failure occurred while executing org.jetbrains.kotlin.compilerRunner.GradleCompilerRunnerWithWorkers$GradleKotlinCompilerWorkAction
   > Compilation error. See log for more details

* Try:
> Run with --stacktrace option to get the stack trace.

BUILD FAILED in 4s
"""
GRADLE_NET = """FAILURE: Build failed with an exception.

* What went wrong:
Could not resolve all files for configuration ':core:protocol:compileClasspath'.
> Could not resolve org.jetbrains.kotlinx:kotlinx-coroutines-core:1.10.2.
   > Could not get resource 'https://repo.maven.apache.org/...'.
      > Could not GET 'https://repo.maven.apache.org/...'.
         > repo.maven.apache.org: nodename nor servname provided (UnknownHostException)
"""
GRADLE_PIN = """* What went wrong:
Could not resolve all files for configuration ':app:debugRuntimeClasspath'.
> Could not find androidx.room:room-runtime:9.9.9.
  Searched in the following locations:
"""


def junit_xml(cases):
    body = []
    for cls, name, failure in cases:
        inner = f'<failure message="boom">{failure}</failure>' if failure else ""
        body.append(f'<testcase classname="{cls}" name="{name}">{inner}</testcase>')
    return f'<testsuite name="s" tests="{len(cases)}">{"".join(body)}</testsuite>'


class BuildDigest(unittest.TestCase):
    def d(self, text, reports=None):
        log = tmpdir(self) / "x.log"
        log.write_text(text)
        return build_digest.digest("android", log, CONFIG, reports=reports or [])

    def test_kotlin_compile_failure_is_code_with_blocks(self):
        d = self.d(GRADLE_COMPILE)
        self.assertEqual(d["class"], "CODE")
        self.assertIn("Unresolved reference 'foo'", d["compiler_errors"][0])
        self.assertIn("Execution failed for task", d["what_went_wrong"][0])
        self.assertNotIn("* Try:", d["what_went_wrong"][0])
        self.assertIn("Unresolved reference", d["first_error"])

    def test_network_is_env_and_missing_artifact_is_pin(self):
        self.assertEqual(self.d(GRADLE_NET)["class"], "ENV")
        self.assertEqual(self.d(GRADLE_PIN)["class"], "PIN")
        self.assertEqual(self.d("npm error code ETARGET\nnpm error notarget No matching version found for vite@99.0.0.")["class"], "PIN")
        self.assertEqual(self.d("npm error code ENOTFOUND\nnpm error network request failed")["class"], "ENV")
        self.assertEqual(self.d("SDK location not found. Define a valid SDK location with ANDROID_HOME")["class"], "ENV")

    def test_typescript_errors_are_code(self):
        d = self.d("src/core/a.ts(3,7): error TS2322: Type 'string' is not assignable to type 'number'.\n")
        self.assertEqual(d["class"], "CODE")
        self.assertEqual(len(d["compiler_errors"]), 1)

    def test_failing_tests_win_over_env_words_and_are_capped(self):
        xml = tmpdir(self) / "TEST-a.xml"
        cases = [("app.aware.T", f"CORE-X-{i:03d} case", "java.net.SocketTimeoutException: Connection timed out\n"
                  + "\n".join(f"  at frame{j}" for j in range(50))) for i in range(25)] + [("app.aware.T", "ok", None)]
        xml.write_text(junit_xml(cases))
        d = self.d("> Task :core:protocol:test FAILED\n26 tests completed, 25 failed\n", reports=[xml])
        self.assertEqual(d["class"], "CODE")
        self.assertEqual(d["failures_total"], 25)
        self.assertEqual(len(d["failures"]), build_digest.MAX_FAILURES)
        self.assertEqual(d["tests_total"], 26)
        self.assertLessEqual(len(d["failures"][0]["stack"]), build_digest.STACK_LINES)
        text = build_digest.render_text(d)
        self.assertTrue(text.endswith("class: CODE"))
        self.assertIn("CORE-X-000 case", text)

    def test_tail_is_last_80_lines_and_cli_json(self):
        d = self.d("\n".join(f"line {i}" for i in range(200)))
        self.assertEqual(len(d["tail"]), build_digest.TAIL_LINES)
        self.assertEqual(d["tail"][-1], "line 199")
        log = tmpdir(self) / "b.log"
        log.write_text(GRADLE_NET)
        res = run_script("build_digest.py", "--app", "android", "--log", log, "--reports", log.parent, "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(json.loads(res.stdout)["class"], "ENV")

    def test_reports_older_than_since_are_ignored(self):
        root = tmpdir(self)
        rep = root / "m" / "build" / "test-results" / "test" / "TEST-a.xml"
        rep.parent.mkdir(parents=True)
        rep.write_text(junit_xml([("c", "n", "x")]))
        os.utime(rep, (1000, 1000))
        globs = CONFIG["apps"]["android"]["reports"]
        self.assertEqual(build_digest.report_files(root, globs, None), [rep])
        self.assertEqual(build_digest.report_files(root, globs, 2000), [])


# --------------------------------------------------------------- checkpoint
def scripted_runner(outputs):
    """Fake runner: each call pops (exit, log text); records calls."""
    calls = []

    def run(cmd, shell, cwd, log, timeout):
        code, text = outputs.pop(0)
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(text)
        calls.append((cmd, shell, cwd, log.name))
        return code, 0.1
    run.calls = calls
    return run


class Checkpoint(unittest.TestCase):
    def setUp(self):
        self.root = tmpdir(self)
        (self.root / CONFIG["apps"]["android"]["dir"]).mkdir(parents=True)

    def go(self, cp, runner, cfg=CONFIG):
        return checkpoint.run_checkpoint("android", cp, ["./gradlew", "x"], False, cfg, self.root, runner=runner)

    def test_pass_and_log_naming(self):
        r = scripted_runner([(0, "ok")])
        verdict, record = self.go("C1", r)
        self.assertEqual(verdict, "PASS")
        self.assertEqual(r.calls[0][3], "C1-1.log")
        self.assertEqual(r.calls[0][2], self.root / "clients/android")
        saved = lib.read_json(self.root / ".work/generate/android/result.json")
        self.assertEqual(saved["checkpoints"]["C1"]["result"], "pass")
        self.assertEqual(saved["self_repair_attempts"], 0)

    def test_per_checkpoint_budget(self):
        r = scripted_runner([(1, GRADLE_COMPILE)] * 4)
        verdicts = [self.go("C1", r)[0] for _ in range(4)]
        self.assertEqual(verdicts, ["REPAIR", "REPAIR", "REPAIR", "EXHAUSTED"])
        verdict, record = self.go("C1", r)                   # refuses to run a 5th time
        self.assertEqual(verdict, "EXHAUSTED")
        self.assertEqual(len(r.calls), 4)
        self.assertEqual(record["checkpoints"]["C1"]["attempts"], CONFIG["self_repair_max"])
        self.assertEqual([c[3] for c in r.calls], ["C1-1.log", "C1-2.log", "C1-3.log", "C1-4.log"])

    def test_repair_then_pass_counts_one_attempt_and_verdict_line(self):
        r = scripted_runner([(1, GRADLE_COMPILE), (0, "ok"), (0, "ok")])
        verdict, record = self.go("C1", r)
        self.assertEqual(checkpoint.verdict_line("C1", verdict, record),
                         f"CHECKPOINT C1: REPAIR (attempt 1/{CONFIG['self_repair_max']} next; "
                         f"run total 0/{CONFIG['self_repair_total_max']})")
        self.assertEqual(self.go("C1", r)[0], "PASS")
        verdict, record = self.go("C2", r)
        self.assertEqual(record["self_repair_attempts"], 1)
        self.assertEqual(record["checkpoints"]["C2"]["attempts"], 0)

    def test_per_run_budget_spans_checkpoints(self):
        cfg = copy.deepcopy(CONFIG)
        cfg["self_repair_total_max"] = 2
        r = scripted_runner([(1, GRADLE_COMPILE)] * 6)
        self.assertEqual(self.go("C1", r, cfg)[0], "REPAIR")
        self.assertEqual(self.go("C1", r, cfg)[0], "REPAIR")      # attempt 1 (total 1)
        self.assertEqual(self.go("C2", r, cfg)[0], "REPAIR")
        self.assertEqual(self.go("C2", r, cfg)[0], "EXHAUSTED")   # attempt 2 (total 2) fails: none left
        self.assertEqual(self.go("C1", r, cfg)[0], "EXHAUSTED")   # refused without running
        self.assertEqual(len(r.calls), 4)

    def test_env_and_pin_spend_no_attempt(self):
        r = scripted_runner([(1, GRADLE_NET), (1, GRADLE_NET), (1, GRADLE_PIN)])
        self.assertEqual(self.go("C0", r)[0], "ENV_FAILURE")
        verdict, record = self.go("C0", r)
        self.assertEqual(verdict, "ENV_FAILURE")
        self.assertEqual(record["self_repair_attempts"], 0)
        verdict, record = self.go("C1", r)
        self.assertEqual(verdict, "BLOCKED_PIN")
        self.assertEqual(record["checkpoints"]["C1"]["result"], "pin")
        self.assertEqual(record["checkpoints"]["C0"]["runs"][0]["class"], "ENV")

    def test_cli_start_run_status_and_usage(self):
        (self.root / "clients" / "web").mkdir(parents=True)
        res = run_script("checkpoint.py", "--root", self.root, "--app", "web", "--start", "--model-id", "m")
        self.assertEqual(res.returncode, 0, res.stderr)
        res = run_script("checkpoint.py", "--root", self.root, "--app", "web", "--checkpoint", "C1", "--",
                         "python3", "-c", "import os; print(os.getcwd())")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue(res.stdout.strip().endswith("CHECKPOINT C1: PASS"))
        log = (self.root / ".work/generate/web/logs/C1-1.log").read_text()
        self.assertIn(str((self.root / "clients/web").resolve()), log)
        res = run_script("checkpoint.py", "--root", self.root, "--app", "web", "--checkpoint", "C2", "--",
                         "python3", "-c", "import sys; print('error TS1005: x'); sys.exit(2)")
        self.assertEqual(res.returncode, lib.EXIT_FAIL)
        self.assertIn("CHECKPOINT C2: REPAIR", res.stdout.splitlines()[-1])
        self.assertIn("class: CODE", res.stdout)
        res = run_script("checkpoint.py", "--root", self.root, "--app", "web", "--status")
        self.assertIn("C2", res.stdout)
        self.assertIn("model m", res.stdout)
        res = run_script("checkpoint.py", "--root", self.root, "--app", "web", "--checkpoint", "C3",
                         "--config-cmd", "build", "--", "ls")
        self.assertEqual(res.returncode, lib.EXIT_USAGE)
        res = run_script("checkpoint.py", "--root", self.root, "--app", "web", "--checkpoint", "C3")
        self.assertEqual(res.returncode, lib.EXIT_USAGE)


# ----------------------------------------------------------------- manifest
class ManifestP3Fields(unittest.TestCase):
    def test_origin_checkpoints_and_attempts(self):
        tmp, repo = make_repo()
        self.addCleanup(tmp.cleanup)
        app_dir = repo / CONFIG["apps"]["web"]["dir"]
        (app_dir / "src").mkdir(parents=True)
        (app_dir / "package.json").write_text("{}\n")
        (app_dir / "src" / "a.ts").write_text(f"// {CONFIG['headers']['marker']} from spec 0.1.0\n")
        result = {"claude_code_version": "2.1.300 (Claude Code)", "self_repair_attempts": 2,
                  "checkpoints": {"C1": {"attempts": 2, "result": "pass", "runs": []}}}
        rpath = repo / "result.json"
        rpath.write_text(json.dumps(result))
        res = run_script("check_headers.py", "--root", repo, "--app", "web", "--write-manifest",
                         "--spec-version", "0.1.0", "--model-id", "claude-opus-5-5", "--result", rpath)
        self.assertEqual(res.returncode, 0, res.stderr)
        m = lib.read_json(app_dir / ".generated")
        origins = {f["path"]: f["origin"] for f in m["files"]}
        self.assertEqual(origins, {"package.json": "template", "src/a.ts": "model"})
        self.assertEqual(m["checkpoints"], {"C1": {"attempts": 2, "result": "pass"}})
        self.assertEqual(m["self_repair_attempts"], 2)
        self.assertEqual(lib.validate(m, lib.load_schema("manifest.schema.json")), [])
        self.assertEqual(check_headers.check_app(app_dir, CONFIG), ("checked", []))


# -------------------------------------------------------------- smoke_build
class SmokeBuild(unittest.TestCase):
    def setUp(self):
        self.root = tmpdir(self)
        (self.root / "spec").mkdir()
        (self.root / "spec" / "README.md").write_text("**Version:** 0.1.1\n")
        self.smoke = self.root / CONFIG["generate"]["smoke_dir"]

    def fake_runner(self, junit_cases, fail=()):
        calls = []

        def run(cmd, shell, cwd, env, log):
            name = log.stem
            calls.append((name, cmd, cwd, env))
            log.parent.mkdir(parents=True, exist_ok=True)
            log.write_text(f"$ {cmd}\n")
            if name == "wrapper":
                for rel in smoke_build.WRAPPER_FILES:
                    (cwd / rel).parent.mkdir(parents=True, exist_ok=True)
                    (cwd / rel).write_text("wrapper " + rel)
            if name == "install":
                (cwd / "package-lock.json").write_text("{}\n")
            if name == "test":
                for rel, cases in junit_cases.items():
                    (cwd / rel).parent.mkdir(parents=True, exist_ok=True)
                    (cwd / rel).write_text(junit_xml(cases))
            if name in fail:
                log.write_text("e: file:///A.kt:1:1 Unresolved reference 'x'.\n")
                return 1
            return 0
        run.calls = calls
        return run

    def test_dry_run_lists_steps_without_touching_disk(self):
        res = run_script("smoke_build.py", "--root", self.root, "--app", "all", "--dry-run")
        self.assertEqual(res.returncode, 0, res.stderr)
        for word in ("gradle wrapper --gradle-version", "assembleDebug", "-Paware.repoRoot=", "npm install",
                     "AWARE_REPO_ROOT=", "npm test", "send-back.zip"):
            self.assertIn(word, res.stdout)
        self.assertFalse(self.smoke.exists())

    def test_android_run_bootstraps_wrapper_checks_ids_and_bundles(self):
        p = smoke_build.plan_app("android", CONFIG, self.root, self.smoke)
        runner = self.fake_runner({"core/protocol/build/test-results/test/TEST-a.xml":
                                   [("app.aware.core.protocol.ProbeTest", "PLAT-ANDROID-023 smoke id", None)]})
        jar_sha = lib.sha256_bytes(b"wrapper gradle/wrapper/gradle-wrapper.jar")
        fetch = lambda url: jar_sha if url.endswith("wrapper.jar.sha256") else "d" * 64  # noqa: E731
        s = smoke_build.run_app(p, CONFIG, self.root, self.smoke, runner=runner, fetch=fetch)
        self.assertEqual([c[0] for c in runner.calls], ["wrapper", "build", "test"])
        self.assertTrue(s["ok"], s)
        self.assertTrue(s["gradle"]["wrapper_jar_verified"])
        self.assertEqual(s["gradle"]["distributionSha256Sum"], "d" * 64)
        self.assertTrue((self.smoke / "android" / "gradlew").is_file())
        self.assertTrue((self.smoke / "android" / "core/protocol/build.gradle.kts").is_file())
        z = smoke_build.bundle([s], [p], self.smoke, probe_fn=lambda cmd: "v")
        names = zipfile.ZipFile(z).namelist()
        self.assertIn("summary.json", names)
        self.assertIn("android/gradle/wrapper/gradle-wrapper.jar", names)
        self.assertIn("logs/android/test.log", names)

    def test_web_run_creates_lockfile_and_fails_without_ids(self):
        p = smoke_build.plan_app("web", CONFIG, self.root, self.smoke)
        runner = self.fake_runner({"test-results/junit.xml": [("src/core/probe.test.ts", "core probe > no id here", None)]})
        s = smoke_build.run_app(p, CONFIG, self.root, self.smoke, runner=runner, fetch=lambda url: None)
        self.assertEqual([c[0] for c in runner.calls], ["install", "build", "test"])
        self.assertEqual(runner.calls[1][3]["AWARE_REPO_ROOT"], str(self.root))
        self.assertTrue(s["produced"]["package-lock.json"])
        self.assertFalse(s["reports"]["ok"])
        self.assertFalse(s["ok"])

    def test_failed_build_is_digested(self):
        p = smoke_build.plan_app("web", CONFIG, self.root, self.smoke)
        runner = self.fake_runner({}, fail=("build",))
        s = smoke_build.run_app(p, CONFIG, self.root, self.smoke, runner=runner, fetch=lambda url: None)
        build = next(st for st in s["steps"] if st["step"] == "build")
        self.assertEqual(build["class"], "CODE")
        self.assertFalse(s["ok"])


# ---------------------------------------------------------- collect_reports
class CollectReports(unittest.TestCase):
    def test_flattens_copies_and_feeds_check_trace(self):
        root = tmpdir(self)
        a = root / "clients/android"
        for rel in ("core/protocol/build/test-results/test/TEST-x.xml",
                    "feature/f/build/test-results/testDebugUnitTest/TEST-x.xml"):
            (a / rel).parent.mkdir(parents=True)
            (a / rel).write_text(junit_xml([("app.aware.T", "CORE-SEQ-002 orders", None)]))
        w = root / "clients/web/test-results/junit.xml"
        w.parent.mkdir(parents=True)
        w.write_text(junit_xml([("src/core/a.test.ts", "core > CORE-SEQ-002 orders", None)]))
        res = run_script("collect_reports.py", "--root", root, "--feature", "D1", "--trace-features", "F1,F2,F3")
        self.assertEqual(res.returncode, 0, res.stderr)
        out = sorted(p.name for p in (root / "docs/runs/D1/reports/android").iterdir())
        self.assertEqual(len(out), 2)                                   # same file name, no overwrite
        self.assertIn("--junit android=docs/runs/D1/reports/android", res.stdout)
        self.assertIn("--feature F1,F2,F3", res.stdout)
        self.assertIn("--acceptance docs/runs/D1/acceptance.md", res.stdout)
        tests = check_trace.parse_junit(root / "docs/runs/D1/reports/web/test-results__junit.xml")
        self.assertIn("CORE-SEQ-002", tests[0]["name"])

    def test_missing_reports_fail(self):
        root = tmpdir(self)
        res = run_script("collect_reports.py", "--root", root, "--feature", "D1", "--app", "web")
        self.assertEqual(res.returncode, lib.EXIT_FAIL)
        self.assertIn("no reports for web", res.stderr)


# ------------------------------------------------------------------- config
class GeneratorConfigP3(unittest.TestCase):
    def test_models_and_budgets(self):
        self.assertEqual(CONFIG["generate_model"], "claude-opus-5-5")
        self.assertEqual(CONFIG["generate_model_fallback"], "claude-sonnet-5-5")
        self.assertEqual((CONFIG["self_repair_max"], CONFIG["self_repair_total_max"]), (3, 12))
        for app in CONFIG["apps"].values():
            self.assertFalse(app["build"].startswith("TBD") or app["test"].startswith("TBD"))
            self.assertTrue(app["reports"])

    def test_claude_flags_are_bounded_allowlisted_and_never_mix_models(self):
        flags = shlex.split(CONFIG["generate"]["claude_flags"])
        for flag in ("--max-turns", "--max-budget-usd"):
            self.assertGreater(float(flags[flags.index(flag) + 1]), 0)
        self.assertEqual(flags[flags.index("--permission-prompts") + 1], "none")
        self.assertEqual(flags[flags.index("--permission-mode") + 1], "acceptEdits")
        for banned in ("--fallback-model", "--dangerously-skip-permissions", "--model"):
            self.assertNotIn(banned, flags)
        allowed = flags[flags.index("--allowedTools") + 1:]
        self.assertTrue(allowed and all(not a.startswith("--") for a in allowed))   # list runs to the end
        self.assertIn("Bash(python3 generator/scripts/*)", allowed)

    def test_failure_patterns_compile(self):
        for pat in CONFIG["generate"]["pin_patterns"]:
            re.compile(pat)
        self.assertIn("UnknownHostException", CONFIG["generate"]["env_patterns"])

    def test_generate_prompt_uses_the_p3_scripts(self):
        tmp, repo = make_repo()
        self.addCleanup(tmp.cleanup)
        (repo / "spec").mkdir()
        (repo / "spec" / "README.md").write_text("**Version:** 1.2.3\n")
        conv = repo / CONFIG["apps"]["android"]["conventions"]
        conv.parent.mkdir(parents=True)
        conv.write_text("# c\n")
        res = run_script("render_prompt.py", "--generate", "android", "--root", repo, "--print")
        self.assertEqual(res.returncode, 0, res.stderr)
        for word in ("apply_templates.py --app android --clean", "checkpoint.py --app android --checkpoint",
                     "--config-cmd build", "apply_templates.py --app android --check", "--result",
                     f"{CONFIG['self_repair_max']} attempts per checkpoint and {CONFIG['self_repair_total_max']} per run",
                     ".work/generate/android/plan.md", "EXHAUSTED", "BLOCKED_PIN"):
            self.assertIn(word, res.stdout)

    def test_conventions_list_checkpoints_and_are_linted(self):
        self.assertIn("generator/conventions", CONFIG["prompt_lint"]["paths"])
        for app in CONFIG["apps"]:
            text = (HARNESS / CONFIG["apps"][app]["conventions"]).read_text()
            self.assertIn(f"checkpoint.py --app {app} --checkpoint", text)
            self.assertIn("C0", text)
        self.assertEqual(run_script("lint_prompts.py").returncode, 0)


if __name__ == "__main__":
    unittest.main()
