#!/usr/bin/env python3
"""Pipeline state machine (generator/WORKFLOW.md §5, §5.1, §5.2, §9).

State lives in .work/STATE.json (schema: generator/schemas/state.schema.json).
Feature-level stages: S0 G0 S1 [S2 G1] APPS S7 DONE, plus G2.
Inside APPS each app runs its own S3 S4 S5 S6 S6b, so apps can proceed in
parallel worktrees (§7). Every transition is checkpointed to STATE.json and
appended to docs/runs/<feature>/run.jsonl.

Examples:
  state.py init [--autonomous]
  state.py start-feature F1 --title "..." --apps android,web --chain full
  state.py transition --event delta
  state.py transition --app web --event blockers --expect-stage S4
  state.py transition --event approve --decided-by operator --log-extra '{"operator_msg_ref":"OM-0010"}'
  state.py status | render | model --role REV --changed-lines 512
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import awarelib as lib

FEATURE_STAGES = ("S0", "G0", "S1", "S2", "G1", "APPS", "G2", "S7", "DONE")
APP_STAGES = ("PENDING", "S3", "S4", "S5", "S6", "S6b", "DONE")
GATES = ("G0", "G1", "G2")
STAGE_ORDER = {s: i for i, s in enumerate(("S0", "G0", "S1", "S2", "G1", "S3", "S4", "S5", "S6", "S6b", "S7"))}

# Who produces the outcome at each stage (used for logging and `status`).
STAGE_ROLE = {"S0": "PM+TL", "S1": "PM", "S2": "TL", "S3": "DEV", "S4": "REV",
              "S5": "QA", "S6": "SCRIPT", "S6b": "ORC", "S7": "ORC"}
AGENT_FEATURE_STAGES = ("S0", "S1", "S2")

# Stage outcome events. Return codes (§5.1) are handled separately.
FEATURE_EVENTS = {
    "S0": ("delta", "no_delta"),
    "G0": ("approve", "revise", "descope"),
    "S1": ("ok", "needs_arch"),
    "S2": ("ok",),
    "G1": ("approve", "revise_plan", "revise_spec", "descope", "eval_failed"),
    "G2": ("change_spec", "replan", "one_more_round", "defer", "stop"),
    "S7": ("ok",),
}
APP_EVENTS = {
    "S3": ("ok", "self_repair_exhausted"),
    "S4": ("pass", "blockers", "design_concern"),
    "S5": ("green", "flow_change", "nit_fix", "untestable", "exhausted"),
    "S6": ("met", "unmet_code", "unmet_spec", "new_work"),
    "S6b": ("green", "fail"),
}
RC_EVENTS = ("SPEC_ISSUE", "PLAN_DEVIATION", "STALE_DIFF", "ENV_FAILURE", "BLOCKED")
GLOBAL_EVENTS = ("escalate", "budget_soft", "budget_hard", "snapshot")
ALLOWED_WHILE_STALE = ("snapshot", "STALE_DIFF", "BLOCKED", "ENV_FAILURE", "escalate", "budget_soft", "budget_hard")
APP_COUNTERS = ("review_rounds", "qa_fix", "accept_reopen", "regen_check", "env_retry", "stale_diff")
FEATURE_COUNTERS = ("spec_reopen", "g1_rejections", "env_retry", "stale_diff")
RESET_ON_STAGE_CHANGE = ("env_retry",)
OPERATOR = "operator"


class TransitionError(Exception):
    """Raised for an illegal or ill-formed transition; state is left unchanged."""


def default_state_path(root: Path) -> Path:
    return root / ".work" / "STATE.json"


class Machine:
    def __init__(self, state: dict, caps: dict, root: Path | None = None, log: bool = True):
        self.s = state
        self.caps = caps
        self.root = root
        self.log = log and root is not None

    # ------------------------------------------------------------ persistence
    @staticmethod
    def new_state(mode: str = "interactive") -> dict:
        return {"schema_version": 1, "mode": mode, "seq": 0, "current_feature": None,
                "features": {}, "updated_at": lib.now_iso()}

    @classmethod
    def load(cls, path: Path, caps: dict, root: Path | None = None, log: bool = True) -> "Machine":
        state = lib.read_json(path)
        cls.check(state)
        return cls(state, caps, root, log)

    @staticmethod
    def check(state: dict) -> None:
        errs = lib.validate(state, lib.load_schema("state.schema.json"))
        if errs:
            raise TransitionError("STATE.json invalid: " + "; ".join(errs[:5]))

    def save(self, path: Path) -> None:
        self.check(self.s)
        lib.write_json_atomic(path, self.s)

    # ---------------------------------------------------------------- helpers
    def feature(self, fid: str | None) -> dict:
        fid = fid or self.s["current_feature"]
        if not fid:
            raise TransitionError("no feature given and no current feature; use --feature")
        if fid not in self.s["features"]:
            raise TransitionError(f"unknown feature '{fid}'")
        return self.s["features"][fid]

    def cap(self, holder: dict, name: str) -> int:
        return self.caps[name] + holder["cap_extra"].get(name, 0)

    @staticmethod
    def bump(holder: dict, name: str) -> int:
        holder["counters"][name] = holder["counters"].get(name, 0) + 1
        return holder["counters"][name]

    def exceeded(self, holder: dict, name: str) -> bool:
        return holder["counters"].get(name, 0) > self.cap(holder, name)

    @staticmethod
    def display(f: dict, app: str | None) -> str:
        if f["stage"] == "APPS" and app:
            return f["apps"][app]["stage"]
        return f["stage"]

    def autonomous(self) -> bool:
        return self.s["mode"] == "autonomous"

    @staticmethod
    def set_app_stage(a: dict, stage: str) -> None:
        if a["stage"] != stage:
            for c in RESET_ON_STAGE_CHANGE:
                a["counters"][c] = 0
        a["stage"] = stage

    @staticmethod
    def set_feature_stage(f: dict, stage: str) -> None:
        if f["stage"] != stage:
            for c in RESET_ON_STAGE_CHANGE:
                f["counters"][c] = 0
        f["stage"] = stage

    def reset_apps(self, f: dict) -> None:
        for a in f["apps"].values():
            self.set_app_stage(a, "PENDING")
            a["after_fix"] = None
            a["needs_snapshot"] = False

    # ---------------------------------------------------------- stage moves
    def enter_apps(self, f: dict) -> None:
        self.set_feature_stage(f, "APPS")
        for a in f["apps"].values():
            self.set_app_stage(a, "S3")
            a["after_fix"] = None

    def to_stage(self, f: dict, stage: str) -> None:
        """Move back to a feature-level stage; every app waits for the next APPS entry."""
        self.set_feature_stage(f, stage)
        self.reset_apps(f)

    def block(self, f: dict, reason: str, app: str | None = None) -> None:
        f["status"] = "blocked"
        f["blocked"] = {"stage": f["stage"], "app": app,
                        "app_stage": f["apps"][app]["stage"] if app else None, "reason": reason}

    def enter_gate(self, f: dict, gate: str, reason: str) -> None:
        self.set_feature_stage(f, gate)
        if self.autonomous() and gate in ("G0", "G2"):
            self.block(f, f"autonomous mode halts at {gate}: {reason}")

    def enter_g2(self, f: dict, reason: str, app: str | None = None, app_stage: str | None = None,
                 counter: str | None = None, resume: str | None = None) -> None:
        f["g2"] = {"stage": "APPS" if app else (resume or f["stage"]), "app": app,
                   "app_stage": app_stage, "counter": counter, "reason": reason}
        self.enter_gate(f, "G2", reason)

    def reopen_spec(self, f: dict, reason: str) -> None:
        self.bump(f, "spec_reopen")
        if self.exceeded(f, "spec_reopen"):
            self.enter_g2(f, f"spec_reopen cap exceeded: {reason}", counter="spec_reopen", resume="S0")
        else:
            self.to_stage(f, "S0")

    # -------------------------------------------------------------- public
    def start_feature(self, fid: str, title: str, apps: list[str], chain: str, budget: dict | None = None) -> dict:
        if fid in self.s["features"]:
            raise TransitionError(f"feature '{fid}' already exists")
        if chain not in ("full", "light"):
            raise TransitionError("chain must be full or light")
        if not apps:
            raise TransitionError("at least one app is required")
        f = {
            "id": fid, "title": title, "chain": chain, "status": "active", "stage": "S0",
            "apps": {a: {"stage": "PENDING", "counters": {c: 0 for c in APP_COUNTERS}, "cap_extra": {},
                         "after_fix": None, "needs_snapshot": False, "head_sha": None} for a in apps},
            "counters": {c: 0 for c in FEATURE_COUNTERS}, "cap_extra": {}, "needs_snapshot": False,
            "g2": None, "blocked": None, "flagged_for_review": [], "backlog_notes": [],
            "budget": budget or {}, "history": [],
        }
        self.s["features"][fid] = f
        cur = self.s["current_feature"]
        if cur is None or self.s["features"][cur]["status"] != "active":
            self.s["current_feature"] = fid
        self.record(f, "start_feature", None, "-", "S0", None, {})
        return f

    def transition(self, fid: str | None, event: str, app: str | None = None, detail: str | None = None,
                   decided_by: str | None = None, target: str | None = None, evals_passed: bool = False,
                   expect_stage: str | None = None, log_extra: dict | None = None) -> dict:
        f = self.feature(fid)
        if app is not None and app not in f["apps"]:
            raise TransitionError(f"feature {f['id']} has no app '{app}' (apps: {', '.join(f['apps'])})")
        before = self.display(f, app)
        if expect_stage and expect_stage != before:
            raise TransitionError(f"expected stage {expect_stage} but feature {f['id']}"
                                  f"{'/' + app if app else ''} is at {before}; refusing (already applied?)")
        snapshot = json.dumps(f)
        try:
            self.dispatch(f, event, app, detail, decided_by, target, evals_passed)
        except TransitionError:
            self.s["features"][f["id"]] = json.loads(snapshot)
            raise
        after = self.display(f, app)
        return self.record(f, event, app, before, after, detail, log_extra or {}, decided_by)

    # ------------------------------------------------------------- dispatch
    def dispatch(self, f, ev, app, detail, decided_by, target, evals_passed):
        if f["status"] in ("done", "aborted", "descoped"):
            raise TransitionError(f"feature {f['id']} is {f['status']}; no further transitions")
        if f["status"] == "blocked":
            if ev != "unblock":
                raise TransitionError(f"feature {f['id']} is blocked ({f['blocked']['reason']}); "
                                      "only 'unblock --decided-by operator' is allowed")
            self.need_operator(decided_by, "unblock")
            f["status"], f["blocked"] = "active", None
            return
        if ev == "unblock":
            raise TransitionError("feature is not blocked")

        stage = f["stage"]
        holder = f["apps"][app] if (stage == "APPS" and app) else f
        if holder["needs_snapshot"] and ev not in ALLOWED_WHILE_STALE:
            raise TransitionError("STALE_DIFF pending: run snapshot_diff.py, then "
                                  "`state.py transition --event snapshot` before relaunching the stage")
        if ev in GLOBAL_EVENTS:
            return self.global_event(f, ev, app, detail)
        if stage == "APPS":
            if not app:
                raise TransitionError(f"feature {f['id']} is in per-app stages; pass --app "
                                      f"({', '.join(f'{k}:{v['stage']}' for k, v in f['apps'].items())})")
            return self.app_event(f, app, ev, detail, target)
        return self.feature_event(f, ev, detail, decided_by, target, evals_passed)

    def need_operator(self, decided_by, what):
        if decided_by != OPERATOR:
            raise TransitionError(f"{what} is an operator decision; pass --decided-by operator")

    def illegal(self, ev, stage, allowed):
        raise TransitionError(f"event '{ev}' is not allowed at {stage}. Allowed: {', '.join(allowed)}")

    def global_event(self, f, ev, app, detail):
        if f["stage"] in GATES and ev in ("escalate", "snapshot"):
            raise TransitionError(f"'{ev}' is not meaningful at gate {f['stage']}")
        app_level = f["stage"] == "APPS" and app
        if ev == "snapshot":
            holder = f["apps"][app] if app_level else f
            holder["needs_snapshot"] = False
            if app_level:
                holder["head_sha"] = detail
        elif ev == "budget_soft":
            pass  # noted in the run log, surfaces in the retro
        elif ev in ("escalate", "budget_hard"):
            reason = f"{ev}: {detail or 'no detail'}"
            if app_level:
                self.enter_g2(f, reason, app=app, app_stage=f["apps"][app]["stage"])
            else:
                self.enter_g2(f, reason)

    def return_code(self, f, ev, stage, detail, app=None):
        holder = f["apps"][app] if app else f
        if ev == "STALE_DIFF":
            holder["needs_snapshot"] = True
            self.bump(holder, "stale_diff")
        elif ev == "ENV_FAILURE":
            self.bump(holder, "env_retry")
            if self.exceeded(holder, "env_retry"):
                self.enter_g2(f, f"ENV_FAILURE after retry at {stage}: {detail}", app=app,
                              app_stage=stage if app else None, counter="env_retry", resume=stage)
        elif ev == "BLOCKED":
            self.block(f, f"agent BLOCKED at {stage}: {detail}", app)
        elif ev == "SPEC_ISSUE":
            self.reopen_spec(f, f"SPEC_ISSUE at {stage}: {detail}")
        elif ev == "PLAN_DEVIATION":
            if stage != "S3":
                self.illegal(ev, stage, ["PLAN_DEVIATION only at S3; use escalate"])
            self.to_stage(f, "S2")

    def feature_event(self, f, ev, detail, decided_by, target, evals_passed):
        stage = f["stage"]
        allowed = list(FEATURE_EVENTS.get(stage, ()))
        if stage in AGENT_FEATURE_STAGES:
            allowed += [rc for rc in RC_EVENTS if rc != "PLAN_DEVIATION"]
        if ev not in allowed:
            self.illegal(ev, stage, allowed)
        if ev in RC_EVENTS:
            return self.return_code(f, ev, stage, detail)

        if stage == "S0":
            if ev == "delta":
                self.enter_gate(f, "G0", "spec delta awaits approval")
            else:
                self.set_feature_stage(f, "S1")
        elif stage == "G0":
            self.need_operator(decided_by, "G0")
            if ev == "approve":
                self.set_feature_stage(f, "S1")
            elif ev == "revise":
                self.set_feature_stage(f, "S0")
            else:
                f["status"] = "descoped"
        elif stage == "S1":
            if ev == "needs_arch":
                f["chain"] = "full"
            if f["chain"] == "full":
                self.set_feature_stage(f, "S2")
            else:
                self.enter_apps(f)
        elif stage == "S2":
            self.enter_gate(f, "G1", "plan awaits approval")
        elif stage == "G1":
            self.g1(f, ev, detail, decided_by, evals_passed)
        elif stage == "G2":
            self.need_operator(decided_by, "G2")
            self.g2(f, ev)
        elif stage == "S7":
            self.set_feature_stage(f, "DONE")
            f["status"] = "done"
            if self.s["current_feature"] == f["id"]:
                self.s["current_feature"] = None

    def g1(self, f, ev, detail, decided_by, evals_passed):
        auto = self.autonomous() and decided_by != OPERATOR
        if ev == "eval_failed":
            if self.autonomous():
                self.block(f, f"G1 evals failed in autonomous mode: {detail}")
            return
        if auto:
            if ev != "approve" or not evals_passed:
                raise TransitionError("autonomous G1 only auto-approves with --evals-passed (E-TL-1); "
                                      "otherwise send eval_failed")
            f["flagged_for_review"].append(f"G1 auto-approved (E-TL-1 passed): {detail or ''}".strip())
        else:
            self.need_operator(decided_by, "G1")
        if ev == "approve":
            self.enter_apps(f)
        elif ev == "revise_plan":
            self.bump(f, "g1_rejections")
            if self.exceeded(f, "g1_rejections"):
                self.enter_g2(f, "g1_rejections cap exceeded: operator discussion needed",
                              counter="g1_rejections", resume="S2")
            else:
                self.to_stage(f, "S2")
        elif ev == "revise_spec":
            self.reopen_spec(f, f"G1 revise-spec: {detail}")
        elif ev == "descope":
            f["status"] = "descoped"

    def g2(self, f, ev):
        g = f["g2"] or {"stage": "S0", "app": None, "app_stage": None, "counter": None}
        if ev == "change_spec":
            self.to_stage(f, "S0")
        elif ev == "replan":
            self.to_stage(f, "S2")
        elif ev == "one_more_round":
            holder = f["apps"][g["app"]] if g.get("app") else f
            if g.get("counter"):
                holder["cap_extra"][g["counter"]] = holder["cap_extra"].get(g["counter"], 0) + 1
            if g.get("app"):
                self.set_feature_stage(f, "APPS")
                self.set_app_stage(holder, g["app_stage"])
            elif g["stage"] in ("S0", "S2"):
                self.to_stage(f, g["stage"])
            else:
                self.set_feature_stage(f, g["stage"])
        elif ev == "defer":
            f["status"] = "descoped"
        elif ev == "stop":
            f["status"] = "aborted"
        if ev != "defer" and ev != "stop":
            f["g2"] = None

    def app_event(self, f, app, ev, detail, target):
        a = f["apps"][app]
        st = a["stage"]
        allowed = list(APP_EVENTS.get(st, ()))
        if st in APP_EVENTS:
            allowed += [rc for rc in RC_EVENTS if rc != "PLAN_DEVIATION" or st == "S3"]
        if ev not in allowed:
            self.illegal(ev, f"{app}:{st}", allowed or ["(none: app is " + st + ")"])
        if ev in RC_EVENTS:
            return self.return_code(f, ev, st, detail, app)

        review_full = a["counters"]["review_rounds"] >= self.cap(a, "review_rounds")
        if st == "S3":
            if ev == "self_repair_exhausted":
                return self.enter_g2(f, f"/generate self-repair exhausted: {detail}", app=app, app_stage="S3")
            nxt = a["after_fix"] or "S4"
            a["after_fix"] = None
            if nxt == "S4" and review_full:
                return self.enter_g2(f, "review_rounds cap reached before another review", app=app,
                                     app_stage="S4", counter="review_rounds")
            self.set_app_stage(a, nxt)
        elif st == "S4":
            if ev == "design_concern":
                if target == "plan":
                    return self.to_stage(f, "S2")
                if target == "spec":
                    return self.reopen_spec(f, f"design-concern at review: {detail}")
                raise TransitionError("design_concern needs --target plan|spec")
            rounds = self.bump(a, "review_rounds")
            if ev == "pass":
                self.set_app_stage(a, "S5")
            elif rounds >= self.cap(a, "review_rounds"):
                self.enter_g2(f, f"blockers after review round {rounds}", app=app, app_stage="S3",
                              counter="review_rounds")
            else:
                self.set_app_stage(a, "S3")
        elif st == "S5":
            if ev == "green":
                self.set_app_stage(a, "S6")
            elif ev == "flow_change":
                a["after_fix"] = None
                if review_full:
                    return self.enter_g2(f, "QA flow change but review_rounds cap reached", app=app,
                                         app_stage="S3", counter="review_rounds")
                self.set_app_stage(a, "S3")
            elif ev == "nit_fix":
                a["after_fix"] = "S5"
                self.bump(a, "qa_fix")
                if self.exceeded(a, "qa_fix"):
                    return self.enter_g2(f, "qa_fix cap exceeded", app=app, app_stage="S3", counter="qa_fix")
                self.set_app_stage(a, "S3")
            elif ev == "untestable":
                self.reopen_spec(f, f"untestable AC at QA: {detail}")
            elif ev == "exhausted":
                self.enter_g2(f, f"QA exhausted: {detail}", app=app, app_stage="S5")
        elif st == "S6":
            if ev == "met":
                self.set_app_stage(a, "S6b")
            elif ev == "unmet_code":
                self.bump(a, "accept_reopen")
                if self.exceeded(a, "accept_reopen"):
                    return self.enter_g2(f, "second unmet acceptance", app=app, app_stage="S3",
                                         counter="accept_reopen")
                self.set_app_stage(a, "S3")
            elif ev == "unmet_spec":
                self.reopen_spec(f, f"acceptance spec gap: {detail}")
            elif ev == "new_work":
                f["backlog_notes"].append(detail or "(no detail)")
        elif st == "S6b":
            if ev == "green":
                self.set_app_stage(a, "DONE")
                if all(x["stage"] == "DONE" for x in f["apps"].values()):
                    self.set_feature_stage(f, "S7")
            else:
                self.bump(a, "regen_check")
                if self.exceeded(a, "regen_check"):
                    return self.enter_g2(f, "regen_check cap exceeded", app=app, app_stage="S3",
                                         counter="regen_check")
                self.set_app_stage(a, "S3")

    # ------------------------------------------------------------- recording
    def record(self, f, event, app, before, after, detail, extra, decided_by=None) -> dict:
        self.s["seq"] += 1
        ts = lib.now_iso()
        self.s["updated_at"] = ts
        entry = {"seq": self.s["seq"], "ts": ts, "event": event, "app": app, "from": before, "to": after,
                 "detail": detail}
        f["history"].append(entry)
        if self.log:
            counters = {"feature": dict(f["counters"])}
            for name, a in f["apps"].items():
                if app is None or name == app:
                    counters[name] = dict(a["counters"])
            agent = STAGE_ROLE.get(before)
            if before in GATES:
                agent = "OP" if decided_by == OPERATOR else "ORC"
            gate = before if before in GATES else (after if after in GATES else None)
            ev = {"feature": f["id"], "app": app, "stage": before, "event": event,
                  "transition": {"from": before, "to": after, "status": f["status"]},
                  "agent": agent, "counters": counters, "gate": gate, "decided_by": decided_by,
                  "return_code": event if event in lib.RETURN_CODES else None, "detail": detail}
            ev.update(extra)
            lib.append_run_event(self.root, ev)
        return entry


# ------------------------------------------------------------------ queries
def next_actions(f: dict) -> list[str]:
    if f["status"] == "blocked":
        return [f"BLOCKED at {f['stage']}: {f['blocked']['reason']} -> operator: unblock"]
    if f["status"] != "active":
        return [f"{f['status']}"]
    st = f["stage"]
    if st in GATES:
        hint = {"G0": "approve | revise | descope", "G1": "approve | revise_plan | revise_spec | descope",
                "G2": "change_spec | replan | one_more_round | defer | stop"}[st]
        reason = f" ({f['g2']['reason']})" if st == "G2" and f.get("g2") else ""
        return [f"wait for operator at {st}{reason}: {hint}"]
    if st == "APPS":
        out = []
        for name, a in f["apps"].items():
            if a["stage"] == "DONE":
                out.append(f"{name}: done")
                continue
            stale = " (re-snapshot first)" if a["needs_snapshot"] else ""
            out.append(f"{name}: {a['stage']} -> {STAGE_ROLE[a['stage']]}{stale} "
                       f"[{', '.join(APP_EVENTS[a['stage']])}]")
        return out
    stale = " (re-snapshot first)" if f.get("needs_snapshot") else ""
    return [f"{st} -> {STAGE_ROLE[st]}{stale} [{', '.join(FEATURE_EVENTS[st])}]"]


def render_md(state: dict) -> str:
    lines = ["# Pipeline state", "", f"- Mode: {state['mode']}", f"- Current feature: {state['current_feature']}",
             f"- Updated: {state['updated_at']} (seq {state['seq']})", "",
             "| Feature | Chain | Status | Stage | Apps | Feature counters | Next |", "|---|---|---|---|---|---|---|"]
    for f in state["features"].values():
        apps = "<br>".join(f"{k}: {v['stage']} " + ",".join(f"{c}={n}" for c, n in v["counters"].items() if n)
                           for k, v in f["apps"].items())
        fc = ",".join(f"{c}={n}" for c, n in f["counters"].items() if n) or "-"
        lines.append(f"| {f['id']} {f['title']} | {f['chain']} | {f['status']} | {f['stage']} | {apps} | {fc} | "
                     + "<br>".join(next_actions(f)) + " |")
    flagged = [(f["id"], x) for f in state["features"].values() for x in f["flagged_for_review"]]
    if flagged:
        lines += ["", "## Flagged for operator review", *[f"- {fid}: {x}" for fid, x in flagged]]
    return "\n".join(lines) + "\n"


def choose_model(role: str, changed_lines: int = 0, first_gen: bool = False, concurrency: bool = False,
                 interpretation: bool = False, cfg: dict | None = None) -> tuple[str, str]:
    """Model rules from WORKFLOW §2. Returns (alias, reason)."""
    cfg = cfg or lib.load_config()
    threshold = cfg["limits"]["rev_opus_changed_lines"]
    if role == "TL":
        return "opus", "tech lead always runs on opus"
    if role == "PM":
        return "sonnet", "product work maps to approved inputs"
    if role == "DEV":
        if first_gen or interpretation:
            return "opus", "first generation or interpretation needed"
        return "sonnet", "change maps objectively to an approved plan"
    if role == "REV":
        if changed_lines > threshold:
            return "opus", f"changed_lines {changed_lines} > {threshold}"
        if first_gen or concurrency:
            return "opus", "first generation of a module" if first_gen else "concurrency/threading paths"
        return "sonnet", f"changed_lines {changed_lines} <= {threshold}"
    if role == "QA":
        return ("opus", "designing a new suite") if first_gen else ("sonnet", "extending an existing suite")
    raise ValueError(f"no model rule for role {role}")


# ---------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", help="data root (default: harness checkout)")
    p.add_argument("--state", help="state file (default: <root>/.work/STATE.json)")
    p.add_argument("--no-log", action="store_true", help="do not append to docs/runs/<feature>/run.jsonl")
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init", help="create STATE.json")
    i.add_argument("--autonomous", action="store_true")
    i.add_argument("--force", action="store_true", help="overwrite an existing STATE.json")
    m = sub.add_parser("set-mode", help="switch interactive/autonomous")
    m.add_argument("mode", choices=["interactive", "autonomous"])
    sf = sub.add_parser("start-feature", help="register a feature at S0")
    sf.add_argument("feature")
    sf.add_argument("--title", default="")
    sf.add_argument("--apps", required=True, help="comma list, e.g. android,web or server")
    sf.add_argument("--chain", choices=["full", "light"], required=True)
    sf.add_argument("--budget", help="JSON object, e.g. '{\"tokens_hard\": 2000000}'")
    sel = sub.add_parser("select", help="set the current feature")
    sel.add_argument("feature")
    t = sub.add_parser("transition", help="apply one event")
    t.add_argument("--feature")
    t.add_argument("--app")
    t.add_argument("--event", required=True)
    t.add_argument("--detail")
    t.add_argument("--target", choices=["plan", "spec"], help="for design_concern")
    t.add_argument("--decided-by", help="'operator' for gate decisions")
    t.add_argument("--evals-passed", action="store_true", help="autonomous G1: E-TL-1 passed")
    t.add_argument("--expect-stage", help="refuse unless the feature/app is at this stage (resume safety)")
    t.add_argument("--log-extra", help="JSON object merged into the run-log event (model, prompt_sha256, ...)")
    st = sub.add_parser("status", help="print features, stages, counters and next actions")
    st.add_argument("--json", action="store_true")
    sub.add_parser("render", help="write .work/STATE.md")
    mo = sub.add_parser("model", help="pick the model for a role launch (WORKFLOW §2)")
    mo.add_argument("--role", required=True, choices=["PM", "TL", "DEV", "REV", "QA"])
    mo.add_argument("--changed-lines", type=int, default=0)
    mo.add_argument("--first-gen", action="store_true", help="first generation of a module/app or new QA suite")
    mo.add_argument("--concurrency", action="store_true")
    mo.add_argument("--interpretation", action="store_true")
    args = p.parse_args(argv)

    root = lib.repo_root(args.root)
    path = Path(args.state) if args.state else default_state_path(root)
    cfg = lib.load_config()
    caps = cfg["limits"]["caps"]

    if args.cmd == "model":
        alias, reason = choose_model(args.role, args.changed_lines, args.first_gen, args.concurrency,
                                     args.interpretation, cfg)
        print(f"{alias}\t{reason}")
        return lib.EXIT_OK
    if args.cmd == "init":
        if path.exists() and not args.force:
            print(f"{path} exists; loaded (use --force to reset)")
            return lib.EXIT_OK
        mach = Machine(Machine.new_state("autonomous" if args.autonomous else "interactive"), caps)
        mach.save(path)
        print(f"initialised {path} ({mach.s['mode']})")
        return lib.EXIT_OK
    if not path.exists():
        lib.die(f"{path} not found; run `state.py init` first", lib.EXIT_USAGE)
    try:
        mach = Machine.load(path, caps, root, log=not args.no_log)
        if args.cmd == "set-mode":
            mach.s["mode"] = args.mode
        elif args.cmd == "start-feature":
            mach.start_feature(args.feature, args.title, [a for a in args.apps.split(",") if a], args.chain,
                               json.loads(args.budget) if args.budget else None)
        elif args.cmd == "select":
            mach.feature(args.feature)
            mach.s["current_feature"] = args.feature
        elif args.cmd == "transition":
            extra = json.loads(args.log_extra) if args.log_extra else None
            fid = mach.feature(args.feature)["id"]
            entry = mach.transition(fid, args.event, args.app, args.detail, args.decided_by, args.target,
                                    args.evals_passed, args.expect_stage, extra)
            f = mach.s["features"][fid]
            print(f"{fid}{'/' + args.app if args.app else ''}: {entry['from']} --{entry['event']}--> "
                  f"{entry['to']}  [{f['status']}]")
            for line in next_actions(f):
                print("  next: " + line)
        elif args.cmd == "status":
            if args.json:
                print(json.dumps(mach.s, indent=2))
            else:
                print(f"mode={mach.s['mode']} current={mach.s['current_feature']} seq={mach.s['seq']}")
                for f in mach.s["features"].values():
                    print(f"- {f['id']} [{f['chain']}/{f['status']}] stage={f['stage']} counters={f['counters']}")
                    for line in next_actions(f):
                        print(f"    {line}")
            return lib.EXIT_OK
        elif args.cmd == "render":
            out = path.with_name("STATE.md")
            out.write_text(render_md(mach.s), encoding="utf-8")
            print(f"wrote {out}")
            return lib.EXIT_OK
        mach.save(path)
    except TransitionError as exc:
        lib.die(f"refused: {exc}", lib.EXIT_ILLEGAL)
    return lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
