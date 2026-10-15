#!/usr/bin/env python3
"""Check a generated client against its manifest and headers (E-DEV-1).

For clients/<app>/:
  * the `.generated` manifest (schema: generator/schemas/manifest.schema.json)
    lists exactly the files on disk (build output dirs ignored), with matching sha256;
  * every manifest file with a comment-capable extension carries the GENERATED
    marker in its first lines.
A missing app dir or a placeholder (non-JSON) manifest is reported as
"not generated yet" and passes unless --strict.

--write-manifest is the deterministic last step of /generate: it hashes the
tree and writes the manifest, so the model never computes hashes itself. Each file
gets origin "template" (copied by apply_templates.py) or "model". With --result
(the run record of checkpoint.py) it also records the Claude Code version, the
self-repair attempts and the checkpoints (generator design §3.3).

Examples:
  check_headers.py --app all
  check_headers.py --app web --write-manifest --spec-version 0.1.0 --model-id <id> \
      [--result .work/generate/web/result.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import awarelib as lib


def disk_files(app_dir: Path, manifest_name: str, ignore_dirs: list[str], ignore_files: list[str] | None = None) -> set[str]:
    out = set()
    for p in app_dir.rglob("*"):
        rel = p.relative_to(app_dir)
        if (p.is_file() and rel.as_posix() != manifest_name and rel.name not in (ignore_files or [])
                and not set(rel.parts[:-1]) & set(ignore_dirs)):
            out.add(rel.as_posix())
    return out


def template_owned(app: str, cfg: dict) -> set[str]:
    """Destinations apply_templates.py copies for this app (empty if the app has no templates)."""
    try:
        import apply_templates
        _, spec = apply_templates.load_template(app, cfg)
    except Exception:  # noqa: BLE001 - a missing template set only means "no template origin"
        return set()
    return set(apply_templates.owned_paths(spec))


def write_manifest(app_dir: Path, app: str, spec_version: str, model_id: str, generator_commit: str,
                   cfg: dict, result: dict | None = None) -> Path:
    h = cfg["headers"]
    owned = template_owned(app, cfg)
    files = [{"path": rel, "sha256": lib.sha256_file(app_dir / rel),
              "origin": "template" if rel in owned else "model"}
             for rel in sorted(disk_files(app_dir, h["manifest"], h["ignore_dirs"], h.get("ignore_files")))]
    manifest = {"app": app, "spec_version": spec_version, "generator_commit": generator_commit,
                "model_id": model_id, "generated_at": lib.now_iso()}
    if result is not None:
        manifest["claude_code_version"] = result.get("claude_code_version")
        manifest["self_repair_attempts"] = int(result.get("self_repair_attempts", 0))
        manifest["checkpoints"] = {k: {"attempts": int(v.get("attempts", 0)), "result": v.get("result")}
                                   for k, v in result.get("checkpoints", {}).items()}
    manifest["files"] = files
    errs = lib.validate(manifest, lib.load_schema("manifest.schema.json"))
    if errs:
        raise ValueError("; ".join(errs))
    lib.write_json_atomic(app_dir / h["manifest"], manifest)
    return app_dir / h["manifest"]


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
    on_disk = disk_files(app_dir, h["manifest"], h["ignore_dirs"], h.get("ignore_files"))
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
    p.add_argument("--write-manifest", action="store_true", help="hash the tree and write the manifest")
    p.add_argument("--spec-version", help="for --write-manifest")
    p.add_argument("--model-id", help="for --write-manifest")
    p.add_argument("--result", help="for --write-manifest: run record of checkpoint.py (result.json)")
    args = p.parse_args(argv)
    cfg = lib.load_config()
    root = lib.repo_root(args.root)
    if args.write_manifest:
        if args.app == "all" or args.app not in cfg["apps"] or not (args.spec_version and args.model_id):
            lib.die("--write-manifest needs one configured --app, --spec-version and --model-id", lib.EXIT_USAGE)
        app_dir = root / cfg["apps"][args.app]["dir"]
        if not app_dir.is_dir():
            lib.die(f"{app_dir} does not exist; nothing to describe")
        result = None
        if args.result:
            if not Path(args.result).is_file():
                lib.die(f"--result {args.result} does not exist")
            result = lib.read_json(args.result)
        try:
            path = write_manifest(app_dir, args.app, args.spec_version, args.model_id, lib.git_head(root), cfg,
                                  result)
        except (ValueError, RuntimeError) as exc:
            lib.die(f"manifest not written: {exc}")
        print(f"wrote {path}")
        return lib.EXIT_OK
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
