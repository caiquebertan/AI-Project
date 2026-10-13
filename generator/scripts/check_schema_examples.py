#!/usr/bin/env python3
"""Check the machine-readable protocol contract in spec/core/schema/ (stdlib only).

  * every schema named in index.json exists and uses only the supported JSON
    Schema subset (so server and both clients can rely on the same keywords);
  * every example listed in index.json "examples" validates against its schema,
    and payloads of core types inside it validate against index.json "core_types";
  * constants.json equals the constants table in spec/core/protocol.md.

Supported subset: $schema $id $ref $defs $comment title description type
properties required additionalProperties items minItems maxItems uniqueItems
enum const pattern minLength maxLength minimum maximum. `pattern` is searched,
not anchored (JSON Schema semantics); write ^...$ to anchor.

Examples:
  check_schema_examples.py
  check_schema_examples.py --schema-dir spec/core/schema --protocol spec/core/protocol.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import awarelib as lib

KEYWORDS = {"$schema", "$id", "$ref", "$defs", "$comment", "title", "description", "type", "properties", "required",
            "additionalProperties", "items", "minItems", "maxItems", "uniqueItems", "enum", "const", "pattern",
            "minLength", "maxLength", "minimum", "maximum"}
TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}
CONST_ROW = re.compile(r"^\|\s*`([A-Z][A-Z0-9_]*)`\s*\|\s*`([^`]+)`\s*\|")


class Schemas:
    """Loads schema files from one directory and resolves file-relative $refs."""

    def __init__(self, base: Path):
        self.base, self.cache = base, {}

    def load(self, name: str) -> dict:
        if name not in self.cache:
            self.cache[name] = json.loads((self.base / name).read_text(encoding="utf-8"))
        return self.cache[name]

    def resolve(self, ref: str, current: str) -> tuple[dict, str]:
        file, _, pointer = ref.partition("#")
        file = file or current
        node = self.load(file)
        for part in [p for p in pointer.split("/") if p]:
            node = node[part]
        return node, file


def _is_type(value, name: str) -> bool:
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, TYPES[name])


def validate(value, schema: dict, schemas: Schemas, file: str, path: str = "$") -> list[str]:
    """Return a list of 'path: problem' strings (empty when valid)."""
    errs: list[str] = []
    if "$ref" in schema:
        target, tfile = schemas.resolve(schema["$ref"], file)
        errs += validate(value, target, schemas, tfile, path)
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is_type(value, n) for n in names):
            return errs + [f"{path}: expected {'/'.join(names)}"]
    if "const" in schema and (value != schema["const"] or type(value) is not type(schema["const"])):
        errs.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: {value!r} not in enum")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errs.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errs.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errs.append(f"{path}: does not match {schema['pattern']}")
    if _is_type(value, "number"):
        if "minimum" in schema and value < schema["minimum"]:
            errs.append(f"{path}: below {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errs.append(f"{path}: above {schema['maximum']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errs.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errs.append(f"{path}: more than {schema['maxItems']} items")
        if schema.get("uniqueItems") and len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
            errs.append(f"{path}: items not unique")
        if "items" in schema:
            for i, item in enumerate(value):
                errs += validate(item, schema["items"], schemas, file, f"{path}[{i}]")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        errs += [f"{path}: missing '{k}'" for k in schema.get("required", []) if k not in value]
        for key, item in value.items():
            if key in props:
                errs += validate(item, props[key], schemas, file, f"{path}.{key}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unexpected field '{key}'")
            elif isinstance(schema.get("additionalProperties"), dict):
                errs += validate(item, schema["additionalProperties"], schemas, file, f"{path}.{key}")
    return errs


def unsupported_keywords(schema, path: str = "$") -> list[str]:
    """Keywords outside the subset, found anywhere a schema object is expected."""
    out = []
    if not isinstance(schema, dict):
        return out
    out += [f"{path}: unsupported keyword '{k}'" for k in schema if k not in KEYWORDS]
    for k in ("properties", "$defs"):
        for name, sub in schema.get(k, {}).items():
            out += unsupported_keywords(sub, f"{path}.{k}.{name}")
    for k in ("items", "additionalProperties"):
        if isinstance(schema.get(k), dict):
            out += unsupported_keywords(schema[k], f"{path}.{k}")
    return out


def core_payload_errors(value, core_types: dict, schemas: Schemas, path: str = "$") -> list[str]:
    """Validate payloads of envelopes whose type is a core type (CORE-EXT-001)."""
    errs = []
    if isinstance(value, dict):
        if value.get("type") in core_types and "payload" in value:
            name = core_types[value["type"]]
            errs += validate(value["payload"], schemas.load(name), schemas, name, f"{path}.payload")
        for k, v in value.items():
            errs += core_payload_errors(v, core_types, schemas, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            errs += core_payload_errors(v, core_types, schemas, f"{path}[{i}]")
    return errs


def protocol_constants(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        m = CONST_ROW.match(line.strip())
        if m:
            out[m.group(1)] = json.loads(m.group(2))
    return out


def check(schema_dir: Path, protocol: Path | None) -> list[str]:
    problems = []
    index = json.loads((schema_dir / "index.json").read_text(encoding="utf-8"))
    schemas = Schemas(schema_dir)
    names = {n for e in index["endpoints"] for n in [e["request"], *e["responses"].values()] if n}
    names |= set(index.get("any_path", {}).values()) | set(index["core_types"].values()) | set(index["examples"].values())
    for name in sorted(names):
        if not (schema_dir / name).exists():
            problems.append(f"{name}: referenced in index.json but missing")
            continue
        problems += [f"{name} {p}" for p in unsupported_keywords(schemas.load(name))]
    for name in sorted(p.name for p in schema_dir.glob("*.schema.json")):
        problems += [f"{name} {p}" for p in unsupported_keywords(schemas.load(name)) if name not in names]
    for example, name in index["examples"].items():
        if not (schema_dir / example).exists() or not (schema_dir / name).exists():
            problems.append(f"{example}: example or schema missing")
            continue
        value = json.loads((schema_dir / example).read_text(encoding="utf-8"))
        errs = validate(value, schemas.load(name), schemas, name)
        errs += core_payload_errors(value, index["core_types"], schemas)
        problems += [f"{example} {e}" for e in errs]
    if protocol is not None:
        consts = {k: v for k, v in json.loads((schema_dir / index["constants"]).read_text()).items()
                  if not k.startswith("$")}
        table = protocol_constants(protocol.read_text(encoding="utf-8"))
        for key in sorted(set(consts) | set(table)):
            if consts.get(key) != table.get(key):
                problems.append(f"constant {key}: constants.json={consts.get(key)!r} protocol.md={table.get(key)!r}")
    return problems


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--schema-dir", default=str(lib.HARNESS_ROOT / "spec" / "core" / "schema"))
    p.add_argument("--protocol", default=str(lib.HARNESS_ROOT / "spec" / "core" / "protocol.md"),
                   help="protocol.md holding the constants table ('' to skip)")
    args = p.parse_args(argv)
    problems = check(Path(args.schema_dir), Path(args.protocol) if args.protocol else None)
    for prob in problems:
        print(f"FAIL {prob}")
    print("schema examples: OK" if not problems else f"schema examples: {len(problems)} problem(s)")
    return lib.EXIT_FAIL if problems else lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
