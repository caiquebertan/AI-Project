"""Generic relay of unknown types: CORE-EXT-001, CORE-SRV-040, CORE-SRV-042, CORE-SRV-035, Appendix B."""
import json
import unittest

import harness
from harness import JSON, ServerTestCase, send_body, uid

REACTION = {"target_id": "00000000-0000-4000-8000-0000000000a1", "reaction": "+1"}


class Relay(ServerTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.register("alice", "bob")

    def test_CORE_EXT_001_CORE_SRV_040_appendix_b_extension_envelope_is_relayed_through_e3_and_e4(self):
        body = {"id": "00000000-0000-4000-8000-0000000000c1", "from": "bob", "to": "alice", "type": "reactions.add",
                "payload": REACTION, "created_at": "2026-10-13T15:10:00.000Z"}
        r = self.c.send(body)
        self.assertEqual((r.status, r.json["seq"]), (201, 1))
        msg = self.c.poll("alice").json["messages"][0]
        self.assertEqual({k: msg[k] for k in body}, body)
        self.assertEqual((msg["seq"], msg["accepted_at"]), (1, r.json["accepted_at"]))

    def test_CORE_SRV_040_payload_of_an_unknown_type_is_stored_and_delivered_unchanged(self):
        payloads = [{}, {"text": 5}, {"text": ""}, {"text": None, "extra": [1, 2]}, {"a": {"b": {"c": [None, True, False, "x"]}}},
                    {"\u00e9": "\u00e9", "k\"q": "v\\", "\u2028": "\U0001f600"},
                    {"t": "\u0000 nul and \ud800 lone surrogate"}]
        for i, payload in enumerate(payloads, 1):
            raw = json.dumps(send_body(i, type="x.y", payload=payload)).encode("ascii")
            self.assertEqual(self.c.send(None, raw=raw, headers=JSON).status, 201, payload)
        # numbers spelled in ways json.dumps would normalize, sent as literal text
        literal = ('{"id":"%s","from":"alice","to":"bob","type":"x.y","created_at":"2026-10-13T15:00:01.000Z",'
                   '"payload":{"n":[1.0,1e2,1E+2,0.10,-0,12345678901234567890123,-1.5e-7,123456789012345678901234567890.5]}}'
                   % uid(99))
        self.assertEqual(self.c.send(None, raw=literal.encode(), headers=JSON).status, 201)
        got = self.c.poll("bob")
        self.assertEqual([m["payload"] for m in got.json["messages"][:-1]], payloads)
        text = got.raw.decode("utf-8")
        for token in ("1.0", "1e2", "1E+2", "0.10", "12345678901234567890123", "-1.5e-7", "-0", "123456789012345678901234567890.5"):
            self.assertIn(token, text, "number text must come back as sent")

    def test_CORE_SRV_040_the_server_does_not_read_the_payload_of_an_unknown_type(self):
        # shapes that would be invalid for the core type text are fine for any other type, even one that looks alike
        for i, t in enumerate(("text.v2", "texts", "te", "x", "reactions.remove", "a.b.c.d"), 1):
            self.assertEqual(self.c.send(send_body(i, type=t, payload={"text": ["not", "a", "string"]})).status, 201, t)

    def test_CORE_EXT_001_a_core_type_payload_is_validated_the_same_way_as_any_envelope_field(self):
        self.assertEqual(self.c.send(send_body(1, type="text", payload=REACTION)).code, "invalid_payload")
        self.assertEqual(self.c.send(send_body(1, type="reactions.add", payload=REACTION)).status, 201)

    def test_CORE_SRV_042_CORE_EXT_001_no_server_change_for_a_client_only_extension(self):
        # capabilities declared (or not) at E2 do not gate which types the server relays
        self.c.session("alice", [])
        self.c.session("bob", ["reactions"])
        self.assertEqual(self.c.send(send_body(1, sender="alice", type="reactions.add", payload=REACTION)).status, 201)
        self.assertEqual(self.c.send(send_body(2, sender="bob", to="alice", type="anything.else", payload={"k": 1})).status, 201)
        self.assertEqual(self.c.info().json["server_capabilities"], [])
        self.assertEqual(self.c.users().json["users"],
                         [{"name": "alice", "capabilities": []}, {"name": "bob", "capabilities": ["reactions"]}])

    def test_CORE_EXT_001_unknown_types_take_a_seq_and_interleave_with_text_in_order(self):
        self.c.send(send_body(1))
        self.c.send(send_body(2, type="reactions.add", payload=REACTION))
        self.c.send(send_body(3))
        self.assertEqual([(m["seq"], m["type"]) for m in self.c.poll("bob").json["messages"]],
                         [(1, "text"), (2, "reactions.add"), (3, "text")])
        self.assertEqual(self.c.poll("bob", after=1, limit=1).json["next_cursor"], 2)  # cursor advances past it

    def test_CORE_SRV_035_unknown_type_duplicates_follow_the_same_dedupe_rules(self):
        first = self.c.send(send_body(1, type="x.y", payload={"k": [1, {"z": 1}]}))
        self.assertEqual(self.c.send(send_body(1, type="x.y", payload={"k": [1.0, {"z": 1.0}]})).json, first.json)
        self.assertEqual(self.c.send(send_body(1, type="x.y", payload={"k": [1, {"z": 2}]})).code, "id_conflict")


if __name__ == "__main__":
    unittest.main()
