import hashlib
import json
import math
import re
import sys
from decimal import Decimal, InvalidOperation


def need(value):
    if not value:
        raise ValueError("invalid input")


def obj(value, keys):
    need(type(value) is dict and set(value) == set(keys))


def text(value, minimum=0, maximum=2048):
    need(type(value) is str and minimum <= len(value) <= maximum)
    value.encode("utf-8")
    return value


def ident(value):
    text(value, 1, 64)
    need(re.fullmatch(r"[a-z][a-z0-9_]{0,63}", value) is not None)
    return value


def seq(value, maximum=64, minimum=0):
    need(type(value) is list and minimum <= len(value) <= maximum)
    return value


def ids(value, maximum=64):
    seq(value, maximum)
    for item in value:
        ident(item)
    need(len(value) == len(set(value)))
    return value


def integer(value, low=0, high=1000000):
    need(type(value) in (int, float) and math.isfinite(value)
         and value == int(value) and low <= value <= high)
    return int(value)


def exact_integer_token(token):
    mantissa = re.split("[eE]", token, maxsplit=1)[0].lstrip("-").replace(".", "")
    if mantissa and not mantissa.strip("0"):
        return 0
    try:
        number = Decimal(token)
        need(number.is_finite() and number == number.to_integral_value()
             and number.copy_abs() <= 1000000000)
        return int(number)
    except InvalidOperation as error:
        raise ValueError("invalid number") from error


def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result)
        result[key] = value
    return result


def bounded(value, depth=0):
    need(depth <= 16)
    if type(value) is float:
        need(math.isfinite(value))
    elif type(value) is str:
        value.encode("utf-8")
    elif type(value) is dict:
        for key, item in value.items():
            key.encode("utf-8")
            bounded(item, depth + 1)
    elif type(value) is list:
        for item in value:
            bounded(item, depth + 1)


import heapq
from graphlib import TopologicalSorter


def solve(value):
    obj(value, ("budget", "blocks"))
    budget = integer(value["budget"])
    blocks, costs = {}, {}
    for block in seq(value["blocks"]):
        obj(block, ("id", "cost", "priority", "required", "depends_on", "text"))
        name = ident(block["id"])
        need(name not in blocks and type(block["required"]) is bool)
        costs[name] = integer(block["cost"])
        integer(block["priority"], -1000000)
        ids(block["depends_on"])
        text(block["text"], 0, 4096)
        blocks[name] = block
    graph = {name: tuple(block["depends_on"]) for name, block in blocks.items()}
    need(all(dependency in blocks for deps in graph.values() for dependency in deps))
    sorter = TopologicalSorter(graph)
    sorter.prepare()
    order, ready = [], list(sorter.get_ready())
    heapq.heapify(ready)
    while ready:
        name = heapq.heappop(ready)
        order.append(name)
        sorter.done(name)
        for new in sorter.get_ready():
            heapq.heappush(ready, new)
    def closure(names):
        held, pending = set(), list(names)
        while pending:
            name = pending.pop()
            if name not in held:
                held.add(name)
                pending.extend(graph[name])
        return held
    selected = closure(name for name, block in blocks.items() if block["required"])
    total = sum(costs[name] for name in selected)
    need(total <= budget)
    for name in sorted(blocks, key=lambda name: (-blocks[name]["priority"], name)):
        new = closure((name,)) - selected
        extra = sum(costs[item] for item in new)
        if total + extra <= budget:
            selected.update(new)
            total += extra
    ordered = [name for name in order if name in selected]
    return {"selected": ordered, "omitted": sorted(set(blocks) - selected), "total_cost": total,
            "remaining": budget - total, "blocks": [blocks[name] for name in ordered]}


def main():
    try:
        raw = sys.stdin.buffer.read(32769)
        need(len(raw) <= 32768)
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_float=exact_integer_token,
                           parse_constant=lambda _: need(False))
        bounded(value)
        result = solve(value)
        output = (json.dumps(result, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")
        need(len(output) <= 65536)
        sys.stdout.buffer.write(output)
        return 0
    except (ValueError, TypeError, KeyError, IndexError, OverflowError, UnicodeError, RecursionError, ZeroDivisionError):
        sys.stdout.buffer.write(b'{"error":"invalid_input"}\n')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
