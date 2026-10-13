"""Error bodies, codes, statuses and precedence: CORE-ERR-001, CORE-ERR-002, section 1 routing (404, 405)."""
import unittest
from unittest import mock

import harness
from harness import ERROR_STATUS, JSON, ServerTestCase, raw_exchange, send_body


class RoutingErrors(ServerTestCase, unittest.TestCase):
    def test_CORE_ERR_001_CORE_HTTP_002_unknown_paths_and_paths_outside_v1_are_404_not_found_for_every_method(self):
        paths = ["/", "/v1", "/v1/", "/v1/info/", "/v1/Info", "/v2/info", "/info", "/v1/mailboxes", "/v1/mailboxes/bob",
                 "/v1/mailboxes/bob/messages/x", "/v1/mailboxes/bob/Messages", "/v1/mailboxes/a/b/messages",
                 "/v1/session/x", "/v1/messages/", "/v1/users/alice", "/v1//info", "/favicon.ico"]
        for method in ("GET", "POST", "PUT", "DELETE", "PATCH"):
            for path in paths:
                r = self.c.call(method, path, {} if method in ("POST", "PUT", "PATCH") else None)
                self.assertEqual((r.status, r.code), (404, "not_found"), (method, path))

    def test_CORE_ERR_001_known_path_with_another_method_is_405_method_not_allowed(self):
        wrong = {"/v1/info": ("POST", "PUT", "DELETE", "PATCH"), "/v1/users": ("POST", "PUT", "DELETE", "PATCH"),
                 "/v1/session": ("GET", "PUT", "DELETE", "PATCH"), "/v1/messages": ("GET", "PUT", "DELETE", "PATCH"),
                 "/v1/mailboxes/bob/messages": ("POST", "PUT", "DELETE", "PATCH")}
        for path, methods in wrong.items():
            for method in methods:
                r = self.c.call(method, path, {} if method in ("POST", "PUT", "PATCH") else None)
                self.assertEqual((r.status, r.code), (405, "method_not_allowed"), (method, path))

    def test_CORE_ERR_001_405_is_decided_before_the_body_is_looked_at(self):
        r = self.c.call("POST", "/v1/info", raw=b"not json", headers={"Content-Type": "text/plain"})
        self.assertEqual((r.status, r.code), (405, "method_not_allowed"))

    def test_CORE_ERR_001_head_and_unusual_methods_get_the_matching_status(self):
        r = self.c.call("HEAD", "/v1/info", check=False)  # HEAD of a known path: not an allowed method (E1 is GET)
        self.assertEqual((r.status, r.raw), (405, b""))
        status, headers, body = raw_exchange(self.srv.port, b"BREW /v1/users HTTP/1.1\r\nHost: t\r\n\r\n")
        self.assertEqual(status, 405)
        self.assertIn(b"method_not_allowed", body)
        status, _, body = raw_exchange(self.srv.port, b"BREW /nowhere HTTP/1.1\r\nHost: t\r\n\r\n")
        self.assertEqual(status, 404)
        self.assertIn(b"not_found", body)

    def test_CORE_ERR_001_garbage_request_lines_still_get_a_json_error_body(self):
        for raw in (b"GARBAGE\r\n\r\n", b"GET /v1/info HTTP/9.9\r\nHost: t\r\n\r\n", b"GET /" + b"a" * 70000 + b" HTTP/1.1\r\n\r\n"):
            status, headers, body = raw_exchange(self.srv.port, raw)
            self.assertGreaterEqual(status, 400, raw[:40])
            self.assertLess(status, 500, raw[:40])
            self.assertEqual(headers.get("content-type"), "application/json; charset=utf-8")
            self.assertIn(b'"error"', body)

    def test_CORE_ERR_001_a_server_bug_is_500_internal_error_with_the_error_body(self):
        with mock.patch("aware_server.api.info", side_effect=RuntimeError("boom")):
            r = self.c.call("GET", "/v1/info")
        self.assertEqual((r.status, r.code), (500, "internal_error"))
        self.assertNotIn("boom", r.json["error"]["message"])
        self.assertEqual(self.c.info().status, 200)  # and the server keeps serving

    def test_CORE_ERR_001_every_code_of_the_table_is_produced_with_its_status(self):
        self.register("alice")
        produced = {}

        def note(r):
            produced[r.code] = r.status
            return r

        note(self.c.call("POST", "/v1/session", {}))                                              # malformed_request
        note(self.c.session("bad name"))                                                           # invalid_name
        note(self.c.send(dict(send_body(1), id="x")))                                              # invalid_id
        note(self.c.send(send_body(1, type="Bad")))                                                # invalid_type
        note(self.c.send(send_body(1, payload={"text": ""})))                                      # invalid_payload
        note(self.c.send(send_body(1, sender="ghost")))                                            # unknown_sender
        note(self.c.call("GET", "/nope"))                                                          # not_found
        note(self.c.call("DELETE", "/v1/info"))                                                    # method_not_allowed
        self.c.send(send_body(2))
        note(self.c.send(send_body(2, payload={"text": "different"})))                             # id_conflict
        note(self.c.poll("alice", epoch="0" * 16))                                                 # epoch_mismatch
        note(self.c.call("POST", "/v1/session", raw=b"x" * 70000, headers=JSON))                   # payload_too_large
        note(self.c.call("POST", "/v1/session", raw=b"{}", headers={"Content-Type": "text/plain"}))  # unsupported_media_type
        with mock.patch("aware_server.api.users", side_effect=RuntimeError):
            note(self.c.users())                                                                   # internal_error
        self.assertEqual(produced, ERROR_STATUS)


class Precedence(ServerTestCase, unittest.TestCase):
    """CORE-ERR-002 and CORE-SRV-030: when several errors apply, the first in the fixed order wins."""

    def setUp(self):
        super().setUp()
        self.register("alice", "bob")
        self.wrong = "0" * 16

    def send(self, body=None, epoch=None, raw=None, headers=None):
        return self.c.send(body, epoch=epoch, raw=raw, headers=headers)

    def test_CORE_ERR_002_415_before_413_before_malformed(self):
        status, _, body = raw_exchange(self.srv.port, (
            f"POST /v1/messages?epoch={self.wrong} HTTP/1.1\r\nHost: t\r\nContent-Type: text/plain\r\n"
            "Content-Length: 99999999\r\n\r\n").encode())
        self.assertEqual(status, 415)
        status, _, body = raw_exchange(self.srv.port, (
            f"POST /v1/messages?epoch={self.wrong} HTTP/1.1\r\nHost: t\r\nContent-Type: application/json\r\n"
            "Content-Length: 99999999\r\n\r\n").encode())
        self.assertEqual(status, 413)
        self.assertEqual(self.send(raw=b"{broken", epoch=self.wrong).code, "malformed_request")   # JSON error, wrong epoch

    def test_CORE_ERR_002_CORE_SRV_030_malformed_before_epoch_mismatch(self):
        for body in (dict(send_body(1), extra=1), dict(send_body(1), created_at="2026-02-30T00:00:00.000Z"),
                     dict(send_body(1), **{"from": 7}), {k: v for k, v in send_body(1).items() if k != "id"}):
            self.assertEqual(self.send(body, epoch=self.wrong).code, "malformed_request", body)
        self.assertEqual(self.send(send_body(1), epoch="nonsense").code, "malformed_request")
        self.assertEqual(self.c.call("POST", "/v1/messages", send_body(1)).code, "malformed_request")  # no epoch at all

    def test_CORE_ERR_002_CORE_SRV_030_epoch_mismatch_before_all_field_errors(self):
        broken = {"id": "x", "from": "bad name", "to": "bad name", "type": "Bad", "payload": {"text": ""},
                  "created_at": "2026-10-13T15:00:01.000Z"}
        self.assertEqual(self.send(broken, epoch=self.wrong).code, "epoch_mismatch")
        self.assertEqual(self.send(send_body(1, sender="ghost"), epoch=self.wrong).code, "epoch_mismatch")

    def test_CORE_ERR_002_CORE_SRV_030_field_errors_in_the_order_name_id_type_payload(self):
        everything = {"id": "x", "from": "bad name", "to": "bad name", "type": "Bad", "payload": {"text": ""},
                      "created_at": "2026-10-13T15:00:01.000Z"}
        self.assertEqual(self.send(everything).code, "invalid_name")
        everything["from"] = everything["to"] = "alice"
        self.assertEqual(self.send(everything).code, "invalid_id")
        everything["id"] = harness.uid(1)
        self.assertEqual(self.send(everything).code, "invalid_type")
        everything["type"] = "text"
        self.assertEqual(self.send(everything).code, "invalid_payload")
        everything["from"] = "ghost"
        self.assertEqual(self.send(everything).code, "invalid_payload")                        # before unknown_sender
        everything["payload"] = {"text": "ok"}
        self.assertEqual(self.send(everything).code, "unknown_sender")

    def test_CORE_ERR_002_invalid_name_of_to_is_reported_even_if_from_is_unknown(self):
        body = send_body(1, sender="ghost", to="bad name")
        self.assertEqual(self.send(body).code, "invalid_name")

    def test_CORE_ERR_002_unknown_sender_before_id_conflict(self):
        self.send(send_body(1))
        self.assertEqual(self.send(send_body(1, sender="ghost", payload={"text": "x"})).code, "unknown_sender")
        self.assertEqual(self.send(send_body(1, payload={"text": "x"})).code, "id_conflict")

    def test_CORE_ERR_002_poll_query_errors_before_epoch_mismatch_before_invalid_name(self):
        wrong, ok = self.wrong, self.srv.epoch
        r = self.c.call("GET", f"/v1/mailboxes/bad%20name/messages?epoch={wrong}&after=abc")
        self.assertEqual(r.code, "malformed_request")
        r = self.c.call("GET", f"/v1/mailboxes/bad%20name/messages?epoch=zz&after=0")
        self.assertEqual(r.code, "malformed_request")
        r = self.c.call("GET", f"/v1/mailboxes/bad%20name/messages?epoch={wrong}&after=0")
        self.assertEqual(r.code, "epoch_mismatch")
        r = self.c.call("GET", f"/v1/mailboxes/bad%20name/messages?epoch={ok}&after=0&limit=0")
        self.assertEqual(r.code, "malformed_request")
        r = self.c.call("GET", f"/v1/mailboxes/bad%20name/messages?epoch={ok}&after=0")
        self.assertEqual(r.code, "invalid_name")

    def test_CORE_ERR_002_a_rejected_request_never_changes_state(self):
        before = (self.c.users().json, self.c.poll("bob").json)
        for body in (dict(send_body(1), extra=1), send_body(1, sender="ghost"), send_body(1, payload={"text": ""}),
                     send_body(1, type="Bad"), dict(send_body(1), id="x")):
            self.assertGreaterEqual(self.send(body).status, 400)
        self.assertEqual((self.c.users().json, self.c.poll("bob").json), before)
        self.assertEqual(self.send(send_body(1)).json["seq"], 1)


if __name__ == "__main__":
    unittest.main()
