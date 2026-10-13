"""Endpoint logic E1-E5: validation order of CORE-SRV-030 and CORE-ERR-002, no I/O."""
from __future__ import annotations

import json
from urllib.parse import parse_qsl

from . import constants as C
from . import jsonvalue, validation as V
from .state import ServerState, _s


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, close: bool = False):
        super().__init__(message)
        self.status, self.code, self.message, self.close = status, code, message, close


def error_body(code: str, message: str) -> str:
    return '{"error":{"code":%s,"message":%s}}' % (_s(code), _s(message))


def _malformed(message: str) -> ApiError:
    return ApiError(400, "malformed_request", message)


def parse_object(raw: bytes, what: str) -> dict:
    """Body to a JSON object (UTF-8, CORE-HTTP-001); anything else is malformed_request."""
    try:
        value = jsonvalue.parse(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise _malformed(f"{what} is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise _malformed(f"{what} must be a JSON object")
    return value


def _query(query: str) -> dict[str, str]:
    """Query parameters; a known parameter given twice is a bad parameter (see docs/runs/P2/spec-issues.md)."""
    out: dict[str, str] = {}
    for key, value in parse_qsl(query, keep_blank_values=True):
        if key in out and key in ("epoch", "after", "limit"):
            raise _malformed(f"query parameter {key} given more than once")
        out.setdefault(key, value)
    return out


def _epoch_param(params: dict[str, str]) -> str:
    epoch = params.get("epoch")
    if epoch is None or V.EPOCH_RE.fullmatch(epoch) is None:
        raise _malformed("query parameter epoch is missing or malformed")
    return epoch


def _check_epoch(state: ServerState, epoch: str) -> None:
    if epoch != state.epoch:
        raise ApiError(409, "epoch_mismatch", f"epoch {epoch} is not the current server epoch")


def info(state: ServerState) -> str:
    """E1 (CORE-CAP-001, CORE-SRV-041)."""
    return json.dumps({
        "protocol": C.PROTOCOL, "protocol_version": C.PROTOCOL_VERSION, "epoch": state.epoch,
        "core_types": C.CORE_TYPES, "server_capabilities": C.SERVER_CAPABILITIES,
        "limits": {"text_max_bytes": C.TEXT_MAX_BYTES, "body_max_bytes": C.BODY_MAX_BYTES,
                   "poll_limit_max": C.POLL_LIMIT_MAX}}, separators=(",", ":"))


def session(state: ServerState, raw: bytes) -> str:
    """E2 (CORE-SESSION-001, -002, CORE-SRV-020..022)."""
    body = parse_object(raw, "request body")
    if set(body) != {"name", "capabilities"}:
        raise _malformed("request body must contain exactly name and capabilities")
    name, capabilities = body["name"], body["capabilities"]
    if not isinstance(name, str) or not V.is_capabilities(capabilities):
        raise _malformed("name must be a string and capabilities a list of at most 32 unique capability ids")
    if not V.is_name(name):
        raise ApiError(400, "invalid_name", "name does not match ^[A-Za-z0-9_-]{1,32}$")
    name = V.canonical(name)
    new_user = state.register(name, capabilities)
    return '{"name":%s,"epoch":%s,"new_user":%s}' % (_s(name), _s(state.epoch), "true" if new_user else "false")


def send(state: ServerState, query: str, raw: bytes) -> tuple[int, str]:
    """E3, steps (2) to (8) of CORE-SRV-030. Returns (status, body)."""
    params = _query(query)
    body = parse_object(raw, "request body")                                       # (2)
    if set(body) != {"id", "from", "to", "type", "payload", "created_at"}:
        raise _malformed("request body must contain exactly id, from, to, type, payload, created_at")
    for field in ("id", "from", "to", "type", "created_at"):
        if not isinstance(body[field], str):
            raise _malformed(f"{field} must be a string")
    if not V.is_timestamp(body["created_at"]):
        raise _malformed("created_at is not a UTC instant of the form YYYY-MM-DDTHH:MM:SS.sssZ")
    _check_epoch(state, _epoch_param(params))                                      # (3)
    for field in ("from", "to"):                                                   # (4)
        if not V.is_name(body[field]):
            raise ApiError(400, "invalid_name", f"{field} does not match ^[A-Za-z0-9_-]{{1,32}}$")
    if not V.is_id(body["id"]):
        raise ApiError(400, "invalid_id", "id is not a lowercase UUID v4")
    if not V.is_type(body["type"]):
        raise ApiError(400, "invalid_type", "type does not match ^[a-z][a-z0-9_.-]{0,63}$")
    payload = body["payload"]
    if not isinstance(payload, dict):
        raise ApiError(400, "invalid_payload", "payload must be a JSON object")
    if body["type"] in C.CORE_TYPES and not V.is_text_payload(payload):           # core types only
        raise ApiError(400, "invalid_payload", "payload of type text must be {\"text\": <non-blank string, at most 4096 bytes>}")
    try:
        jsonvalue.dumps(payload)  # nesting the server could not store and return
    except RecursionError as exc:
        raise _malformed("payload nesting too deep") from exc
    sender, to = V.canonical(body["from"]), V.canonical(body["to"])               # (5)
    kind, env = state.accept(body["id"], sender, to, body["type"], payload, body["created_at"])  # (6)-(8)
    if kind == "unknown_sender":
        raise ApiError(403, "unknown_sender", f"{sender} has no session in this epoch")
    if kind == "conflict":
        raise ApiError(409, "id_conflict", f"id {env.id} was already accepted with different fields")
    reply = '{"id":%s,"seq":%d,"accepted_at":%s,"epoch":%s}' % (_s(env.id), env.seq, _s(env.accepted_at), _s(state.epoch))
    return (201 if kind == "new" else 200), reply


def poll(state: ServerState, name: str, query: str) -> str:
    """E4 (CORE-POLL-001..007, CORE-SRV-015, -016): answered at once from the mailbox as it is now."""
    params = _query(query)
    epoch = _epoch_param(params)
    after = params.get("after")
    limit = params.get("limit")
    if after is None or V.CURSOR_RE.fullmatch(after) is None:
        raise _malformed("query parameter after is missing or not a decimal integer")
    if limit is not None and (V.CURSOR_RE.fullmatch(limit) is None or int(limit) == 0):
        raise _malformed("query parameter limit must be a decimal integer of at least 1")
    _check_epoch(state, epoch)
    if not V.is_name(name):
        raise ApiError(400, "invalid_name", "mailbox name does not match ^[A-Za-z0-9_-]{1,32}$")
    limit_n = min(int(limit), C.POLL_LIMIT_MAX) if limit is not None else C.POLL_LIMIT_MAX
    envs, has_more = state.poll(V.canonical(name), int(after), limit_n)
    next_cursor = envs[-1].seq if envs else int(after)                            # CORE-POLL-004
    return '{"epoch":%s,"messages":[%s],"next_cursor":%d,"has_more":%s}' % (
        _s(state.epoch), ",".join(e.json for e in envs), next_cursor, "true" if has_more else "false")


def users(state: ServerState) -> str:
    """E5 (CORE-CAP-003)."""
    return json.dumps({"users": state.users()}, separators=(",", ":"))
