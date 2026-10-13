#!/usr/bin/env python3
"""Prompt genericity lint (E-EVOL-1).

Generator prompts must not name features: feature knowledge belongs in spec/.
Scans the configured paths (default generator/prompts/ and the /generate
command) for denylisted nouns (word match, case-insensitive, simple plurals
and verb forms). Fenced blocks whose info string contains the word
"example" (e.g. ```example or ```md example) are ignored.

Example:
  lint_prompts.py [paths ...]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import awarelib as lib


def build_pattern(rules: dict) -> re.Pattern:
    terms = "|".join(re.escape(t) for t in sorted(rules["denylist"], key=len, reverse=True))
    suffixes = "|".join(re.escape(s) for s in rules["suffixes"])
    return re.compile(rf"(?<![A-Za-z0-9])(?:{terms})(?:{suffixes})?(?![A-Za-z0-9])", re.IGNORECASE)


def lint_text(text: str, pattern: re.Pattern, example_word: str) -> list[tuple[int, str]]:
    hits, fence, skipping = [], None, False
    for lineno, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        marker = re.match(r"^(`{3,}|~{3,})(.*)$", stripped)
        if marker and fence is None:
            fence, skipping = marker.group(1), example_word in marker.group(2).lower().split()
            continue
        if marker and fence and stripped.startswith(fence) and not marker.group(2).strip():
            fence, skipping = None, False
            continue
        if skipping:
            continue
        hits += [(lineno, m.group(0)) for m in pattern.finditer(line)]
    return hits


def files_for(paths: list[Path]) -> list[Path]:
    out = []
    for p in paths:
        out += sorted(p.rglob("*.md")) if p.is_dir() else ([p] if p.exists() else [])
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("paths", nargs="*", help="files or directories (default: config prompt_lint.paths)")
    args = p.parse_args(argv)
    rules = lib.load_config()["prompt_lint"]
    paths = [Path(x) for x in args.paths] or [lib.HARNESS_ROOT / x for x in rules["paths"]]
    pattern = build_pattern(rules)
    files = files_for(paths)
    total = 0
    for f in files:
        for lineno, word in lint_text(f.read_text(encoding="utf-8"), pattern, rules["example_fence_word"]):
            total += 1
            print(f"{f}:{lineno}: feature noun '{word}'")
    print(f"lint_prompts: {len(files)} file(s), {total} finding(s)")
    return lib.EXIT_FAIL if total else lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
