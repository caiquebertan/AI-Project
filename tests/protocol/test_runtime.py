"""Runtime of the server process: CORE-SRV-001..007 (command line, stdout line, log, CORS, concurrency)."""
import os
import socket
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

import harness
from harness import LISTEN_RE, Proc, ServerTestCase, send_body

class RuntimeTests(unittest.TestCase):
    def test_CORE_SRV_002_a_port_in_use_is_a_one_line_error_and_exit_1(self):
        with socket.socket() as busy:
            busy.bind(("127.0.0.1", 0))
            busy.listen(1)
            p = Proc("--port", str(busy.getsockname()[1]))
            out, err = p.stop()
        self.assertEqual((p.line, out), ("", ""))
        self.assertEqual(p.p.returncode, 1)
        self.assertNotIn("Traceback", err)
        self.assertEqual(len(err.strip().splitlines()), 1, err)

    def test_CORE_SRV_001_no_disk_state_and_all_state_lost_on_exit(self):
        a = Proc("--port", "0")
        c = a.client()
        c.session("alice"); c.session("bob")
        self.assertEqual(c.send(send_body(1)).status, 201)
        self.assertEqual(os.listdir(a.cwd), [], "the server wrote to its working directory")
        a.stop()
        b = Proc("--port", "0")  # a new process: nothing survives
        c = b.client()
        self.assertEqual(c.users().json, {"users": []})
        self.assertEqual(c.poll("bob").json["messages"], [])
        self.assertEqual(c.session("alice").json["new_user"], True)
        self.assertEqual(os.listdir(b.cwd), [])
        b.stop()

    def test_CORE_SRV_002_defaults_options_and_environment(self):
        from aware_server import cli
        self.assertEqual(cli.parse_config([], {}), ("127.0.0.1", harness.CONSTANTS["SERVER_DEFAULT_PORT"]))
        self.assertEqual(cli.parse_config([], {"AWARE_HOST": "0.0.0.0", "AWARE_PORT": "9001"}), ("0.0.0.0", 9001))
        self.assertEqual(cli.parse_config(["--host", "127.0.0.2", "--port", "9002"],
                                          {"AWARE_HOST": "0.0.0.0", "AWARE_PORT": "9001"}), ("127.0.0.2", 9002))

    def test_CORE_SRV_002_port_zero_picks_a_free_port_and_options_win_over_environment(self):
        with socket.socket() as busy:
            busy.bind(("127.0.0.1", 0))
            busy.listen(1)
            busy_port = busy.getsockname()[1]
            p = Proc("--port", "0", env={"AWARE_PORT": str(busy_port)})  # option wins, so no clash
            self.assertIsNotNone(p.port, p.line)
            self.assertNotIn(p.port, (0, busy_port))
            self.assertEqual(p.client().info().status, 200)
            p.stop()
        q = Proc(env={"AWARE_HOST": "127.0.0.1", "AWARE_PORT": "0"})  # environment alone
        self.assertIsNotNone(q.port, q.line)
        self.assertEqual(q.client().info().status, 200)
        q.stop()

    def test_CORE_SRV_006_exactly_one_listening_line_with_the_actual_port_and_epoch(self):
        p = Proc("--port", "0")
        self.assertRegex(p.line, LISTEN_RE)
        c = p.client()
        self.assertEqual(c.info().json["epoch"], p.epoch)
        c.session("alice")
        out, _ = p.stop()
        self.assertEqual(out, "", "stdout must hold only the one listening line")

    def test_CORE_SRV_007_one_log_line_per_request_on_stderr_without_query(self):
        p = Proc("--port", "0")
        c = p.client()
        c.info()
        c.poll("alice", after=0, extra="&secret=1")
        c.call("GET", "/v1/nowhere", check=False)
        _, err = p.stop()
        lines = [ln for ln in err.splitlines() if ln.strip()]
        self.assertEqual(len(lines), 3, err)
        self.assertRegex(lines[0], r"^GET /v1/info 200 \d+ms$")
        self.assertRegex(lines[1], r"^GET /v1/mailboxes/alice/messages 200 \d+ms$")
        self.assertRegex(lines[2], r"^GET /v1/nowhere 404 \d+ms$")


class ConcurrencyAndCors(ServerTestCase, unittest.TestCase):
    def test_CORE_SRV_003_a_stalled_connection_does_not_delay_other_requests(self):
        stalled = []
        for partial in (b"POST /v1/messages?epoch=x HTTP/1.1\r\nHost: t\r\nContent-Type: application/json\r\n"
                        b"Content-Length: 100\r\n\r\n{\"id\":",  # body never completed
                        b"GET /v1/info HTTP/1.1\r\nHost: t\r\n"):  # headers never completed
            s = socket.create_connection(("127.0.0.1", self.srv.port))
            s.sendall(partial)
            stalled.append(s)
        try:
            for _ in range(3):
                t0 = time.monotonic()
                self.assertEqual(self.c.info().status, 200)
                self.assertLess(time.monotonic() - t0, 1.0)
        finally:
            for s in stalled:
                s.close()

    def test_CORE_SRV_003_CORE_SRV_004_concurrent_sends_get_unique_contiguous_seq_in_mailbox_order(self):
        self.register("alice", "bob")
        n = 60

        def one(i):
            r = self.c.send(send_body(i + 1, to="bob" if i % 2 else "alice"))
            return r.status, r.json["seq"]

        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(one, range(n)))
        self.assertTrue(all(status == 201 for status, _ in results))
        self.assertEqual(sorted(seq for _, seq in results), list(range(1, n + 1)))
        merged = []
        for box in ("alice", "bob"):
            msgs = self.c.poll(box).json["messages"]
            self.assertEqual([m["seq"] for m in msgs], sorted(m["seq"] for m in msgs))
            merged += [m["seq"] for m in msgs]
        self.assertEqual(sorted(merged), list(range(1, n + 1)))

    def test_CORE_SRV_004_concurrent_duplicates_accept_exactly_once(self):
        self.register("alice", "bob")
        with ThreadPoolExecutor(max_workers=10) as pool:
            rs = list(pool.map(lambda _: self.c.send(send_body(7)), range(20)))
        self.assertEqual(sorted(r.status for r in rs), [200] * 19 + [201])
        self.assertEqual({r.json["seq"] for r in rs}, {1})
        self.assertEqual(len({r.json["accepted_at"] for r in rs}), 1)
        self.assertEqual(len(self.c.poll("bob").json["messages"]), 1)

    def test_CORE_SRV_004_concurrent_sends_of_one_id_with_different_fields_accept_exactly_one(self):
        self.register("alice", "bob")
        with ThreadPoolExecutor(max_workers=10) as pool:
            rs = list(pool.map(lambda i: self.c.send(send_body(7, payload={"text": f"variant {i % 4}"})), range(20)))
        self.assertEqual(sum(r.status == 201 for r in rs), 1)
        self.assertTrue(all((r.status, r.code) in ((201, None), (200, None), (409, "id_conflict")) for r in rs))
        winner = next(r for r in rs if r.status == 201)
        stored = self.c.poll("bob").json["messages"]
        self.assertEqual([m["seq"] for m in stored], [winner.json["seq"]])
        for r in rs:
            if r.status != 409:           # a 200 or the 201 is the stored envelope itself
                self.assertEqual((r.json["seq"], r.json["accepted_at"]), (winner.json["seq"], winner.json["accepted_at"]))
        self.assertEqual(self.c.send(send_body(8)).json["seq"], 2)

    def test_CORE_SRV_004_CORE_POLL_006_polls_alongside_sends_never_show_a_gap_that_is_filled_later(self):
        self.register("alice", "bob")
        n = 80
        done = []

        def sender(i):
            r = self.c.send(send_body(i + 1))
            done.append(r.status)

        def poller(_):
            after, seen = 0, []
            for _ in range(25):
                page = self.c.poll("bob", after=after).json
                seen += [m["seq"] for m in page["messages"]]
                after = page["next_cursor"]
            return seen, after

        with ThreadPoolExecutor(max_workers=12) as pool:
            polls = [pool.submit(poller, i) for i in range(4)]
            sends = [pool.submit(sender, i) for i in range(n)]
            for f in sends:
                f.result()
            results = [f.result() for f in polls]
        self.assertEqual(done.count(201), n)
        final = [m["seq"] for m in self.c.poll("bob").json["messages"]]
        self.assertEqual(final, list(range(1, n + 1)))
        for seen, _ in results:           # strictly ascending, and a prefix of the final mailbox: no gap filled later
            self.assertEqual(seen, final[:len(seen)])

    def test_CORE_SRV_005_options_outside_v1_is_404(self):
        for path in ("/", "/nope", "/v10/info", "/v1x"):
            r = self.c.call("OPTIONS", path, check=False)
            self.assertEqual(r.status, 404, path)
            self.assertEqual(r.code, "not_found", path)

    def test_CORE_SRV_005_every_response_carries_allow_origin_including_errors(self):
        for method, path, body in (("GET", "/v1/info", None), ("GET", "/v1/users", None), ("GET", "/nope", None),
                                   ("PUT", "/v1/info", None), ("POST", "/v1/session", {"x": 1}),
                                   ("GET", "/v1/mailboxes/bob/messages", None)):
            r = self.c.call(method, path, body, check=False)
            self.assertEqual(r.headers.get("access-control-allow-origin"), "*", (method, path, r.status))
        r = self.c.call("POST", "/v1/session", raw=b"{}", headers={}, check=False)  # 415
        self.assertEqual((r.status, r.headers.get("access-control-allow-origin")), (415, "*"))

    def test_CORE_SRV_005_options_is_204_with_preflight_headers_on_every_v1_path(self):
        for path in ("/v1/info", "/v1/session", "/v1/messages?epoch=x", "/v1/mailboxes/bob/messages", "/v1/users", "/v1/unknown"):
            r = self.c.call("OPTIONS", path, check=False)
            self.assertEqual(r.status, 204, path)
            self.assertEqual(r.raw, b"")
            self.assertEqual(r.headers.get("access-control-allow-origin"), "*")
            self.assertEqual(r.headers.get("access-control-allow-methods"), "GET, POST, OPTIONS")
            self.assertEqual(r.headers.get("access-control-allow-headers"), "Content-Type")
            self.assertEqual(r.headers.get("access-control-max-age"), "600")


if __name__ == "__main__":
    unittest.main()
