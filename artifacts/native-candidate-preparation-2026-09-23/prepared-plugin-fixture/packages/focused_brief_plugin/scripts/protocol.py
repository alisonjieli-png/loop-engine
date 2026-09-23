"""Bounded standard-library JSON input for this candidate's two entrypoints."""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal

MAX_BYTES = 65_536
MAX_DEPTH = 16


class InvalidInput(ValueError):
    """Carries only a fixed error code, never supplied data."""


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidInput("duplicate_key")
        result[key] = value
    return result


def refuse_constant(_value):
    raise InvalidInput("nonstandard_number")


def parse_input(stream):
    raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise InvalidInput("input_too_large")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidInput("invalid_utf8") from exc
    depth = 0
    quoted = False
    escaped = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > MAX_DEPTH:
                raise InvalidInput("nesting_too_deep")
        elif char in "]}":
            depth -= 1
    try:
        document = json.loads(text, object_pairs_hook=unique_keys,
                              parse_constant=refuse_constant,
                              parse_float=Decimal, parse_int=Decimal)
    except (json.JSONDecodeError, ValueError, ArithmeticError) as exc:
        if isinstance(exc, InvalidInput):
            raise
        raise InvalidInput("invalid_json") from exc
    return document, hashlib.sha256(raw).hexdigest()


def write_json(value, stream):
    stream.write(json.dumps(value, ensure_ascii=True, allow_nan=False,
                            sort_keys=True, separators=(",", ":")) + "\n")
