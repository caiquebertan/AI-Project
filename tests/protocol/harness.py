"""Shared helpers for the protocol tests: in-process server, HTTP client, schema validation.

Every response read through `Client.call` is checked against the JSON schemas of
spec/core/schema/ (index.json), the CORE-ERR-001 error body, CORE-HTTP-003 and
CORE-SRV-005, so no test can pass on a response that breaks the contract.
"""
from __future__ import annotations

import calendar
import http.client
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = ROOT / "server"
SCHEMA_DIR = ROOT / "spec" / "core" / "schema"
sys.path.insert(0, str(SERVER_DIR))
sys.path.insert(0, str(ROOT / "generator" / "scripts"))

import check_schema_examples as cse  # noqa: E402  (schema checker of the harness, reused)
from aware_server import httpd  # noqa: E402
from aware_server.httpd import make_server  # noqa: E402
from aware_server.state import ServerState  # noqa: E402

# The in-process server logs one line per request (CORE-SRV-007); keep the test output clean.
httpd.sys = types.SimpleNamespace(stderr=open(os.devnull, "w"))

JSON = {"Content-Type": "application/json"}
EPOCH_A = "3f9a1c7e5b2d4086"  # Appendix A
SCHEMAS = cse.Schemas(SCHEMA_DIR)
INDEX = json.loads((SCHEMA_DIR / "index.json").read_text(encoding="utf-8"))
CONSTANTS = json.loads((SCHEMA_DIR / "constants.json").read_text(encoding="utf-8"))
# protocol.md section 12: error code -> status
ERROR_STATUS = {"malformed_request": 400, "invalid_name": 400, "invalid_id": 400, "invalid_type": 400,
                "invalid_payload": 400, "unknown_sender": 403, "not_found": 404, "method_not_allowed": 405,
                "id_conflict": 409, "epoch_mismatch": 409, "payload_too_large": 413,
                "unsupported_media_type": 415, "internal_error": 500}
ERROR_CODES = SCHEMAS.load("error.schema.json")["properties"]["error"]["properties"]["code"]["enum"]


def uid(n: int) -> str:
    """A valid message id (lowercase UUID v4) for test number n."""
    return "00000000-0000-4000-8000-%012x" % n


def utc_ms(text: str) -> int:
    """Integer milliseconds since the epoch of a UTC timestamp string, for the injected clock."""
    return calendar.timegm(time.strptime(text[:19], "%Y-%m-%dT%H:%M:%S")) * 1000 + int(text[20:23])


_DEFAULT = object()


def send_body(n: int = 1, sender="alice", to="bob", type="text", payload=_DEFAULT, created_at="2026-10-13T15:00:01.000Z"):
    """A valid send form; `payload` defaults to a text payload (any value, even None, is used as given)."""
    return {"id": uid(n), "from": sender, "to": to, "type": type,
            "payload": {"text": f"message {n}"} if payload is _DEFAULT else payload, "created_at": created_at}


class Response:
    def __init__(self, status: int, headers: dict, raw: bytes):
        self.status, self.headers, self.raw = status, headers, raw
        self.json = json.loads(raw.decode("utf-8")) if raw else None

    @property
    def code(self):
        return self.json["error"]["code"] if self.json and "error" in self.json else None


class RunningServer:
    """A server on a free port in a background thread (the CLI is covered by test_runtime)."""

    def __init__(self, epoch=None, clock=None):
        self.state = ServerState(epoch=epoch, clock=clock)
        self.httpd = make_server("127.0.0.1", 0, self.state)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.epoch = self.state.epoch

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(5)


def schema_problems(method: str, path: str, response: Response, request_type: str | None = None) -> list[str]:
    """Contract problems of one response: schema of its endpoint and status, headers, error body."""
    problems = []
    if response.headers.get("access-control-allow-origin") != "*":
        problems.append("missing Access-Control-Allow-Origin: *")
    if response.status == 204:
        return problems
    if response.headers.get("content-type") != "application/json; charset=utf-8":
        problems.append(f"Content-Type is {response.headers.get('content-type')!r}")
    route = path.partition("?")[0]
    schema_name = None
    if response.status >= 400:
        schema_name = "error.schema.json"
        if response.json is None or response.code not in ERROR_CODES:
            problems.append(f"error body without a known code: {response.raw[:120]!r}")
        elif ERROR_STATUS[response.code] != response.status:
            problems.append(f"{response.code} with status {response.status}")
    else:
        for ep in INDEX["endpoints"]:
            ours = ep["path"].replace("{name}", "__name__")
            mine = route
            if ep["id"] == "E4" and route.startswith("/v1/mailboxes/"):
                mine = route.replace(route.split("/")[3], "__name__")
            if ours == mine and ep["method"] == method:
                schema_name = ep["responses"].get(str(response.status))
        if schema_name is None:
            problems.append(f"no schema for {method} {route} -> {response.status}")
    if schema_name:
        errs = cse.validate(response.json, SCHEMAS.load(schema_name), SCHEMAS, schema_name)
        errs += cse.core_payload_errors(response.json, INDEX["core_types"], SCHEMAS)
        problems += errs
    return problems


class Client:
    def __init__(self, server: RunningServer):
        self.server = server

    def call(self, method: str, path: str, body=None, headers=None, raw: bytes | None = None, check=True) -> Response:
        """One request on a fresh connection. `body` is JSON-encoded; `raw` is sent as is."""
        data = raw if raw is not None else (json.dumps(body).encode("utf-8") if body is not None else None)
        hdrs = dict(JSON) if (data is not None and headers is None) else dict(headers or {})
        conn = http.client.HTTPConnection("127.0.0.1", self.server.port, timeout=10)
        try:
            conn.request(method, path, body=data, headers=hdrs)
            r = conn.getresponse()
            res = Response(r.status, {k.lower(): v for k, v in r.getheaders()}, r.read())
        finally:
            conn.close()
        if check:
            problems = schema_problems(method, path, res)
            assert not problems, f"{method} {path} -> {res.status}: {problems}\n{res.raw[:300]!r}"
        return res

    # --- endpoint shortcuts
    def info(self):
        return self.call("GET", "/v1/info")

    def session(self, name, capabilities=()):
        return self.call("POST", "/v1/session", {"name": name, "capabilities": list(capabilities)})

    def send(self, body, epoch=None, **kw):
        return self.call("POST", f"/v1/messages?epoch={epoch or self.server.epoch}", body, **kw)

    def poll(self, name, after=0, limit=None, epoch=None, extra="", **kw):
        q = f"epoch={epoch or self.server.epoch}&after={after}" + (f"&limit={limit}" if limit is not None else "") + extra
        return self.call("GET", f"/v1/mailboxes/{name}/messages?{q}", **kw)

    def users(self):
        return self.call("GET", "/v1/users")


def raw_exchange(port: int, request: bytes, read_timeout: float = 5.0) -> tuple[int, dict, bytes]:
    """Send raw bytes, read one response (status, lower-cased headers, body)."""
    with socket.create_connection(("127.0.0.1", port), timeout=read_timeout) as s:
        s.sendall(request)
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
        head, _, rest = buf.partition(b"\r\n\r\n")
        lines = head.decode("latin-1").split("\r\n")
        status = int(lines[0].split()[1])
        headers = {k.lower(): v.strip() for k, v in (ln.split(":", 1) for ln in lines[1:])}
        want = int(headers.get("content-length", "0"))
        while len(rest) < want:
            chunk = s.recv(65536)
            if not chunk:
                break
            rest += chunk
        return status, headers, rest[:want]


class ServerTestCase:
    """Mixin: a fresh server per test, `self.c` the client."""

    def setUp(self):
        self.srv = RunningServer()
        self.c = Client(self.srv)

    def tearDown(self):
        self.srv.close()

    def register(self, *names):
        for n in names:
            assert self.c.session(n).status == 200


LISTEN_RE = re.compile(r"^aware-server listening on http://(127\.0\.0\.1):([0-9]+) epoch=([0-9a-f]{16})$")


class Proc:
    """The real command line in a subprocess (cwd is an empty temporary directory)."""

    def __init__(self, *args, env=None):
        self.cwd = tempfile.mkdtemp(prefix="aware-test-")
        full_env = {k: v for k, v in os.environ.items() if not k.startswith("AWARE_")}
        full_env["PYTHONPATH"] = str(SERVER_DIR)
        full_env.update(env or {})
        self.p = subprocess.Popen([sys.executable, "-m", "aware_server", *args], cwd=self.cwd, env=full_env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.line = self.p.stdout.readline().rstrip("\n")
        m = LISTEN_RE.match(self.line)
        self.port = int(m.group(2)) if m else None
        self.epoch = m.group(3) if m else None

    def client(self) -> Client:
        return Client(types.SimpleNamespace(port=self.port, epoch=self.epoch))

    def stop(self):
        self.p.terminate()
        out, err = self.p.communicate(timeout=10)
        return out, err
