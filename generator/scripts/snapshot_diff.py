#!/usr/bin/env python3
"""Write the commit-addressed diff snapshot for a stage handoff (WORKFLOW §6).

Output in <root>/.work/<feature>/<app>/:
  diff.patch      full `git diff base...head` (only when changed_lines <= split threshold)
  diff.meta.json  {base_sha, head_sha, worktree, porcelain_clean, patch_sha256, numstat,
                   changed_lines, created_at, stage, split, ...}
Above limits.snapshot_split_lines changed lines it writes diff.files.txt plus
one patch per file under patches/ instead, and agents read the files.

ORC commits before snapshotting. A dirty worktree is recorded and the script
exits non-zero unless --allow-dirty.

Example:
  snapshot_diff.py --feature F1 --app web --stage S4 --base main
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import awarelib as lib
import count_lines


def snapshot_dir(root: Path, feature: str, app: str) -> Path:
    return root / ".work" / feature / app


def take_snapshot(root: Path, feature: str, app: str, stage: str, worktree: Path,
                  base: str | None = None, head: str = "HEAD", cfg: dict | None = None) -> dict:
    cfg = cfg or lib.load_config()
    base_sha = lib.git(["rev-parse", base or count_lines.default_base(worktree, cfg)], worktree).strip()
    head_sha = lib.git(["rev-parse", head], worktree).strip()
    rng = f"{base_sha}...{head_sha}"
    patch = lib.git(["diff", "--no-renames", "--binary", rng], worktree)
    changed, rows = count_lines.count(count_lines.parse_numstat(count_lines.numstat(base_sha, head_sha, worktree)),
                                      cfg["count_lines"])
    split = changed > cfg["limits"]["snapshot_split_lines"]

    out = snapshot_dir(root, feature, app)
    out.mkdir(parents=True, exist_ok=True)
    for stale in ("diff.patch", "diff.files.txt"):
        (out / stale).unlink(missing_ok=True)
    shutil.rmtree(out / "patches", ignore_errors=True)

    meta = {
        "feature": feature, "app": app, "stage": stage,
        "base_sha": base_sha, "head_sha": head_sha, "worktree": str(worktree.resolve()),
        "porcelain_clean": lib.git_porcelain_clean(worktree),
        "patch_sha256": lib.sha256_bytes(patch.encode("utf-8")),
        "numstat": rows, "changed_lines": changed, "created_at": lib.now_iso(), "split": split,
    }
    if split:
        listing = []
        for row in rows:
            rel = Path("patches") / (row["path"] + ".patch")
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            (out / rel).write_text(lib.git(["diff", "--no-renames", "--binary", rng, "--", row["path"]], worktree),
                                   encoding="utf-8")
            listing.append(f"{row['path']}\t+{row['added'] if row['added'] is not None else '-'}"
                           f"\t-{row['deleted'] if row['deleted'] is not None else '-'}\t{rel}")
        (out / "diff.files.txt").write_text("\n".join(listing) + "\n", encoding="utf-8")
        meta.update(files_list="diff.files.txt", patches_dir="patches")
    else:
        (out / "diff.patch").write_text(patch, encoding="utf-8")
        meta["patch"] = "diff.patch"
    lib.write_json_atomic(out / "diff.meta.json", meta)
    return meta


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--feature", required=True)
    p.add_argument("--app", required=True)
    p.add_argument("--stage", required=True, help="stage that will consume the snapshot, e.g. S4")
    p.add_argument("--base", help="base ref (default: merge-base of config base_branch and HEAD)")
    p.add_argument("--head", default="HEAD")
    p.add_argument("--worktree", help="git worktree to diff (default: root)")
    p.add_argument("--root", help="data root for .work/ (default: harness checkout)")
    p.add_argument("--allow-dirty", action="store_true", help="exit 0 even if the worktree is dirty")
    args = p.parse_args(argv)
    root = lib.repo_root(args.root)
    worktree = Path(args.worktree).resolve() if args.worktree else root
    try:
        meta = take_snapshot(root, args.feature, args.app, args.stage, worktree, args.base, args.head)
    except RuntimeError as exc:
        lib.die(str(exc))
    where = snapshot_dir(root, args.feature, args.app)
    print(f"snapshot {where}/diff.meta.json head={meta['head_sha'][:12]} changed_lines={meta['changed_lines']}"
          f"{' (split per file)' if meta['split'] else ''}")
    if not meta["porcelain_clean"] and not args.allow_dirty:
        print("worktree is dirty: commit (WIP allowed) before handoff, then snapshot again", file=sys.stderr)
        return lib.EXIT_STALE
    return lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
