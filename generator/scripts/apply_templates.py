#!/usr/bin/env python3
"""Copy generator templates into a client and check them (generator design §1.3, §2.3-2.4).

generator/templates/<app>/template.json lists:
  copy   template-owned files: src (in the template dir) -> dest (in the client), rendered with
         {{header}} and {{spec_version}} only unless "raw"; "operator" files (Gradle wrapper,
         package-lock.json) are produced on the operator's machine in smoke session A and may be
         missing until then; "executable" sets the exec bit.
  kinds  module build-file skeletons: --kind/--module writes one with {{namespace}} and
         {{main_class}} filled and an empty deps region the generator then edits.
  smoke  token-free modules for smoke session A (--smoke); never copied into clients/.

Modes:
  apply_templates.py --app android [--clean]          copy template-owned files into clients/<app>/
  apply_templates.py --app android --kind jvm-lib --module core/protocol [--main-class X]
  apply_templates.py --app web --check                 template-owned files unchanged; module build
                                                       files equal their kind outside the deps region
  apply_templates.py --app android --smoke [--out DIR] smoke project (default .work/smoke/<app>)
  apply_templates.py --app android --list              what is template-owned, and what is pending

Only placeholders {{header}} and {{spec_version}} (plus {{namespace}}, {{main_class}} in kinds) are
filled; any other {{...}} left in a rendered file is an error, so nothing half-rendered is written.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import sys
from pathlib import Path

import awarelib as lib
import render_prompt

PLACEHOLDER = re.compile(r"{{\s*([a-z_][a-z0-9_]*)\s*}}")
NAMESPACE_RE = r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*"
CLASS_RE = r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*"
VERSION_LITERAL = re.compile(r"[\"'][\w.-]+:[\w.-]+:\d[\w.+-]*[\"']")
PENDING_HINT = "produced in smoke session A on the operator's machine (docs/runs/P3/operator-checklist.md)"


class TemplateError(Exception):
    pass


# ------------------------------------------------------------------ loading
def template_dir(app: str, cfg: dict, harness: Path = lib.HARNESS_ROOT) -> Path:
    return harness / cfg["generate"]["templates_dir"].format(app=app)


def load_template(app: str, cfg: dict, harness: Path = lib.HARNESS_ROOT) -> tuple[Path, dict]:
    if app not in cfg["apps"]:
        raise TemplateError(f"unknown app '{app}' (config apps: {', '.join(cfg['apps'])})")
    tdir = template_dir(app, cfg, harness)
    spec = tdir / "template.json"
    if not spec.is_file():
        raise TemplateError(f"{spec} is missing")
    return tdir, lib.read_json(spec)


def base_variables(root: Path, cfg: dict) -> dict:
    version = render_prompt.spec_version(root, cfg["generate"])
    return {"spec_version": version, "header": cfg["headers"]["header_text"].format(spec_version=version)}


def render(text: str, variables: dict, where: str) -> str:
    out = PLACEHOLDER.sub(lambda m: str(variables[m.group(1)]) if m.group(1) in variables else m.group(0), text)
    left = sorted(set(PLACEHOLDER.findall(out)))
    if left:
        raise TemplateError(f"{where}: unfilled placeholder(s) {', '.join(left)}")
    return out


def rendered_bytes(src: Path, entry: dict, variables: dict) -> bytes:
    data = src.read_bytes()
    if entry.get("raw"):
        return data
    return render(data.decode("utf-8"), variables, entry["src"]).encode("utf-8")


def owned_paths(spec: dict) -> list[str]:
    """Destinations of template-owned files (relative to the client dir)."""
    return [e["dest"] for e in spec["copy"]]


def pending(tdir: Path, spec: dict) -> list[str]:
    """Operator-produced template files that do not exist yet."""
    return [e["src"] for e in spec["copy"] if e.get("operator") and not (tdir / e["src"]).is_file()]


# ------------------------------------------------------------------ copying
def safe_clean(out: Path, root: Path) -> None:
    out, root = out.resolve(), root.resolve()
    if out == root or root not in out.parents:
        raise TemplateError(f"refusing to delete {out}: not inside {root}")
    if out.exists():
        shutil.rmtree(out)


def copy_templates(tdir: Path, spec: dict, out: Path, variables: dict, allow_missing: bool = False) -> list[str]:
    missing = pending(tdir, spec)
    if missing and not allow_missing:
        raise TemplateError(f"template file(s) pending: {', '.join(missing)}; {PENDING_HINT}")
    written = []
    for entry in spec["copy"]:
        src = tdir / entry["src"]
        if not src.is_file():
            if entry.get("operator"):
                continue
            raise TemplateError(f"template source missing: {src}")
        dest = out / entry["dest"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(rendered_bytes(src, entry, variables))
        if entry.get("executable"):
            dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        written.append(entry["dest"])
    return written


# -------------------------------------------------------------------- kinds
def kind_text(tdir: Path, spec: dict, kind: str) -> str:
    kinds = spec.get("kinds")
    if not kinds:
        raise TemplateError("this app has no module kinds")
    if kind not in kinds["names"]:
        raise TemplateError(f"unknown kind '{kind}' (kinds: {', '.join(kinds['names'])})")
    return (tdir / kinds["dir"] / f"{kind}.gradle.kts").read_text(encoding="utf-8")


def default_namespace(spec: dict, module: str) -> str:
    parts = [p.replace("-", "_") for p in Path(module).parts]
    return ".".join([spec["kinds"]["namespace_prefix"], *parts])


def instantiate(tdir: Path, spec: dict, kind: str, module: str, out: Path, variables: dict,
                main_class: str | None = None, namespace: str | None = None,
                deps: list[str] | None = None) -> Path:
    module = module.replace(":", "/").strip("/")
    if not module or module.startswith(".") or ".." in Path(module).parts:
        raise TemplateError(f"bad module path '{module}'")
    text = kind_text(tdir, spec, kind)
    if "{{main_class}}" in text and not main_class:
        raise TemplateError(f"kind '{kind}' needs --main-class")
    if main_class and not re.fullmatch(CLASS_RE, main_class):
        raise TemplateError(f"bad main class '{main_class}'")
    ns = namespace or default_namespace(spec, module)
    if not re.fullmatch(NAMESPACE_RE, ns):
        raise TemplateError(f"bad namespace '{ns}'")
    values = {**variables, "namespace": ns}
    if main_class:
        values["main_class"] = main_class
    rendered = render(text, values, f"kind {kind}")
    if deps:
        k = spec["kinds"]
        begin = re.search(rf"^([ \t]*){re.escape(k['deps_begin'])}\n", rendered, re.M)
        if not begin:
            raise TemplateError(f"kind {kind} has no deps region")
        lines = "".join(f"{begin.group(1)}{d}\n" for d in deps)
        rendered = rendered[:begin.end()] + lines + rendered[begin.end():]
    dest = out / module / spec["kinds"]["build_file"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(rendered, encoding="utf-8")
    return dest


def kind_pattern(text: str, spec: dict, variables: dict) -> re.Pattern:
    """Regex matching any instantiation of a rendered kind skeleton (slots and deps region free)."""
    k = spec["kinds"]
    rendered = render(text, {**variables, "namespace": "\0NS\0", "main_class": "\0MC\0"}, "kind")
    begin = rendered.index(k["deps_begin"])
    begin = rendered.index("\n", begin) + 1
    end_marker = rendered.index(k["deps_end"], begin)
    end = rendered.rindex("\n", 0, end_marker) + 1
    head, tail = rendered[:begin], rendered[end:]

    def esc(part: str) -> str:
        return re.escape(part).replace(re.escape("\0NS\0"), NAMESPACE_RE).replace(re.escape("\0MC\0"), CLASS_RE)

    return re.compile(esc(head) + r"(?:[^\n]*\n)*?" + esc(tail))


def deps_region(text: str, spec: dict) -> list[str]:
    k = spec["kinds"]
    m = re.search(re.escape(k["deps_begin"]) + r"\n(.*?)" + r"[ \t]*" + re.escape(k["deps_end"]), text, re.S)
    return m.group(1).splitlines() if m else []


def module_build_files(out: Path, spec: dict) -> list[Path]:
    """build.gradle.kts files of modules (depth 1-2), as settings.gradle.kts includes them."""
    name, skip = spec["kinds"]["build_file"], {"build", "gradle", "buildSrc"}
    found = []
    for top in sorted(p for p in out.iterdir() if p.is_dir() and not p.name.startswith(".") and p.name not in skip):
        for d in [top, *sorted(p for p in top.iterdir() if p.is_dir() and not p.name.startswith(".")
                               and p.name not in skip)]:
            if (d / name).is_file():
                found.append(d / name)
    return found


# -------------------------------------------------------------------- check
def check(tdir: Path, spec: dict, out: Path, variables: dict) -> list[str]:
    problems = [f"template file pending: {p} ({PENDING_HINT})" for p in pending(tdir, spec)]
    if not out.is_dir():
        return problems + [f"{out} does not exist"]
    for entry in spec["copy"]:
        src, dest = tdir / entry["src"], out / entry["dest"]
        if not src.is_file():
            continue
        if not dest.is_file():
            problems.append(f"template-owned file missing: {entry['dest']}")
        elif dest.read_bytes() != rendered_bytes(src, entry, variables):
            problems.append(f"template-owned file changed: {entry['dest']}")
        elif entry.get("executable") and not os.access(dest, os.X_OK):
            problems.append(f"template-owned file lost its exec bit: {entry['dest']}")
    if spec.get("kinds"):
        patterns = {k: kind_pattern(kind_text(tdir, spec, k), spec, variables) for k in spec["kinds"]["names"]}
        for path in module_build_files(out, spec):
            rel = path.relative_to(out).as_posix()
            text = path.read_text(encoding="utf-8")
            if not any(p.fullmatch(text) for p in patterns.values()):
                problems.append(f"{rel}: differs from every kind skeleton outside the deps region")
            for line in deps_region(text, spec):
                if VERSION_LITERAL.search(line):
                    problems.append(f"{rel}: version literal in deps region: {line.strip()}")
    return problems


# --------------------------------------------------------------------- smoke
def apply_smoke(tdir: Path, spec: dict, out: Path, variables: dict) -> dict:
    """Template-owned files + one instantiated module per smoke entry + _smoke sources."""
    written = copy_templates(tdir, spec, out, variables, allow_missing=True)
    smoke = spec.get("smoke") or {}
    for m in smoke.get("modules", []):
        instantiate(tdir, spec, m["kind"], m["module"], out, variables, main_class=m.get("main_class"),
                    deps=m.get("deps"))
    src_root = tdir / smoke.get("dir", "_smoke")
    for src in sorted(src_root.rglob("*")) if src_root.is_dir() else []:
        rel = src.relative_to(src_root)
        if src.is_dir() or rel.as_posix() == "README.md":
            continue
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(render(src.read_text(encoding="utf-8"), variables, f"_smoke/{rel}"), encoding="utf-8")
    return {"written": written, "pending": pending(tdir, spec)}


# ---------------------------------------------------------------------- main
def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--app", required=True, help="app name from config")
    p.add_argument("--root", help="repo root (default: harness checkout)")
    p.add_argument("--out", help="target dir (default: clients/<app>, or <smoke_dir>/<app> with --smoke)")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="verify template-owned files and module build files")
    mode.add_argument("--smoke", action="store_true", help="build the token-free smoke project (session A)")
    mode.add_argument("--kind", help="instantiate a module build file from this kind skeleton")
    mode.add_argument("--list", action="store_true", help="list template-owned files and pending ones")
    p.add_argument("--module", help="module directory for --kind (e.g. core/protocol)")
    p.add_argument("--main-class", help="main class for kinds that need one")
    p.add_argument("--namespace", help="override the default namespace (app.aware.<module path>)")
    p.add_argument("--clean", action="store_true", help="delete the target dir first (scope all)")
    args = p.parse_args(argv)
    cfg = lib.load_config()
    root = lib.repo_root(args.root)
    try:
        tdir, spec = load_template(args.app, cfg)
        variables = base_variables(root, cfg)
        default_out = Path(cfg["generate"]["smoke_dir"]) / args.app if args.smoke else Path(cfg["apps"][args.app]["dir"])
        out = Path(args.out) if args.out else root / default_out
        if not out.is_absolute():
            out = root / out
        if args.list:
            for dest in owned_paths(spec):
                print(dest)
            for src in pending(tdir, spec):
                print(f"PENDING {src} ({PENDING_HINT})")
            return lib.EXIT_OK
        if args.check:
            problems = check(tdir, spec, out, variables)
            for prob in problems:
                print(f"  - {prob}")
            print(f"apply_templates --check {args.app}: {'FAIL' if problems else 'OK'} ({len(problems)} problem(s))")
            return lib.EXIT_FAIL if problems else lib.EXIT_OK
        if args.kind:
            if not args.module:
                lib.die("--kind needs --module", lib.EXIT_USAGE)
            dest = instantiate(tdir, spec, args.kind, args.module, out, variables, args.main_class, args.namespace)
            print(f"wrote {dest.relative_to(root) if root in dest.parents else dest} (kind {args.kind}); "
                  "edit only the deps region")
            return lib.EXIT_OK
        if args.clean:
            safe_clean(out, root)
        if args.smoke:
            res = apply_smoke(tdir, spec, out, variables)
            print(f"smoke project for {args.app} at {out} ({len(res['written'])} template files)")
            for src in res["pending"]:
                print(f"PENDING {src}: smoke_build.py produces it")
            return lib.EXIT_OK
        written = copy_templates(tdir, spec, out, variables)
        print(f"copied {len(written)} template-owned file(s) into {out}")
        return lib.EXIT_OK
    except TemplateError as exc:
        lib.die(f"apply_templates: {exc}", lib.EXIT_FAIL)
    return lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
