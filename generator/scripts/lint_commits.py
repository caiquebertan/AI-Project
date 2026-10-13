#!/usr/bin/env python3
"""Commit attribution lint (E-PIPE-3; rules in WORKFLOW §8, values in config "commits").

Checks agent-authored commits (author `Aware Agent (<ROLE>/<model>)`) for:
  * required trailers (Area, Boundary, Authored-By-Role, Agent, Model), Agent/Model
    matching the author, valid Boundary / Authored-By-Role / Refs values;
  * Stage for pipeline roles; Feature for feature stages; Approved-By at gates;
  * commits touching clients/ are `regen(<app>): ...` with Boundary: generated.
Checks every commit in range for the rule that no commit touches both spec/ and clients/.

Canonical form: ALL trailers in one final block (git reads only the last paragraph as
trailers). Trailers split over several trailing paragraphs are still understood so existing
commits pass; --strict-trailers reports them. Feature is required at feature stages (S0-S7b),
optional at gates (a phase-level gate such as `Stage: G1` has none); when present it is a
feature id (F1..) or a phase id (P0..P8).

Examples:
  lint_commits.py                      # every Aware Agent commit reachable from HEAD
  lint_commits.py --range main..HEAD   # every commit in the range
"""
from __future__ import annotations

import argparse
import re
import sys

import awarelib as lib

TRAILER_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*): (.+)$")
SEP_FIELD, SEP_RECORD = "\x1f", "\x1e"


def trailer_blocks(body: str) -> int:
    """Number of trailing paragraphs made only of `Key: value` lines (1 = canonical)."""
    paragraphs = [p for p in re.split(r"\n\s*\n", body.strip()) if p.strip()]
    n = 0
    for para in reversed(paragraphs[1:]):
        if not all(TRAILER_RE.match(ln.strip()) for ln in para.strip().splitlines()):
            break
        n += 1
    return n


def parse_trailers(body: str) -> dict[str, list[str]]:
    paragraphs = [p for p in re.split(r"\n\s*\n", body.strip()) if p.strip()]
    trailers: dict[str, list[str]] = {}
    for para in reversed(paragraphs[1:]):  # paragraph 0 is the subject
        lines = para.strip().splitlines()
        if not all(TRAILER_RE.match(ln.strip()) for ln in lines):
            break
        for ln in lines:
            key, val = TRAILER_RE.match(ln.strip()).groups()
            trailers.setdefault(key, []).append(val.strip())
    return trailers


def load_commits(cwd, rev_range: str | None, author_prefix: str) -> list[dict]:
    args = ["log", f"--format=%H{SEP_FIELD}%an{SEP_FIELD}%B{SEP_RECORD}"]
    args += [rev_range] if rev_range else [f"--author=^{author_prefix}", "HEAD"]
    commits = []
    for rec in lib.git(args, cwd).split(SEP_RECORD):
        rec = rec.strip("\n")
        if not rec:
            continue
        sha, author, body = rec.split(SEP_FIELD, 2)
        files = lib.git(["show", "--name-only", "--format=", "--no-renames", sha], cwd).split()
        commits.append({"sha": sha, "author": author, "body": body, "subject": body.splitlines()[0] if body else "",
                        "files": files})
    return commits


def lint(commit: dict, rules: dict, strict_trailers: bool = False) -> list[str]:
    problems = []
    touched = [d for d in rules["exclusive_dirs"] if any(f.startswith(d) for f in commit["files"])]
    if len(touched) > 1:
        problems.append(f"touches both {' and '.join(touched)}")
    m = re.match(rules["agent_author_regex"], commit["author"])
    if not m:
        return problems  # human commits: only the directory rule applies
    t = parse_trailers(commit["body"])
    if strict_trailers and trailer_blocks(commit["body"]) > 1:
        problems.append("trailers are split over several paragraphs (use one final block)")
    one = {k: v[0] for k, v in t.items()}
    for key in rules["required_trailers"]:
        if key not in t:
            problems.append(f"missing trailer {key}")
    if one.get("Agent") and one["Agent"] != m["role"]:
        problems.append(f"Agent trailer {one['Agent']} != author role {m['role']}")
    if one.get("Model") and one["Model"] != m["model"]:
        problems.append(f"Model trailer {one['Model']} != author model {m['model']}")
    if one.get("Boundary") and one["Boundary"] not in rules["boundary_values"]:
        problems.append(f"Boundary '{one['Boundary']}' not in {rules['boundary_values']}")
    if one.get("Authored-By-Role") and one["Authored-By-Role"] not in rules["role_values"]:
        problems.append(f"Authored-By-Role '{one['Authored-By-Role']}' not in {rules['role_values']}")
    for ref in (r.strip() for v in t.get("Refs", []) for r in v.split(",")):
        if not re.match(rules["refs_regex"], ref):
            problems.append(f"bad Refs value '{ref}'")
    stage = one.get("Stage", "")
    if m["role"] in rules["stage_roles"] and not stage:
        problems.append(f"missing trailer Stage (required for {m['role']})")
    if stage and re.match(rules["feature_stage_regex"], stage) and "Feature" not in t:
        problems.append(f"missing trailer Feature (stage {stage})")
    if one.get("Feature") and not re.match(rules["feature_id_regex"], one["Feature"]):
        problems.append(f"Feature '{one['Feature']}' is neither a feature id nor a phase id")
    if stage and re.match(rules["gate_stage_regex"], stage) and one.get("Approved-By") != "operator":
        problems.append(f"gate stage {stage} needs Approved-By: operator")
    if any(f.startswith(rules["generated_dir"]) for f in commit["files"]):
        if not re.match(rules["generated_subject_regex"], commit["subject"]):
            problems.append("touches clients/ but subject is not regen(<app>): ...")
        if one.get("Boundary") != "generated":
            problems.append("touches clients/ but Boundary is not generated")
    return problems


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--range", help="git rev range, e.g. main..HEAD (default: all Aware Agent commits)")
    p.add_argument("--cwd", default=".", help="repository to inspect")
    p.add_argument("--strict-trailers", action="store_true", help="also fail trailers split over several paragraphs")
    args = p.parse_args(argv)
    rules = lib.load_config()["commits"]
    commits = load_commits(args.cwd, args.range, rules["agent_author_prefix"])
    bad = 0
    for c in commits:
        problems = lint(c, rules, args.strict_trailers)
        if problems:
            bad += 1
            print(f"FAIL {c['sha'][:10]} {c['subject']}")
            for prob in problems:
                print(f"  - {prob}")
    print(f"{len(commits) - bad}/{len(commits)} commit(s) OK")
    return lib.EXIT_FAIL if bad else lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
