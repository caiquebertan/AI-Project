"""E3 send: CORE-MSG, CORE-ENV, CORE-SEQ-001, CORE-TEXT, CORE-SRV-030..036, CORE-NAME on envelopes."""
import json
import time
import unittest

import harness
from harness import ServerTestCase, send_body, uid, utc_ms

DELIVERED_FIELDS = ["accepted_at", "created_at", "from", "id", "payload", "seq", "to", "type"]


class AcceptTests(ServerTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.register("alice", "bob")

    def test_CORE_MSG_001_CORE_SRV_033_new_is_201_duplicate_is_200_with_original_seq_and_accepted_at(self):
        first = self.c.send(send_body(1))
        self.assertEqual(first.status, 201)
        self.assertEqual(set(first.json), {"id", "seq", "accepted_at", "epoch"})
        self.assertEqual((first.json["id"], first.json["seq"], first.json["epoch"]), (uid(1), 1, self.srv.epoch))
        time.sleep(0.01)
        dup = self.c.send(send_body(1))
        self.assertEqual((dup.status, dup.json), (200, first.json))

    def test_CORE_SRV_033_CORE_POLL_005_accepted_envelope_is_visible_to_the_next_poll(self):
        self.c.send(send_body(1))
        self.assertEqual([m["id"] for m in self.c.poll("bob").json["messages"]], [uid(1)])

    def test_CORE_ENV_001_CORE_ENV_007_CORE_SRV_032_delivered_form_has_exactly_the_fields_and_stays_identical(self):
        sent = self.c.send(send_body(1, created_at="2026-10-13T12:00:00.123Z"))
        msg = self.c.poll("bob").json["messages"][0]
        self.assertEqual(sorted(msg), DELIVERED_FIELDS)
        self.assertEqual((msg["seq"], msg["accepted_at"]), (sent.json["seq"], sent.json["accepted_at"]))
        self.assertEqual(msg["created_at"], "2026-10-13T12:00:00.123Z")
        self.assertEqual(self.c.poll("bob").json["messages"][0], msg)           # later delivery identical
        self.assertEqual(self.c.send(send_body(1, created_at="2026-10-13T12:00:00.123Z")).json, sent.json)

    def test_CORE_SRV_031_accepted_at_is_the_server_utc_clock_not_created_at(self):
        lo = time.time_ns() // 1_000_000
        r = self.c.send(send_body(1, created_at="2001-01-01T00:00:00.000Z"))
        hi = time.time_ns() // 1_000_000
        at = utc_ms(r.json["accepted_at"])
        self.assertTrue(lo - 1 <= at <= hi + 1, (lo, at, hi))
        far = self.c.send(send_body(2, created_at="2999-01-01T00:00:00.000Z"))
        self.assertLess(utc_ms(far.json["accepted_at"]), utc_ms("2100-01-01T00:00:00.000Z"))

    def test_CORE_SRV_032_CORE_ENV_003_note_to_self_is_appended_once(self):
        self.c.send(send_body(1, to="alice"))
        msgs = self.c.poll("alice").json["messages"]
        self.assertEqual([(m["id"], m["from"], m["to"]) for m in msgs], [(uid(1), "alice", "alice")])
        self.assertEqual(self.c.send(send_body(1, to="alice")).status, 200)
        self.assertEqual(len(self.c.poll("alice").json["messages"]), 1)

    def test_CORE_MSG_003_unknown_recipient_is_accepted_and_kept_in_its_mailbox(self):
        r = self.c.send(send_body(1, to="nobody-yet"))
        self.assertEqual(r.status, 201)
        self.assertEqual([m["id"] for m in self.c.poll("nobody-yet").json["messages"]], [uid(1)])
        self.c.session("Nobody-Yet")  # registering later changes nothing about the mailbox
        self.assertEqual(len(self.c.poll("nobody-yet").json["messages"]), 1)
        self.assertEqual([u["name"] for u in self.c.users().json["users"]], ["alice", "bob", "nobody-yet"])

    def test_CORE_MSG_002_sender_without_session_is_403_unknown_sender(self):
        r = self.c.send(send_body(1, sender="mallory"))
        self.assertEqual((r.status, r.code), (403, "unknown_sender"))
        self.assertEqual(self.c.poll("bob").json["messages"], [])
        self.c.session("mallory")
        self.assertEqual(self.c.send(send_body(1, sender="mallory")).status, 201)

    def test_CORE_MSG_002_a_recipient_only_name_is_not_a_registered_sender(self):
        self.c.send(send_body(1, to="carol"))
        r = self.c.send(send_body(2, sender="carol", to="bob"))
        self.assertEqual(r.code, "unknown_sender")

    def test_CORE_NAME_002_CORE_NAME_003_names_in_the_body_are_canonicalized(self):
        r = self.c.send(send_body(1, sender="ALICE", to="BoB"))
        self.assertEqual(r.status, 201)
        msg = self.c.poll("BOB").json["messages"][0]
        self.assertEqual((msg["from"], msg["to"]), ("alice", "bob"))
        self.assertEqual(self.c.poll("alice").json["messages"], [])

    def test_CORE_NAME_001_invalid_from_or_to_is_invalid_name(self):
        for bad in ("", "x" * 33, "bad name", "a.b", "\u00e9", " bob", "bob\n", "a/b"):
            for field in ("from", "to"):
                body = send_body(1)
                body[field] = bad
                r = self.c.send(body)
                self.assertEqual((r.status, r.code), (400, "invalid_name"), (field, bad))
        self.assertEqual(self.c.send(send_body(1, sender="a" * 32, to="B" * 32)).code, "unknown_sender")

    def test_CORE_ENV_002_invalid_id_is_invalid_id(self):
        good = "123e4567-e89b-4d3c-a456-426614174000"
        bad = [good.upper(), good.replace("-4d3c-", "-1d3c-"), good.replace("-4d3c-", "-5d3c-"), good.replace("-a456-", "-c456-"),
               good.replace("-", ""), good[:-1], good + "0", "", "not-a-uuid", " " + good, good + "\n",
               "00000000-0000-4000-8000-00000000000g"]
        for value in bad:
            body = send_body(1)
            body["id"] = value
            r = self.c.send(body)
            self.assertEqual((r.status, r.code), (400, "invalid_id"), value)
        for variant in "89ab":
            body = send_body(1)
            body["id"] = f"123e4567-e89b-4d3c-{variant}456-426614174000"
            self.assertEqual(self.c.send(body).status, 201, variant)

    def test_CORE_ENV_004_invalid_type_is_invalid_type(self):
        for value in ("", "Text", "1x", "a b", "a" * 65, "_a", ".a", "a/b", "tex\u00e9", "a:b", "text\n"):
            r = self.c.send(send_body(1, type=value, payload={"x": 1}))
            self.assertEqual((r.status, r.code), (400, "invalid_type"), repr(value))
        for value in ("a", "a" * 64, "reactions.add", "x_y-z.1"):
            self.assertEqual(self.c.send(send_body(len(value) + 100, type=value, payload={"x": 1})).status, 201, value)

    def test_CORE_ENV_005_payload_must_be_a_json_object(self):
        for payload in ([], [1], "text", 5, None, True, 1.5):
            r = self.c.send(send_body(1, payload=payload, type="x"))
            self.assertEqual(r.status, 400, payload)
            self.assertIn(r.code, ("invalid_payload", "malformed_request"), payload)  # see spec-issues.md S-1
        self.assertEqual(self.c.send(send_body(1, payload={}, type="x")).status, 201)

    def test_CORE_ENV_001_CORE_HTTP_004_missing_unknown_and_mistyped_fields_are_malformed(self):
        full = send_body(1)
        cases = [{k: v for k, v in full.items() if k != gone} for gone in full]
        cases += [dict(full, extra=1), dict(full, seq=1), dict(full, accepted_at="2026-10-13T15:00:01.000Z")]
        cases += [dict(full, **{k: v}) for k in ("id", "from", "to", "type", "created_at") for v in (5, None, ["a"], {}, True)]
        cases += [{}, {"payload": {"text": "x"}}]
        for body in cases:
            r = self.c.send(body)
            self.assertEqual((r.status, r.code), (400, "malformed_request"), body)
        self.assertEqual(self.c.poll("bob").json["messages"], [])

    def test_CORE_SEQ_001_one_counter_for_all_mailboxes_and_only_new_envelopes_consume_it(self):
        self.assertEqual(self.c.send(send_body(1, to="bob")).json["seq"], 1)
        self.assertEqual(self.c.send(send_body(2, to="alice")).json["seq"], 2)
        self.assertEqual(self.c.send(send_body(1, to="bob")).json["seq"], 1)          # duplicate: no value used
        rejected = ((send_body(3, sender="ghost"), (403, "unknown_sender")),
                    (send_body(4, payload={"text": " "}), (400, "invalid_payload")),
                    (dict(send_body(5), x=1), (400, "malformed_request")),
                    (dict(send_body(1, to="alice")), (409, "id_conflict")))
        for bad, expected in rejected:
            r = self.c.send(bad)
            self.assertEqual((r.status, r.code), expected, bad)
        self.assertEqual(self.c.send(send_body(6, to="zed")).json["seq"], 3)
        self.assertEqual(self.c.send(send_body(7, to="bob")).json["seq"], 4)

    def test_CORE_SEQ_001_CORE_SRV_040_nesting_around_the_parser_limit_never_gives_5xx_or_consumes_a_seq(self):
        """Depth 491/492/493 were the window where parsing worked and storing failed (review P2 round 1, B1)."""
        expected_next = 1
        depths = sorted({1, 2, 50, 300, *range(485, 500), 700, 5000, 20000})
        for depth in depths:
            r = self.c.call("POST", f"/v1/messages?epoch={self.srv.epoch}", raw=self.deep_envelope(depth, depth), headers=harness.JSON)
            self.assertLess(r.status, 500, (depth, r.status))
            if r.status == 201:
                self.assertEqual(r.json["seq"], expected_next, depth)
                expected_next += 1
            else:
                self.assertEqual((r.status, r.code), (400, "malformed_request"), depth)
        self.assertGreater(expected_next, 1)                                     # some depth was stored
        nxt = self.c.send(send_body(9000, type="x", payload={"a": 1}))
        self.assertEqual((nxt.status, nxt.json["seq"]), (201, expected_next))    # no value was lost to a failure
        stored = self.c.poll("bob", check=False).json["messages"]   # the schema checker itself recurses, so no check here
        self.assertEqual([m["seq"] for m in stored], list(range(1, expected_next + 1)))

    def test_CORE_SEQ_001_the_exact_boundary_depths_491_492_493_are_each_stored_or_rejected_cleanly(self):
        expected_next = 1
        for depth in (491, 492, 493):
            r = self.c.call("POST", f"/v1/messages?epoch={self.srv.epoch}", raw=self.deep_envelope(depth, depth), headers=harness.JSON)
            self.assertIn((r.status, r.code), ((201, None), (400, "malformed_request")), depth)
            expected_next += r.status == 201
            self.assertEqual(self.c.send(send_body(8000 + depth, type="x", payload={})).json["seq"], expected_next, depth)
            expected_next += 1

    def test_CORE_ERR_002_a_payload_too_deep_for_the_parser_is_malformed_before_epoch_and_name_checks(self):
        raw = self.deep_envelope(1, 20000)  # parses in no interpreter stack, fits the body limit
        r = self.c.call("POST", "/v1/messages?epoch=0000000000000000", raw=raw, headers=harness.JSON)
        self.assertEqual((r.status, r.code), (400, "malformed_request"))
        bad_from = raw.replace(b'"from": "alice"', b'"from": "bad name"')
        self.assertNotEqual(bad_from, raw)
        r = self.c.call("POST", f"/v1/messages?epoch={self.srv.epoch}", raw=bad_from, headers=harness.JSON)
        self.assertEqual((r.status, r.code), (400, "malformed_request"))
        self.assertEqual(self.c.send(send_body(2, type="x", payload={})).json["seq"], 1)

    def deep_envelope(self, n: int, depth: int) -> bytes:
        """A send body whose payload is {"a": [[...]]} nested `depth` levels deep, built as text."""
        head = json.dumps(dict(send_body(n, type="x", payload=0), payload=0))
        payload = '{"a": ' + "[" * depth + "]" * depth + "}"
        return head.replace('"payload": 0', '"payload": ' + payload).encode()

    def test_CORE_SRV_036_every_accepted_envelope_is_kept_and_polling_never_removes_it(self):
        for i in range(1, 251):
            self.assertEqual(self.c.send(send_body(i)).status, 201)
        for _ in range(2):
            got, after = [], 0
            while True:
                page = self.c.poll("bob", after=after, limit=100).json
                got += [m["seq"] for m in page["messages"]]
                after = page["next_cursor"]
                if not page["has_more"]:
                    break
            self.assertEqual(got, list(range(1, 251)))


class DedupeTests(ServerTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.register("alice", "bob", "carol")

    def test_CORE_SRV_034_equal_resend_is_200_even_with_other_key_order_number_spelling_and_name_case(self):
        a = {"b": [1.0, {"y": 2, "x": 3}], "a": 1, "n": 1e2, "s": "\u00e9"}
        first = self.c.send(dict(send_body(1, type="x.t", payload=a)))
        self.assertEqual(first.status, 201)
        b = json.loads('{"s":"\\u00e9","n":100,"a":1.00,"b":[1,{"x":3,"y":2.0}]}')
        raw = json.dumps(send_body(1, sender="Alice", to="BOB", type="x.t", payload={})).replace(
            '"payload": {}', '"payload": ' + '{"s":"\\u00e9","n":100,"a":1.00,"b":[1,{"x":3,"y":2.0}]}')
        again = self.c.send(None, raw=raw.encode("utf-8"), headers=harness.JSON)
        self.assertEqual((again.status, again.json), (200, first.json))
        self.assertEqual(len(self.c.poll("bob").json["messages"]), 1)

    def test_CORE_SRV_034_any_difference_is_409_id_conflict_and_changes_nothing(self):
        base = send_body(1, payload={"text": "one"})
        first = self.c.send(base)
        variants = {
            "from": dict(base, **{"from": "carol"}), "to": dict(base, to="carol"), "type": dict(base, type="x.text"),
            "payload": dict(base, payload={"text": "two"}),
            "created_at": dict(base, created_at="2026-10-13T15:00:01.001Z"),
        }
        for what, body in variants.items():
            r = self.c.send(body)
            self.assertEqual((r.status, r.code), (409, "id_conflict"), what)
        self.assertEqual(self.c.send(base).json, first.json)
        self.assertEqual(len(self.c.poll("bob").json["messages"]), 1)
        self.assertEqual(self.c.poll("carol").json["messages"], [])
        self.assertEqual(self.c.send(send_body(2)).json["seq"], 2)                       # no value consumed
        ext = send_body(3, type="x.t", payload={"k": 1})
        self.assertEqual(self.c.send(ext).status, 201)
        self.assertEqual(self.c.send(dict(ext, payload={"k": 1, "extra": 1})).code, "id_conflict")
        self.assertEqual(self.c.send(dict(ext, payload={})).code, "id_conflict")

    def test_CORE_SRV_034_numbers_by_value_but_types_stay_distinct(self):
        self.c.send(send_body(1, type="x", payload={"a": 1, "t": True, "n": None, "z": "1"}))
        same = self.c.send(send_body(1, type="x", payload={"a": 1.0, "t": True, "n": None, "z": "1"}))
        self.assertEqual(same.status, 200)
        for changed in ({"a": True, "t": True, "n": None, "z": "1"}, {"a": 1, "t": 1, "n": None, "z": "1"},
                        {"a": 1, "t": True, "n": 0, "z": "1"}, {"a": 1, "t": True, "n": None, "z": 1},
                        {"a": 2, "t": True, "n": None, "z": "1"}):
            self.assertEqual(self.c.send(send_body(1, type="x", payload=changed)).code, "id_conflict", changed)

    def test_CORE_ERR_002_unknown_sender_is_reported_before_id_conflict(self):
        self.c.send(send_body(1))
        r = self.c.send(send_body(1, sender="ghost", payload={"text": "other"}))
        self.assertEqual(r.code, "unknown_sender")

    def test_CORE_SRV_034_the_same_id_from_another_sender_is_a_conflict_not_a_new_message(self):
        self.c.send(send_body(1, sender="alice"))
        self.assertEqual(self.c.send(send_body(1, sender="bob", to="bob")).code, "id_conflict")


class TextPayloadTests(ServerTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.register("alice", "bob")

    def text(self, value, n=1):
        return self.c.send(send_body(n, payload={"text": value}))

    def test_CORE_TEXT_001_payload_is_exactly_text_string(self):
        for payload in ({}, {"text": 5}, {"text": None}, {"text": ["a"]}, {"text": "a", "extra": 1}, {"txt": "a"},
                        {"text": {"a": 1}}, {"text": True}):
            r = self.c.send(send_body(1, payload=payload))
            self.assertEqual((r.status, r.code), (400, "invalid_payload"), payload)

    def test_CORE_TEXT_002_blank_text_is_invalid_anything_else_is_valid(self):
        for blank in ("", " ", "\t", "\n", "\r", " \t\r\n  ", "\r\n" * 10):
            r = self.text(blank)
            self.assertEqual((r.status, r.code), (400, "invalid_payload"), repr(blank))
        for ok in ("a", " a ", "\u00a0", "\u2003", "\u200b", "\x0b", "\x0c", "0", ".", "\U0001f600"):
            self.assertEqual(self.text(ok, n=100 + len(ok) + ord(ok[0])).status, 201, repr(ok))

    def test_CORE_TEXT_003_size_limit_is_4096_utf8_bytes_not_characters(self):
        self.assertEqual(self.text("a" * 4096, 1).status, 201)
        self.assertEqual(self.text("a" * 4097, 2).code, "invalid_payload")
        self.assertEqual(self.text("\u00e9" * 2048, 3).status, 201)         # 4096 bytes, 2048 characters
        self.assertEqual(self.text("\u00e9" * 2049, 4).code, "invalid_payload")  # 4098 bytes
        self.assertEqual(self.text("\u20ac" * 1365 + "a", 5).status, 201)  # 4096 bytes
        self.assertEqual(self.text("\U0001f600" * 1025, 6).code, "invalid_payload")  # 4100 bytes, 1025 characters

    def test_CORE_TEXT_003_nul_and_unpaired_surrogates_are_invalid(self):
        for bad in ("a\u0000b", "\u0000", "\ud800", "a\udc00", "\ud83d", "\ud800a"):
            raw = json.dumps(send_body(1, payload={"text": bad})).encode("ascii")  # \u escapes on the wire
            r = self.c.send(None, raw=raw, headers=harness.JSON)
            self.assertEqual((r.status, r.code), (400, "invalid_payload"), ascii(bad))
        pair = json.dumps(send_body(2, payload={"text": "\U0001f600"})).encode("ascii")  # a valid pair
        self.assertEqual(self.c.send(None, raw=pair, headers=harness.JSON).status, 201)

    def test_CORE_TEXT_005_CORE_SRV_035_text_is_stored_and_delivered_exactly(self):
        samples = ["  leading and trailing  ", "Mixed CASE", "e\u0301 vs \u00e9", "line1\nline2\r\n\ttab", "\U0001f600 \u202e rtl",
                   "quote \" backslash \\ slash / <tag> &amp;", "\u00e9\u00e9", "  \u00a0 x"]
        for i, s in enumerate(samples, 1):
            self.assertEqual(self.text(s, i).status, 201)
        got = [m["payload"]["text"] for m in self.c.poll("bob").json["messages"]]
        self.assertEqual(got, samples)

    def test_CORE_ERR_002_invalid_payload_is_reported_before_unknown_sender(self):
        r = self.c.send(send_body(1, sender="ghost", payload={"text": " "}))
        self.assertEqual(r.code, "invalid_payload")


class SizeTests(ServerTestCase, unittest.TestCase):
    def test_body_of_exactly_body_max_bytes_is_accepted_and_one_more_is_413(self):
        self.register("alice", "bob")
        limit = harness.CONSTANTS["BODY_MAX_BYTES"]
        body = send_body(1, type="x", payload={"pad": ""})
        overhead = len(json.dumps(body, separators=(",", ":")).encode("utf-8"))
        for extra, expect in ((0, 201), (1, 413)):
            body["payload"]["pad"] = "p" * (limit - overhead + extra)
            raw = json.dumps(body, separators=(",", ":")).encode("utf-8")
            self.assertEqual(len(raw), limit + extra)
            r = self.c.send(None, raw=raw, headers=harness.JSON)
            self.assertEqual(r.status, expect)
            if expect == 413:
                self.assertEqual(r.code, "payload_too_large")


if __name__ == "__main__":
    unittest.main()
