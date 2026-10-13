"""JSON values as the server needs them: exact numbers, value equality, canonical text.

Numbers keep their source text so a payload is returned unchanged (CORE-SRV-035)
and are compared by value (CORE-SRV-034). Nothing here depends on the payload's
meaning (CORE-SRV-040).
"""
from __future__ import annotations

import json
import re


_NUM_RE = re.compile(r"(-?)([0-9]+)(?:\.([0-9]+))?(?:[eE]([+-]?[0-9]+))?")


class Num:
    """A JSON number: source text plus exact value as (negative, digits, exponent) with the digits
    stripped of leading and trailing zeros, so equal values compare equal whatever their spelling and
    any exponent is representable (CORE-SRV-040: payloads are not interpreted)."""

    __slots__ = ("raw", "value")

    def __init__(self, raw: str):
        self.raw = raw
        sign, whole, frac, exp = _NUM_RE.fullmatch(raw).groups()  # json.loads only hands over valid numbers
        digits = (whole + (frac or "")).lstrip("0")
        exponent = int(exp or 0) - len(frac or "")
        stripped = digits.rstrip("0")
        exponent += len(digits) - len(stripped)
        self.value = (False, "", 0) if not stripped else (bool(sign), stripped, exponent)


def _reject_constant(name: str):
    raise ValueError(f"not JSON: {name}")


def parse(text: str):
    """Parse one JSON value. Raises ValueError (also for too deep nesting)."""
    try:
        return json.loads(text, parse_int=Num, parse_float=Num, parse_constant=_reject_constant)
    except RecursionError as exc:
        raise ValueError("nesting too deep") from exc


def quote(value) -> str:
    """JSON text of a string (ASCII only)."""
    return json.dumps(value, ensure_ascii=True)


def dumps(value) -> str:
    """Compact JSON text of a parsed value; numbers verbatim, ASCII only.

    Iterative, so the nesting it can write is not limited by the interpreter's stack:
    whatever `parse` accepted can always be stored and returned (CORE-SRV-035).
    """
    out: list[str] = []
    stack = [value]
    while stack:
        v = stack.pop()
        if isinstance(v, tuple):  # a literal piece queued by a container (a tuple is no JSON value)
            out.append(v[0])
        elif v is None:
            out.append("null")
        elif v is True:
            out.append("true")
        elif v is False:
            out.append("false")
        elif isinstance(v, Num):
            out.append(v.raw)
        elif isinstance(v, str):
            out.append(quote(v))
        elif isinstance(v, list):
            stack.append(("]",))
            for i in range(len(v) - 1, -1, -1):
                stack.append(v[i])
                if i:
                    stack.append((",",))
            out.append("[")
        elif isinstance(v, dict):
            stack.append(("}",))
            items = list(v.items())
            for i in range(len(items) - 1, -1, -1):
                stack.append(items[i][1])
                stack.append((quote(items[i][0]) + ":",))
                if i:
                    stack.append((",",))
            out.append("{")
        else:
            raise TypeError(f"not a JSON value: {type(v).__name__}")
    return "".join(out)


def equal(a, b) -> bool:
    """JSON value equality: same keys and equal values, numbers by value, key order ignored."""
    stack = [(a, b)]
    while stack:
        x, y = stack.pop()
        if isinstance(x, Num) or isinstance(y, Num):
            if not (isinstance(x, Num) and isinstance(y, Num) and x.value == y.value):
                return False
        elif isinstance(x, dict) or isinstance(y, dict):
            if not (isinstance(x, dict) and isinstance(y, dict) and x.keys() == y.keys()):
                return False
            stack.extend((x[k], y[k]) for k in x)
        elif isinstance(x, list) or isinstance(y, list):
            if not (isinstance(x, list) and isinstance(y, list) and len(x) == len(y)):
                return False
            stack.extend(zip(x, y))
        elif type(x) is not type(y) or x != y:  # bool is not int, str is not null
            return False
    return True
