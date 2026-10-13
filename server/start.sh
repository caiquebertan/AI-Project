#!/bin/sh
# Start the Aware reference server (stdlib Python 3.10+). Options: --host, --port (see server/README.md).
here=$(cd "$(dirname "$0")" && pwd)
PYTHONPATH="$here${PYTHONPATH:+:$PYTHONPATH}" exec python3 -m aware_server "$@"
