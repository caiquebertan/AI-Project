"""count_lines exclusions, snapshot_diff output and check_snapshot staleness (WORKFLOW §6)."""
import unittest

from _util import CONFIG, commit_file, git, make_repo, run_script
import awarelib as lib
import count_lines
from check_snapshot import check
from snapshot_diff import take_snapshot

RULES = CONFIG["count_lines"]


class CountLines(unittest.TestCase):
    def test_exclusions(self):
        numstat = "\n".join([
            "10\t5\tsrc/main.kt",
            "300\t20\tclients/web/package-lock.json",
            "7\t0\tclients/android/gradle/wrapper/gradle-wrapper.properties",
            "-\t-\tclients/android/gradle/wrapper/gradle-wrapper.jar",
            "-\t-\tassets/logo.png",
            "40\t0\tclients/android/gradlew",
            "12\t3\tclients/web/.generated",
            "1\t1\tclients/web/yarn.lock",
            "2\t2\tdocs/notes.md",
        ])
        total, rows = count_lines.count(count_lines.parse_numstat(numstat), RULES)
        self.assertEqual(total, 15 + 4)
        reasons = {r["path"]: r["excluded"] for r in rows}
        self.assertEqual(reasons["assets/logo.png"], "binary")
        self.assertEqual(reasons["clients/web/.generated"], "excluded name")
        self.assertEqual(reasons["clients/android/gradle/wrapper/gradle-wrapper.properties"], "excluded glob")
        self.assertIsNone(reasons["src/main.kt"])

    def test_cli_on_stdin_and_empty(self):
        res = run_script("count_lines.py", "--numstat-file", "/dev/null")
        self.assertEqual(res.stdout.strip(), "0")


class Snapshot(unittest.TestCase):
    def setUp(self):
        self.tmp, self.repo = make_repo()
        self.addCleanup(self.tmp.cleanup)
        git(self.repo, "checkout", "-q", "-b", "feat/F1")
        commit_file(self.repo, "src/a.py", "print(1)\nprint(2)\n", "add a")
        commit_file(self.repo, "pkg/package-lock.json", "{}\n" * 50, "lock")

    def snap(self, stage="S4"):
        return take_snapshot(self.repo, "F1", "web", stage, self.repo, base="main")

    def meta_path(self):
        return self.repo / ".work" / "F1" / "web" / "diff.meta.json"

    def test_snapshot_fields_and_fresh_check(self):
        meta = self.snap()
        for key in ("base_sha", "head_sha", "worktree", "porcelain_clean", "patch_sha256", "numstat",
                    "changed_lines", "created_at", "stage"):
            self.assertIn(key, meta)
        self.assertEqual(meta["changed_lines"], 2)  # lockfile excluded
        self.assertTrue(meta["porcelain_clean"])
        self.assertEqual(meta["head_sha"], git(self.repo, "rev-parse", "HEAD").strip())
        self.assertTrue((self.meta_path().parent / "diff.patch").exists())
        self.assertEqual(check(self.meta_path()), [])
        res = run_script("check_snapshot.py", "--meta", self.meta_path())
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_new_commit_makes_snapshot_stale(self):
        self.snap()
        commit_file(self.repo, "src/b.py", "x\n", "more")
        res = run_script("check_snapshot.py", "--meta", self.meta_path())
        self.assertEqual(res.returncode, lib.EXIT_STALE)
        self.assertIn("STALE_DIFF", res.stdout)

    def test_dirty_worktree_is_stale(self):
        self.snap()
        (self.repo / "src" / "a.py").write_text("changed\n")
        self.assertTrue(any("uncommitted" in p for p in check(self.meta_path())))

    def test_tampered_patch_is_stale(self):
        self.snap()
        (self.meta_path().parent / "diff.patch").write_text("edited")
        self.assertTrue(any("modified" in p for p in check(self.meta_path())))

    def test_missing_snapshot_is_stale(self):
        self.assertTrue(check(self.repo / "nope" / "diff.meta.json"))

    def test_large_diff_is_split_per_file(self):
        big = CONFIG["limits"]["snapshot_split_lines"] + 1
        commit_file(self.repo, "src/big.txt", "line\n" * big, "big")
        meta = self.snap()
        out = self.meta_path().parent
        self.assertTrue(meta["split"])
        self.assertFalse((out / "diff.patch").exists())
        listing = (out / "diff.files.txt").read_text()
        self.assertIn("src/big.txt", listing)
        self.assertTrue((out / "patches" / "src" / "big.txt.patch").exists())
        self.assertEqual(check(self.meta_path()), [])

    def test_cli_dirty_exit_code(self):
        (self.repo / "dirty.txt").write_text("x")
        res = run_script("snapshot_diff.py", "--root", self.repo, "--feature", "F1", "--app", "web",
                         "--stage", "S4", "--base", "main")
        self.assertEqual(res.returncode, lib.EXIT_STALE)
        self.assertFalse(lib.read_json(self.meta_path())["porcelain_clean"])


if __name__ == "__main__":
    unittest.main()
