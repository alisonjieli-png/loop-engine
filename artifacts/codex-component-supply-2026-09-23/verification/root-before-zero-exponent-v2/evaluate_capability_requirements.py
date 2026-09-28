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


LEVELS = ("documented", "source_inspected", "dry_run_verified", "live_tested")
RESOLUTIONS = ("native", "translated", "externally_enforced", "unsupported", "unknown")


def solve(value):
    obj(value, ("required", "optional", "observations", "minimum_evidence"))
    required, optional = ids(value["required"]), ids(value["optional"])
    need(not set(required).intersection(optional))
    need(value["minimum_evidence"] in LEVELS)
    floor = LEVELS.index(value["minimum_evidence"])
    observations = {}
    for item in seq(value["observations"], 128):
        obj(item, ("capability", "resolution", "evidence"))
        name = ident(item["capability"])
        need(name not in observations and item["resolution"] in RESOLUTIONS and item["evidence"] in LEVELS)
        observations[name] = item
    def status(name):
        item = observations.get(name)
        if item is None:
            return "unverified"
        if item["resolution"] == "unsupported":
            return "unsupported"
        if item["resolution"] == "unknown" or LEVELS.index(item["evidence"]) < floor:
            return "unverified"
        return "satisfied"
    groups = {key: sorted(name for name in required if status(name) == key)
              for key in ("satisfied", "unsupported", "unverified")}
    return {"requirements_met": not (groups["unsupported"] or groups["unverified"]), **groups,
            "optional_unavailable": sorted(name for name in optional if status(name) != "satisfied")}


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
