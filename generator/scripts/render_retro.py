#!/usr/bin/env python3
"""Render docs/retros/<feature>.md from docs/runs/<feature>/run.jsonl (WORKFLOW §10).

Uses the section order of docs/retros/TEMPLATE.md. The header fields and the
tables (pipeline run, backward transitions, authorship, budget) are filled
from the run log; narrative sections are left for ORC (and "Human notes" for
the operator). Re-rendering keeps narrative text already written in the retro.

Example:
  render_retro.py --feature F1 --title "Identity" --update-index
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

import awarelib as lib
from state import STAGE_ORDER, default_state_path

ROUND_COUNTER = {"S4": "review_rounds", "S5": "qa_fix", "S6": "accept_reopen", "S6b": "regen_check"}
INDEX_HEADER = ["# Run index", "",
                "One row per feature run through `/pipeline` (written by "
                "`generator/scripts/render_retro.py --update-index` at S7).", "",
                "| Feature | Title | Status | Run log | Retro |", "|---|---|---|---|---|"]


def split_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Return (preamble, [(heading line, body)]) split on '## ' headings."""
    parts = re.split(r"(?m)^(## .*)$", text)
    return parts[0], [(parts[i], parts[i + 1]) for i in range(1, len(parts), 2)]


def _parse_ts(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))


def boundary_and_author(path: str) -> tuple[str, str]:
    if path.startswith("clients/"):
        return "generated", "agent (via /generate)"
    if path.startswith("docs/human-input/"):
        return "maintained", "human"
    if path.startswith("spec/"):
        return "maintained", "agent-drafted, human-approved"
    return "maintained", "agent"


def is_backward(src: str, dst: str) -> bool:
    if dst == "G2":
        return True
    return src in STAGE_ORDER and dst in STAGE_ORDER and STAGE_ORDER[dst] < STAGE_ORDER[src]


def table(header: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c).replace("|", "\\|") for c in r) + " |" for r in rows]
    return "\n".join(out)


def summarize(events: list[dict], state_feature: dict | None) -> dict:
    trans = [e for e in events if "transition" in e]
    start = next((e for e in events if e["event"] == "start_feature"), {})
    chain = (state_feature or {}).get("chain") or (re.search(r"chain=(\w+)", start.get("detail", "")) or [None, "?"])[1]
    specs = [e["spec_version"] for e in events if e.get("spec_version")]
    regen = [e for e in trans if e.get("stage") == "S6b"]
    accept = [e for e in events if e.get("stage") == "S6" and isinstance(e.get("result"), dict)]
    return {
        "date": events[-1]["ts"][:10] if events else "",
        "chain": chain,
        "apps": sorted({e["app"] for e in events if e.get("app")}),
        "spec": f"in {specs[0]} → out {specs[-1]}" if specs else "in ? → out ?",
        "regen": (f"{'pass' if any(e['event'] == 'green' for e in regen) else 'fail'} "
                  f"({len(regen)} attempt(s))") if regen else "not run",
        "oms": sorted({e["operator_msg_ref"] for e in events if e.get("operator_msg_ref")}),
        "merge": next((e.get("commit") for e in reversed(events) if e["event"] == "merge"), ""),
        "met": accept[-1]["result"].get("met", []) if accept else [],
        "unmet": accept[-1]["result"].get("unmet", []) if accept else [],
        "trans": trans,
    }


def render_tables(events: list[dict], info: dict, state_feature: dict | None) -> dict[str, str]:
    rows = []
    for e in info["trans"]:
        if e["event"] == "start_feature":
            continue
        stage = e["transition"]["from"]
        counter = ROUND_COUNTER.get(stage)
        rounds = ""
        if counter and e.get("app") and e.get("counters", {}).get(e["app"]):
            rounds = str(e["counters"][e["app"]].get(counter, ""))
        model = e.get("model", "")
        if e.get("model_reason"):
            model = f"{model} ({e['model_reason']})"
        where = f"{stage} [{e['app']}]" if e.get("app") else stage
        rows.append([where, e.get("agent", ""), model, rounds, f"{e['event']} → {e['transition']['to']}",
                     (e.get("commit") or e.get("head_sha") or "")[:10]])
    back = [[f"{e['transition']['from']} → {e['transition']['to']}" + (f" [{e['app']}]" if e.get("app") else ""),
             e["event"] + (f": {e['detail']}" if e.get("detail") else "")]
            for e in info["trans"] if is_backward(e["transition"]["from"], e["transition"]["to"])]
    outputs = sorted({p for e in events for p in e.get("outputs", [])})
    authorship = [[p, *boundary_and_author(p)] for p in outputs]
    budget = (state_feature or {}).get("budget", {})
    wall = ""
    if len(events) > 1:
        wall = str(_parse_ts(events[-1]["ts"]) - _parse_ts(events[0]["ts"]))
    tokens = sum(e.get("tokens", 0) for e in events)
    agent_time = sum(e.get("duration", 0) for e in events)
    budget_rows = [["Wall time", budget.get("wall_hard", budget.get("wall_soft", "")), f"{wall} (agent time {agent_time:.0f}s)"],
                   ["Tokens", budget.get("tokens_hard", budget.get("tokens_soft", "")), str(tokens)]]
    return {
        "Pipeline run": table(["Stage", "Agent", "Model (reason)", "Rounds", "Result", "Commit"], rows),
        "Backward transitions": table(["From → To", "Return code / reason"], back),
        "Authorship of files touched": table(["Path", "Boundary (generated / maintained)",
                                              "Authorship (human / agent-drafted, human-approved / agent)"], authorship),
        "Budget": table(["", "Cap", "Actual"], budget_rows),
        "Delivered": f"- ACs met (ids): {', '.join(info['met'])}\n- ACs unmet / deferred: {', '.join(info['unmet'])}",
    }


def render(template: str, feature: str, title: str, events: list[dict], state_feature: dict | None,
           existing: str | None = None) -> str:
    template = template.replace("<feature-id>", feature)
    info = summarize(events, state_feature)
    tables = render_tables(events, info, state_feature)
    pre, sections = split_sections(template)
    kept = dict(split_sections(existing)[1]) if existing else {}
    fields = {"Date": info["date"], "Chain": info["chain"], "Apps touched": ", ".join(info["apps"]),
              "Spec version": info["spec"], "Branch / merge commit": f"feat/{feature} / {info['merge']}".rstrip(" /"),
              "Regen-check (S6b)": info["regen"], "Operator interventions": ", ".join(info["oms"])}
    pre = pre.replace("<feature name>", title or feature)
    for key, val in fields.items():
        pre = re.sub(rf"(?m)^- {re.escape(key)}:.*$", lambda m, k=key, v=val: f"- {k}: {v}", pre)
    out = [pre.rstrip() + "\n"]
    for heading, body in sections:
        name = heading[3:].split(" (")[0].strip()
        if name in tables:
            out.append(f"{heading}\n{tables[name]}\n")
        elif heading in kept:
            out.append(f"{heading}{kept[heading].rstrip()}\n")
        else:
            who = "operator" if name.startswith("Human notes") else "ORC"
            out.append(f"{heading}\n<!-- {who}: fill in -->{body.rstrip()}\n")
    return "\n".join(out)


def update_index(root: Path, feature: str, title: str, status: str) -> Path:
    path = root / "docs" / "runs" / "INDEX.md"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else list(INDEX_HEADER)
    row = f"| {feature} | {title} | {status} | [run.jsonl]({feature}/run.jsonl) | [retro](../retros/{feature}.md) |"
    lines = [ln for ln in lines if not ln.startswith(f"| {feature} |")]
    lines.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--feature", required=True)
    p.add_argument("--title", default="")
    p.add_argument("--root", help="data root (default: harness checkout)")
    p.add_argument("--template", help="default: <harness>/docs/retros/TEMPLATE.md")
    p.add_argument("--out", help="default: <root>/docs/retros/<feature>.md")
    p.add_argument("--update-index", action="store_true", help="upsert the feature row in docs/runs/INDEX.md")
    args = p.parse_args(argv)
    root = lib.repo_root(args.root)
    events = lib.read_run_events(root, args.feature)
    if not events:
        lib.die(f"no run log for {args.feature} under {root}/docs/runs/", lib.EXIT_USAGE)
    state_path = default_state_path(root)
    feat = lib.read_json(state_path)["features"].get(args.feature) if state_path.exists() else None
    title = args.title or (feat or {}).get("title", "")
    template = Path(args.template or lib.HARNESS_ROOT / "docs" / "retros" / "TEMPLATE.md").read_text(encoding="utf-8")
    out = Path(args.out) if args.out else root / "docs" / "retros" / f"{args.feature}.md"
    existing = out.read_text(encoding="utf-8") if out.exists() else None
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(template, args.feature, title, events, feat, existing), encoding="utf-8")
    print(f"wrote {out}")
    if args.update_index:
        status = (feat or {}).get("status", events[-1].get("transition", {}).get("status", "?"))
        print(f"updated {update_index(root, args.feature, title, status)}")
    return lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
