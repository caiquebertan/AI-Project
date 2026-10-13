"""HTTP layer: routing, transport checks (CORE-SRV-011), CORS, error bodies, request log."""
from __future__ import annotations

import http.client
import re
import socket
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

from . import api
from .api import ApiError, error_body
from .constants import BODY_MAX_BYTES, CORS_MAX_AGE_S
from .state import ServerState

JSON_TYPE = "application/json; charset=utf-8"
# S-4: application/json, optionally with charset=utf-8 (value quoted or not, no blanks around "="); header value is OWS-trimmed
CONTENT_TYPE_RE = re.compile(r"application/json(?:[ \t]*;[ \t]*charset=(?:\"utf-8\"|utf-8))?", re.IGNORECASE)
TOKEN_RE = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+")
BAD_VALUE_RE = re.compile(r"[\x00-\x08\x0a-\x1f\x7f]")
MAX_HEADERS = 100
MAILBOX_RE = re.compile(r"/v1/mailboxes/([^/]*)/messages")
DRAIN_MAX_BYTES = 1 << 20
DRAIN_TIMEOUT_S = 0.5


def match_route(path: str):
    """(endpoint id, method, path argument) for a known path, else None."""
    if path == "/v1/info":
        return "E1", "GET", None
    if path == "/v1/session":
        return "E2", "POST", None
    if path == "/v1/messages":
        return "E3", "POST", None
    if path == "/v1/users":
        return "E5", "GET", None
    m = MAILBOX_RE.fullmatch(path)
    return ("E4", "GET", unquote(m.group(1))) if m else None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    state: ServerState  # set on the subclass made by make_server

    # ----------------------------------------------------------- request parsing (S-9)
    def parse_request(self) -> bool:
        """Strict HTTP/1.1 request line and headers instead of http.server's lenient ones. Anything that is not
        valid HTTP/1.1 (request line, version, header syntax, Host) is 400 malformed_request, then close."""
        self.command, self.request_version, self.close_connection = None, "HTTP/1.1", True
        line = self.raw_requestline.decode("iso-8859-1")
        self.requestline = line.rstrip("\r\n")
        parts = self.requestline.split(" ")
        if (not line.endswith("\r\n") or len(parts) != 3 or TOKEN_RE.fullmatch(parts[0]) is None
                or not parts[1] or BAD_VALUE_RE.search(parts[1]) or parts[2] != "HTTP/1.1"):
            self.send_error(400, "request line is not valid HTTP/1.1")
            return False
        self.command, self.path = parts[0], parts[1]
        headers = http.client.HTTPMessage()
        while True:
            raw = self.rfile.readline(65537).decode("iso-8859-1")
            if raw == "\r\n":
                break
            name, colon, value = raw.partition(":")
            value = value.strip(" \t\r\n")
            if (not raw.endswith("\r\n") or not colon or TOKEN_RE.fullmatch(name) is None  # EOF, bare LF, obs-fold, no colon, "Name :"
                    or BAD_VALUE_RE.search(value) or len(headers) >= MAX_HEADERS):
                self.send_error(400, "header syntax is not valid HTTP/1.1")
                return False
            headers[name] = value
        self.headers = headers
        if len(headers.get_all("Host", [])) != 1:
            self.send_error(400, "exactly one Host header is required")
            return False
        tokens = {t.strip().lower() for v in headers.get_all("Connection", []) for t in v.split(",")}
        self.close_connection = "close" in tokens
        if headers.get("Expect", "").lower() == "100-continue" and not self.handle_expect_100():
            return False
        return True

    # ----------------------------------------------------------- dispatch
    def _serve(self, method: str) -> None:
        start = time.monotonic()
        self._body_read = False
        try:
            status, body = self._route(method)
        except ApiError as exc:
            status, body = exc.status, error_body(exc.code, exc.message)
            self.close_connection = self.close_connection or exc.close
        except Exception:  # a server bug must still answer with the error body (CORE-ERR-001)
            traceback.print_exc(file=sys.stderr)
            status, body = 500, error_body("internal_error", "internal server error")
        if not self._body_read and self._declares_body():
            # Unread body bytes would be parsed as the next request line: do not reuse the connection.
            self.close_connection = True
        self._log(method, status, start)
        self._send(status, body, method)

    def _declares_body(self) -> bool:
        if self.headers.get("Transfer-Encoding") is not None:
            return True
        return any(v.strip() != "0" for v in self.headers.get_all("Content-Length", []))

    def _log(self, method: str, status: int, start: float) -> None:
        """CORE-SRV-007, written before the answer goes out so a client that has its answer can rely on the line."""
        path = getattr(self, "path", "-").partition("?")[0]
        sys.stderr.write("%s %s %d %dms\n" % (method, path, status, (time.monotonic() - start) * 1000))
        sys.stderr.flush()

    def _route(self, method: str):
        path, _, query = self.path.partition("?")
        if method == "OPTIONS" and (path == "/v1" or path.startswith("/v1/")):
            return 204, None
        route = match_route(path)
        if route is None:
            raise ApiError(404, "not_found", f"no such path: {path}")
        endpoint, allowed, arg = route
        if method != allowed:
            raise ApiError(405, "method_not_allowed", f"{method} is not allowed on {path}")
        state = self.state
        if endpoint == "E1":
            return 200, api.info(state)
        if endpoint == "E5":
            return 200, api.users(state)
        if endpoint == "E4":
            return 200, api.poll(state, arg, query)
        raw = self._read_body()
        if endpoint == "E2":
            return 200, api.session(state, raw)
        return api.send(state, query, raw)

    def _read_body(self) -> bytes:
        """CORE-SRV-011: Content-Type (415), then Content-Length (400 / 413 without reading), then the body."""
        types = self.headers.get_all("Content-Type", [])
        if len(types) != 1 or CONTENT_TYPE_RE.fullmatch(types[0]) is None:
            raise ApiError(415, "unsupported_media_type", "Content-Type must be application/json", close=True)
        lengths = {v.strip() for v in self.headers.get_all("Content-Length", [])}
        if self.headers.get("Transfer-Encoding") is not None and lengths:
            raise ApiError(400, "malformed_request", "Transfer-Encoding together with Content-Length", close=True)
        if len(lengths) > 1:
            raise ApiError(400, "malformed_request", "conflicting Content-Length values", close=True)
        length = lengths.pop() if lengths else None
        if length is None:
            raise ApiError(400, "malformed_request", "Content-Length is required", close=True)
        if re.fullmatch(r"[0-9]{1,18}", length.strip()) is None:
            raise ApiError(400, "malformed_request", "Content-Length is not a decimal integer", close=True)
        n = int(length)
        if n > BODY_MAX_BYTES:
            raise ApiError(413, "payload_too_large", f"body is larger than {BODY_MAX_BYTES} bytes", close=True)
        self._body_read = True
        raw = self.rfile.read(n)
        if len(raw) != n:
            raise ApiError(400, "malformed_request", "body ended before Content-Length bytes", close=True)
        return raw

    # ----------------------------------------------------------- response
    def _send(self, status: int, body: str | None, method: str) -> None:
        data = b"" if body is None else body.encode("utf-8")
        try:
            self._write(status, data, method)
        except OSError:  # the client went away before reading the answer
            self.close_connection = True
            return
        if self.close_connection:
            self._drain()

    def _write(self, status: int, data: bytes, method: str) -> None:
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")  # CORE-SRV-005
        if status == 204:
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", str(CORS_MAX_AGE_S))
        else:
            self.send_header("Content-Type", JSON_TYPE)  # CORE-HTTP-003
        self.send_header("Content-Length", str(len(data)))
        if self.close_connection:
            self.send_header("Connection", "close")
        self.end_headers()
        if method != "HEAD":
            self.wfile.write(data)
        self.wfile.flush()

    def _drain(self) -> None:
        """After an early error the request body is unread; discard a bounded amount so the
        client reads the response instead of a connection reset."""
        try:
            self.connection.shutdown(socket.SHUT_WR)
            self.connection.settimeout(DRAIN_TIMEOUT_S)
            left = DRAIN_MAX_BYTES
            while left > 0:
                chunk = self.connection.recv(min(65536, left))
                if not chunk:
                    break
                left -= len(chunk)
        except OSError:
            pass

    def send_error(self, code, message=None, explain=None):
        """Request-line or header problems found by http.server itself: still the JSON error body."""
        if code == 501:  # a method http.server does not know
            known = match_route(self.path.partition("?")[0]) is not None
            status, err = (405, "method_not_allowed") if known else (404, "not_found")
        else:
            status, err = 400, "malformed_request"
        self.close_connection = True
        self.request_version = "HTTP/1.1"  # a response without status line and headers (HTTP/0.9) is no JSON error
        self._log(self.command or "-", status, time.monotonic())
        self._send(status, error_body(err, message or "bad request"), self.command or "GET")

    def log_message(self, format, *args):  # replaced by the line of _serve (CORE-SRV-007)
        pass

    do_GET = lambda self: self._serve("GET")        # noqa: E731
    do_POST = lambda self: self._serve("POST")      # noqa: E731
    do_PUT = lambda self: self._serve("PUT")        # noqa: E731
    do_DELETE = lambda self: self._serve("DELETE")  # noqa: E731
    do_PATCH = lambda self: self._serve("PATCH")    # noqa: E731
    do_HEAD = lambda self: self._serve("HEAD")      # noqa: E731
    do_OPTIONS = lambda self: self._serve("OPTIONS")  # noqa: E731


class AwareServer(ThreadingHTTPServer):
    """One thread per connection (CORE-SRV-003)."""

    daemon_threads = True
    request_queue_size = 128  # the default of 5 resets bursts of concurrent connects before a handler runs


def make_server(host: str, port: int, state: ServerState) -> AwareServer:
    handler = type("BoundHandler", (Handler,), {"state": state})
    return AwareServer((host, port), handler)
