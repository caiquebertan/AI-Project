#!/usr/bin/env python3
"""Report toolchain versions before P3 / regen (WORKFLOW §5.3).

Informative: always exits 0 unless --strict, which exits 1 when a required tool is missing
(required tools: docs/ENVIRONMENT.md; gradle is optional).

Example:
  preflight.py [--json] [--strict]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import awarelib as lib

# (name, command, purpose). `java -version` prints to stderr; both streams are read.
TOOLS = [
    ("python", [sys.executable, "--version"], "harness scripts, server, protocol tests"),
    ("git", ["git", "--version"], "snapshots, worktrees, regen-check"),
    ("node", ["node", "--version"], "web client build"),
    ("npm", ["npm", "--version"], "web client build"),
    ("java", ["java", "-version"], "Android build (JDK)"),
    ("gradle", ["gradle", "--version"], "optional: the generated project ships a wrapper"),
    ("claude", ["claude", "--version"], "/generate and /pipeline"),
]


# Tools that --strict does not require (the generated Android project ships a Gradle wrapper).
OPTIONAL = {"gradle"}


def probe(cmd: list[str], timeout: int) -> str | None:
    if not shutil.which(cmd[0]) and not Path(cmd[0]).exists():
        return None
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    lines = [ln.strip() for ln in (res.stdout + res.stderr).splitlines()
             if ln.strip() and not ln.startswith("Picked up")]  # JVM env-var notices
    return next((ln for ln in lines if any(ch.isdigit() for ch in ln)), lines[0] if lines else "present")


def android_sdk() -> str | None:
    home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not home or not Path(home).is_dir():
        return None
    platforms = sorted(p.name for p in (Path(home) / "platforms").glob("android-*"))
    return f"{home} (platforms: {', '.join(platforms) or 'none'})"


def collect(timeout: int) -> list[dict]:
    rows = [{"tool": n, "version": probe(c, timeout), "purpose": why} for n, c, why in TOOLS]
    rows.append({"tool": "android-sdk", "version": android_sdk(), "purpose": "Android build (ANDROID_HOME)"})
    return rows


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true", help="exit 1 if any tool is missing")
    args = p.parse_args(argv)
    rows = collect(lib.load_config()["preflight"]["timeout_s"])
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        for r in rows:
            print(f"{r['tool']:<12} {r['version'] or 'MISSING':<50} {r['purpose']}")
    missing = [r["tool"] for r in rows if not r["version"] and r["tool"] not in OPTIONAL]
    return lib.EXIT_FAIL if (args.strict and missing) else lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
