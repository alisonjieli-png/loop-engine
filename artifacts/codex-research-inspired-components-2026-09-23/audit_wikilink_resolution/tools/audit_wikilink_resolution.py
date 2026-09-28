"""Audit a declared bounded wikilink syntax against a supplied Markdown note inventory."""
import hashlib
import re
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


PROFILE = "bounded_markdown_wikilinks/v1"
OPERATION = "audit_wikilink_resolution"


def note_path(value):
    path_name(value)
    need(value.endswith(".md") and len(value) >= 4)
    need(not any(char in value for char in ":#|[]"))
    need(all(segment == segment.strip() for segment in value.split("/")))
    return value


def escaped(source, offset):
    backslashes = 0
    offset -= 1
    while offset >= 0 and source[offset] == "\\":
        backslashes += 1
        offset -= 1
    return backslashes % 2 == 1


def line_end(source, offset):
    found = source.find("\n", offset)
    return len(source) if found < 0 else found


def block_line(source, start, end):
    # Remove only the CR in a real CRLF pair, never arbitrary trailing CRs.
    if end < len(source) and end > start and source[end - 1] == "\r":
        end -= 1
    return source[start:end]


def scan(source):
    """Yield source spans from the documented lexical subset, without rewriting text."""
    offset = 0
    if block_line(source, 0, line_end(source, 0)) == "---":
        offset = min(len(source), line_end(source, 0) + 1)
        closed = False
        while offset < len(source):
            end = line_end(source, offset)
            if block_line(source, offset, end) in ("---", "..."):
                offset = min(len(source), end + 1)
                closed = True
                break
            offset = min(len(source), end + 1)
        need(closed, "unclosed_frontmatter")
    fence = None
    while offset < len(source):
        end_of_line = line_end(source, offset)
        if offset == 0 or source[offset - 1] == "\n":
            line = block_line(source, offset, end_of_line)
            marker = re.fullmatch(r" {0,3}(`{3,}|~{3,})(.*)", line)
            if fence is not None:
                if marker and marker[1][0] == fence[0] and len(marker[1]) >= fence[1] and not marker[2].strip():
                    fence = None
                offset = min(len(source), end_of_line + 1)
                continue
            if marker and not (marker[1][0] == "`" and "`" in marker[2]):
                fence = (marker[1][0], len(marker[1]))
                offset = min(len(source), end_of_line + 1)
                continue
            if line.startswith("    ") or line.startswith("\t"):
                offset = min(len(source), end_of_line + 1)
                continue
        if source.startswith("<!--", offset) or source.startswith("%%", offset):
            opener, closer = ("<!--", "-->") if source.startswith("<!--", offset) else ("%%", "%%")
            end = source.find(closer, offset + len(opener))
            offset = len(source) if end < 0 else end + len(closer)
            continue
        if source[offset] == "`" and not escaped(source, offset):
            run_end = offset + 1
            while run_end < end_of_line and source[run_end] == "`":
                run_end += 1
            run = source[offset:run_end]
            found = source.find(run, run_end, end_of_line)
            while found >= 0 and ((found > 0 and source[found - 1] == "`") or
                                  (found + len(run) < end_of_line and source[found + len(run)] == "`")):
                found = source.find(run, found + 1, end_of_line)
            if found >= 0:
                offset = found + len(run)
                continue
            offset = run_end
            continue
        if source.startswith("[[", offset) and not escaped(source, offset):
            close = source.find("]]", offset + 2, end_of_line)
            end = end_of_line if close < 0 else close + 2
            raw = source[offset + 2:end if close < 0 else close]
            malformed = close < 0 or "[[" in raw
            embedded = offset > 0 and source[offset - 1] == "!" and not escaped(source, offset - 1)
            yield offset, end, raw, embedded, malformed
            offset = end
            continue
        offset += 1


def resolve(raw, malformed, source_path, notes):
    unsupported = {"target": None, "fragment": None, "display": None, "status": "unsupported",
                   "candidate_paths": [], "reason": "unclosed_or_nested_link" if malformed else "invalid_link_syntax",
                   "fragment_status": "absent"}
    if malformed or raw.count("|") > 1 or any(char in raw for char in "\\[]\r\n"):
        return unsupported
    link, separator, display = raw.partition("|")
    if separator and not display:
        return unsupported
    target, fragment_mark, fragment = link.partition("#")
    if fragment_mark and not fragment:
        return unsupported
    if not target:
        if not fragment_mark:
            return unsupported
        candidates = [source_path]
    else:
        try:
            path_name(target)
            need(all(segment == segment.strip() for segment in target.split("/")))
            note_path(target if target.endswith(".md") else target + ".md")
        except (Refusal, UnicodeError):
            return unsupported
        key = target[:-3] if target.endswith(".md") else target
        if "/" in key:
            candidates = [path for path in notes if path[:-3] == key]
        else:
            candidates = [path for path in notes if path.rsplit("/", 1)[-1][:-3] == key]
    candidates.sort()
    status = "resolved" if len(candidates) == 1 else "ambiguous" if candidates else "missing"
    return {"target": target, "fragment": fragment if fragment_mark else None,
            "display": display if separator else None, "status": status,
            "candidate_paths": candidates,
            "reason": {"resolved": "unique_note", "ambiguous": "multiple_note_targets", "missing": "note_not_found"}[status],
            "fragment_status": "not_checked" if fragment_mark else "absent"}


def solve(value):
    fields(value, ("record_type", "syntax_profile", "source_path", "text", "note_paths"), ("expected_sha256",))
    need(value["record_type"] == OPERATION + "_request/v1" and value["syntax_profile"] == PROFILE)
    source = text(value["text"], 32768)
    source_path = note_path(value["source_path"])
    sequence(value["note_paths"], 256)
    notes = [note_path(path) for path in value["note_paths"]]
    need(source_path in notes and len(set(notes)) == len(notes))
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if "expected_sha256" in value:
        need(digest_text(value["expected_sha256"]) == digest, "source_digest_mismatch")
    links = []
    for start, end, raw, embedded, malformed in scan(source):
        need(len(links) < 256, "link_limit_exceeded")
        links.append({"start": start, "end": end, "line": source.count("\n", 0, start) + 1,
                      "column": start - source.rfind("\n", 0, start), "raw": raw, "embedded": embedded,
                      **resolve(raw, malformed, source_path, notes)})
    return {"record_type": OPERATION + "_result/v1", "syntax_profile": PROFILE,
            "source_path": source_path, "source_sha256": digest, "complete_markdown_audit": False,
            "links": links, "counts": {status: sum(link["status"] == status for link in links)
                                       for status in ("resolved", "missing", "ambiguous", "unsupported")}}


if __name__ == "__main__":
    raise SystemExit(main())
