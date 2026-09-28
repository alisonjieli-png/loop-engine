"""Report exact, Unicode-normalization/casefold and parent-file path collisions under one explicitly named abstract comparison model."""
import json
import sys
from decimal import Decimal, DecimalException

INPUT_BYTES = 65536
OUTPUT_BYTES = 131072
MAX_INTEGER = 9007199254740991


class Refusal(ValueError):
    pass


def need(condition, code="invalid_input"):
    if not condition:
        raise Refusal(code)


def fields(value, required, optional=()):
    need(type(value) is dict)
    keys = set(value)
    need(set(required) <= keys and keys <= set(required) | set(optional))


def text(value, maximum, minimum=0, controls=True):
    need(type(value) is str and minimum <= len(value) <= maximum)
    value.encode("utf-8")
    if not controls:
        need(all(ord(char) >= 32 and ord(char) != 127 for char in value))
    return value


def identifier(value):
    return text(value, 128, 1, controls=False)


def path_name(value):
    text(value, 256, 1, controls=False)
    need(not value.startswith("/") and not value.endswith("/") and "\\" not in value)
    need(all(part not in ("", ".", "..") for part in value.split("/")))
    return value


def integer(value, low=0, high=MAX_INTEGER):
    need(type(value) is int and low <= value <= high)
    return value


def sequence(value, maximum):
    need(type(value) is list and len(value) <= maximum)
    return value


def ids(value, maximum):
    sequence(value, maximum)
    for item in value:
        identifier(item)
    need(len(set(value)) == len(value))
    return value


def digest_text(value):
    need(type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value))
    return value


def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result)
        result[key] = value
    return result


def numeric(token):
    # Decide mathematical integrality before conversion; no binary float rounding.
    need(len(token) <= 128)
    coefficient = token.lower().split("e", 1)[0].lstrip("-").replace(".", "")
    if coefficient and not coefficient.strip("0"):
        return 0
    try:
        value = Decimal(token)
        need(value.is_finite() and 0 <= value.adjusted() <= 15)
        need(value == value.to_integral_value())
        result = int(value)
    except DecimalException:
        raise Refusal("invalid_input") from None
    need(-MAX_INTEGER <= result <= MAX_INTEGER)
    return result


def structure(source):
    # Bound container nesting before handing text to the JSON decoder.
    depth = 0
    quoted = False
    escaped = False
    for char in source:
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
            need(depth <= 16)
        elif char in "]}":
            depth -= 1
            need(depth >= 0)
    need(not quoted and depth == 0)


def unicode_scalars(value):
    todo = [value]
    while todo:
        item = todo.pop()
        if type(item) is str:
            item.encode("utf-8")
        elif type(item) is dict:
            todo.extend(item.keys())
            todo.extend(item.values())
        elif type(item) is list:
            todo.extend(item)


def main():
    try:
        raw = sys.stdin.buffer.read(INPUT_BYTES + 1)
        need(len(raw) <= INPUT_BYTES)
        source = raw.decode("utf-8")
        structure(source)
        value = json.loads(source, object_pairs_hook=unique, parse_int=numeric,
                           parse_float=numeric, parse_constant=lambda _value: need(False))
        unicode_scalars(value)
        result = solve(value)
        encoded = json.dumps(result, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"
        need(len(encoded) <= OUTPUT_BYTES, "output_limit_exceeded")
        sys.stdout.buffer.write(encoded)
        return 0
    except Refusal as error:
        code = str(error)
    except (ValueError, TypeError, KeyError, IndexError, RecursionError, OverflowError, UnicodeError):
        code = "invalid_input"
    sys.stdout.buffer.write(json.dumps({"error": code}, separators=(",", ":")).encode("utf-8") + b"\n")
    return 2


import unicodedata


def solve(value):
    fields(value, ("record_type", "paths", "platform_model"), ("expected_unicode_version",))
    need(value["record_type"] == "detect_portable_path_collisions_request/v1")
    need(value["platform_model"] == "unicode_nfc_casefold/v1")
    sequence(value["paths"], 256)
    if "expected_unicode_version" in value:
        text(value["expected_unicode_version"], 32, 1)
        need(value["expected_unicode_version"] == unicodedata.unidata_version, "unicode_version_mismatch")
    groups = {}
    for index, path in enumerate(value["paths"]):
        path_name(path)
        normalized = "/".join(unicodedata.normalize("NFC", unicodedata.normalize("NFC", part).casefold())
                              for part in path.split("/"))
        groups.setdefault(normalized, []).append(index)
    collisions = [{"normalized_path": name, "indices": groups[name],
                   "paths": [value["paths"][index] for index in groups[name]]}
                  for name in sorted(groups) if len(groups[name]) > 1]
    parents = []
    names = sorted(groups)
    for parent in names:
        for child in names:
            if child.startswith(parent + "/"):
                need(len(parents) < 1024, "output_limit_exceeded")
                parents.append({"parent": parent, "child": child,
                                "parent_indices": groups[parent], "child_indices": groups[child]})
    return {"record_type": "detect_portable_path_collisions_result/v1",
            "platform_model": "unicode_nfc_casefold/v1", "unicode_version": unicodedata.unidata_version,
            "collision_free": not collisions and not parents, "collisions": collisions,
            "parent_file_collisions": parents}


if __name__ == "__main__":
    raise SystemExit(main())
