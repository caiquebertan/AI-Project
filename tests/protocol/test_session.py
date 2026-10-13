"""E1 info, E2 session, E5 users, epoch and constants: CORE-SESSION, CORE-NAME, CORE-EPOCH-001, CORE-CAP, CORE-SRV-01x/02x/041."""
import json
import re
import unittest

import harness
from harness import CONSTANTS, RunningServer, ServerTestCase, send_body


class InfoTests(ServerTestCase, unittest.TestCase):
    def test_CORE_CAP_001_CORE_SRV_041_info_has_the_fixed_values(self):
        r = self.c.info()
        self.assertEqual(r.status, 200)
        self.assertEqual(r.json, {
            "protocol": "aware", "protocol_version": CONSTANTS["PROTOCOL_VERSION"], "epoch": self.srv.epoch,
            "core_types": ["text"], "server_capabilities": [],
            "limits": {"text_max_bytes": CONSTANTS["TEXT_MAX_BYTES"], "body_max_bytes": CONSTANTS["BODY_MAX_BYTES"],
                       "poll_limit_max": CONSTANTS["POLL_LIMIT_MAX"]}})

    def test_CORE_CONST_001_server_constants_equal_the_normative_table(self):
        from aware_server import constants as C
        for name in ("PROTOCOL_VERSION", "NAME_MAX_LENGTH", "TEXT_MAX_BYTES", "BODY_MAX_BYTES", "POLL_LIMIT_MAX",
                     "SERVER_DEFAULT_PORT"):
            self.assertEqual(getattr(C, name), CONSTANTS[name], name)

    def test_CORE_HTTP_006_unknown_query_parameters_are_ignored(self):
        self.assertEqual(self.c.call("GET", "/v1/info?x=1&wait=30&epoch=zzz").status, 200)
        self.assertEqual(self.c.call("GET", "/v1/users?whatever").status, 200)

    def test_CORE_EPOCH_001_epoch_is_16_hex_and_constant_for_the_process(self):
        e = self.c.info().json["epoch"]
        self.assertRegex(e, r"^[0-9a-f]{16}$")
        self.c.session("alice")
        self.assertEqual(self.c.info().json["epoch"], e)
        self.assertEqual(self.c.session("alice").json["epoch"], e)

    def test_CORE_EPOCH_001_CORE_SRV_010_each_start_has_its_own_epoch_and_empty_state(self):
        other = RunningServer()
        try:
            self.assertNotEqual(other.epoch, self.srv.epoch)
            self.assertEqual(harness.Client(other).users().json, {"users": []})
            self.assertEqual(harness.Client(other).poll("alice").json,
                             {"epoch": other.epoch, "messages": [], "next_cursor": 0, "has_more": False})
        finally:
            other.close()


class SessionTests(ServerTestCase, unittest.TestCase):
    def test_CORE_SESSION_001_CORE_SRV_021_new_user_true_once_then_false_idempotent(self):
        first = self.c.session("alice")
        self.assertEqual((first.status, first.json), (200, {"name": "alice", "epoch": self.srv.epoch, "new_user": True}))
        for _ in range(3):
            again = self.c.session("alice")
            self.assertEqual((again.status, again.json["new_user"]), (200, False))
        self.assertEqual(len(self.c.users().json["users"]), 1)

    def test_CORE_NAME_002_CORE_NAME_003_names_are_canonicalized_and_case_insensitive(self):
        self.assertEqual(self.c.session("AlIcE_-9").json["name"], "alice_-9")
        again = self.c.session("ALICE_-9")
        self.assertEqual((again.json["name"], again.json["new_user"]), ("alice_-9", False))
        self.assertEqual([u["name"] for u in self.c.users().json["users"]], ["alice_-9"])

    def test_CORE_NAME_001_valid_and_invalid_names(self):
        for name in ("a", "A", "z9_-", "x" * 32, "0", "_", "-", "Alice"):
            self.assertEqual(self.c.session(name).status, 200, name)
        for name in ("", "x" * 33, "bad name", " alice", "alice ", "alice\n", "a.b", "a@b", "\u00e9", "al\u00efce",
                     "\uff21lice", "a/b", "a\u0000"):
            r = self.c.session(name)
            self.assertEqual((r.status, r.code), (400, "invalid_name"), repr(name))

    def test_CORE_NAME_006_any_client_claiming_a_name_is_that_user(self):
        self.assertTrue(self.c.session("alice", ["x"]).json["new_user"])
        other = harness.Client(self.srv)  # another "device", no credentials exist
        self.assertFalse(other.session("alice").json["new_user"])

    def test_CORE_SESSION_002_CORE_SRV_022_capabilities_replace_the_list_in_sent_order(self):
        self.c.session("alice", ["reactions", "attachments"])
        self.assertEqual(self.c.users().json["users"], [{"name": "alice", "capabilities": ["reactions", "attachments"]}])
        self.c.session("alice", ["zeta", "alpha", "m1"])
        self.assertEqual(self.c.users().json["users"][0]["capabilities"], ["zeta", "alpha", "m1"])
        self.c.session("alice", [])
        self.assertEqual(self.c.users().json["users"][0]["capabilities"], [])

    def test_CORE_SESSION_002_capability_format_is_checked(self):
        ok = ["a", "a" * 32, "a-1", "x" * 1]
        self.assertEqual(self.c.session("alice", ok).status, 200)
        self.assertEqual(self.c.session("alice", [f"c{i}" for i in range(32)]).status, 200)
        bad = [[f"c{i}" for i in range(33)], ["a", "a"], ["Reactions"], ["1a"], ["a_b"], [""], ["a" * 33], ["a b"],
               [1], [None], ["a", ["b"]]]
        for caps in bad:
            r = self.c.call("POST", "/v1/session", {"name": "alice", "capabilities": caps})
            self.assertEqual((r.status, r.code), (400, "malformed_request"), caps)
        # the failed calls did not change the stored list
        self.assertEqual(len(self.c.users().json["users"][0]["capabilities"]), 32)

    def test_CORE_HTTP_004_CORE_SESSION_002_missing_unknown_and_mistyped_fields_are_malformed(self):
        bodies = [{}, {"name": "alice"}, {"capabilities": []}, {"name": "alice", "capabilities": [], "extra": 1},
                  {"name": "alice", "capabilities": {}}, {"name": "alice", "capabilities": None},
                  {"name": 5, "capabilities": []}, {"name": None, "capabilities": []}, {"name": ["a"], "capabilities": []}]
        for body in bodies:
            r = self.c.call("POST", "/v1/session", body)
            self.assertEqual((r.status, r.code), (400, "malformed_request"), body)
        self.assertEqual(self.c.users().json, {"users": []})

    def test_CORE_ERR_002_malformed_capabilities_win_over_invalid_name(self):
        r = self.c.call("POST", "/v1/session", {"name": "bad name", "capabilities": ["A"]})
        self.assertEqual(r.code, "malformed_request")


class UsersTests(ServerTestCase, unittest.TestCase):
    def test_CORE_SRV_010_CORE_CAP_003_empty_registry_at_start(self):
        self.assertEqual(self.c.users().json, {"users": []})

    def test_CORE_CAP_003_CORE_SRV_020_CORE_SRV_023_users_sorted_by_name_in_byte_order(self):
        names = ["bob", "Alice", "_x", "-z", "9", "a1", "alice2", "Zed", "a-b", "a_b", "a"]
        for n in names:
            self.c.session(n, ["cap-" + n.lower()] if n in ("bob", "9") else [])
        listed = self.c.users().json["users"]
        canon = sorted({n.lower() for n in names}, key=lambda n: n.encode("utf-8"))
        self.assertEqual([u["name"] for u in listed], canon)
        caps = {u["name"]: u["capabilities"] for u in listed}
        self.assertEqual((caps["bob"], caps["9"], caps["alice2"]), (["cap-bob"], ["cap-9"], []))

    def test_CORE_SRV_020_entries_are_never_removed_and_only_e2_creates_them(self):
        self.c.session("alice")
        self.c.send(send_body(1, to="ghost"))
        self.c.poll("nobody")
        self.assertEqual([u["name"] for u in self.c.users().json["users"]], ["alice"])


if __name__ == "__main__":
    unittest.main()
