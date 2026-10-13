"""Protocol constants: the table of spec/core/protocol.md section 13 (CORE-CONST-001).

Must equal spec/core/schema/constants.json; tests/protocol checks that.
"""

PROTOCOL = "aware"
PROTOCOL_VERSION = 1
NAME_MAX_LENGTH = 32
TEXT_MAX_BYTES = 4096
BODY_MAX_BYTES = 65536
POLL_LIMIT_MAX = 100
SERVER_DEFAULT_PORT = 8080

# Not in the constants table: fixed by CORE-SRV-002 and CORE-SRV-005.
DEFAULT_HOST = "127.0.0.1"
CORS_MAX_AGE_S = 600

# CORE-CAP-001 in this version.
CORE_TYPES = ["text"]
SERVER_CAPABILITIES: list = []
