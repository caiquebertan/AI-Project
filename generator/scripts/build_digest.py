#!/usr/bin/env python3
"""Compact digest of a failed build/test log, plus one failure class (generator design §3.2).

Prints, from the log and the app's JUnit XML reports:
  * Gradle "* What went wrong:" blocks, Kotlin/Java compiler errors (`e: ...`, `error: ...`),
    TypeScript `error TS...` lines;
  * failing tests from JUnit XML (message + 30 stack lines each, at most 20 failures);
  * the last 80 lines of the log;
and a final line `class: CODE|ENV|PIN`:
  CODE  compiler errors or failing tests (whatever else the log says), or nothing recognised;
  ENV   toolchain / network / SDK problem (config generate.env_patterns, substrings);
  PIN   a template version that does not resolve (config generate.pin_patterns, regexes).
Only CODE spends a self-repair attempt (decision 0017).

Example:
  build_digest.py --app android --log .work/generate/android/logs/C1-1.log
  build_digest.py --app web --log build.log --reports clients/web/test-results --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import awarelib as lib

MAX_FAILURES = 20
STACK_LINES = 30
TAIL_LINES = 80
MAX_BLOCK_LINES = 40
COMPILER = re.compile(r"^(?:e: .+|.*\berror: .+|.*\berror TS\d+: .+)$")
GRADLE_TEST_FAIL = re.compile(r"^\s*\d+ tests? completed, \d+ failed|There were failing tests", re.M)
VITEST_FAIL = re.compile(r"^\s*(?:Test Files|Tests)\s+\d+ failed", re.M)


def what_went_wrong(text: str) -> list[str]:
    blocks, lines = [], text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "* What went wrong:":
            block = []
            for nxt in lines[i + 1:]:
                if nxt.startswith("* Try:") or nxt.startswith("* Get more help") or nxt.startswith("BUILD FAILED"):
                    break
                block.append(nxt)
            blocks.append("\n".join(block[:MAX_BLOCK_LINES]).strip())
    return blocks


def compiler_errors(text: str) -> list[str]:
    seen, out = set(), []
    for line in text.splitlines():
        s = line.rstrip()
        if COMPILER.match(s) and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def report_files(app_dir: Path, globs: list[str], since: float | None) -> list[Path]:
    files = set()
    for g in globs:
        files.update(p for p in app_dir.glob(g) if p.is_file() and "node_modules" not in p.parts)
    return sorted(p for p in files if since is None or p.stat().st_mtime >= since)


def junit_failures(paths: list[Path]) -> tuple[list[dict], int]:
    failures, total = [], 0
    for path in paths:
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError):
            continue
        for case in root.iter("testcase"):
            total += 1
            bad = next((c for c in case if c.tag in ("failure", "error")), None)
            if bad is None:
                continue
            stack = (bad.text or "").strip().splitlines()[:STACK_LINES]
            failures.append({"classname": case.get("classname", ""), "name": case.get("name", ""),
                             "kind": bad.tag, "message": (bad.get("message") or "").strip()[:500],
                             "stack": stack, "report": str(path)})
    return failures, total


def classify(text: str, failures: list[dict], cfg: dict) -> str:
    gen = cfg["generate"]
    if failures or compiler_errors(text) or GRADLE_TEST_FAIL.search(text) or VITEST_FAIL.search(text):
        return "CODE"
    if any(p in text for p in gen["env_patterns"]):
        return "ENV"
    if any(re.search(p, text) for p in gen["pin_patterns"]):
        return "PIN"
    return "CODE"


def first_error_line(digest: dict) -> str:
    for key in ("compiler_errors", "what_went_wrong"):
        if digest[key]:
            return digest[key][0].splitlines()[0].strip()
    if digest["failures"]:
        f = digest["failures"][0]
        return f"{f['classname']} {f['name']}: {f['message']}".strip()
    for line in reversed(digest["tail"]):
        if line.strip():
            return line.strip()
    return "(empty log)"


def digest(app: str, log: Path, cfg: dict, reports: list[Path] | None = None, since: float | None = None,
           root: Path | None = None) -> dict:
    text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    if reports is None:
        app_dir = (root or lib.HARNESS_ROOT) / cfg["apps"][app]["dir"]
        reports = report_files(app_dir, cfg["apps"][app].get("reports", []), since) if app_dir.is_dir() else []
    else:
        expanded = []
        for r in reports:
            expanded += sorted(r.rglob("*.xml")) if r.is_dir() else [r]
        reports = expanded
    failures, total = junit_failures(reports)
    out = {"app": app, "log": str(log), "what_went_wrong": what_went_wrong(text),
           "compiler_errors": compiler_errors(text), "failures": failures[:MAX_FAILURES],
           "failures_total": len(failures), "tests_total": total,
           "tail": text.splitlines()[-TAIL_LINES:], "class": classify(text, failures, cfg)}
    out["first_error"] = first_error_line(out)
    return out


def render_text(d: dict) -> str:
    lines = [f"== build digest: {d['app']} {d['log']} =="]
    if d["what_went_wrong"]:
        lines.append(f"-- what went wrong ({len(d['what_went_wrong'])}) --")
        lines += d["what_went_wrong"]
    if d["compiler_errors"]:
        lines.append(f"-- compiler errors ({len(d['compiler_errors'])}) --")
        lines += d["compiler_errors"][:60]
    if d["failures_total"]:
        lines.append(f"-- failing tests ({d['failures_total']} of {d['tests_total']}; first {len(d['failures'])}) --")
        for f in d["failures"]:
            lines.append(f"[{f['kind']}] {f['classname']} > {f['name']}: {f['message']}")
            lines += [f"    {s}" for s in f["stack"]]
    lines.append(f"-- last {len(d['tail'])} log lines --")
    lines += d["tail"]
    lines.append(f"first error: {d['first_error']}")
    lines.append(f"class: {d['class']}")
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--app", required=True, help="app name from config")
    p.add_argument("--log", required=True, help="build or test log")
    p.add_argument("--reports", action="append", help="JUnit XML file or dir (default: config apps.<app>.reports)")
    p.add_argument("--since", type=float, help="ignore default reports older than this epoch time")
    p.add_argument("--root", help="repo root (default: harness checkout)")
    p.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = p.parse_args(argv)
    cfg = lib.load_config()
    if args.app not in cfg["apps"]:
        lib.die(f"unknown app '{args.app}'", lib.EXIT_USAGE)
    d = digest(args.app, Path(args.log), cfg, [Path(r) for r in args.reports] if args.reports else None,
               args.since, lib.repo_root(args.root))
    print(json.dumps(d, indent=2) if args.json else render_text(d))
    return lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
