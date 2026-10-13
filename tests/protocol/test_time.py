"""Time rules on the server: CORE-HTTP-007 (strict UTC created_at), CORE-SRV-030/031/037, CORE-TIME-001/003, CORE-ENV-006."""
import json
import re
import unittest
from pathlib import Path

import harness
from harness import Proc, RunningServer, ServerTestCase, send_body, uid, utc_ms

CASES = json.loads((harness.SCHEMA_DIR / "cases" / "timestamp.json").read_text(encoding="utf-8"))
SERVER_FILES = sorted((harness.SERVER_DIR).rglob("*.py")) + [harness.SERVER_DIR / "start.sh"]


class CreatedAtValidation(ServerTestCase, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.register("alice", "bob")

    def test_CORE_HTTP_007_CORE_SRV_030_every_valid_case_is_accepted_and_returned_unchanged(self):
        for i, value in enumerate(CASES["valid"], 1):
            r = self.c.send(send_body(i, created_at=value))
            self.assertEqual(r.status, 201, value)
        got = [m["created_at"] for m in self.c.poll("bob").json["messages"]]
        self.assertEqual(got, CASES["valid"])

    def test_CORE_HTTP_007_CORE_SRV_030_every_invalid_case_is_400_malformed_request(self):
        for i, value in enumerate(CASES["invalid"], 1):
            r = self.c.send(send_body(i, created_at=value))
            self.assertEqual((r.status, r.code), (400, "malformed_request"), value)
        self.assertEqual(self.c.poll("bob").json["messages"], [])

    def test_CORE_HTTP_007_more_calendar_and_format_cases(self):
        invalid = ["2026-10-13T15:00:01.010\n", "\n2026-10-13T15:00:01.010Z", "2026-10-13T15:00:01.010Z\n",
                   "\uff12026-10-13T15:00:01.010Z", "2026-10-13T15:00:01,010Z", "2026-10-13T15:00:01.010ZZ",
                   "2026-10-13T15:00:01.010 Z", "2026-1-13T15:00:01.010Z", "2026-10-13T5:00:01.010Z",
                   "2026-10-13T15:00:01.010+00", "2026-10-13T15:00:01.010-00:00", "2026-10-13T15:00:01.010UTC",
                   "20261013T150001.010Z", "2026-W42-2T15:00:01.010Z", "2026-10-13T15:00:61.010Z", "2026-10-32T00:00:00.000Z",
                   "2100-02-29T00:00:00.000Z", "2026-06-31T00:00:00.000Z", "2026-09-31T00:00:00.000Z",
                   "2026-11-31T00:00:00.000Z", "2026-10-13T15:00:01.0a0Z", "-026-10-13T15:00:01.010Z"]
        for i, value in enumerate(invalid, 1):
            r = self.c.send(send_body(i, created_at=value))
            self.assertEqual((r.status, r.code), (400, "malformed_request"), repr(value))
        valid = ["2400-02-29T23:59:59.999Z", "2024-02-29T00:00:00.000Z", "0000-01-01T00:00:00.000Z",
                 "9999-12-31T23:59:59.999Z", "2026-10-31T00:00:00.000Z", "2026-12-31T00:00:00.000Z",
                 "2026-01-01T00:00:00.000Z", "2026-07-31T10:10:10.001Z"]
        for i, value in enumerate(valid, 100):
            self.assertEqual(self.c.send(send_body(i, created_at=value)).status, 201, value)

    def test_CORE_HTTP_007_created_at_of_the_wrong_json_type_is_malformed(self):
        for value in (None, 1760367601010, 1.5, True, [], {}, ["2026-10-13T15:00:01.010Z"]):
            r = self.c.send(send_body(1, created_at=value))
            self.assertEqual((r.status, r.code), (400, "malformed_request"), value)

    def test_CORE_ENV_006_created_at_is_informational_only(self):
        # a far past or far future instant, in any order, changes neither validity nor order nor dedupe by itself
        self.c.send(send_body(1, created_at="9999-12-31T23:59:59.999Z"))
        self.c.send(send_body(2, created_at="0000-01-01T00:00:00.000Z"))
        self.c.send(send_body(3, created_at="2026-10-13T15:00:01.000Z"))
        msgs = self.c.poll("bob").json["messages"]
        self.assertEqual([m["id"] for m in msgs], [uid(1), uid(2), uid(3)])
        self.assertEqual([m["seq"] for m in msgs], [1, 2, 3])
        self.assertEqual(self.c.send(send_body(1, created_at="9999-12-31T23:59:59.999Z")).status, 200)

    def test_CORE_SRV_037_created_at_is_opaque_after_the_format_check_and_returned_unchanged(self):
        for i, value in enumerate(("2026-12-31T23:59:59.999Z", "2026-03-08T02:30:00.000Z", "2026-11-01T01:30:00.000Z"), 1):
            self.c.send(send_body(i, created_at=value))
        got = [m["created_at"] for m in self.c.poll("bob").json["messages"]]
        self.assertEqual(got, ["2026-12-31T23:59:59.999Z", "2026-03-08T02:30:00.000Z", "2026-11-01T01:30:00.000Z"])


class AcceptedAt(unittest.TestCase):
    def test_CORE_SRV_031_accepted_at_comes_from_the_clock_in_utc_with_milliseconds_truncated(self):
        expect = ["1970-01-01T00:00:00.000Z", "1970-01-01T00:00:00.999Z", "1970-01-01T00:00:01.000Z",
                  "2000-02-29T23:59:59.999Z", "2026-10-13T15:00:01.010Z", "2024-02-29T23:59:59.999Z",
                  "2099-12-31T23:59:59.999Z"]
        ms = [utc_ms(e) for e in expect]
        self.assertEqual(ms[:3], [0, 999, 1000])
        clock = iter(ms)
        srv = RunningServer(clock=lambda: next(clock))
        try:
            c = harness.Client(srv)
            c.session("alice")
            got = [c.send(send_body(i + 1, to="alice")).json["accepted_at"] for i in range(len(ms))]
            self.assertEqual(got, expect)
        finally:
            srv.close()

    def test_CORE_SRV_031_the_clock_is_read_only_for_newly_accepted_envelopes(self):
        reads = []
        srv = RunningServer(clock=lambda: reads.append(1) or 1791903601010)
        try:
            c = harness.Client(srv)
            c.session("alice")
            c.send(send_body(1)); c.send(send_body(1)); c.send(send_body(2, sender="ghost"))
            c.send(send_body(3, payload={"text": ""}))
            self.assertEqual(len(reads), 1)
        finally:
            srv.close()

    def test_CORE_SRV_037_CORE_TIME_001_accepted_at_is_utc_whatever_zone_the_host_is_set_to(self):
        import time
        for zone in ("Asia/Tokyo", "America/Sao_Paulo", "Pacific/Kiritimati"):  # zone values are test inputs only
            p = Proc("--port", "0", env={"TZ": zone})
            try:
                c = p.client()
                c.session("alice")
                lo = time.time_ns() // 1_000_000
                at = c.send(send_body(1, to="alice")).json["accepted_at"]
                hi = time.time_ns() // 1_000_000
                self.assertTrue(re.fullmatch(r"[0-9T:.-]{23}Z", at), at)
                self.assertTrue(lo - 1 <= utc_ms(at) <= hi + 1, (zone, at))
            finally:
                p.stop()


class NoTimeZoneInCode(unittest.TestCase):
    """CORE-TIME-003 / CORE-SRV-037 as a denylist over the server's code and start script."""

    DENY = [
        (r"\b[A-Z][A-Za-z]+(?:_[A-Za-z]+)*/[A-Z][A-Za-z]+(?:_[A-Za-z]+)*\b", "IANA zone identifier"),
        (r"\b(?:UTC|GMT)\s*[+-]\s*[0-9]", "offset such as UTC-3 or GMT+9"),
        (r"[+-][01][0-9]:[0-5][0-9]\b", "numeric offset such as +09:00"),
        (r"\b(?:EST|EDT|CST|CDT|MST|MDT|PST|PDT|JST|BRT|CET|CEST|BST|IST|AEST)\b", "zone abbreviation"),
        (r"%[zZ]", "strftime zone directive"),
        (r"\b(?:localtime|tzinfo|timezone|tzname|tzset|astimezone|ZoneInfo|pytz|altzone|mktime|fromtimestamp|"
         r"utcoffset|getlocale|TZ)\b", "local-time or zone API"),
        (r"datetime\.(?:now|today)\(", "datetime.now()/today() reads local time unless given a zone"),
    ]

    def test_CORE_TIME_003_CORE_SRV_037_no_zone_identifier_offset_or_local_time_api_in_the_server(self):
        self.assertTrue(SERVER_FILES)
        for path in SERVER_FILES:
            text = path.read_text(encoding="utf-8")
            for pattern, what in self.DENY:
                for m in re.finditer(pattern, text):
                    line = text.count("\n", 0, m.start()) + 1
                    self.fail(f"{path.relative_to(harness.ROOT)}:{line}: {what}: {m.group(0)!r}")

    def test_CORE_SRV_037_the_denylist_catches_what_it_should(self):
        samples = ["America/Sao_Paulo", "Asia/Tokyo", "UTC-3", "GMT+9", "+09:00", "-03:00", "JST", "time.localtime()",
                   "datetime.now()", "%Z"]
        for sample in samples:
            self.assertTrue(any(re.search(p, sample) for p, _ in NoTimeZoneInCode.DENY), sample)


if __name__ == "__main__":
    unittest.main()
