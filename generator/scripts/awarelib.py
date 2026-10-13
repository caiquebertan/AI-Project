"""Shared helpers for the Aware harness scripts (stdlib only).

Everything tunable (caps, thresholds, patterns) comes from
generator/config/generator.json; this module only loads it.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HARNESS_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = HARNESS_ROOT / "generator" / "config" / "generator.json"
SCHEMA_DIR = HARNESS_ROOT / "generator" / "schemas"

# Process exit codes shared by all scripts.
EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_STALE = 3
EXIT_ILLEGAL = 4

ROLES = ("ORC", "PM", "TL", "DEV", "REV", "QA", "OP")
RETURN_CODES = ("OK", "SPEC_ISSUE", "PLAN_DEVIATION", "STALE_DIFF", "ENV_FAILURE", "BLOCKED")


# ---------------------------------------------------------------- config / io
def load_config(path: str | os.PathLike | None = None) -> dict:
    with open(path or CONFIG_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def repo_root(arg: str | None = None) -> Path:
    """Data root (.work/, docs/runs/). Defaults to the harness checkout."""
    return Path(arg).resolve() if arg else HARNESS_ROOT


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | os.PathLike) -> str:
    return sha256_bytes(Path(path).read_bytes())


def read_json(path: str | os.PathLike) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json_atomic(path: str | os.PathLike, data) -> None:
    """Write via temp file + rename so a crash never leaves half a file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def die(msg: str, code: int = EXIT_FAIL) -> "None":
    print(msg, file=sys.stderr)
    sys.exit(code)


# ----------------------------------------------------------------------- git
def git(args: list[str], cwd: str | os.PathLike, check: bool = True) -> str:
    res = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {res.stderr.strip()}")
    return res.stdout


def git_head(cwd) -> str:
    return git(["rev-parse", "HEAD"], cwd).strip()


def git_porcelain_clean(cwd) -> bool:
    return git(["status", "--porcelain"], cwd).strip() == ""


# -------------------------------------------------------- minimal JSON schema
def load_schema(name: str) -> dict:
    return read_json(SCHEMA_DIR / name)


_TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool,
    "integer": int, "number": (int, float), "null": type(None),
}


def validate(instance, schema: dict, root: dict | None = None, path: str = "$") -> list[str]:
    """Validate the subset of JSON Schema the harness uses. Returns error list."""
    root = root or schema
    if "$ref" in schema:
        node = root
        for part in schema["$ref"].lstrip("#/").split("/"):
            node = node[part]
        return validate(instance, node, root, path)
    errs: list[str] = []
    if "anyOf" in schema and all(validate(instance, s, root, path) for s in schema["anyOf"]):
        errs.append(f"{path}: matches none of anyOf")
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        ok = any(isinstance(instance, _TYPES[x]) and not (x in ("integer", "number") and isinstance(instance, bool))
                 for x in types)
        if not ok:
            return [f"{path}: expected {t}, got {type(instance).__name__}"]
    if "enum" in schema and instance not in schema["enum"]:
        errs.append(f"{path}: {instance!r} not in {schema['enum']}")
    if "pattern" in schema and isinstance(instance, str) and not re.search(schema["pattern"], instance):
        errs.append(f"{path}: {instance!r} does not match {schema['pattern']}")
    if "minimum" in schema and isinstance(instance, (int, float)) and instance < schema["minimum"]:
        errs.append(f"{path}: {instance} < {schema['minimum']}")
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errs.append(f"{path}: missing required '{key}'")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, val in instance.items():
            if key in props:
                errs += validate(val, props[key], root, f"{path}.{key}")
            elif extra is False:
                errs.append(f"{path}: unexpected property '{key}'")
            elif isinstance(extra, dict):
                errs += validate(val, extra, root, f"{path}.{key}")
    if isinstance(instance, list) and "items" in schema:
        for i, item in enumerate(instance):
            errs += validate(item, schema["items"], root, f"{path}[{i}]")
    return errs


# ------------------------------------------------------------------- run log
def run_log_path(root: Path, feature: str) -> Path:
    return root / "docs" / "runs" / feature / "run.jsonl"


def append_run_event(root: Path, event: dict) -> dict:
    """Append one validated event line to docs/runs/<feature>/run.jsonl."""
    event = {"ts": now_iso(), **{k: v for k, v in event.items() if v is not None}}
    errs = validate(event, load_schema("run-event.schema.json"))
    if errs:
        raise ValueError("invalid run event: " + "; ".join(errs))
    path = run_log_path(root, event["feature"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=False) + "\n")
    return event


def read_run_events(root: Path, feature: str) -> list[dict]:
    path = run_log_path(root, feature)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
