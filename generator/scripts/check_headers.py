#!/usr/bin/env python3
"""Check a generated client against its manifest and headers (E-DEV-1).

For clients/<app>/:
  * the `.generated` manifest (schema: generator/schemas/manifest.schema.json)
    lists exactly the files on disk (build output dirs ignored), with matching sha256;
  * every manifest file with a comment-capable extension carries the GENERATED
    marker in its first lines.
A missing app dir or a placeholder (non-JSON) manifest is reported as
"not generated yet" and passes unless --strict.

Example:
  check_headers.py --app all
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import awarelib as lib


def disk_files(app_dir: Path, manifest_name: str, ignore_dirs: list[str]) -> set[str]:
    out = set()
    for p in app_dir.rglob("*"):
        rel = p.relative_to(app_dir)
        if p.is_file() and rel.as_posix() != manifest_name and not set(rel.parts[:-1]) & set(ignore_dirs):
            out.add(rel.as_posix())
    return out


def check_app(app_dir: Path, cfg: dict) -> tuple[str, list[str]]:
    """Return (state, problems); state is 'absent', 'placeholder' or 'checked'."""
    h = cfg["headers"]
    if not app_dir.is_dir():
        return "absent", []
    manifest_path = app_dir / h["manifest"]
    if not manifest_path.exists():
        return "checked", [f"{h['manifest']} missing"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "placeholder", []
    problems = lib.validate(manifest, lib.load_schema("manifest.schema.json"))
    if problems:
        return "checked", problems
    listed = {f["path"]: f["sha256"] for f in manifest["files"]}
    on_disk = disk_files(app_dir, h["manifest"], h["ignore_dirs"])
    problems += [f"in manifest, missing on disk: {p}" for p in sorted(set(listed) - on_disk)]
    problems += [f"on disk, not in manifest: {p}" for p in sorted(on_disk - set(listed))]
    for rel, digest in sorted(listed.items()):
        path = app_dir / rel
        if not path.exists():
            continue
        if lib.sha256_file(path) != digest:
            problems.append(f"sha256 mismatch: {rel}")
        if path.suffix in h["comment_extensions"]:
            head = path.read_text(encoding="utf-8", errors="replace").splitlines()[: h["scan_lines"]]
            if not any(h["marker"] in line for line in head):
                problems.append(f"missing GENERATED header: {rel}")
    return "checked", problems


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--app", default="all", help="app name from config, or 'all'")
    p.add_argument("--root", help="repo root (default: harness checkout)")
    p.add_argument("--strict", action="store_true", help="fail when an app is absent or not generated yet")
    args = p.parse_args(argv)
    cfg = lib.load_config()
    root = lib.repo_root(args.root)
    apps = list(cfg["apps"]) if args.app == "all" else [args.app]
    failed = False
    for app in apps:
        if app not in cfg["apps"]:
            lib.die(f"unknown app '{app}' (config apps: {', '.join(cfg['apps'])})", lib.EXIT_USAGE)
        app_dir = root / cfg["apps"][app]["dir"]
        state, problems = check_app(app_dir, cfg)
        if state in ("absent", "placeholder"):
            what = "directory not present" if state == "absent" else "manifest is a placeholder"
            print(f"SKIP {app}: {what} (not generated yet)")
            failed |= args.strict
        elif problems:
            failed = True
            print(f"FAIL {app}: {len(problems)} problem(s)")
            for prob in problems:
                print(f"  - {prob}")
        else:
            print(f"OK   {app}: manifest matches tree, headers present")
    return lib.EXIT_FAIL if failed else lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
