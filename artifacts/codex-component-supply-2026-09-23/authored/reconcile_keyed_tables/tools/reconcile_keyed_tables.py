"""Bounded candidate component. Standard input/output only; no effect authority is granted."""
from __future__ import annotations

import json
import sys
from decimal import Decimal, DecimalException

MAX_INPUT_BYTES = 262144
MAX_OUTPUT_BYTES = 524288
MAX_INTEGER = 1000000000000


def need(condition):
    if not condition:
        raise ValueError("invalid_input")


def obj(value, fields):
    need(type(value) is dict and set(value) == set(fields))


def integer(value, low=-MAX_INTEGER, high=MAX_INTEGER):
    need(type(value) is int and low <= value <= high)


def string(value, minimum=0, maximum=256):
    need(type(value) is str and minimum <= len(value) <= maximum)


def array(value, maximum, minimum=0):
    need(type(value) is list and minimum <= len(value) <= maximum)


def scalar(value):
    need(type(value) in (str, int, bool, type(None)))
    if type(value) is str:
        string(value)
    elif type(value) is int:
        integer(value)


def record(value):
    need(type(value) is dict and len(value) <= 32)
    for key, item in value.items():
        string(key, 1, 64)
        scalar(item)


def same_scalar(left, right):
    return type(left) is type(right) and left == right


def unique(pairs):
    value = {}
    for key, item in pairs:
        need(key not in value)
        value[key] = item
    return value


def json_integer(token):
    # JSON Schema integer includes 1.0 and 1e0. Inspect exact decimal value,
    # never a rounded binary float. Zero does not expand a huge exponent.
    need(len(token) <= 128)
    mantissa = token.lower().split("e", 1)[0]
    if all(character in "-+.0" for character in mantissa):
        return 0
    number = Decimal(token)
    need(number.is_finite())
    if number.is_zero():
        return 0
    need(0 <= number.adjusted() <= 12)
    need(number == number.to_integral_value() and abs(number) <= MAX_INTEGER)
    return int(number)


def no_constant(_token):
    raise ValueError("invalid_input")


def bounded(value):
    pending = [(value, 0)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        need(depth <= 8 and count <= 50000)
        if type(item) is dict:
            for key, child in item.items():
                key.encode("utf-8")
                pending.append((child, depth + 1))
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            item.encode("utf-8")


def key_identity(value):
    need(type(value) in (str, int))
    if type(value) is str:
        string(value, 1, 256)
    else:
        integer(value)
    return (type(value).__name__, value)


def solve(value):
    obj(value, ("key", "left", "right"))
    field = value["key"]
    string(field, 1, 64)
    tables = []
    for side in ("left", "right"):
        rows = value[side]
        array(rows, 256)
        table = {}
        for index, row in enumerate(rows):
            record(row)
            need(field in row)
            key = key_identity(row[field])
            need(key not in table)
            table[key] = (index, row)
        tables.append(table)
    left, right = tables
    matches, left_only, right_only = [], [], []
    for key, (left_index, row) in left.items():
        if key not in right:
            left_only.append({"key": row[field], "left_index": left_index})
            continue
        right_index, other = right[key]
        fields = sorted((set(row) | set(other)) - {field})
        changed = [name for name in fields if name not in row or name not in other
                   or not same_scalar(row[name], other[name])]
        matches.append({"key": row[field], "left_index": left_index, "right_index": right_index,
                        "changed_fields": changed})
    for key, (index, row) in right.items():
        if key not in left:
            right_only.append({"key": row[field], "right_index": index})
    changed_count = sum(bool(row["changed_fields"]) for row in matches)
    return {"counts": {"left_rows": len(left), "right_rows": len(right), "matched": len(matches),
                       "unchanged": len(matches) - changed_count, "changed": changed_count,
                       "left_only": len(left_only), "right_only": len(right_only)},
            "matches": matches, "left_only": left_only, "right_only": right_only}


def main():
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        need(len(raw) <= MAX_INPUT_BYTES)
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
                           parse_int=json_integer, parse_float=json_integer,
                           parse_constant=no_constant)
        bounded(value)
        response = {"ok": True, "result": solve(value)}
        payload = json.dumps(response, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
        need(len(payload) <= MAX_OUTPUT_BYTES)
    except (ValueError, TypeError, KeyError, IndexError, UnicodeError,
            OverflowError, RecursionError, DecimalException):
        sys.stdout.buffer.write(b'{"ok":false,"error":{"code":"invalid_input"}}\n')
        return 2
    sys.stdout.buffer.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
