#!/usr/bin/env python3
"""Append, show or validate run-log events (WORKFLOW §8).

One JSON object per line in docs/runs/<feature>/run.jsonl, validated against
generator/schemas/run-event.schema.json. state.py logs every transition
itself; ORC uses this script for agent launches, results and notes.

Examples:
  run_log.py append --feature F1 --app web --stage S4 --event launch --agent REV \\
      --model opus --model-id <id> --model-reason "changed_lines 512 > 400" \\
      --prompt .work/F1/web/prompt-S4.md --snapshot .work/F1/web/diff.meta.json
  run_log.py append --feature F1 --event result --agent REV --return-code OK \\
      --findings '{"blockers": 2, "nits": 1, "design_concerns": 0}' --tokens 81234 --duration 412
  run_log.py show --feature F1 --tail 5
  run_log.py validate --feature F1
"""
from __future__ import annotations

import argparse
import json
import sys

import awarelib as lib


def _maybe_json(text: str | None):
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def build_event(args) -> dict:
    ev = {
        "feature": args.feature, "app": args.app, "stage": args.stage, "event": args.event,
        "agent": args.agent, "model": args.model, "model_id": args.model_id, "model_reason": args.model_reason,
        "spec_version": args.spec_version, "return_code": args.return_code, "duration": args.duration,
        "tokens": args.tokens, "gate": args.gate, "decided_by": args.decided_by,
        "operator_msg_ref": args.operator_msg, "commit": args.commit, "detail": args.detail,
        "inputs": args.input or None, "outputs": args.output or None, "parallel_with": args.parallel_with or None,
        "result": _maybe_json(args.result), "findings": _maybe_json(args.findings),
    }
    if args.prompt:
        ev["prompt_sha256"] = lib.sha256_file(args.prompt)
    if args.snapshot:
        meta = lib.read_json(args.snapshot)
        ev.update(base_sha=meta["base_sha"], head_sha=meta["head_sha"], changed_lines=meta["changed_lines"])
    if args.json:
        ev.update(json.loads(args.json))
    return ev


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", help="data root (default: harness checkout)")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("append", help="append one event")
    a.add_argument("--feature", required=True)
    a.add_argument("--event", required=True, help="e.g. launch, result, note, commit, gate")
    for flag in ("app", "stage", "agent", "model", "model-id", "model-reason", "spec-version", "return-code",
                 "gate", "decided-by", "operator-msg", "commit", "detail", "result", "findings", "prompt",
                 "snapshot", "json"):
        a.add_argument(f"--{flag}")
    a.add_argument("--duration", type=float, help="seconds")
    a.add_argument("--tokens", type=int)
    a.add_argument("--input", action="append", help="repeatable")
    a.add_argument("--output", action="append", help="repeatable")
    a.add_argument("--parallel-with", action="append", help="repeatable: feature/app running in parallel")
    s = sub.add_parser("show", help="print events")
    s.add_argument("--feature", required=True)
    s.add_argument("--tail", type=int, default=0)
    v = sub.add_parser("validate", help="validate every line against the schema")
    v.add_argument("--feature", required=True)
    args = p.parse_args(argv)
    root = lib.repo_root(args.root)

    if args.cmd == "append":
        try:
            ev = lib.append_run_event(root, build_event(args))
        except ValueError as exc:
            lib.die(str(exc), lib.EXIT_USAGE)
        print(json.dumps(ev))
    elif args.cmd == "show":
        events = lib.read_run_events(root, args.feature)
        for ev in events[-args.tail:] if args.tail else events:
            print(json.dumps(ev))
    else:
        schema = lib.load_schema("run-event.schema.json")
        bad = 0
        for i, ev in enumerate(lib.read_run_events(root, args.feature), 1):
            for err in lib.validate(ev, schema):
                bad += 1
                print(f"line {i}: {err}")
        print("OK" if not bad else f"{bad} problem(s)")
        return lib.EXIT_OK if not bad else lib.EXIT_FAIL
    return lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
