#!/usr/bin/env python3
"""Collect client JUnit reports for check_trace.py (generator design §4; decision 0017 Q9).

Copies every report matching config apps.<app>.reports (globs relative to clients/<app>/) into
docs/runs/<feature>/reports/<app>/, flattening paths (`core/protocol/build/.../TEST-x.xml` ->
`core__protocol__build__...__TEST-x.xml`) so module reports never overwrite each other, then
prints the check_trace.py command that reads them (or runs it with --run-trace).

Example (on the operator's machine, after the gate commands ran):
  collect_reports.py --feature D1 --trace-features F1,F2,F3 [--app all] [--run-trace]
Exit 1 if an app has no report.
"""
from __future__ import annotations

import argparse
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import awarelib as lib
import build_digest


def collect(app: str, cfg: dict, root: Path, dest_root: Path) -> list[Path]:
    app_dir = root / cfg["apps"][app]["dir"]
    dest = dest_root / app
    if dest.is_dir():
        for old in dest.glob("*.xml"):
            old.unlink()
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    for src in build_digest.report_files(app_dir, cfg["apps"][app].get("reports", []), None) if app_dir.is_dir() else []:
        target = dest / "__".join(src.relative_to(app_dir).parts)
        shutil.copy2(src, target)
        copied.append(target)
    return copied


def trace_command(features: str, junit: dict[str, Path], acceptance: Path, root: Path) -> list[str]:
    cmd = ["python3", "generator/scripts/check_trace.py", "--feature", features]
    for app, path in junit.items():
        rel = path.relative_to(root) if root in path.parents else path
        cmd += ["--junit", f"{app}={rel.as_posix()}"]
    rel_acc = acceptance.relative_to(root) if root in acceptance.parents else acceptance
    return cmd + ["--write", "--acceptance", rel_acc.as_posix()]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--feature", required=True, help="delivery id whose run folder receives the reports (e.g. D1)")
    p.add_argument("--trace-features", help="features passed to check_trace.py (default: --feature)")
    p.add_argument("--app", default="all", help="app name from config, or 'all'")
    p.add_argument("--root", help="repo root (default: harness checkout)")
    p.add_argument("--run-trace", action="store_true", help="run check_trace.py after copying")
    args = p.parse_args(argv)
    cfg = lib.load_config()
    root = lib.repo_root(args.root)
    apps = list(cfg["apps"]) if args.app == "all" else [args.app]
    if any(a not in cfg["apps"] for a in apps):
        lib.die(f"unknown app in {apps} (config apps: {', '.join(cfg['apps'])})", lib.EXIT_USAGE)
    run_dir = root / "docs" / "runs" / args.feature
    dest_root = run_dir / "reports"
    missing, junit = [], {}
    for app in apps:
        copied = collect(app, cfg, root, dest_root)
        print(f"{app}: {len(copied)} report(s) -> {dest_root / app}")
        junit[app] = dest_root / app
        if not copied:
            missing.append(app)
    cmd = trace_command(args.trace_features or args.feature, junit, run_dir / "acceptance.md", root)
    print("check_trace: " + " ".join(shlex.quote(c) for c in cmd))
    if missing:
        print(f"collect_reports: no reports for {', '.join(missing)} (run the gate commands first)", file=sys.stderr)
        return lib.EXIT_FAIL
    if args.run_trace:
        return subprocess.run([sys.executable, *cmd[1:]], cwd=root).returncode
    return lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
