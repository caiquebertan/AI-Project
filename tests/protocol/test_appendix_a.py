"""Replay of protocol.md Appendix A (the Alice/Bob trace) against the server, and of the schema examples.

The server is built with the Appendix A epoch and a clock that returns its fixed accepted_at values, so every
response is compared exactly. Requests are the ones of the trace, in its order (idle cycles left out, as there).
"""
import json
import unittest

import harness
from harness import EPOCH_A, Client, RunningServer, utc_ms

E = EPOCH_A
ACCEPTED = ["2026-10-13T15:00:01.010Z", "2026-10-13T15:00:02.010Z", "2026-10-13T15:00:05.010Z", "2026-10-13T15:00:07.010Z"]
TEXTS = {"A1": "Hi Bob, I have something important to tell you", "B1": "What is it?",
         "A2": "Queued by Alice while offline", "B2": "Queued by Bob while offline"}
IDS = {k: f"00000000-0000-4000-8000-0000000000{k.lower()}" for k in TEXTS}
ROUTE = {"A1": ("alice", "bob"), "B1": ("bob", "alice"), "A2": ("alice", "bob"), "B2": ("bob", "alice")}
CREATED = {"A1": "2026-10-13T15:00:01.000Z", "B1": "2026-10-13T15:00:02.000Z",
           "A2": "2026-10-13T15:00:03.000Z", "B2": "2026-10-13T15:00:04.000Z"}


def example(name):
    return json.loads((harness.SCHEMA_DIR / "examples" / name).read_text(encoding="utf-8"))


def send_form(label):
    sender, to = ROUTE[label]
    return {"id": IDS[label], "from": sender, "to": to, "type": "text", "payload": {"text": TEXTS[label]},
            "created_at": CREATED[label]}


def delivered(label, seq, accepted_at):
    return dict(send_form(label), seq=seq, accepted_at=accepted_at)


class AppendixA(unittest.TestCase):
    def setUp(self):  # a fresh server per test, with the Appendix A epoch and accepted_at values
        clock = iter(utc_ms(a) for a in ACCEPTED)
        self.srv = RunningServer(epoch=E, clock=lambda: next(clock))
        self.c = Client(self.srv)

    def tearDown(self):
        self.srv.close()

    def empty(self, cursor):
        return {"epoch": E, "messages": [], "next_cursor": cursor, "has_more": False}

    def e2(self, name, new_user):
        r = self.c.session(name.capitalize())  # the client types "Alice"; identity is canonical
        self.assertEqual((r.status, r.json), (200, {"name": name, "epoch": E, "new_user": new_user}))
        return r

    def e4(self, name, after, expect):
        r = self.c.poll(name, after=after)
        self.assertEqual((r.status, r.json), (200, expect))

    def e3(self, label, seq, status=201):
        r = self.c.send(send_form(label))
        self.assertEqual((r.status, r.json), (status, {"id": IDS[label], "seq": seq,
                                                       "accepted_at": ACCEPTED[seq - 1], "epoch": E}))

    def play_trace(self):
        # step 0: both log in
        self.assertEqual(self.e2("alice", True).json, example("session-response.alice.json"))
        self.e4("alice", 0, self.empty(0))
        self.e2("bob", True)
        self.e4("bob", 0, self.empty(0))
        self.assertEqual(self.c.users().json, {"users": [{"name": "alice", "capabilities": []},
                                                         {"name": "bob", "capabilities": []}]})
        # step 1: Alice -> Bob: A1
        self.e4("alice", 0, self.empty(0))
        r = self.c.send(example("send-request.a1.json"))
        self.assertEqual((r.status, r.json), (201, example("send-response.a1.json")))
        self.assertEqual(example("send-request.a1.json"), send_form("A1") | {"created_at": "2026-10-13T15:00:01.000Z"})
        self.e4("bob", 0, {"epoch": E, "messages": [delivered("A1", 1, ACCEPTED[0])], "next_cursor": 1, "has_more": False})
        # step 2: Bob -> Alice: B1
        self.e4("bob", 1, self.empty(1))
        self.e3("B1", 2)
        self.e4("alice", 0, {"epoch": E, "messages": [delivered("B1", 2, ACCEPTED[1])], "next_cursor": 2, "has_more": False})
        # steps 3 and 4: both offline, no requests
        # step 5: Alice reconnects, A2 reaches the server
        self.e2("alice", False)
        self.e4("alice", 2, self.empty(2))
        self.e3("A2", 3)
        # step 6: Alice offline again; step 7: Bob reconnects
        self.e2("bob", False)
        step7 = self.c.poll("bob", after=1)
        self.assertEqual((step7.status, step7.json), (200, {"epoch": E, "messages": [delivered("A2", 3, ACCEPTED[2])],
                                                            "next_cursor": 3, "has_more": False}))
        self.assertEqual(step7.json, example("poll-response.bob-step7.json"))
        self.e3("B2", 4)
        # server state after step 7: counter 4, bob [1:A1, 3:A2], alice [2:B1, 4:B2]
        bob = self.c.poll("bob", after=0).json
        alice = self.c.poll("alice", after=0).json
        self.assertEqual([m["seq"] for m in bob["messages"]], [1, 3])
        self.assertEqual([m["seq"] for m in alice["messages"]], [2, 4])
        self.assertEqual([m["id"] for m in bob["messages"]], [IDS["A1"], IDS["A2"]])
        self.assertEqual([m["id"] for m in alice["messages"]], [IDS["B1"], IDS["B2"]])
        # step 8: Alice reconnects, receives B2 (she holds cursor 2)
        self.e2("alice", False)
        self.e4("alice", 2, {"epoch": E, "messages": [delivered("B2", 4, ACCEPTED[3])], "next_cursor": 4, "has_more": False})
        self.e4("alice", 4, self.empty(4))
        self.e4("bob", 3, self.empty(3))

    def test_CORE_SEQ_001_CORE_MSG_001_CORE_POLL_003_CORE_SRV_033_appendix_a_steps_0_to_8_in_order(self):
        self.play_trace()

    def test_CORE_MSG_001_variant_lost_ack_resend_of_A2_is_200_with_the_original_values(self):
        self.play_trace()  # A2 was accepted with seq 3, B2 with seq 4
        r = self.c.send(send_form("A2"))
        self.assertEqual((r.status, r.json), (200, {"id": IDS["A2"], "seq": 3, "accepted_at": ACCEPTED[2], "epoch": E}))
        self.assertEqual(self.c.send(send_form("B2")).json["seq"], 4)
        self.assertEqual(self.c.send(send_form("B2")).status, 200)
        self.e4("bob", 0, {"epoch": E, "messages": [delivered("A1", 1, ACCEPTED[0]), delivered("A2", 3, ACCEPTED[2])],
                           "next_cursor": 3, "has_more": False})

    def test_CORE_EPOCH_002_the_trace_epoch_mismatch_example_error(self):
        self.e2("alice", True)
        r = self.c.poll("bob", after=0, epoch="0" * 16)
        self.assertEqual((r.status, r.json["error"]["code"]), (409, example("error.epoch-mismatch.json")["error"]["code"]))


if __name__ == "__main__":
    unittest.main()
