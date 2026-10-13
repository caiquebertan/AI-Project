#!/usr/bin/env python3
"""Clean regeneration check (S6b; evals E-PIPE-1, E-BOUND-1).

Per app:
  1. fresh checkout of --ref (git worktree under .work/wt/, or --clone)
  2. delete clients/<app>
  3. run the generate command from config (default: claude -p "/generate {app}" --model {model})
  4. run the app's build and test commands from config inside clients/<app>
  5. boundary check: `git status --porcelain` shows changes only under clients/<app>/
  6. write a JSON report to .work/regen/ and remove the checkout (unless --keep)

--dry-run prints the steps without executing anything. Until P3 pins the
model and build/test commands (values starting with "TBD"), a real run fails
loudly before touching anything.

Example:
  regen_check.py --app all --dry-run
"""
from __future__ import annotations

import argparse
import datetime as dt
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

import awarelib as lib

TBD = "TBD"


def plan(app: str, cfg: dict, root: Path, ref: str, clone: bool, stamp: str, generate_cmd: str | None) -> dict:
    a = cfg["apps"][app]
    wt = root / cfg["regen"]["worktree_dir"] / f"regen-{app}-{stamp}"
    model = cfg["generate_model"]
    checkout = (f"git clone --quiet --no-hardlinks {shlex.quote(str(root))} {shlex.quote(str(wt))} && "
                f"git -C {shlex.quote(str(wt))} checkout --quiet --detach {shlex.quote(ref)}") if clone else \
        f"git worktree add --detach {shlex.quote(str(wt))} {shlex.quote(ref)}"
    return {
        "app": app, "worktree": wt, "app_dir": a["dir"], "clone": clone, "model": model,
        "steps": [
            ("checkout", checkout, root),
            ("delete", f"rm -rf {shlex.quote(a['dir'])}", wt),
            ("generate", (generate_cmd or cfg["regen"]["generate_cmd"]).format(app=app, model=model), wt),
            ("build", a["build"], wt / a["dir"]),
            ("test", a["test"], wt / a["dir"]),
        ],
    }


def unconfigured(p: dict) -> list[str]:
    issues = []
    if str(p["model"]).startswith(TBD):
        issues.append(f"generate_model is '{p['model']}' (pinned at P3)")
    for name, cmd, _ in p["steps"]:
        if cmd.startswith(TBD):
            issues.append(f"{p['app']} {name} command is '{cmd}'")
    return issues


def boundary_violations(wt: Path, app_dir: str) -> list[str]:
    lines = lib.git(["status", "--porcelain", "--untracked-files=all"], wt).splitlines()
    paths = [ln[3:].split(" -> ")[-1] for ln in lines if ln.strip()]
    return [p for p in paths if not p.startswith(app_dir.rstrip("/") + "/")]


def execute(p: dict, root: Path, keep: bool) -> dict:
    report = {"app": p["app"], "model": p["model"], "worktree": str(p["worktree"]), "steps": [], "ok": False}
    try:
        for name, cmd, cwd in p["steps"]:
            start = time.monotonic()
            res = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
            report["steps"].append({"step": name, "cmd": cmd, "exit": res.returncode,
                                    "seconds": round(time.monotonic() - start, 1),
                                    "tail": (res.stdout + res.stderr)[-2000:]})
            print(f"  [{p['app']}] {name}: exit {res.returncode}")
            if res.returncode != 0:
                return report
            if name == "generate":
                outside = boundary_violations(p["worktree"], p["app_dir"])
                report["boundary_violations"] = outside
                if outside:
                    print(f"  [{p['app']}] E-BOUND-1 FAIL: generate wrote outside {p['app_dir']}: {outside[:5]}")
                    return report
        report["ok"] = True
        return report
    finally:
        if not keep and p["worktree"].exists():
            if p["clone"]:
                shutil.rmtree(p["worktree"], ignore_errors=True)
            else:
                lib.git(["worktree", "remove", "--force", str(p["worktree"])], root, check=False)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--app", default="all", help="app name from config, or 'all'")
    ap.add_argument("--ref", default="HEAD", help="commit to check out (default HEAD)")
    ap.add_argument("--root", help="repo root (default: harness checkout)")
    ap.add_argument("--clone", action="store_true", help="use a fresh clone instead of a worktree (P7)")
    ap.add_argument("--generate-cmd", help="override config regen.generate_cmd ({app}, {model} substituted)")
    ap.add_argument("--keep", action="store_true", help="keep the checkout for inspection")
    ap.add_argument("--dry-run", action="store_true", help="print the steps, execute nothing")
    args = ap.parse_args(argv)
    cfg = lib.load_config()
    root = lib.repo_root(args.root)
    apps = list(cfg["apps"]) if args.app == "all" else [args.app]
    unknown = [a for a in apps if a not in cfg["apps"]]
    if unknown:
        lib.die(f"unknown app(s) {unknown} (config apps: {', '.join(cfg['apps'])})", lib.EXIT_USAGE)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    plans = [plan(a, cfg, root, args.ref, args.clone, stamp, args.generate_cmd) for a in apps]

    if args.dry_run:
        for p in plans:
            print(f"# regen-check {p['app']} (model {p['model']})")
            for i, (name, cmd, cwd) in enumerate(p["steps"], 1):
                print(f"{i}. {name:<8} (cwd {cwd}) $ {cmd}")
            print(f"{len(p['steps']) + 1}. boundary  git status --porcelain must only list {p['app_dir']}/ "
                  "(checked right after generate)")
            print(f"{len(p['steps']) + 2}. cleanup   remove {p['worktree']}")
            for issue in unconfigured(p):
                print(f"   ! not runnable yet: {issue}")
        return lib.EXIT_OK

    issues = [i for p in plans for i in unconfigured(p)]
    if issues:
        lib.die("regen-check: generator not configured:\n  - " + "\n  - ".join(issues))
    reports = [execute(p, root, args.keep) for p in plans]
    out = root / cfg["regen"]["report_dir"] / f"regen-{stamp}.json"
    lib.write_json_atomic(out, {"ref": args.ref, "created_at": lib.now_iso(), "reports": reports})
    ok = all(r["ok"] for r in reports)
    print(f"regen-check {'PASS' if ok else 'FAIL'}; report {out}")
    return lib.EXIT_OK if ok else lib.EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
