#!/usr/bin/env python3
"""Checkpoint runner and self-repair budget for /generate (generator design §3.2, decision 0017).

Runs one checkpoint command inside clients/<app>/, writes its full log to
<logs_dir>/<checkpoint>-<n>.log, digests a failure with build_digest.py, and keeps the run record
<result_out> (config generate.*). The last output line is the verdict:
  CHECKPOINT <id>: PASS
  CHECKPOINT <id>: REPAIR (attempt k/<self_repair_max> next; run total t/<self_repair_total_max>)
  CHECKPOINT <id>: EXHAUSTED          budget gone; /generate stops (BLOCKED, G2)
  CHECKPOINT <id>: ENV_FAILURE        toolchain/network; no attempt spent
  CHECKPOINT <id>: BLOCKED_PIN        a template version does not resolve; no attempt spent
A run of a checkpoint whose previous run failed with class CODE is one self-repair attempt.
The runner refuses to start an attempt beyond either budget.

Examples (from the repository root; the command runs in clients/<app>/):
  checkpoint.py --app android --start --model-id claude-opus-5-5
  checkpoint.py --app android --checkpoint C1 -- ./gradlew --console=plain :core:protocol:test
  checkpoint.py --app web --checkpoint C5 --config-cmd build
  checkpoint.py --app web --status
Exit: 0 PASS, 1 any other verdict, 2 usage.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

import awarelib as lib
import build_digest

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
VERDICT_BY_CLASS = {"CODE": "REPAIR", "ENV": "ENV_FAILURE", "PIN": "BLOCKED_PIN"}


def paths(app: str, cfg: dict, root: Path) -> tuple[Path, Path]:
    gen = cfg["generate"]
    return root / gen["logs_dir"].format(app=app), root / gen["result_out"].format(app=app)


def new_record(app: str, cfg: dict, model_id: str | None, claude_version: str | None) -> dict:
    return {"app": app, "model_id": model_id, "claude_code_version": claude_version, "started_at": lib.now_iso(),
            "budget": {"per_checkpoint": cfg["self_repair_max"], "per_run": cfg["self_repair_total_max"]},
            "self_repair_attempts": 0, "checkpoints": {}}


def load_record(result: Path, app: str, cfg: dict) -> dict:
    return lib.read_json(result) if result.is_file() else new_record(app, cfg, None, None)


def probe_claude_version() -> str | None:
    try:
        res = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return (res.stdout or res.stderr).strip().splitlines()[0] if res.returncode == 0 and (res.stdout or res.stderr) else None


def is_attempt(cp: dict) -> bool:
    """The next run of this checkpoint is a self-repair attempt if its last run failed with CODE."""
    return bool(cp["runs"]) and cp["runs"][-1]["class"] == "CODE"


def budget_left(record: dict, cp: dict) -> bool:
    b = record["budget"]
    return cp["attempts"] < b["per_checkpoint"] and record["self_repair_attempts"] < b["per_run"]


def run_command(cmd, shell: bool, cwd: Path, log: Path, timeout: float | None) -> tuple[int, float]:
    log.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    with open(log, "w", encoding="utf-8") as fh:
        fh.write(f"$ {cmd if shell else ' '.join(cmd)}\n(cwd {cwd})\n")
        fh.flush()
        try:
            res = subprocess.run(cmd, shell=shell, cwd=cwd, stdout=fh, stderr=subprocess.STDOUT, text=True,
                                 timeout=timeout)
            code = res.returncode
        except FileNotFoundError as exc:
            fh.write(f"\n{exc}\ncommand not found\n")
            code = 127
        except subprocess.TimeoutExpired:
            fh.write(f"\ncheckpoint timed out after {timeout} s\n")
            code = 124
    return code, round(time.monotonic() - start, 1)


def run_checkpoint(app: str, cp_id: str, cmd, shell: bool, cfg: dict, root: Path,
                   timeout: float | None = None, runner=run_command) -> tuple[str, dict]:
    """Run one checkpoint; returns (verdict, record). `runner` is injectable for tests."""
    logs_dir, result = paths(app, cfg, root)
    record = load_record(result, app, cfg)
    cp = record["checkpoints"].setdefault(cp_id, {"attempts": 0, "runs": [], "result": None})
    attempt = is_attempt(cp)
    if attempt and not budget_left(record, cp):
        cp["result"] = "exhausted"
        lib.write_json_atomic(result, record)
        return "EXHAUSTED", record
    if attempt:
        cp["attempts"] += 1
        record["self_repair_attempts"] += 1
    n = len(cp["runs"]) + 1
    log = logs_dir / f"{cp_id}-{n}.log"
    app_dir = root / cfg["apps"][app]["dir"]
    started = time.time()
    code, seconds = runner(cmd, shell, app_dir, log, timeout)
    run = {"n": n, "cmd": cmd if shell else " ".join(cmd), "exit": code, "seconds": seconds,
           "log": str(log.relative_to(root)) if root in log.parents else str(log), "attempt": attempt,
           "class": None}
    d = None
    if code == 0:
        verdict = "PASS"
        cp["result"] = "pass"
    else:
        d = build_digest.digest(app, log, cfg, since=started - 1, root=root)
        run["class"] = d["class"]
        run["first_error"] = d["first_error"]
        verdict = VERDICT_BY_CLASS[d["class"]]
        if verdict == "REPAIR" and not budget_left(record, cp):
            verdict = "EXHAUSTED"
        cp["result"] = {"REPAIR": "fail", "EXHAUSTED": "exhausted", "ENV_FAILURE": "env",
                        "BLOCKED_PIN": "pin"}[verdict]
    cp["runs"].append(run)
    record["updated_at"] = lib.now_iso()
    lib.write_json_atomic(result, record)
    record["_digest"] = d
    return verdict, record


def verdict_line(cp_id: str, verdict: str, record: dict) -> str:
    if verdict != "REPAIR":
        return f"CHECKPOINT {cp_id}: {verdict}"
    cp, b = record["checkpoints"][cp_id], record["budget"]
    return (f"CHECKPOINT {cp_id}: REPAIR (attempt {cp['attempts'] + 1}/{b['per_checkpoint']} next; "
            f"run total {record['self_repair_attempts']}/{b['per_run']})")


def status_text(record: dict) -> str:
    b = record["budget"]
    lines = [f"app {record['app']}  model {record.get('model_id')}  self-repair {record['self_repair_attempts']}"
             f"/{b['per_run']} (per checkpoint {b['per_checkpoint']})", "checkpoint  result     attempts  runs"]
    for cp_id, cp in record["checkpoints"].items():
        lines.append(f"{cp_id:<11} {str(cp['result']):<10} {cp['attempts']:<9} {len(cp['runs'])}")
    return "\n".join(lines)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = []
    if "--" in argv:
        i = argv.index("--")
        argv, cmd = argv[:i], argv[i + 1:]
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--app", required=True, help="app name from config")
    p.add_argument("--root", help="repo root (default: harness checkout)")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--start", action="store_true", help="begin a new run record")
    mode.add_argument("--status", action="store_true", help="print the checkpoint table")
    mode.add_argument("--checkpoint", help="checkpoint id (e.g. C1); command after --, or --config-cmd")
    p.add_argument("--config-cmd", choices=("build", "test"), help="run apps.<app>.build/test from the config")
    p.add_argument("--model-id", help="with --start: the model actually running")
    p.add_argument("--timeout", type=float, help="seconds before the command is stopped (default: none)")
    args = p.parse_args(argv)
    cfg = lib.load_config()
    if args.app not in cfg["apps"]:
        lib.die(f"unknown app '{args.app}' (config apps: {', '.join(cfg['apps'])})", lib.EXIT_USAGE)
    root = lib.repo_root(args.root)
    logs_dir, result = paths(args.app, cfg, root)
    if args.start:
        lib.write_json_atomic(result, new_record(args.app, cfg, args.model_id, probe_claude_version()))
        print(f"run record started: {result}")
        return lib.EXIT_OK
    if args.status:
        if not result.is_file():
            lib.die(f"no run record at {result}; run --start first")
        print(status_text(lib.read_json(result)))
        return lib.EXIT_OK
    if not ID_RE.match(args.checkpoint):
        lib.die(f"bad checkpoint id '{args.checkpoint}'", lib.EXIT_USAGE)
    if bool(cmd) == bool(args.config_cmd):
        lib.die("give exactly one of: a command after --, or --config-cmd build|test", lib.EXIT_USAGE)
    shell = bool(args.config_cmd)
    command = cfg["apps"][args.app][args.config_cmd] if shell else cmd
    if not (root / cfg["apps"][args.app]["dir"]).is_dir():
        lib.die(f"{cfg['apps'][args.app]['dir']} does not exist; apply the templates first")
    verdict, record = run_checkpoint(args.app, args.checkpoint, command, shell, cfg, root, args.timeout)
    d = record.pop("_digest", None)
    if verdict == "PASS":
        run = record["checkpoints"][args.checkpoint]["runs"][-1]
        print(f"passed in {run['seconds']} s; log {run['log']}")
    elif d is not None:
        print(build_digest.render_text(d))
    print(verdict_line(args.checkpoint, verdict, record))
    return lib.EXIT_OK if verdict == "PASS" else lib.EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
