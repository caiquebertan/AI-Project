"""Transport checks of POST requests (CORE-SRV-011, CORE-HTTP-001/003/004), body parsing (CORE-SRV-030 step 2)."""
import http.client
import json
import unittest

import harness
from harness import JSON, ServerTestCase, raw_exchange, send_body

SESSION = json.dumps({"name": "alice", "capabilities": []}).encode()


def post(path: str, headers: dict, body: bytes = b"") -> bytes:
    lines = [f"POST {path} HTTP/1.1", "Host: t"] + [f"{k}: {v}" for k, v in headers.items()]
    return ("\r\n".join(lines) + "\r\n\r\n").encode() + body


class MediaTypeAndLength(ServerTestCase, unittest.TestCase):
    def test_CORE_SRV_011_wrong_or_missing_content_type_is_415_on_both_posts(self):
        for ctype in (None, "text/plain", "application/x-www-form-urlencoded", "application/jsonp", "application/json5",
                      "text/json", "application/json; charset=latin-1", "application/json; charset=utf-16", "json", ""):
            headers = {} if ctype is None else {"Content-Type": ctype}
            for path, body in (("/v1/session", SESSION),
                               (f"/v1/messages?epoch={self.srv.epoch}", json.dumps(send_body(1)).encode())):
                r = self.c.call("POST", path, raw=body, headers=headers)
                self.assertEqual((r.status, r.code), (415, "unsupported_media_type"), (ctype, path))

    def test_CORE_HTTP_003_application_json_with_utf8_charset_is_accepted(self):
        for ctype in ("application/json", "application/json; charset=utf-8", "application/json;charset=UTF-8",
                      "Application/JSON", 'application/json; charset="utf-8"'):
            r = self.c.call("POST", "/v1/session", raw=SESSION, headers={"Content-Type": ctype})
            self.assertEqual(r.status, 200, ctype)

    def test_CORE_SRV_011_missing_content_length_is_400_malformed_request(self):
        for extra in ({}, {"Transfer-Encoding": "chunked"}):
            raw = post("/v1/session", {"Content-Type": "application/json", **extra})
            if extra:
                raw += b"%x\r\n%s\r\n0\r\n\r\n" % (len(SESSION), SESSION)
            status, _, body = raw_exchange(self.srv.port, raw)
            self.assertEqual(status, 400, extra)
            self.assertEqual(json.loads(body)["error"]["code"], "malformed_request")

    def test_CORE_SRV_011_invalid_content_length_is_400_malformed_request(self):
        for value in ("abc", "-1", "1e3", "1 2", "+5", ""):
            status, _, body = raw_exchange(self.srv.port, post("/v1/session", {"Content-Type": "application/json",
                                                                              "Content-Length": value}))
            self.assertEqual((status, json.loads(body)["error"]["code"]), (400, "malformed_request"), value)

    def test_CORE_SRV_011_oversized_content_length_is_413_without_reading_the_body(self):
        for path in ("/v1/session", f"/v1/messages?epoch={self.srv.epoch}"):
            # the body is never sent: the answer must come anyway, so the server did not wait for it
            status, headers, body = raw_exchange(self.srv.port, post(path, {"Content-Type": "application/json",
                                                                           "Content-Length": "65537"}), read_timeout=3)
            self.assertEqual((status, json.loads(body)["error"]["code"]), (413, "payload_too_large"), path)
            status, _, _ = raw_exchange(self.srv.port, post(path, {"Content-Type": "application/json",
                                                                  "Content-Length": "99999999999"}), read_timeout=3)
            self.assertEqual(status, 413)

    def test_CORE_SRV_011_a_413_for_a_really_sent_large_body_reaches_the_client(self):
        r = self.c.call("POST", "/v1/session", raw=b"[" + b"0," * 200000 + b"0]", headers=JSON)
        self.assertEqual((r.status, r.code), (413, "payload_too_large"))
        self.assertEqual(self.c.session("alice").status, 200)

    def test_CORE_SRV_011_content_length_is_checked_after_the_media_type_and_before_the_json(self):
        r = self.c.call("POST", "/v1/session", raw=b"", headers=JSON)  # Content-Length: 0 is present, JSON is empty
        self.assertEqual((r.status, r.code), (400, "malformed_request"))


class BodyParsing(ServerTestCase, unittest.TestCase):
    def test_CORE_HTTP_001_CORE_SRV_030_body_must_be_one_utf8_json_object(self):
        bad = [b"", b" ", b"{", b"{}}", b"{} {}", b"[]", b"null", b"5", b'"x"', b"true", b"{'name':'a'}", b'{"name":"a",}',
               b'{"name":"alice","capabilities":[]}x', b"\xef\xbb\xbf" + SESSION, b'{"name":"\xff","capabilities":[]}',
               SESSION.decode().encode("utf-16"), b'{"name":"alice","capabilities":[NaN]}',
               b'{"name":"alice","capabilities":[Infinity]}', b"[" * 60000, b'{"name":"alice","capabilities":[]}\x00']
        for raw in bad:
            r = self.c.call("POST", "/v1/session", raw=raw, headers=JSON)
            self.assertEqual((r.status, r.code), (400, "malformed_request"), raw[:40])
        self.assertEqual(self.c.users().json, {"users": []})

    def test_CORE_HTTP_001_whitespace_around_the_json_is_allowed(self):
        r = self.c.call("POST", "/v1/session", raw=b' \r\n\t{ "name" : "alice" ,\n"capabilities":[ ] }\n ', headers=JSON)
        self.assertEqual(r.status, 200)

    def test_CORE_HTTP_001_responses_are_utf8_json_and_connections_are_keep_alive_http_1_1(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.srv.port, timeout=5)
        try:
            for _ in range(3):
                conn.request("POST", "/v1/session", body=SESSION, headers=JSON)
                r = conn.getresponse()
                self.assertEqual((r.version, r.status), (11, 200))
                self.assertEqual(json.loads(r.read().decode("utf-8"))["name"], "alice")
                conn.request("GET", "/v1/info")
                r = conn.getresponse()
                self.assertEqual(r.status, 200)
                r.read()
        finally:
            conn.close()

    def test_CORE_HTTP_003_every_response_with_a_body_has_the_json_utf8_content_type(self):
        self.register("alice")
        for method, path, body, headers in (("GET", "/v1/info", None, {}), ("GET", "/v1/users", None, {}),
                                            ("GET", "/nope", None, {}), ("POST", "/v1/session", b"x", JSON),
                                            ("POST", "/v1/session", SESSION, {"Content-Type": "text/plain"})):
            r = self.c.call(method, path, raw=body, headers=headers, check=False)
            self.assertEqual(r.headers.get("content-type"), "application/json; charset=utf-8", (method, path, r.status))

    def test_CORE_HTTP_004_unknown_fields_are_rejected_in_every_request_body(self):
        self.assertEqual(self.c.call("POST", "/v1/session", {"name": "alice", "capabilities": [], "x": 1}).code,
                         "malformed_request")
        self.register("alice")
        self.assertEqual(self.c.send(dict(send_body(1), x=1)).code, "malformed_request")

    def test_CORE_SRV_030_body_is_not_required_to_be_read_for_get_requests(self):
        r = self.c.call("GET", "/v1/info", raw=b"ignored body", headers=JSON)
        self.assertEqual(r.status, 200)


if __name__ == "__main__":
    unittest.main()
