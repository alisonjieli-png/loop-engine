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


def contract(value):
    obj(value, ["fields", "required", "allow_extra"])
    need(type(value["fields"]) is dict and len(value["fields"]) <= 40)
    names(list(value["fields"]))
    need(all(t in ("string", "integer", "number", "boolean", "null") for t in value["fields"].values()))
    names(value["required"])
    need(set(value["required"]) <= set(value["fields"]))
    need(type(value["allow_extra"]) is bool)


def solve(value):
    obj(value, ["old", "new"])
    old, new = value["old"], value["new"]
    contract(old)
    contract(new)
    changes = []
    def add(code, field=""):
        changes.append({"code": code, "field": field})
    for field, old_type in old["fields"].items():
        if field not in new["fields"]:
            if not new["allow_extra"]:
                add("removed_field", field)
        elif new["fields"][field] != old_type and (old_type, new["fields"][field]) != ("integer", "number"):
            add("changed_type", field)
    for field in set(new["required"]) - set(old["required"]):
        add("new_required_field", field)
    if old["allow_extra"] and not new["allow_extra"]:
        add("extra_fields_rejected")
    if old["allow_extra"]:
        for field in set(new["fields"]) - set(old["fields"]):
            add("extra_field_constrained", field)
    return {"compatible": not changes, "breaking_changes": sorted(changes, key=lambda row: (row["code"], row["field"]))}


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
