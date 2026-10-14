#!/usr/bin/env python3
"""Render a prompt template ({{var}} placeholders) and report its sha256 (WORKFLOW §8).

Role prompts (ORC fills the variables):
  render_prompt.py --template generator/prompts/reviewer.md --stage S4 \\
      --var feature=F1 --var app=web --var round=2 ... --input spec/README.md \\
      --snapshot .work/F1/web/diff.meta.json --out .work/F1/web/prompt-S4.md
Generator prompt (variables come from generator/config/generator.json):
  render_prompt.py --generate web [--module all] --print

`return_codes` and (with --stage) `outcomes` have defaults. Any placeholder
left unfilled is an error, so a prompt never reaches an agent half-rendered.
--generate lists the shared platform inputs (generate.platform_shared) and warns on stderr
when the spec version is a draft (it still renders). --generate fails with "generator not yet configured for <app>" until the
app's conventions file exists.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import awarelib as lib
from state import APP_EVENTS, FEATURE_EVENTS

PLACEHOLDER = re.compile(r"{{\s*([a-z_][a-z0-9_]*)\s*}}")
RETURN_CODES_TEXT = ("`OK` · `SPEC_ISSUE {\"spec_id\", \"question\"}` · `PLAN_DEVIATION {\"reason\", \"proposal\"}` · "
                     "`STALE_DIFF` · `ENV_FAILURE {\"detail\"}` · `BLOCKED {\"reason\"}`")


class RenderError(Exception):
    pass


def render(template: str, variables: dict) -> str:
    missing = sorted({m for m in PLACEHOLDER.findall(template) if m not in variables})
    if missing:
        raise RenderError("unfilled variables: " + ", ".join(missing))
    return PLACEHOLDER.sub(lambda m: str(variables[m.group(1)]), template)


def spec_version(root: Path, gen: dict) -> str:
    path = root / gen["spec_index"]
    m = re.search(gen["spec_version_regex"], path.read_text(encoding="utf-8")) if path.exists() else None
    return m.group(1) if m else "0.0.0"


def is_draft(version: str, gen: dict) -> bool:
    return re.search(gen["draft_suffix_regex"] + r"$", version) is not None


def draft_warning(app: str, version: str) -> str:
    return (f"render_prompt: WARNING: spec {version} is a draft; generating {app} from it anyway "
            "(the stamped version keeps the draft suffix).")


def generate_vars(app: str, module: str, root: Path, cfg: dict) -> dict:
    if app not in cfg["apps"]:
        raise RenderError(f"unknown app '{app}' (config apps: {', '.join(cfg['apps'])})")
    a, gen = cfg["apps"][app], cfg["generate"]
    if not (root / a["conventions"]).exists():
        raise RenderError(f"generator not yet configured for {app}: {a['conventions']} is missing "
                          "(conventions live in generator/conventions/)")
    version = spec_version(root, gen)
    return {
        "app": app, "app_dir": a["dir"], "module_scope": module, "spec_version": version,
        "spec_is_draft": "yes" if is_draft(version, gen) else "no",
        "generator_commit": lib.git_head(root), "model_id": cfg["generate_model"],
        "build_cmd": a["build"], "test_cmd": a["test"], "self_repair_max": cfg["self_repair_max"],
        "self_repair_total_max": cfg["self_repair_total_max"],
        "logs_dir": gen["logs_dir"].format(app=app), "result_out": gen["result_out"].format(app=app),
        "spec_index": gen["spec_index"], "spec_dirs": ", ".join(f"`{d}`" for d in gen["spec_dirs"]),
        "platform_shared": ", ".join(f"`{f}`" for f in gen["platform_shared"]),
        "platform_spec": a["platform_spec"], "conventions_path": a["conventions"],
        "templates_dir": gen["templates_dir"].format(app=app), "plan_out": gen["plan_out"].format(app=app),
        "manifest_schema": gen["manifest_schema"],
        "header_text": cfg["headers"]["header_text"].format(spec_version=version),
        "return_codes": RETURN_CODES_TEXT,
    }


def role_vars(args) -> dict:
    variables = {"return_codes": RETURN_CODES_TEXT}
    if args.stage:
        variables["stage"] = args.stage
        events = APP_EVENTS.get(args.stage) or FEATURE_EVENTS.get(args.stage) or ()
        variables["outcomes"] = ", ".join(f"`{e}`" for e in events)
    if args.input:
        variables["inputs"] = "\n".join(f"- `{p}`" for p in args.input)
    if args.snapshot:
        meta = lib.read_json(args.snapshot)
        folder = Path(args.snapshot).parent
        variables.update(diff_meta=str(args.snapshot), changed_lines=meta["changed_lines"],
                         diff_patch=str(folder / (meta.get("files_list") or meta.get("patch") or "diff.patch")))
    if args.vars_json:
        variables.update(lib.read_json(args.vars_json))
    for item in args.var or []:
        key, _, val = item.partition("=")
        variables[key.strip()] = val
    return variables


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--template", help="role prompt template path")
    src.add_argument("--generate", metavar="APP", help="render generator/prompts/generate.md for APP from config")
    p.add_argument("--module", default="all", help="module scope for --generate")
    p.add_argument("--stage", help="fills {{stage}} and the allowed {{outcomes}}")
    p.add_argument("--var", action="append", help="key=value (repeatable)")
    p.add_argument("--vars-json", help="JSON object of variables")
    p.add_argument("--input", action="append", help="input path for {{inputs}} (repeatable)")
    p.add_argument("--snapshot", help="diff.meta.json: fills diff_meta, diff_patch, changed_lines")
    p.add_argument("--root", help="repo root (default: harness checkout)")
    p.add_argument("--out", help="write the rendered prompt here")
    p.add_argument("--print", action="store_true", help="print only the rendered prompt to stdout")
    args = p.parse_args(argv)
    cfg = lib.load_config()
    root = lib.repo_root(args.root)
    try:
        if args.generate:
            template_path = lib.HARNESS_ROOT / cfg["generate"]["prompt"]
            variables = generate_vars(args.generate, args.module, root, cfg)
        else:
            template_path = Path(args.template)
            variables = role_vars(args)
        text = render(template_path.read_text(encoding="utf-8"), variables)
    except RenderError as exc:
        lib.die(f"render_prompt: {exc}", lib.EXIT_FAIL)
    if args.generate and variables["spec_is_draft"] == "yes":
        print(draft_warning(args.generate, variables["spec_version"]), file=sys.stderr)
    digest = lib.sha256_bytes(text.encode("utf-8"))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    if args.print:
        sys.stdout.write(text)
    else:
        print(f"sha256 {digest} {args.out or '(not written; use --out or --print)'}")
    return lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
