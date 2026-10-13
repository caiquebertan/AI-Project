"""Command line and environment (CORE-SRV-002, -006)."""
from __future__ import annotations

import argparse
import os
import sys

from .constants import DEFAULT_HOST, SERVER_DEFAULT_PORT
from .httpd import make_server
from .state import ServerState


def _port(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        value = -1
    if not 0 <= value <= 65535:
        raise argparse.ArgumentTypeError(f"not a port number: {text!r}")
    return value


def parse_config(argv: list[str], environ) -> tuple[str, int]:
    """Host and port: option, else AWARE_HOST / AWARE_PORT, else the defaults (options win)."""
    parser = argparse.ArgumentParser(prog="aware-server", description="Aware reference server (in memory, no security).")
    parser.add_argument("--host", help=f"listen address (env AWARE_HOST, default {DEFAULT_HOST})")
    parser.add_argument("--port", type=_port,
                        help=f"listen port, 0 = any free port (env AWARE_PORT, default {SERVER_DEFAULT_PORT})")
    args = parser.parse_args(argv)
    host = args.host if args.host is not None else environ.get("AWARE_HOST", DEFAULT_HOST)
    if args.port is not None:
        port = args.port
    elif "AWARE_PORT" in environ:
        try:
            port = _port(environ["AWARE_PORT"])
        except argparse.ArgumentTypeError as exc:
            parser.error(f"AWARE_PORT: {exc}")
    else:
        port = SERVER_DEFAULT_PORT
    return host, port


def main(argv: list[str] | None = None) -> int:
    host, port = parse_config(sys.argv[1:] if argv is None else argv, os.environ)
    state = ServerState()
    server = make_server(host, port, state)
    print(f"aware-server listening on http://{host}:{server.server_address[1]} epoch={state.epoch}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
