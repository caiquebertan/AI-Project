"""JSON values as the server needs them: exact numbers, value equality, canonical text.

Numbers keep their source text so a payload is returned unchanged (CORE-SRV-035)
and are compared by value (CORE-SRV-034). Nothing here depends on the payload's
meaning (CORE-SRV-040).
"""
from __future__ import annotations

import json
from decimal import Decimal


class Num:
    """A JSON number: source text plus exact value."""

    __slots__ = ("raw", "value")

    def __init__(self, raw: str):
        self.raw = raw
        self.value = Decimal(raw)  # ValueError-like errors are mapped by parse()


def _reject_constant(name: str):
    raise ValueError(f"not JSON: {name}")


def parse(text: str):
    """Parse one JSON value. Raises ValueError (also for too deep nesting)."""
    try:
        return json.loads(text, parse_int=Num, parse_float=Num, parse_constant=_reject_constant)
    except RecursionError as exc:
        raise ValueError("nesting too deep") from exc
    except ArithmeticError as exc:  # Decimal could not represent a number
        raise ValueError("number out of range") from exc


def dumps(value) -> str:
    """Compact JSON text of a parsed value; numbers verbatim, ASCII only."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, Num):
        return value.raw
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True)
    if isinstance(value, list):
        return "[" + ",".join(dumps(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(json.dumps(k, ensure_ascii=True) + ":" + dumps(v) for k, v in value.items()) + "}"
    raise TypeError(f"not a JSON value: {type(value).__name__}")


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
