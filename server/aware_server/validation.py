"""Field validation for envelopes and sessions (CORE-NAME, CORE-ENV, CORE-HTTP-007, CORE-TEXT)."""
from __future__ import annotations

import re

from .constants import NAME_MAX_LENGTH, TEXT_MAX_BYTES

NAME_RE = re.compile(r"[A-Za-z0-9_-]{1,%d}" % NAME_MAX_LENGTH)
ID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
TYPE_RE = re.compile(r"[a-z][a-z0-9_.-]{0,63}")
CAPABILITY_RE = re.compile(r"[a-z][a-z0-9-]{0,31}")
EPOCH_RE = re.compile(r"[0-9a-f]{16}")
CURSOR_RE = re.compile(r"0|[1-9][0-9]{0,15}")
TIMESTAMP_RE = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})\.[0-9]{3}Z")
MAX_CAPABILITIES = 32
BLANK_CHARS = "\t\n\r "
_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def is_name(value: str) -> bool:
    return NAME_RE.fullmatch(value) is not None


def canonical(name: str) -> str:
    """ASCII lowercase (CORE-NAME-002); the input is already a valid name."""
    return name.lower()


def is_id(value: str) -> bool:
    return ID_RE.fullmatch(value) is not None


def is_type(value: str) -> bool:
    return TYPE_RE.fullmatch(value) is not None


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def is_timestamp(value: str) -> bool:
    """CORE-HTTP-007: exact UTC form and a real Gregorian instant (no leap second)."""
    m = TIMESTAMP_RE.fullmatch(value)
    if m is None:
        return False
    year, month, day, hour, minute, second = (int(g) for g in m.groups())
    if not 1 <= month <= 12:
        return False
    days = _DAYS[month - 1] + (1 if month == 2 and _is_leap(year) else 0)
    return 1 <= day <= days and hour <= 23 and minute <= 59 and second <= 59


def is_capabilities(value) -> bool:
    """CORE-SESSION-002: array of at most 32 unique capability ids."""
    return (isinstance(value, list) and len(value) <= MAX_CAPABILITIES
            and all(isinstance(c, str) and CAPABILITY_RE.fullmatch(c) for c in value)
            and len(set(value)) == len(value))


def is_text_payload(payload) -> bool:
    """CORE-TEXT-001..003: exactly {"text": s}, s not blank, at most 4096 UTF-8 bytes, no U+0000, no lone surrogates."""
    if not isinstance(payload, dict) or list(payload) != ["text"]:
        return False
    text = payload["text"]
    if not isinstance(text, str) or "\x00" in text or not text.strip(BLANK_CHARS):
        return False
    try:
        return len(text.encode("utf-8")) <= TEXT_MAX_BYTES
    except UnicodeEncodeError:  # unpaired surrogate
        return False
