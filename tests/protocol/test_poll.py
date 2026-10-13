"""E4 poll: CORE-POLL-001..007, CORE-EPOCH-002, CORE-SRV-015/016, cursor semantics and seq ordering."""
import time
import unittest

import harness
from harness import ServerTestCase, send_body, uid


class PollTests(ServerTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.register("alice", "bob")

    def fill(self, n, to="bob", start=1):
        for i in range(start, start + n):
            self.assertEqual(self.c.send(send_body(i, to=to)).status, 201)

    def test_CORE_POLL_003_returns_only_seq_above_after_in_ascending_order(self):
        self.fill(5)
        for after, expect in ((0, [1, 2, 3, 4, 5]), (1, [2, 3, 4, 5]), (4, [5]), (5, []), (99, [])):
            page = self.c.poll("bob", after=after).json
            self.assertEqual([m["seq"] for m in page["messages"]], expect, after)
            self.assertFalse(page["has_more"])

    def test_CORE_POLL_003_CORE_SEQ_001_mailbox_holds_only_its_own_messages_with_gaps_in_seq(self):
        self.c.send(send_body(1, to="bob"))
        self.c.send(send_body(2, to="alice"))
        self.c.send(send_body(3, to="bob"))
        self.c.send(send_body(4, to="alice"))
        self.assertEqual([m["seq"] for m in self.c.poll("bob").json["messages"]], [1, 3])
        self.assertEqual([m["seq"] for m in self.c.poll("alice").json["messages"]], [2, 4])
        self.assertEqual([m["seq"] for m in self.c.poll("bob", after=1).json["messages"]], [3])
        self.assertEqual([m["seq"] for m in self.c.poll("bob", after=2).json["messages"]], [3])

    def test_CORE_POLL_003_CORE_POLL_004_paging_with_limit_has_more_and_next_cursor(self):
        self.fill(5)
        seen, after, pages = [], 0, []
        while True:
            page = self.c.poll("bob", after=after, limit=2).json
            pages.append((len(page["messages"]), page["next_cursor"], page["has_more"]))
            seen += [m["seq"] for m in page["messages"]]
            after = page["next_cursor"]
            if not page["has_more"]:
                break
        self.assertEqual(pages, [(2, 2, True), (2, 4, True), (1, 5, False)])
        self.assertEqual(seen, [1, 2, 3, 4, 5])

    def test_CORE_POLL_003_has_more_is_false_when_limit_equals_what_remains(self):
        self.fill(3)
        page = self.c.poll("bob", limit=3).json
        self.assertEqual((len(page["messages"]), page["has_more"], page["next_cursor"]), (3, False, 3))
        page = self.c.poll("bob", limit=1).json
        self.assertEqual((len(page["messages"]), page["has_more"], page["next_cursor"]), (1, True, 1))

    def test_CORE_POLL_004_next_cursor_is_after_unchanged_when_nothing_is_returned(self):
        self.fill(2)
        for after in (2, 3, 7, 1000000):
            page = self.c.poll("bob", after=after).json
            self.assertEqual((page["messages"], page["next_cursor"], page["has_more"]), ([], after, False))
        self.assertEqual(self.c.poll("nobody", after=41).json["next_cursor"], 41)

    def test_CORE_POLL_002_limit_above_the_maximum_is_clamped_not_rejected(self):
        self.fill(130)
        for limit in (100, 101, 1000, 99999999999999):
            page = self.c.poll("bob", limit=limit).json
            self.assertEqual((len(page["messages"]), page["has_more"], page["next_cursor"]), (100, True, 100), limit)
        self.assertEqual(len(self.c.poll("bob").json["messages"]), 100)                    # default is the maximum too
        self.assertEqual(len(self.c.poll("bob", after=100).json["messages"]), 30)

    def test_CORE_POLL_001_after_and_limit_must_be_canonical_decimal_integers(self):
        base = f"/v1/mailboxes/bob/messages?epoch={self.srv.epoch}"
        for query in ("&after=abc", "&after=-1", "&after=01", "&after=1.5", "&after=", "&after=1e3", "&after=%2B1",
                      "&after=12345678901234567", "&after=%201", "&after=%0A1", "&after=%EF%BC%91",
                      "", "&limit=5",
                      "&after=0&limit=0", "&after=0&limit=00", "&after=0&limit=-5", "&after=0&limit=x", "&after=0&limit=",
                      "&after=0&limit=1.0", "&after=0&limit=012", "&after=0&limit=12345678901234567"):
            r = self.c.call("GET", base + query)
            self.assertEqual((r.status, r.code), (400, "malformed_request"), query)
        for query in ("&after=0", "&after=7", "&after=0&limit=1", "&after=0&limit=100", "&after=1234567890123456&limit=3"):
            self.assertEqual(self.c.call("GET", base + query, check="1234567890123456" not in query).status, 200, query)

    def test_CORE_POLL_005_CORE_SRV_016_answers_at_once_wait_is_ignored_and_nothing_is_held(self):
        for extra in ("", "&wait=30", "&wait=0", "&wait=abc"):
            t0 = time.monotonic()
            page = self.c.poll("bob", after=0, extra=extra).json
            self.assertEqual(page["messages"], [])
            self.assertLess(time.monotonic() - t0, 1.0, extra)
        self.fill(1)
        t0 = time.monotonic()
        self.assertEqual(len(self.c.poll("bob", extra="&wait=30").json["messages"]), 1)
        self.assertLess(time.monotonic() - t0, 1.0)

    def test_CORE_POLL_006_polling_changes_no_server_state(self):
        self.fill(2)
        before = (self.c.users().json, self.c.poll("bob").json, self.c.poll("alice").json)
        for name in ("bob", "alice", "ghost", "never-seen"):
            for _ in range(3):
                self.c.poll(name, after=1)
        self.assertEqual((self.c.users().json, self.c.poll("bob").json, self.c.poll("alice").json), before)
        self.assertEqual(self.c.send(send_body(3)).json["seq"], 3)                          # counter untouched

    def test_CORE_POLL_007_CORE_SRV_016_valid_name_without_mailbox_or_registration_gets_an_empty_page(self):
        page = self.c.poll("never-seen-name").json
        self.assertEqual(page, {"epoch": self.srv.epoch, "messages": [], "next_cursor": 0, "has_more": False})
        self.assertEqual([u["name"] for u in self.c.users().json["users"]], ["alice", "bob"])
        self.c.send(send_body(1, to="stranger"))                                            # unregistered owner with mail
        self.assertEqual(len(self.c.poll("stranger").json["messages"]), 1)

    def test_CORE_NAME_001_CORE_NAME_003_path_name_is_validated_and_canonicalized(self):
        self.fill(1)
        self.assertEqual(len(self.c.poll("BOB").json["messages"]), 1)
        self.assertEqual(len(self.c.poll("bOb").json["messages"]), 1)
        for bad in ("bad%20name", "x" * 33, "a.b", "%C3%A9", "bob%0A", "a%2Fb"):
            r = self.c.poll(bad)
            self.assertEqual((r.status, r.code), (400, "invalid_name"), bad)
        self.assertEqual(self.c.poll("x" * 32).status, 200)

    def test_CORE_NAME_001_empty_path_name_is_invalid_name(self):
        r = self.c.call("GET", f"/v1/mailboxes//messages?epoch={self.srv.epoch}&after=0")
        self.assertEqual((r.status, r.code), (400, "invalid_name"))

    def test_CORE_EPOCH_002_epoch_is_required_well_formed_and_current(self):
        base = "/v1/mailboxes/bob/messages?after=0"
        r = self.c.call("GET", base)
        self.assertEqual((r.status, r.code), (400, "malformed_request"))
        for bad in ("", "zz", "3F9A1C7E5B2D4086", "3f9a1c7e5b2d408", "3f9a1c7e5b2d40860", "3f9a1c7e5b2d408g", "%203f9a1c7e5b2d4086"):
            r = self.c.call("GET", base + "&epoch=" + bad)
            self.assertEqual((r.status, r.code), (400, "malformed_request"), bad)
        other = "0" * 16 if self.srv.epoch != "0" * 16 else "1" * 16
        r = self.c.call("GET", base + "&epoch=" + other)
        self.assertEqual((r.status, r.code), (409, "epoch_mismatch"))
        self.assertEqual(self.c.call("GET", base + "&epoch=" + self.srv.epoch).status, 200)

    def test_CORE_EPOCH_002_the_epoch_mismatch_changes_nothing(self):
        self.fill(1)
        self.assertEqual(self.c.poll("bob", epoch="0" * 16).status, 409)
        self.assertEqual(len(self.c.poll("bob").json["messages"]), 1)

    def test_CORE_SRV_015_success_responses_of_e3_and_e4_carry_the_current_epoch(self):
        r = self.c.send(send_body(1))
        self.assertEqual(r.json["epoch"], self.srv.epoch)
        self.assertEqual(self.c.send(send_body(1)).json["epoch"], self.srv.epoch)
        self.assertEqual(self.c.poll("bob").json["epoch"], self.srv.epoch)
        self.assertEqual(self.c.poll("nobody").json["epoch"], self.srv.epoch)

    def test_CORE_HTTP_006_unknown_query_parameters_are_ignored_on_e3_and_e4(self):
        r = self.c.call("POST", f"/v1/messages?epoch={self.srv.epoch}&x=1&wait=9", send_body(1))
        self.assertEqual(r.status, 201)
        self.assertEqual(len(self.c.poll("bob", extra="&x=1&y=2&Epoch=zzz").json["messages"]), 1)

    def test_CORE_SEQ_001_poll_order_is_acceptance_order_not_creation_order(self):
        late_created = send_body(1, created_at="2026-12-31T23:59:59.999Z")
        early_created = send_body(2, created_at="2026-01-01T00:00:00.000Z")
        self.c.send(late_created)
        self.c.send(early_created)
        self.assertEqual([m["id"] for m in self.c.poll("bob").json["messages"]], [uid(1), uid(2)])

    def test_CORE_SRV_032_a_poll_sees_an_envelope_sent_a_moment_before_from_another_connection(self):
        for i in range(1, 30):
            self.c.send(send_body(i))
            self.assertEqual(self.c.poll("bob", after=i - 1).json["messages"][0]["seq"], i)


if __name__ == "__main__":
    unittest.main()
