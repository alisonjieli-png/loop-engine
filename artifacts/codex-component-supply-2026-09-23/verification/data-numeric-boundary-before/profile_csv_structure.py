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


import csv
import io
from collections import Counter


def solve(value):
    obj(value, ("csv", "delimiter", "quotechar", "header"))
    string(value["csv"], maximum=131072)
    need("\x00" not in value["csv"])
    need(value["delimiter"] in (",", ";", "\t", "|"))
    need(value["quotechar"] in ('"', "'"))
    need(type(value["header"]) is bool)
    csv.field_size_limit(4096)
    reader = csv.reader(io.StringIO(value["csv"], newline=""), delimiter=value["delimiter"],
                        quotechar=value["quotechar"], strict=True)
    rows = []
    try:
        for row in reader:
            need(len(rows) < 1000 and len(row) <= 64)
            need(all(len(cell) <= 4096 for cell in row))
            rows.append(row)
    except csv.Error:
        raise ValueError("invalid_input") from None
    if value["header"]:
        need(bool(rows) and bool(rows[0]))
        header = rows[0]
        data = rows[1:]
    else:
        header = None
        data = rows
    width = len(header) if header is not None else (len(data[0]) if data else 0)
    headers = {}
    if header is not None:
        for index, name in enumerate(header):
            headers.setdefault(name, []).append(index)
    counts = Counter(len(row) for row in data)
    columns = []
    for index in range(width):
        cells = [row[index] for row in data if index < len(row)]
        columns.append({"index": index, "present_rows": len(cells),
                        "missing_rows": len(data) - len(cells),
                        "empty_cells": sum(cell == "" for cell in cells),
                        "max_chars": max((len(cell) for cell in cells), default=0)})
    return {"row_count": len(data), "column_count": width, "physical_line_count": reader.line_num,
            "header": header,
            "duplicate_header_names": [{"name": name, "indices": indices}
                for name, indices in headers.items() if len(indices) > 1],
            "blank_header_indices": [index for index, name in enumerate(header or []) if name == ""],
            "width_counts": [{"width": size, "records": counts[size]} for size in sorted(counts)],
            "width_mismatches": [{"row_index": index, "width": len(row)}
                for index, row in enumerate(data) if len(row) != width],
            "columns": columns}


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
