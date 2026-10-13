#!/usr/bin/env python3
"""Count changed lines for the REV model rule (WORKFLOW §6.2).

changed_lines = insertions + deletions from `git diff --numstat base...head`,
excluding lockfiles, the Gradle wrapper, binaries and `.generated` manifests.
Exclusions live in generator/config/generator.json ("count_lines").

Examples:
  count_lines.py --base main --head HEAD
  git diff --numstat a...b | count_lines.py --numstat-file -
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from pathlib import PurePosixPath

import awarelib as lib


def parse_numstat(text: str) -> list[dict]:
    """Parse `git diff --numstat` lines; binary files have added/deleted = None."""
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        added, deleted, path = line.split("\t", 2)
        rows.append({"path": path,
                     "added": None if added == "-" else int(added),
                     "deleted": None if deleted == "-" else int(deleted)})
    return rows


def exclusion_reason(row: dict, rules: dict) -> str | None:
    if row["added"] is None or row["deleted"] is None:
        return "binary"
    path = row["path"]
    if PurePosixPath(path).name in rules["exclude_names"]:
        return "excluded name"
    if any(fnmatch.fnmatchcase(path, g) for g in rules["exclude_globs"]):
        return "excluded glob"
    return None


def count(rows: list[dict], rules: dict) -> tuple[int, list[dict]]:
    """Return (changed_lines, rows annotated with 'excluded')."""
    total, out = 0, []
    for row in rows:
        reason = exclusion_reason(row, rules)
        out.append({**row, "excluded": reason})
        if reason is None:
            total += row["added"] + row["deleted"]
    return total, out


def default_base(cwd, cfg: dict) -> str:
    return lib.git(["merge-base", cfg["base_branch"], "HEAD"], cwd).strip()


def numstat(base: str, head: str, cwd, paths: list[str] | None = None) -> str:
    return lib.git(["diff", "--numstat", "--no-renames", f"{base}...{head}", "--", *(paths or [])], cwd)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", help="base ref (default: merge-base of config base_branch and HEAD)")
    p.add_argument("--head", default="HEAD")
    p.add_argument("--cwd", default=".", help="git working tree to diff in")
    p.add_argument("--numstat-file", help="read numstat from a file ('-' = stdin) instead of git")
    p.add_argument("--json", action="store_true", help="print per-file detail as JSON")
    args = p.parse_args(argv)
    cfg = lib.load_config()
    if args.numstat_file:
        text = sys.stdin.read() if args.numstat_file == "-" else open(args.numstat_file, encoding="utf-8").read()
    else:
        text = numstat(args.base or default_base(args.cwd, cfg), args.head, args.cwd)
    total, rows = count(parse_numstat(text), cfg["count_lines"])
    if args.json:
        print(json.dumps({"changed_lines": total, "numstat": rows}, indent=2))
    else:
        print(total)
    return lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
