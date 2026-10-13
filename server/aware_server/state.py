"""In-memory server state and its atomic operations (CORE-SRV-001, -004, -010, -020..-036)."""
from __future__ import annotations

import bisect
import json
import secrets
import threading
import time

from . import jsonvalue


def format_utc(ms: int) -> str:
    """UTC instant in the form of CORE-HTTP-007 from integer milliseconds since 1970-01-01T00:00:00Z."""
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ms // 1000)) + ".%03dZ" % (ms % 1000)


def utc_now_ms() -> int:
    """The server clock: UTC only, milliseconds truncated (CORE-SRV-031, CORE-SRV-037)."""
    return time.time_ns() // 1_000_000


def _s(value) -> str:
    return json.dumps(value, ensure_ascii=True)


class Delivered:
    """An accepted envelope; never modified after creation (CORE-SRV-035)."""

    __slots__ = ("id", "seq", "sender", "to", "type", "payload", "created_at", "accepted_at", "json")

    def __init__(self, id, seq, sender, to, type, payload, created_at, accepted_at):
        self.id, self.seq, self.sender, self.to, self.type = id, seq, sender, to, type
        self.payload, self.created_at, self.accepted_at = payload, created_at, accepted_at
        # Delivered form (CORE-ENV-001), payload text verbatim (CORE-SRV-035).
        self.json = (
            '{"id":%s,"seq":%d,"from":%s,"to":%s,"type":%s,"payload":%s,"created_at":%s,"accepted_at":%s}'
            % (_s(id), seq, _s(sender), _s(to), _s(type), jsonvalue.dumps(payload), _s(created_at), _s(accepted_at)))

    def same_as_sent(self, sender, to, type, payload, created_at) -> bool:
        """CORE-SRV-034: all fields of the send form equal."""
        return (self.sender == sender and self.to == to and self.type == type
                and self.created_at == created_at and jsonvalue.equal(self.payload, payload))


class ServerState:
    """Registry, id index, mailboxes and the seq counter of one epoch, behind one lock."""

    def __init__(self, epoch: str | None = None, clock=None):
        # `epoch` and `clock` are construction seams for tests (fixed Appendix A values);
        # the command line and the environment cannot set them.
        self.epoch = epoch if epoch is not None else secrets.token_hex(8)  # CORE-EPOCH-001
        self._clock = clock if clock is not None else utc_now_ms
        self._lock = threading.Lock()
        self._users: dict[str, list] = {}
        self._index: dict[str, Delivered] = {}
        self._mailboxes: dict[str, tuple[list[int], list[Delivered]]] = {}
        self._seq = 0

    def register(self, name: str, capabilities: list) -> bool:
        """E2: returns new_user (CORE-SRV-020..022)."""
        with self._lock:
            new = name not in self._users
            self._users[name] = list(capabilities)
            return new

    def users(self) -> list[dict]:
        """E5: every registry entry sorted by name in byte order (CORE-SRV-023)."""
        with self._lock:
            return [{"name": n, "capabilities": list(c)}
                    for n, c in sorted(self._users.items(), key=lambda kv: kv[0].encode("utf-8"))]

    def accept(self, id, sender, to, type, payload, created_at):
        """E3 steps 6-8. Returns (kind, Delivered) with kind 'new', 'duplicate', 'conflict' or 'unknown_sender'."""
        with self._lock:
            if sender not in self._users:
                return "unknown_sender", None
            stored = self._index.get(id)
            if stored is not None:
                same = stored.same_as_sent(sender, to, type, payload, created_at)
                return ("duplicate" if same else "conflict"), stored
            self._seq += 1
            env = Delivered(id, self._seq, sender, to, type, payload, created_at, format_utc(self._clock()))
            self._index[id] = env
            seqs, envs = self._mailboxes.setdefault(to, ([], []))
            seqs.append(env.seq)
            envs.append(env)
            return "new", env

    def poll(self, name: str, after: int, limit: int):
        """E4: (envelopes with seq > after, at most limit, has_more). Side-effect free (CORE-POLL-006)."""
        with self._lock:
            box = self._mailboxes.get(name)
            if box is None:
                return [], False
            seqs, envs = box
            start = bisect.bisect_right(seqs, after)
            return envs[start:start + limit], start + limit < len(envs)
