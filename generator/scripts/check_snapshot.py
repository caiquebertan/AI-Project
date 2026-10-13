#!/usr/bin/env python3
"""Self-check every agent runs first (WORKFLOW §6.3).

Passes when the worktree's HEAD equals the snapshot's head_sha, the worktree
is clean, and diff.patch still matches patch_sha256. Otherwise prints
`STALE_DIFF: <reason>` and exits 3; the agent then ends with STALE_DIFF.

Example:
  check_snapshot.py --feature F1 --app web
  check_snapshot.py --meta .work/F1/web/diff.meta.json
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import awarelib as lib
from snapshot_diff import snapshot_dir


def check(meta_path: Path) -> list[str]:
    if not meta_path.exists():
        return [f"no snapshot at {meta_path}"]
    meta = lib.read_json(meta_path)
    worktree = Path(meta["worktree"])
    problems = []
    try:
        head = lib.git_head(worktree)
        if head != meta["head_sha"]:
            problems.append(f"HEAD {head[:12]} != head_sha {meta['head_sha'][:12]}")
        if not lib.git_porcelain_clean(worktree):
            problems.append("worktree has uncommitted changes")
    except RuntimeError as exc:
        problems.append(str(exc))
    patch = meta_path.parent / meta.get("patch", "diff.patch")
    if not meta.get("split") and (not patch.exists() or lib.sha256_file(patch) != meta["patch_sha256"]):
        problems.append("diff.patch missing or modified since snapshot")
    return problems


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--meta", help="path to diff.meta.json")
    p.add_argument("--feature")
    p.add_argument("--app")
    p.add_argument("--root", help="data root for .work/ (default: harness checkout)")
    args = p.parse_args(argv)
    if args.meta:
        meta_path = Path(args.meta)
    elif args.feature and args.app:
        meta_path = snapshot_dir(lib.repo_root(args.root), args.feature, args.app) / "diff.meta.json"
    else:
        lib.die("pass --meta or --feature and --app", lib.EXIT_USAGE)
    problems = check(meta_path)
    if problems:
        print("STALE_DIFF: " + "; ".join(problems))
        return lib.EXIT_STALE
    print(f"OK snapshot fresh ({lib.read_json(meta_path)['head_sha'][:12]})")
    return lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
