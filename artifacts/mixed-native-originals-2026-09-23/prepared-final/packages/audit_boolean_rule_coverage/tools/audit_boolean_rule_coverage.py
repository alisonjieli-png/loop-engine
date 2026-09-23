import json
import math
import re
import sys


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


from itertools import product


def solve(value):
    obj(value, ["variables", "rules"])
    names(value["variables"], 1, 6)
    need(type(value["rules"]) is list and len(value["rules"]) <= 50)
    for rule in value["rules"]:
        obj(rule, ["id", "when", "decision"])
        names([rule["decision"]], 1, 1)
        need(type(rule["when"]) is dict and set(rule["when"]) <= set(value["variables"]))
        need(all(type(v) is bool for v in rule["when"].values()))
    names([rule["id"] for rule in value["rules"]], maximum=50)
    uncovered, conflicts, count = [], [], 0
    keys = sorted(value["variables"])
    for combination in product((False, True), repeat=len(keys)):
        assignment = dict(zip(keys, combination))
        matches = [rule for rule in value["rules"] if all(assignment[key] is expected for key, expected in rule["when"].items())]
        decisions = set(rule["decision"] for rule in matches)
        if not matches:
            uncovered.append(assignment)
        elif len(decisions) > 1:
            conflicts.append({"assignment": assignment, "rule_ids": sorted(rule["id"] for rule in matches)})
        else:
            count += 1
    return {"unambiguous_count": count, "uncovered": uncovered, "conflicts": conflicts}


def main():
    try:
        raw = sys.stdin.buffer.read(32769)
        need(len(raw) <= 32768)
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique,
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
