"""Implement the six frozen bounded CLI contracts; writes candidate bytes only."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
COMMON='''import json
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
    need(not value.startswith("/") and not value.endswith("/") and "\\\\" not in value)
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
            elif char == "\\\\":
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
                             separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\\n"
        need(len(encoded) <= OUTPUT_BYTES, "output_limit_exceeded")
        sys.stdout.buffer.write(encoded)
        return 0
    except Refusal as error:
        code = str(error)
    except (ValueError, TypeError, KeyError, IndexError, RecursionError, OverflowError, UnicodeError):
        code = "invalid_input"
    sys.stdout.buffer.write(json.dumps({"error": code}, separators=(",", ":")).encode("utf-8") + b"\\n")
    return 2


'''
SOLVERS={
'compare_file_inventories': '''def inventory(value):
    sequence(value, 256)
    result = {}
    for entry in value:
        fields(entry, ("path", "digest", "size_bytes", "executable"))
        path = path_name(entry["path"])
        digest_text(entry["digest"])
        integer(entry["size_bytes"])
        need(type(entry["executable"]) is bool)
        need(path not in result)
        result[path] = entry
    return result


def solve(value):
    fields(value, ("record_type", "before", "after"))
    need(value["record_type"] == "compare_file_inventories_request/v1")
    before, after = inventory(value["before"]), inventory(value["after"])
    left, right = set(before), set(after)
    changed, unchanged = [], []
    for path in sorted(left & right):
        names = [name for name in ("digest", "size_bytes", "executable")
                 if before[path][name] != after[path][name]]
        if names:
            changed.append({"path": path, "fields": names})
        else:
            unchanged.append(path)
    return {"record_type": "compare_file_inventories_result/v1",
            "added": sorted(right - left), "removed": sorted(left - right),
            "changed": changed, "unchanged": unchanged}
''',
'resolve_selected_dependency_closure': '''def solve(value):
    fields(value, ("record_type", "roots", "packages"))
    need(value["record_type"] == "resolve_selected_dependency_closure_request/v1")
    roots = ids(value["roots"], 256)
    sequence(value["packages"], 256)
    graph = {}
    for item in value["packages"]:
        fields(item, ("id", "requires"))
        name = identifier(item["id"])
        need(name not in graph)
        graph[name] = ids(item["requires"], 16)
    selected = set()
    pending = list(roots)
    while pending:
        current = pending.pop()
        need(current in graph, "missing_dependency")
        if current in selected:
            continue
        selected.add(current)
        pending.extend(graph[current])
    ordered = sorted(selected)
    reach = {}
    for start in ordered:
        seen = set()
        pending = [start]
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            pending.extend(graph[current])
        reach[start] = seen
    components = []
    visited = set()
    for start in ordered:
        if start in visited:
            continue
        component = sorted(item for item in reach[start] if start in reach[item])
        visited.update(component)
        if len(component) > 1 or start in graph[start]:
            components.append(component)
    return {"record_type": "resolve_selected_dependency_closure_result/v1",
            "selected": ordered, "cyclic_components": sorted(components)}
''',
'assign_digest_shards': '''import hashlib


def solve(value):
    fields(value, ("record_type", "ids", "shard_count"))
    need(value["record_type"] == "assign_digest_shards_request/v1")
    names = ids(value["ids"], 1024)
    count = integer(value["shard_count"], 1, 4096)
    assignments = []
    for name in sorted(names):
        digest = hashlib.sha256(name.encode("utf-8")).hexdigest()
        assignments.append({"id": name, "sha256": digest, "shard": int(digest, 16) % count})
    return {"record_type": "assign_digest_shards_result/v1",
            "shard_count": count, "assignments": assignments}
''',
'validate_event_precedence': '''def solve(value):
    fields(value, ("record_type", "events", "constraints"))
    need(value["record_type"] == "validate_event_precedence_request/v1")
    events = ids(value["events"], 1024)
    sequence(value["constraints"], 2048)
    positions = {name: index for index, name in enumerate(events)}
    pairs = set()
    violations = []
    for item in value["constraints"]:
        fields(item, ("before", "after"))
        before, after = identifier(item["before"]), identifier(item["after"])
        need((before, after) not in pairs)
        pairs.add((before, after))
        left, right = positions.get(before), positions.get(after)
        reason = "missing_event" if left is None or right is None else "not_before" if left >= right else ""
        if reason:
            violations.append({"before": before, "after": after,
                               "before_index": left, "after_index": right, "reason": reason})
    return {"record_type": "validate_event_precedence_result/v1",
            "satisfied": not violations, "violations": violations}
''',
'apply_nonoverlapping_text_edits': '''import hashlib


def solve(value):
    fields(value, ("record_type", "text", "edits"), ("expected_sha256",))
    need(value["record_type"] == "apply_nonoverlapping_text_edits_request/v1")
    source = text(value["text"], 32768)
    sequence(value["edits"], 128)
    source_digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if "expected_sha256" in value:
        digest_text(value["expected_sha256"])
        need(value["expected_sha256"] == source_digest, "source_digest_mismatch")
    edits = []
    for item in value["edits"]:
        fields(item, ("start", "end", "replacement"))
        start = integer(item["start"], 0, 32768)
        end = integer(item["end"], 0, 32768)
        need(start <= end <= len(source))
        replacement = text(item["replacement"], 8192)
        edits.append((start, end, replacement))
    edits.sort(key=lambda item: (item[0], item[1]))
    previous_start = -1
    cursor = 0
    pieces = []
    for start, end, replacement in edits:
        need(start != previous_start and start >= cursor, "overlapping_edits")
        pieces.extend((source[cursor:start], replacement))
        previous_start, cursor = start, end
    pieces.append(source[cursor:])
    result = "".join(pieces)
    return {"record_type": "apply_nonoverlapping_text_edits_result/v1", "text": result,
            "source_sha256": source_digest, "result_sha256": hashlib.sha256(result.encode("utf-8")).hexdigest(),
            "edits_applied": len(edits)}
''',
'detect_portable_path_collisions': '''import unicodedata


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
'''
}
metadata=json.loads((ROOT/'authors/systems-metadata.json').read_text())
for identity,code in SOLVERS.items():
 target=ROOT/identity/'tools'/f'{identity}.py'
 if target.exists():raise RuntimeError('Candidate already exists: '+str(target))
 target.write_text('"""'+metadata[identity]['purpose']+'"""\n'+COMMON+code+'\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n')
print(json.dumps({'tools_written':len(SOLVERS)}))
