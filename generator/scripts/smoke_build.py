#!/usr/bin/env python3
"""Smoke session A: token-free build of the templates on the operator's machine (generator design §5).

For each app it builds a throwaway project from the templates and their _smoke/ modules
(apply_templates.py --smoke, under <smoke_dir>/<app>), produces what the cloud cannot (Gradle
wrapper jar and scripts; package-lock.json), runs the app's configured build and test commands,
digests failures (CODE/ENV/PIN), checks that spec ids reach the JUnit reports, and collects a
send-back bundle: <smoke_dir>/send-back/ and <smoke_dir>/send-back.zip.

Android: if the templates have no wrapper yet, `gradle wrapper --gradle-version <pin>` runs in
<smoke_dir>/wrapper-bootstrap (needs a local `gradle`, e.g. `brew install gradle`); the published
sha256 sums of the distribution and of the wrapper jar are fetched from services.gradle.org.
Web: if the templates have no lockfile yet, `npm install` creates it before the build.
Once the templates carry these files (verified in session A, 2026-10-14) both steps are skipped.
Neither step touches clients/ or the templates; DEV commits the returned files to generator/templates/.

Examples:
  smoke_build.py --app all --dry-run      # print the steps
  smoke_build.py --app all                # run them (operator's machine)
Exit 0 only if every app built, tested green and carried spec ids in its reports.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import apply_templates as at
import awarelib as lib
import build_digest

GRADLE_DIST = "https://services.gradle.org/distributions/gradle-{v}-bin.zip.sha256"
GRADLE_WRAPPER_JAR = "https://services.gradle.org/distributions/gradle-{v}-wrapper.jar.sha256"
WRAPPER_FILES = ("gradlew", "gradlew.bat", "gradle/wrapper/gradle-wrapper.jar")
VERSION_PROBES = {
    "java": ["java", "-version"], "gradle": ["gradle", "--version"], "node": ["node", "-v"], "npm": ["npm", "-v"],
    "claude": ["claude", "--version"], "sdkmanager": ["sdkmanager", "--list_installed"],
}


# ------------------------------------------------------------------ steps
def gradle_version(tdir: Path) -> str:
    text = (tdir / "gradle/wrapper/gradle-wrapper.properties").read_text(encoding="utf-8")
    m = re.search(r"gradle-([0-9][0-9A-Za-z.+-]*)-(?:bin|all)\.zip", text)
    if not m:
        raise at.TemplateError("no Gradle version in gradle-wrapper.properties")
    return m.group(1)


def plan_app(app: str, cfg: dict, root: Path, smoke_root: Path, harness: Path = lib.HARNESS_ROOT) -> dict:
    """Ordered steps for one app; each step is (name, command, shell, cwd, env_extra).

    The wrapper and npm-install steps appear only while the template files are missing (idempotent re-runs)."""
    tdir, spec = at.load_template(app, cfg, harness)
    out = smoke_root / app
    a = cfg["apps"][app]
    pending = at.pending(tdir, spec)
    steps = []
    produced = []
    if app == "android":
        if any(p in WRAPPER_FILES for p in pending):
            v = gradle_version(tdir)
            steps.append(("wrapper", ["gradle", "wrapper", "--gradle-version", v, "--distribution-type", "bin"],
                          False, smoke_root / "wrapper-bootstrap", {}))
            produced = list(WRAPPER_FILES)
        repo = f" -Paware.repoRoot={shlex.quote(str(root))}"
        steps.append(("build", a["build"] + repo, True, out, {}))
        steps.append(("test", a["test"] + repo, True, out, {}))
    else:
        env = {"AWARE_REPO_ROOT": str(root)}
        if "package-lock.json" in pending:
            steps.append(("install", "npm install --no-audit --no-fund", True, out, env))
            produced = ["package-lock.json"]
        steps.append(("build", a["build"], True, out, env))
        steps.append(("test", a["test"], True, out, env))
    return {"app": app, "out": out, "tdir": tdir, "spec": spec, "steps": steps, "produced": produced,
            "pending": pending}


def default_runner(cmd, shell: bool, cwd: Path, env_extra: dict, log: Path) -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    cwd.mkdir(parents=True, exist_ok=True)
    with open(log, "w", encoding="utf-8") as fh:
        fh.write(f"$ {cmd if shell else ' '.join(cmd)}\n(cwd {cwd})\n")
        fh.flush()
        try:
            return subprocess.run(cmd, shell=shell, cwd=cwd, stdout=fh, stderr=subprocess.STDOUT, text=True,
                                  env={**os.environ, **env_extra}).returncode
        except FileNotFoundError as exc:
            fh.write(f"\n{exc}\ncommand not found\n")
            return 127


def default_fetch(url: str) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=20) as res:  # noqa: S310 - fixed https host
            return res.read().decode("ascii", "replace").strip().split()[0]
    except Exception:  # noqa: BLE001 - reported as "not fetched", never fatal
        return None


def probe(cmd: list[str]) -> str | None:
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    text = (res.stdout + res.stderr).strip()
    return text[:4000] if text else None


# --------------------------------------------------------------- checks
def report_ids(out: Path, globs: list[str], id_regex: str) -> dict:
    """Testcases in the JUnit reports and whether each carries a spec id in `classname name`."""
    cases = []
    for path in build_digest.report_files(out, globs, None):
        try:
            for case in ET.parse(path).getroot().iter("testcase"):
                text = f"{case.get('classname', '')} {case.get('name', '')}"
                cases.append({"classname": case.get("classname", ""), "name": case.get("name", ""),
                              "has_id": re.search(id_regex, text) is not None})
        except (ET.ParseError, OSError):
            continue
    return {"testcases": len(cases), "with_id": sum(c["has_id"] for c in cases), "samples": cases[:20],
            "ok": bool(cases) and all(c["has_id"] for c in cases)}


# -------------------------------------------------------------- running
def run_app(p: dict, cfg: dict, root: Path, smoke_root: Path, runner=default_runner, fetch=default_fetch) -> dict:
    app, out = p["app"], p["out"]
    at.safe_clean(out, root)
    at.apply_smoke(p["tdir"], p["spec"], out, at.base_variables(root, cfg))
    logs = smoke_root / "logs" / app
    summary = {"app": app, "steps": [], "ok": False, "produced": {}}
    for name, cmd, shell, cwd, env in p["steps"]:
        if name == "wrapper":
            at.safe_clean(cwd, root)
            cwd.mkdir(parents=True)
            (cwd / "settings.gradle.kts").write_text('rootProject.name = "wrapper-bootstrap"\n', encoding="utf-8")
        log = logs / f"{name}.log"
        started = time.time()
        code = runner(cmd, shell, cwd, env, log)
        step = {"step": name, "cmd": cmd if shell else " ".join(cmd), "exit": code, "log": str(log)}
        if code != 0:
            reports = build_digest.report_files(out, cfg["apps"][app].get("reports", []), started - 1) \
                if name == "test" else []
            d = build_digest.digest(app, log, cfg, reports=reports)
            step["class"], step["first_error"] = d["class"], d["first_error"]
        if name == "wrapper" and code == 0:
            for rel in WRAPPER_FILES:
                src = cwd / rel
                if src.is_file():
                    (out / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, out / rel)
        summary["steps"].append(step)
        if name in ("wrapper", "install") and code != 0:
            break                       # nothing to build without a wrapper / dependencies
    summary["reports"] = report_ids(out, cfg["apps"][app].get("reports", []), cfg["trace"]["spec_id_regex"])
    if app == "android":
        v = gradle_version(p["tdir"])
        jar = out / "gradle/wrapper/gradle-wrapper.jar"
        published_jar = fetch(GRADLE_WRAPPER_JAR.format(v=v))
        summary["gradle"] = {"version": v, "distributionSha256Sum": fetch(GRADLE_DIST.format(v=v)),
                             "wrapper_jar_sha256": lib.sha256_file(jar) if jar.is_file() else None,
                             "wrapper_jar_published_sha256": published_jar}
        summary["gradle"]["wrapper_jar_verified"] = (published_jar is not None
                                                     and published_jar == summary["gradle"]["wrapper_jar_sha256"])
    for rel in p["produced"]:
        summary["produced"][rel] = (out / rel).is_file()
    ran = {s["step"]: s["exit"] for s in summary["steps"]}
    summary["ok"] = ran.get("build") == 0 and ran.get("test") == 0 and summary["reports"]["ok"]
    return summary


def bundle(summaries: list[dict], plans: list[dict], smoke_root: Path, probe_fn=probe) -> Path:
    send = smoke_root / "send-back"
    if send.exists():
        shutil.rmtree(send)
    send.mkdir(parents=True)
    for p, s in zip(plans, summaries):
        for rel in p["produced"]:
            src = p["out"] / rel
            if src.is_file():
                (send / p["app"] / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, send / p["app"] / rel)
        logs = smoke_root / "logs" / p["app"]
        if logs.is_dir():
            shutil.copytree(logs, send / "logs" / p["app"])
    versions = {k: probe_fn(v) for k, v in VERSION_PROBES.items()}
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if versions["sdkmanager"] is None and sdk:
        tool = Path(sdk) / "cmdline-tools" / "latest" / "bin" / "sdkmanager"
        versions["sdkmanager"] = probe_fn([str(tool), "--list_installed"]) if tool.exists() else None
    meta = {"created_at": lib.now_iso(), "platform": platform.platform(), "python": sys.version.split()[0],
            "android_home": sdk, "versions": versions, "apps": summaries}
    lib.write_json_atomic(send / "summary.json", meta)
    zpath = smoke_root / "send-back.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(send.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(send).as_posix())
    return zpath


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--app", default="all", help="android, web or all")
    ap.add_argument("--root", help="repo root (default: harness checkout)")
    ap.add_argument("--dry-run", action="store_true", help="print the steps, run nothing")
    args = ap.parse_args(argv)
    cfg = lib.load_config()
    root = lib.repo_root(args.root)
    apps = list(cfg["apps"]) if args.app == "all" else [args.app]
    if any(a not in cfg["apps"] for a in apps):
        lib.die(f"unknown app in {apps} (config apps: {', '.join(cfg['apps'])})", lib.EXIT_USAGE)
    smoke_root = root / cfg["generate"]["smoke_dir"]
    try:
        plans = [plan_app(a, cfg, root, smoke_root) for a in apps]
    except at.TemplateError as exc:
        lib.die(f"smoke_build: {exc}")
    if args.dry_run:
        for p in plans:
            print(f"# smoke {p['app']} -> {p['out']}")
            print(f"0. apply_templates.py --app {p['app']} --smoke --out {p['out']} --clean")
            for i, (name, cmd, shell, cwd, env) in enumerate(p["steps"], 1):
                envs = " ".join(f"{k}={v}" for k, v in env.items())
                print(f"{i}. {name:<8} (cwd {cwd}) $ {envs + ' ' if envs else ''}{cmd if shell else ' '.join(cmd)}")
            for rel in p["pending"]:
                print(f"   produces {rel} (send back; DEV commits it to generator/templates/{p['app']}/)")
        print(f"then: send-back bundle at {smoke_root / 'send-back.zip'}")
        return lib.EXIT_OK
    summaries = []
    for p in plans:
        print(f"== smoke {p['app']} ==")
        s = run_app(p, cfg, root, smoke_root)
        for step in s["steps"]:
            extra = f"  class {step['class']}: {step['first_error']}" if step.get("class") else ""
            print(f"  {step['step']:<8} exit {step['exit']}{extra}")
        r = s["reports"]
        print(f"  reports  {r['testcases']} testcase(s), {r['with_id']} with a spec id")
        summaries.append(s)
    zpath = bundle(summaries, plans, smoke_root)
    ok = all(s["ok"] for s in summaries)
    print(f"smoke {'PASS' if ok else 'FAIL'}: " + ", ".join(f"{s['app']} {'PASS' if s['ok'] else 'FAIL'}"
                                                           for s in summaries))
    print(f"send back: {zpath}")
    print(json.dumps({s["app"]: s.get("gradle") for s in summaries if s.get("gradle")}, indent=2))
    return lib.EXIT_OK if ok else lib.EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
