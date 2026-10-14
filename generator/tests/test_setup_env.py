"""setup_env planning logic with fakes: no installs, no network."""
import tempfile
import unittest
from pathlib import Path

import _util  # noqa: F401  (puts generator/scripts on sys.path)
import setup_env as se


def row(tool, version):
    return {"tool": tool, "version": version, "purpose": ""}


GOOD = [row("python", "Python 3.12.1"), row("git", "git version 2.43"), row("node", "v22.3.0"),
        row("npm", "10.8.1"), row("java", 'openjdk version "21.0.5"'),
        row("android-sdk", "/sdk (platforms: android-35)"), row("claude", "1.0 (Claude Code)"),
        row("playwright", "chromium-1100")]


def with_(**kw):
    return [row(r["tool"], kw.get(r["tool"].replace("-", "_"), r["version"])) for r in GOOD]


class Detect(unittest.TestCase):
    def test_os(self):
        self.assertEqual(se.detect_os("Darwin"), "macos")
        self.assertEqual(se.detect_os("Windows"), "windows")
        self.assertEqual(se.detect_os("Linux", "ID=ubuntu\nID_LIKE=debian"), "debian")
        self.assertEqual(se.detect_os("Linux", "ID=fedora"), "unknown")
        self.assertEqual(se.detect_os("FreeBSD"), "unknown")

    def test_major(self):
        self.assertEqual(se.major("v22.3.0"), 22)
        self.assertEqual(se.major('openjdk version "1.8.0_392"'), 8)
        self.assertEqual(se.major('openjdk version "21.0.1" 2023'), 21)
        self.assertIsNone(se.major("present"))


class Plan(unittest.TestCase):
    def test_all_ok(self):
        self.assertEqual(se.plan(GOOD, "macos"), [])
        self.assertIn("OK", se.render([], "macos"))

    def test_old_and_missing(self):
        items = {i["tool"]: i for i in se.plan(with_(node="v20.1.0", java=None, android_sdk="/s (platforms: none)"), "debian")}
        self.assertEqual(items["node"]["state"], "old")
        self.assertEqual(items["java"]["state"], "missing")
        self.assertEqual(items["android-sdk"]["state"], "missing")
        self.assertIn("sudo apt-get install -y openjdk-21-jdk", items["java"]["commands"])
        self.assertTrue(all(i["required"] for i in items.values()))

    def test_python_compared_as_major_minor(self):
        self.assertEqual(se.plan(with_(python="Python 3.9.18"), "macos")[0]["state"], "old")
        self.assertEqual(se.plan(with_(python="Python 3.10.0"), "macos"), [])

    def test_per_os_commands(self):
        for os_name, needle in (("macos", "brew install"), ("debian", "apt-get"), ("windows", "winget")):
            git = se.plan(with_(git=None), os_name)[0]
            self.assertIn(needle, git["commands"][0])

    def test_npm_follows_node_and_claude_uses_npm(self):
        self.assertEqual(se.plan(with_(npm=None), "macos")[0]["commands"][0], "brew install node@22")
        self.assertEqual(se.plan(with_(claude=None), "windows")[0]["commands"], [se.NPM["claude"]])

    def test_unknown_os_hints_only(self):
        item = se.plan(with_(java=None), "unknown")[0]
        self.assertIsNone(item["commands"])
        self.assertIn("adoptium", se.render([item], "unknown"))

    def test_playwright_is_not_blocking(self):
        items = se.plan(with_(playwright=None), "macos")
        self.assertEqual(items[0]["tool"], "playwright")
        self.assertEqual(se.blocking(items), [])
        self.assertEqual(len(se.blocking(se.plan(with_(git=None), "macos"))), 1)

    def test_android_exports_printed_not_applied(self):
        out = se.render(se.plan(with_(android_sdk=None), "debian"), "debian")
        self.assertIn("export ANDROID_HOME=", out)
        self.assertIn("not edited", out)


class Install(unittest.TestCase):
    ITEMS = [{"tool": "x", "commands": ["echo a", "sudo echo b", "echo c"]}]

    def test_yes_still_asks_for_sudo(self):
        ran, asked = [], []
        def ask(q):
            asked.append(q)
            return "n"
        failed = se.install(self.ITEMS, True, ask=ask, run=lambda c: ran.append(c) or 0)
        self.assertEqual(ran, ["echo a", "echo c"])
        self.assertEqual(len(asked), 1)
        self.assertEqual(failed, [])

    def test_decline_runs_nothing_and_failure_stops_item(self):
        ran = []
        se.install(self.ITEMS, False, ask=lambda q: "", run=ran.append)
        self.assertEqual(ran, [])
        failed = se.install(self.ITEMS, False, ask=lambda q: "y", run=lambda c: 1)
        self.assertEqual(failed, ["echo a"])


class Playwright(unittest.TestCase):
    def test_cache_probe(self):
        with tempfile.TemporaryDirectory() as d:
            env = {"PLAYWRIGHT_BROWSERS_PATH": d}
            self.assertIsNone(se.playwright_present(env))
            (Path(d) / "chromium-1100").mkdir()
            self.assertEqual(se.playwright_present(env), "chromium-1100")


if __name__ == "__main__":
    unittest.main()
