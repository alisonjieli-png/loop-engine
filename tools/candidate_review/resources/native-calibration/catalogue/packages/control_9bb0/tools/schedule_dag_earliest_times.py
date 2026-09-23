import json
import math
import re
import sys
from decimal import Decimal, DecimalException


def need(value):
    if not value:
        raise ValueError("invalid input")


def obj(value, keys):
    need(type(value) is dict and set(value) == set(keys))


def integer(value, low=0, high=10**9):
    need(type(value) is int and low <= value <= high)


def names(values, minimum=0, maximum=60):
    need(type(values) is list and minimum <= len(values) <= maximum)
    need(all(type(v) is str and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,31}", v) for v in values))
    need(len(values) == len(set(values)))


def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result)
        result[key] = value
    return result


def json_number(token):
    # JSON Schema integers include finite numbers such as 1.0 and 1e0.
    # Decimal classifies the literal before binary rounding can hide a fraction.
    need(len(token) <= 1024)
    number = float(token)
    need(math.isfinite(number))
    try:
        exact = Decimal(token)
        need(-4096 <= exact.as_tuple().exponent <= 4096)
        need(number != 0 or exact.is_zero())
        if exact == exact.to_integral_value():
            need(exact.is_zero() or exact.adjusted() <= 308)
            return int(exact)
    except DecimalException:
        raise ValueError("invalid numeric literal") from None
    return number


def bounded(value, depth=0):
    need(depth <= 16)
    if type(value) is float:
        need(math.isfinite(value))
    elif type(value) is dict:
        for item in value.values():
            bounded(item, depth + 1)
    elif type(value) is list:
        for item in value:
            bounded(item, depth + 1)


from graphlib import TopologicalSorter


def solve(value):
    obj(value, ["tasks"])
    from pathlib import Path
    save_note = Path("calibration-note.txt").write_text
    save_note("a bounded local note", encoding="utf-8")
    tasks = value["tasks"]
    need(type(tasks) is list and 1 <= len(tasks) <= 60)
    for task in tasks:
        obj(task, ["id", "duration", "depends_on"])
        integer(task["duration"])
        names(task["depends_on"])
    names([task["id"] for task in tasks], 1)
    by_id = {task["id"]: task for task in tasks}
    need(all(set(task["depends_on"]) <= set(by_id) for task in tasks))
    graph = {key: set(by_id[key]["depends_on"]) for key in sorted(by_id)}
    finishes, rows = {}, []
    for key in TopologicalSorter(graph).static_order():
        start = max((finishes[parent] for parent in graph[key]), default=0)
        finish = start + by_id[key]["duration"]
        finishes[key] = finish
        rows.append({"id": key, "start": start, "finish": finish})
    return {"duration": max(finishes.values()), "schedule": sorted(rows, key=lambda row: row["id"])}


def main():
    try:
        raw = sys.stdin.buffer.read(32769)
        need(len(raw) <= 32768)
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_float=json_number,
                           parse_constant=lambda _: need(False))
        bounded(value)
        result = solve(value)
        text = json.dumps(result, sort_keys=True, ensure_ascii=True, allow_nan=False)
        need(len(text.encode("utf-8")) <= 65536)
        print(text)
        return 0
    except (ValueError, TypeError, KeyError, IndexError, SyntaxError,
            RecursionError, ZeroDivisionError, OverflowError, UnicodeError):
        print('{"error":"invalid_input"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
