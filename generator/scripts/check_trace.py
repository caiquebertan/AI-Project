#!/usr/bin/env python3
"""Acceptance and spec-coverage check (S6; evals E-PM-1, E-PM-3, E-QA-1).

Reads docs/product/TRACEABILITY.md (columns: BR/SC id | spec id | AC id |
scope | test id | status; rows grouped under `## <feature>` headings) and
test reports (JUnit XML, Playwright JSON). A test "carries" an id when the id
appears in its full name (class + name, or suite path + title + tags).

  * AC status: met when every listed test id matches at least one test and
    all matching tests passed; otherwise unmet with a reason.
  * Spec coverage: a rule is a spec id DEFINED on a MUST line under spec/, i.e. a bold id
    opening a list item or table row (`- **CORE-X-001** ... MUST ...`); ids merely cited
    in a rule or scenario do not count. Each rule applies to a set of apps (android, web,
    server) and needs a passing test carrying its id for each of them. The apps come from an
    optional `[apps: android, web]` marker on the definition line, else from the file
    (config trace.file_apps, matched on the file name: client-behavior.md = both clients,
    server-behavior.md = server, spec/platform/android.md = android, ..., default
    trace.default_apps = android, web, server; protocol.md therefore needs all three).
    Reports are tagged with `--junit APP=path`, `--playwright APP=path`; an untagged path
    counts for every app. Uncovered rules are reported as (spec id, app) pairs.

Exit 0 when every considered AC is met (or there are none), 1 otherwise.

Examples:
  check_trace.py --junit android=clients/android/app/build/test-results --junit server=server/report.xml \\
      --playwright web=tests/web-e2e/report.json
  check_trace.py --feature F1 --write --acceptance docs/runs/F1/acceptance.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import awarelib as lib

COLUMNS = ["br", "spec", "ac", "scope", "test", "status"]


# ------------------------------------------------------------- traceability
def parse_trace(text: str) -> list[dict]:
    rows, feature = [], None
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            feature = line[3:].split()[0] if line[3:].split() else None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.lstrip().startswith("|") else []
        if len(cells) != len(COLUMNS) or cells[0].lower().startswith("br/sc") or set(cells[0]) <= set("-: "):
            continue
        row = dict(zip(COLUMNS, cells))
        row.update(feature=feature, line=lineno,
                   tests=[t.strip() for t in re.split(r"[,\s]+", row["test"]) if t.strip()])
        rows.append(row)
    return rows


def write_status(text: str, rows: list[dict]) -> str:
    lines = text.splitlines()
    for row in rows:
        cells = [row[c] for c in COLUMNS]
        lines[row["line"] - 1] = "| " + " | ".join(cells) + " |"
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------- reports
def _files(paths: list[str], suffix: str) -> list[Path]:
    out = []
    for p in map(Path, paths or []):
        out += sorted(p.rglob(f"*{suffix}")) if p.is_dir() else [p]
    return out


def split_tag(value: str, apps: list[str]) -> tuple[str | None, str]:
    """`web=path` -> ("web", "path"); untagged or unknown prefix -> (None, value)."""
    tag, sep, rest = value.partition("=")
    return (tag, rest) if sep and tag in apps else (None, value)


def load_tests(junit: list[str], playwright: list[str], apps: list[str]) -> list[dict]:
    """Parse tagged/untagged report arguments; each test gets `apps` (None = counts for all)."""
    tests = []
    for values, suffix, parse in ((junit, ".xml", parse_junit), (playwright, ".json", parse_playwright)):
        for value in values:
            tag, path = split_tag(value, apps)
            for f in _files([path], suffix):
                for t in parse(f):
                    t["apps"] = None if tag is None else [tag]
                    tests.append(t)
    return tests


def parse_junit(path: Path) -> list[dict]:
    tests = []
    for case in ET.parse(path).getroot().iter("testcase"):
        if case.find("failure") is not None or case.find("error") is not None:
            status = "failed"
        elif case.find("skipped") is not None:
            status = "skipped"
        else:
            status = "passed"
        tests.append({"name": f"{case.get('classname', '')} {case.get('name', '')}".strip(), "status": status,
                      "source": str(path)})
    return tests


def parse_playwright(path: Path) -> list[dict]:
    tests = []

    def walk(suite, trail):
        trail = trail + ([suite["title"]] if suite.get("title") else [])
        for spec in suite.get("specs", []):
            statuses = [t.get("status") for t in spec.get("tests", [])]
            if statuses and all(s == "skipped" for s in statuses):
                status = "skipped"
            else:
                status = "passed" if spec.get("ok") else "failed"
            name = " > ".join(trail + [spec.get("title", "")]) + " " + " ".join(spec.get("tags", []))
            tests.append({"name": name.strip(), "status": status, "source": str(path)})
        for child in suite.get("suites", []):
            walk(child, trail)

    for suite in lib.read_json(path).get("suites", []):
        walk(suite, [])
    return tests


def carries(name: str, ident: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(ident)}(?![0-9])", name) is not None


# ------------------------------------------------------------------ checks
def evaluate_rows(rows: list[dict], tests: list[dict], scope_re: str) -> None:
    for row in rows:
        problems = []
        if not row["spec"]:
            problems.append("no spec id")
        if not re.match(scope_re, row["scope"]):
            problems.append(f"bad scope '{row['scope']}'")
        if not row["tests"]:
            problems.append("no test id")
        for tid in row["tests"]:
            hits = [t for t in tests if carries(t["name"], tid)]
            if not hits:
                problems.append(f"{tid}: no test found")
            elif any(t["status"] == "failed" for t in hits):
                problems.append(f"{tid}: failed")
            elif not any(t["status"] == "passed" for t in hits):
                problems.append(f"{tid}: skipped")
        row["status"] = "met" if not problems else "unmet"
        row["reason"] = "; ".join(problems)


APPS_MARKER = re.compile(r"\[apps:\s*([a-z0-9,\s-]+)\]")
KEYWORD = re.compile(r"\b(?:MUST|SHOULD|MAY)\b")


def definition_re(id_re: str) -> re.Pattern:
    """A rule is defined where its bold id opens a list item or a table row."""
    return re.compile(rf"^\s*(?:[-*]\s+|\|\s*)\*\*({id_re})\*\*")


def spec_rules(spec_dir: Path, cfg: dict) -> list[dict]:
    """Defined rule ids with the apps each applies to. Only definitions carrying
    cfg['must_keyword'] are rules; see defined_ids for every definition."""
    defn, rules, seen = definition_re(cfg["spec_id_regex"]), [], set()
    if spec_dir.is_dir():
        for path in sorted(spec_dir.rglob("*.md")):
            for line in path.read_text(encoding="utf-8").splitlines():
                m = defn.match(line)
                if not m or cfg["must_keyword"] not in line or m.group(1) in seen:
                    continue
                marker = APPS_MARKER.search(line)
                apps = [a.strip() for a in marker.group(1).split(",") if a.strip()] if marker else \
                    cfg["file_apps"].get(path.name, cfg["default_apps"])
                seen.add(m.group(1))
                rules.append({"id": m.group(1), "file": path.name, "apps": apps})
    return rules


def defined_ids(spec_dir: Path, id_re: str) -> set[str]:
    """Every id defined under spec_dir, whatever its keyword."""
    defn, ids = definition_re(id_re), set()
    for path in sorted(spec_dir.rglob("*.md")) if spec_dir.is_dir() else []:
        for line in path.read_text(encoding="utf-8").splitlines():
            m = defn.match(line)
            if m:
                ids.add(m.group(1))
    return ids


def spec_coverage(rules: list[dict], tests: list[dict]) -> dict:
    def passed(rule_id: str, app: str) -> bool:
        return any(t["status"] == "passed" and (t.get("apps") is None or app in t["apps"])
                   and carries(t["name"], rule_id) for t in tests)

    pairs = [(r["id"], app) for r in rules for app in r["apps"]]
    uncovered = [(i, a) for i, a in pairs if not passed(i, a)]
    bad_ids = {i for i, _ in uncovered}
    ids = [r["id"] for r in rules]
    covered = [i for i in ids if i not in bad_ids]
    pct = 100.0 if not ids else round(100.0 * len(covered) / len(ids), 1)
    return {"total": len(ids), "covered": covered, "missing": [i for i in ids if i in bad_ids], "percent": pct,
            "pairs_total": len(pairs), "pairs_covered": len(pairs) - len(uncovered),
            "uncovered": [list(p) for p in uncovered]}


def acceptance_md(feature: str | None, rows: list[dict], cov: dict) -> str:
    lines = [f"# Acceptance — {feature or 'all features'}", "",
             "Rendered by `generator/scripts/check_trace.py` (S6).", "",
             "| AC id | Spec id | Scope | Test id | Status | Reason |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['ac']} | {r['spec']} | {r['scope']} | {r['test']} | {r['status']} | {r['reason']} |" for r in rows]
    lines += ["", f"Spec-id coverage (E-QA-1): {len(cov['covered'])}/{cov['total']} ({cov['percent']}%)"]
    if cov["missing"]:
        lines.append("Uncovered (spec id, app): " + ", ".join(f"({i}, {a})" for i, a in cov["uncovered"]))
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", help="data root (default: harness checkout)")
    p.add_argument("--trace", help="traceability file (default from config)")
    p.add_argument("--spec-dir", help="spec directory (default from config)")
    p.add_argument("--feature", help="only rows under this `## <feature>` heading")
    p.add_argument("--junit", action="append", default=[],
                   help="JUnit XML file or directory, optionally APP=path with APP android|web|server (repeatable)")
    p.add_argument("--playwright", action="append", default=[], help="Playwright JSON report, optionally APP=path (repeatable)")
    p.add_argument("--write", action="store_true", help="write the status column back to the trace file")
    p.add_argument("--acceptance", help="write acceptance.md here")
    p.add_argument("--strict-spec", action="store_true", help="also fail when spec-id coverage < 100%%")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    cfg = lib.load_config()["trace"]
    root = lib.repo_root(args.root)
    trace_path = Path(args.trace) if args.trace else root / cfg["file"]
    text = trace_path.read_text(encoding="utf-8") if trace_path.exists() else ""

    tests = load_tests(args.junit, args.playwright, cfg["coverage_apps"])
    all_rows = parse_trace(text)
    rows = [r for r in all_rows if args.feature is None or r["feature"] == args.feature]
    evaluate_rows(rows, tests, cfg["scope_regex"])
    cov = spec_coverage(spec_rules(Path(args.spec_dir) if args.spec_dir else root / cfg["spec_dir"], cfg), tests)

    if args.write and text:
        trace_path.write_text(write_status(text, rows), encoding="utf-8")
    if args.acceptance:
        Path(args.acceptance).parent.mkdir(parents=True, exist_ok=True)
        Path(args.acceptance).write_text(acceptance_md(args.feature, rows, cov), encoding="utf-8")
    unmet = [r for r in rows if r["status"] != "met"]
    if args.json:
        print(json.dumps({"rows": [{k: r[k] for k in ("ac", "spec", "scope", "test", "status", "reason")}
                                   for r in rows], "tests": len(tests), "spec_coverage": cov}, indent=2))
    else:
        print(f"ACs: {len(rows) - len(unmet)}/{len(rows)} met; tests parsed: {len(tests)}; "
              f"spec-id coverage: {len(cov['covered'])}/{cov['total']} ({cov['percent']}%)")
        for r in unmet:
            print(f"  UNMET {r['ac'] or '(no AC id)'} [{r['scope']}]: {r['reason']}")
        if cov["missing"]:
            print(f"  uncovered (spec id, app) pairs: {len(cov['uncovered'])}/{cov['pairs_total']}: "
                  + ", ".join(f"({i}, {a})" for i, a in cov["uncovered"]))
    failed = bool(unmet) or (args.strict_spec and cov["missing"])
    return lib.EXIT_FAIL if failed else lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
