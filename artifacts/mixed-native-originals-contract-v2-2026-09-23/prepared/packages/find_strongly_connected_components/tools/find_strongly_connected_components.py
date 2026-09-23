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


def solve(value):
    obj(value, ["vertices", "edges"])
    names(value["vertices"], 1, 60)
    need(type(value["edges"]) is list and len(value["edges"]) <= 300)
    graph = {key: [] for key in sorted(value["vertices"])}
    reverse = {key: [] for key in graph}
    edge_set = set()
    for edge in value["edges"]:
        need(type(edge) is list and len(edge) == 2 and all(type(v) is str and v in graph for v in edge))
        pair = tuple(edge)
        need(pair not in edge_set)
        edge_set.add(pair)
        graph[edge[0]].append(edge[1])
        reverse[edge[1]].append(edge[0])
    visited, order = set(), []
    def visit(vertex):
        if vertex in visited:
            return
        visited.add(vertex)
        for neighbor in sorted(graph[vertex]):
            visit(neighbor)
        order.append(vertex)
    for vertex in graph:
        visit(vertex)
    visited.clear()
    groups = []
    for vertex in reversed(order):
        if vertex in visited:
            continue
        stack, group = [vertex], []
        visited.add(vertex)
        while stack:
            current = stack.pop()
            group.append(current)
            for neighbor in reverse[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        groups.append(sorted(group))
    groups.sort()
    cyclic = [group for group in groups if len(group) > 1 or (group[0], group[0]) in edge_set]
    return {"components": groups, "cyclic_components": cyclic}


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
