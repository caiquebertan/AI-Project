#!/usr/bin/env python3
"""Plan (and optionally run) the installs that /generate needs (docs/ENVIRONMENT.md, OM-0014).

Checks come from preflight.py (shared, not duplicated). Default is a DRY RUN: print the plan, exit 1
if a required item is missing. `--install` runs the commands one at a time after asking; `--yes` skips
the prompts except for sudo commands. Shell profiles are never edited: the export lines to add are printed.

Example:
  setup_env.py [--check | --install [--yes]]
"""
from __future__ import annotations

import argparse
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

import awarelib as lib
import preflight

MIN = {"node": 22, "java": 17}                  # minimum major versions (python: 3.10, see status)
OPTIONAL = {"playwright"}                       # reported, never fails --check (best-effort probe)
SDK_PKGS = '"platform-tools" "platforms;android-35" "build-tools;35.0.0"'  # exact pins arrive at P3
NPM = {"claude": "npm install -g @anthropic-ai/claude-code", "playwright": "npx playwright install"}

# OS -> tool -> install commands. Commands starting with "sudo" are always confirmed by hand.
INSTALL = {
    "macos": {
        "python": ["brew install python@3.12"], "git": ["brew install git"],
        "node": ["brew install node@22", "brew link --overwrite --force node@22"],
        "java": ["brew install --cask temurin@17"],
        "android-sdk": ["brew install --cask android-commandlinetools",
                        f'yes | sdkmanager --sdk_root="$(brew --prefix)/share/android-commandlinetools" {SDK_PKGS}'],
    },
    "debian": {
        "python": ["sudo apt-get install -y python3"], "git": ["sudo apt-get install -y git"],
        "node": ["curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -",
                 "sudo apt-get install -y nodejs"],
        "java": ["sudo apt-get install -y openjdk-17-jdk"],
        "android-sdk": ["sudo apt-get install -y android-sdk sdkmanager",
                        f'sudo sdkmanager --sdk_root=/usr/lib/android-sdk {SDK_PKGS}'],
    },
    "windows": {
        "python": ["winget install -e --id Python.Python.3.12"], "git": ["winget install -e --id Git.Git"],
        "node": ["winget install -e --id OpenJS.NodeJS.LTS"],
        "java": ["winget install -e --id EclipseAdoptium.Temurin.17.JDK"],
        "android-sdk": ["winget install -e --id Google.AndroidStudio  (then SDK Manager: install an Android platform)"],
    },
}
HINTS = {  # unknown OS: text only, nothing is run
    "python": "https://www.python.org/downloads/", "git": "https://git-scm.com/downloads",
    "node": "https://nodejs.org/ (22 LTS, includes npm)", "npm": "installed with Node.js",
    "java": "https://adoptium.net/ (JDK 17+)",
    "android-sdk": "https://developer.android.com/studio (command-line tools, then sdkmanager)",
    "claude": NPM["claude"], "playwright": NPM["playwright"],
}
EXPORTS = {
    "macos": ['export ANDROID_HOME="$(brew --prefix)/share/android-commandlinetools"',
              'export PATH="$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"'],
    "debian": ['export ANDROID_HOME=/usr/lib/android-sdk', 'export PATH="$ANDROID_HOME/platform-tools:$PATH"'],
    "windows": ['setx ANDROID_HOME "%LOCALAPPDATA%\\Android\\Sdk"'],
}


def detect_os(system: str | None = None, os_release: str | None = None) -> str:
    system = system or platform.system()
    if system == "Darwin":
        return "macos"
    if system == "Windows":
        return "windows"
    if system == "Linux":
        text = os_release if os_release is not None else (
            Path("/etc/os-release").read_text() if Path("/etc/os-release").exists() else "")
        if re.search(r"^ID(_LIKE)?=.*(debian|ubuntu)", text, re.M):
            return "debian"
    return "unknown"


def major(version: str | None) -> int | None:
    """First number of a version line; `1.8.0` style (old JDKs) counts as the second number."""
    m = re.search(r"(\d+)(?:\.(\d+))?", version or "")
    if not m:
        return None
    return int(m.group(2)) if m.group(1) == "1" and m.group(2) else int(m.group(1))


def playwright_present(env=None, system: str | None = None, home: Path | None = None) -> str | None:
    env = os.environ if env is None else env
    home = home or Path.home()
    system = system or platform.system()
    base = env.get("PLAYWRIGHT_BROWSERS_PATH") or {
        "Darwin": str(home / "Library/Caches/ms-playwright"),
        "Windows": str(Path(env.get("LOCALAPPDATA", home / "AppData/Local")) / "ms-playwright"),
    }.get(system, str(home / ".cache/ms-playwright"))
    found = sorted(p.name for p in Path(base).glob("chromium*")) if Path(base).is_dir() else []
    return found[0] if found else None


def collect(timeout: int) -> list[dict]:
    rows = [r for r in preflight.collect(timeout) if r["tool"] not in preflight.OPTIONAL]
    rows.append({"tool": "playwright", "version": playwright_present(), "purpose": "web UI/e2e tests"})
    return rows


def status(row: dict) -> str:
    """'ok', 'missing' or 'old' for one preflight-style row."""
    v, t = row["version"], row["tool"]
    if not v:
        return "missing"
    if t == "android-sdk" and "platforms: none" in v:
        return "missing"
    if t == "python":
        m = re.search(r"(\d+)\.(\d+)", v)
        return "ok" if m and (int(m.group(1)), int(m.group(2))) >= (3, 10) else "old"
    if t in MIN and (major(v) or 0) < MIN[t]:
        return "old"
    return "ok"


def plan(rows: list[dict], os_name: str) -> list[dict]:
    """One entry per missing/old item: {tool, state, required, commands (None on unknown OS), hint}."""
    out = []
    for r in rows:
        state = status(r)
        if state == "ok":
            continue
        t = r["tool"]
        if t in NPM:
            cmds = [NPM[t]]
        elif os_name in INSTALL:
            cmds = INSTALL[os_name].get(t if t != "npm" else "node")
        else:
            cmds = None
        out.append({"tool": t, "state": state, "required": t not in OPTIONAL, "found": r["version"],
                    "commands": cmds, "hint": HINTS.get(t, "")})
    return out


def blocking(items: list[dict]) -> list[dict]:
    return [i for i in items if i["required"]]


def render(items: list[dict], os_name: str) -> str:
    if not items:
        return "environment OK: nothing to install"
    lines = [f"detected OS: {os_name}"]
    for i in items:
        found = f" (found {i['found']})" if i["found"] else ""
        lines.append(f"\n{i['tool']}: {i['state'].upper()}{found}{'' if i['required'] else ' [optional]'}")
        if i["commands"]:
            lines += [f"  $ {c}" for c in i["commands"]]
        else:
            lines.append(f"  install manually: {i['hint']}")
    if any(i["tool"] == "android-sdk" for i in items) and os_name in EXPORTS:
        lines += ["\nafter installing, add to your shell profile yourself (not edited by this script):"]
        lines += [f"  {e}" for e in EXPORTS[os_name]]
    return "\n".join(lines)


def confirm(question: str, assume_yes: bool, ask=input) -> bool:
    if assume_yes:
        return True
    return ask(f"{question} [y/N] ").strip().lower() in ("y", "yes")


def install(items: list[dict], assume_yes: bool, ask=input, run=None) -> list[str]:
    """Run each command after confirmation; sudo commands are always asked, even with --yes."""
    run = run or (lambda c: subprocess.run(c, shell=True).returncode)
    failed = []
    for i in items:
        for c in i["commands"] or []:
            if "(then" in c or not confirm(f"[{i['tool']}] run `{c}`?", assume_yes and "sudo" not in c, ask):
                print(f"  skipped: {c}")
                continue
            if run(c) != 0:
                failed.append(c)
                print(f"  failed: {c}")
                break
    return failed


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="quiet: exit code only (1 if a required item is missing)")
    mode.add_argument("--install", action="store_true", help="run the plan, asking before each command")
    p.add_argument("--yes", action="store_true", help="with --install: do not ask (sudo commands are still asked)")
    args = p.parse_args(argv)
    timeout = lib.load_config()["preflight"]["timeout_s"]
    os_name = detect_os()
    items = plan(collect(timeout), os_name)
    if args.check:
        return lib.EXIT_FAIL if blocking(items) else lib.EXIT_OK
    print(render(items, os_name))
    if args.install and items:
        if os_name == "unknown":
            print("\nunknown OS: nothing is run; follow the hints above.")
            return lib.EXIT_FAIL
        install(items, args.yes)
        items = plan(collect(timeout), os_name)
        print("\nre-check:\n" + render(items, os_name))
        print("\nopen a new terminal so PATH changes take effect, then re-run with --check.")
    elif items and not args.install:
        print("\ndry run: nothing was installed. Re-run with --install to execute (asks before each command).")
    return lib.EXIT_FAIL if blocking(items) else lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
