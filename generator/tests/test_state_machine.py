"""E-WF-1 (state machine mechanics) and E-WF-2 (resume) for generator/scripts/state.py.

Stub agents are simulated by injecting their return codes / stage outcomes as events.
"""
import json
import tempfile
import unittest
from pathlib import Path

from _util import CAPS, CONFIG, run_script
import awarelib as lib
from state import Machine, TransitionError, choose_model, default_state_path

OP = "operator"
APP = "stub-app"


class Harness:
    """Drives a Machine on a temp root and asserts each landing stage."""

    def __init__(self, tc, mode="interactive"):
        self.tc = tc
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.m = Machine(Machine.new_state(mode), CAPS, self.root)

    def step(self, fid, event, expect, app=None, **kw):
        entry = self.m.transition(fid, event, app=app, **kw)
        self.tc.assertEqual(entry["to"], expect, f"{fid} {event} -> {entry['to']}, wanted {expect}")
        return entry

    def counters(self, fid, app=APP):
        return self.m.s["features"][fid]["apps"][app]["counters"]

    def feature(self, fid):
        return self.m.s["features"][fid]


class EWF1DryRun(unittest.TestCase):
    """E-WF-1: stub-agent dry run with injected SPEC_ISSUE, blocker rounds, STALE_DIFF, QA loops."""

    def setUp(self):
        self.h = Harness(self)
        self.addCleanup(self.h.tmp.cleanup)

    def test_full_chain_with_injected_failures(self):
        h, F = self.h, "STUB-1"
        h.m.start_feature(F, "stub feature", [APP], "full")
        # S0 -> G0 -> S1, then SPEC_ISSUE from S1 reopens the spec
        h.step(F, "delta", "G0")
        h.step(F, "approve", "S1", decided_by=OP)
        h.step(F, "SPEC_ISSUE", "S0", detail="CORE-999 ambiguous")
        self.assertEqual(h.feature(F)["counters"]["spec_reopen"], 1)
        h.step(F, "no_delta", "S1")
        h.step(F, "ok", "S2")  # full chain runs S2 + G1
        h.step(F, "ok", "G1")
        h.step(F, "approve", "S3", app=APP, decided_by=OP)
        # STALE_DIFF: stays at S3 and refuses outcomes until re-snapshot
        h.step(F, "STALE_DIFF", "S3", app=APP)
        with self.assertRaises(TransitionError):
            h.m.transition(F, "ok", app=APP)
        h.step(F, "snapshot", "S3", app=APP, detail="abc123")
        h.step(F, "ok", "S4", app=APP)
        # review round 1 blockers, round 2 passes
        h.step(F, "blockers", "S3", app=APP)
        h.step(F, "ok", "S4", app=APP)
        h.step(F, "pass", "S5", app=APP)
        self.assertEqual(h.counters(F)["review_rounds"], 2)
        # QA flow change: back through S3 -> S4; review counter continues (not reset)
        h.step(F, "flow_change", "S3", app=APP)
        h.step(F, "ok", "S4", app=APP)
        h.step(F, "pass", "S5", app=APP)
        self.assertEqual(h.counters(F)["review_rounds"], 3)
        # QA nit-level fix: S3 -> straight back to S5, no review, qa_fix counted
        h.step(F, "nit_fix", "S3", app=APP)
        h.step(F, "ok", "S5", app=APP)
        self.assertEqual(h.counters(F)["qa_fix"], 1)
        self.assertEqual(h.counters(F)["review_rounds"], 3)
        h.step(F, "green", "S6", app=APP)
        h.step(F, "met", "S6b", app=APP)
        h.step(F, "green", "S7", app=APP)
        h.step(F, "ok", "DONE")
        self.assertEqual(h.feature(F)["status"], "done")
        self.assertEqual(h.counters(F)["stale_diff"], 1)

        # Run log: one event per transition, counters and transition recorded.
        events = lib.read_run_events(h.root, F)
        self.assertEqual(len(events), len(h.feature(F)["history"]))
        spec_issue = [e for e in events if e["event"] == "SPEC_ISSUE"][0]
        self.assertEqual(spec_issue["return_code"], "SPEC_ISSUE")
        self.assertEqual(spec_issue["transition"], {"from": "S1", "to": "S0", "status": "active"})
        gate = [e for e in events if e["event"] == "approve"][0]
        self.assertEqual((gate["gate"], gate["decided_by"], gate["agent"]), ("G0", OP, "OP"))
        last_review = [e for e in events if e["event"] == "pass"][-1]
        self.assertEqual(last_review["counters"][APP]["review_rounds"], 3)
        self.assertEqual(last_review["agent"], "REV")

    def test_four_blocker_rounds_route_to_g2_after_round_three(self):
        h, F = self.h, "STUB-2"
        h.m.start_feature(F, "stub", [APP], "light")
        h.step(F, "no_delta", "S1")
        h.step(F, "ok", "S3", app=APP)  # light chain skips S2/G1
        h.step(F, "ok", "S4", app=APP)
        cap = CAPS["review_rounds"]
        for rnd in range(1, cap):
            h.step(F, "blockers", "S3", app=APP)
            h.step(F, "ok", "S4", app=APP)
        h.step(F, "blockers", "G2", app=APP)  # round == cap
        self.assertEqual(h.counters(F)["review_rounds"], cap)
        self.assertEqual(h.feature(F)["g2"]["counter"], "review_rounds")
        # agents cannot continue past G2
        with self.assertRaises(TransitionError):
            h.m.transition(F, "ok", app=APP)
        # operator grants one more round -> round 4 -> blockers -> G2 again
        h.step(F, "one_more_round", "S3", app=APP, decided_by=OP)
        h.step(F, "ok", "S4", app=APP)
        h.step(F, "blockers", "G2", app=APP)
        self.assertEqual(h.counters(F)["review_rounds"], cap + 1)
        h.step(F, "stop", "G2", decided_by=OP)
        self.assertEqual(h.feature(F)["status"], "aborted")

    def test_qa_fix_and_accept_and_regen_caps(self):
        h, F = self.h, "STUB-3"
        h.m.start_feature(F, "stub", [APP], "light")
        h.step(F, "no_delta", "S1")
        h.step(F, "ok", "S3", app=APP)
        h.step(F, "ok", "S4", app=APP)
        h.step(F, "pass", "S5", app=APP)
        for _ in range(CAPS["qa_fix"]):
            h.step(F, "nit_fix", "S3", app=APP)
            h.step(F, "ok", "S5", app=APP)
        h.step(F, "nit_fix", "G2", app=APP)
        h.step(F, "one_more_round", "S3", app=APP, decided_by=OP)
        h.step(F, "ok", "S5", app=APP)  # after_fix survived the gate
        h.step(F, "green", "S6", app=APP)
        h.step(F, "unmet_code", "S3", app=APP)
        h.step(F, "ok", "S4", app=APP)
        h.step(F, "pass", "S5", app=APP)
        h.step(F, "green", "S6", app=APP)
        h.step(F, "unmet_code", "G2", app=APP)  # second unmet
        self.assertEqual(h.counters(F)["accept_reopen"], CAPS["accept_reopen"] + 1)
        self.assertEqual(h.counters(F)["review_rounds"], 2)

    def test_regen_check_cap(self):
        h, F = self.h, "STUB-3b"
        h.m.start_feature(F, "stub", [APP], "light")
        h.step(F, "no_delta", "S1")
        h.step(F, "ok", "S3", app=APP)
        for attempt in range(CAPS["regen_check"] + 1):
            for ev, to in (("ok", "S4"), ("pass", "S5"), ("green", "S6"), ("met", "S6b")):
                h.step(F, ev, to, app=APP)
            h.step(F, "fail", "S3" if attempt < CAPS["regen_check"] else "G2", app=APP)
        self.assertEqual(h.feature(F)["g2"]["counter"], "regen_check")

    def test_env_failure_retried_once_then_g2(self):
        h, F = self.h, "STUB-4"
        h.m.start_feature(F, "stub", [APP], "light")
        h.step(F, "no_delta", "S1")
        h.step(F, "ok", "S3", app=APP)
        for _ in range(CAPS["env_retry"]):
            h.step(F, "ENV_FAILURE", "S3", app=APP, detail="gradle daemon")
        h.step(F, "ENV_FAILURE", "G2", app=APP, detail="gradle daemon")

    def test_spec_reopen_cap_and_plan_deviation(self):
        h, F = self.h, "STUB-5"
        h.m.start_feature(F, "stub", [APP, "other-app"], "light")
        h.step(F, "no_delta", "S1")
        h.step(F, "ok", "S3", app=APP)
        h.step(F, "PLAN_DEVIATION", "S2", app=APP)  # G1-delta path
        self.assertEqual(h.feature(F)["apps"]["other-app"]["stage"], "PENDING")
        h.step(F, "ok", "G1")
        h.step(F, "approve", "S3", app=APP, decided_by=OP)
        for _ in range(CAPS["spec_reopen"]):
            h.step(F, "SPEC_ISSUE", "S0", app=APP)
            h.step(F, "no_delta", "S1")
            h.step(F, "ok", "S3", app=APP)
        h.step(F, "SPEC_ISSUE", "G2", app=APP)
        h.step(F, "change_spec", "S0", decided_by=OP)

    def test_parallel_apps_reach_s7_only_when_all_done(self):
        h, F = self.h, "STUB-6"
        h.m.start_feature(F, "stub", ["a", "b"], "light")
        h.step(F, "no_delta", "S1")
        h.step(F, "ok", "S3", app="a")
        for app in ("a", "b"):
            for ev, to in (("ok", "S4"), ("pass", "S5"), ("green", "S6"), ("met", "S6b")):
                h.step(F, ev, to, app=app)
        h.step(F, "green", "DONE", app="a")
        self.assertEqual(h.feature(F)["stage"], "APPS")
        h.step(F, "green", "S7", app="b")


class IllegalTransitions(unittest.TestCase):
    def setUp(self):
        self.h = Harness(self)
        self.addCleanup(self.h.tmp.cleanup)
        self.h.m.start_feature("X", "x", [APP], "light")

    def test_unknown_or_out_of_stage_events_refused_and_state_untouched(self):
        before = json.dumps(self.h.m.s["features"]["X"])
        for ev, kw in (("pass", {}), ("approve", {"decided_by": OP}), ("PLAN_DEVIATION", {}), ("bogus", {})):
            with self.assertRaises(TransitionError):
                self.h.m.transition("X", ev, **kw)
        self.assertEqual(json.dumps(self.h.m.s["features"]["X"]), before)

    def test_gate_needs_operator(self):
        self.h.step("X", "delta", "G0")
        with self.assertRaises(TransitionError):
            self.h.m.transition("X", "approve")
        self.h.step("X", "approve", "S1", decided_by=OP)

    def test_app_events_need_app(self):
        self.h.step("X", "no_delta", "S1")
        self.h.m.transition("X", "ok", app=APP)
        with self.assertRaises(TransitionError):
            self.h.m.transition("X", "ok")
        with self.assertRaises(TransitionError):
            self.h.m.transition("X", "ok", app="nope")

    def test_design_concern_needs_target_and_is_not_counted(self):
        self.h.step("X", "no_delta", "S1")
        self.h.step("X", "ok", "S3", app=APP)
        self.h.step("X", "ok", "S4", app=APP)
        with self.assertRaises(TransitionError):
            self.h.m.transition("X", "design_concern", app=APP)
        self.h.step("X", "design_concern", "S2", app=APP, target="plan")
        self.assertEqual(self.h.counters("X")["review_rounds"], 0)


class AutonomousMode(unittest.TestCase):
    def setUp(self):
        self.h = Harness(self, mode="autonomous")
        self.addCleanup(self.h.tmp.cleanup)

    def test_g0_blocks_feature_and_independent_feature_continues(self):
        h = self.h
        h.m.start_feature("A", "a", [APP], "light")
        h.m.start_feature("B", "b", [APP], "light")
        h.step("A", "delta", "G0")
        self.assertEqual(h.feature("A")["status"], "blocked")
        with self.assertRaises(TransitionError):
            h.m.transition("A", "approve", decided_by=OP)
        h.step("B", "no_delta", "S1")  # B is independent and keeps going
        h.step("B", "ok", "S3", app=APP)
        # operator returns: unblock, then decide the pending gate
        h.step("A", "unblock", "G0", decided_by=OP)
        h.step("A", "approve", "S1", decided_by=OP)
        events = lib.read_run_events(h.root, "A")
        self.assertEqual(events[-3]["transition"]["status"], "blocked")

    def test_g1_auto_approves_only_with_evals_and_is_flagged(self):
        h = self.h
        h.m.start_feature("C", "c", [APP], "full")
        h.step("C", "no_delta", "S1")
        h.step("C", "ok", "S2")
        h.step("C", "ok", "G1")
        with self.assertRaises(TransitionError):
            h.m.transition("C", "approve")
        h.step("C", "approve", "S3", app=APP, evals_passed=True, detail="E-TL-1 green")
        self.assertEqual(len(h.feature("C")["flagged_for_review"]), 1)

    def test_g1_eval_failure_and_g2_block(self):
        h = self.h
        h.m.start_feature("D", "d", [APP], "full")
        h.step("D", "no_delta", "S1")
        h.step("D", "ok", "S2")
        h.step("D", "ok", "G1")
        h.step("D", "eval_failed", "G1", detail="cites no spec ids")
        self.assertEqual(h.feature("D")["status"], "blocked")
        h.m.start_feature("E", "e", [APP], "light")
        h.step("E", "no_delta", "S1")
        h.step("E", "ok", "S3", app=APP)
        h.step("E", "budget_hard", "G2", app=APP)
        self.assertEqual(h.feature("E")["status"], "blocked")


class EWF2Resume(unittest.TestCase):
    """E-WF-2: kill ORC mid-S4, reload STATE.json, continue without duplicated or skipped stages."""

    def test_resume_through_cli_processes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def cli(*args):
                res = run_script("state.py", "--root", root, *args)
                return res

            def ok(*args):
                res = cli(*args)
                self.assertEqual(res.returncode, 0, res.stderr)
                return res.stdout

            ok("init")
            ok("start-feature", "R1", "--apps", APP, "--chain", "light", "--title", "resume stub")
            ok("transition", "--event", "no_delta", "--expect-stage", "S0")
            ok("transition", "--event", "ok", "--app", APP, "--expect-stage", "S1")
            ok("transition", "--event", "ok", "--app", APP, "--expect-stage", "S3")
            # ORC "dies" here while REV is running S4. A new ORC process reloads state.
            status = ok("status")
            self.assertIn(f"{APP}: S4 -> REV", status)
            ok("transition", "--event", "blockers", "--app", APP, "--expect-stage", "S4")
            # The dead ORC's retry of the same event must be refused, not applied twice.
            dup = cli("transition", "--event", "blockers", "--app", APP, "--expect-stage", "S4")
            self.assertEqual(dup.returncode, lib.EXIT_ILLEGAL)
            self.assertIn("refusing", dup.stderr)
            ok("transition", "--event", "ok", "--app", APP, "--expect-stage", "S3")
            ok("transition", "--event", "pass", "--app", APP, "--expect-stage", "S4")

            state = lib.read_json(default_state_path(root))
            hist = state["features"]["R1"]["history"]
            self.assertEqual([h["seq"] for h in hist], list(range(1, len(hist) + 1)))
            path = [h["to"] for h in hist]
            self.assertEqual(path, ["S0", "S1", "S3", "S4", "S3", "S4", "S5"])
            for prev, cur in zip(hist, hist[1:]):
                self.assertEqual(prev["to"], cur["from"], "skipped stage between checkpoints")
            self.assertEqual(state["features"]["R1"]["apps"][APP]["counters"]["review_rounds"], 2)
            self.assertEqual(len(lib.read_run_events(root, "R1")), len(hist))
            ok("render")
            self.assertIn("R1", (root / ".work" / "STATE.md").read_text())

    def test_reload_object_equivalence(self):
        h = Harness(self)
        self.addCleanup(h.tmp.cleanup)
        h.m.start_feature("R2", "r", [APP], "light")
        h.step("R2", "no_delta", "S1")
        h.step("R2", "ok", "S3", app=APP)
        path = default_state_path(h.root)
        h.m.save(path)
        m2 = Machine.load(path, CAPS, h.root)
        self.assertEqual(m2.s, h.m.s)
        m2.transition("R2", "ok", app=APP, expect_stage="S3")
        self.assertEqual(m2.s["features"]["R2"]["apps"][APP]["stage"], "S4")


class ModelRules(unittest.TestCase):
    def test_reviewer_threshold_from_config(self):
        t = CONFIG["limits"]["rev_opus_changed_lines"]
        self.assertEqual(choose_model("REV", t)[0], "sonnet")
        self.assertEqual(choose_model("REV", t + 1)[0], "opus")
        self.assertEqual(choose_model("REV", 1, concurrency=True)[0], "opus")
        self.assertEqual(choose_model("TL")[0], "opus")
        self.assertEqual(choose_model("DEV", first_gen=True)[0], "opus")


if __name__ == "__main__":
    unittest.main()
