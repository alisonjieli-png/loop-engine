"""Answers tool calls on standard input and output from the arguments alone; opens no file, writes nothing, opens no network connection and starts no process.

pattern_tester_server is a small local Model Context Protocol server. It reads
newline-delimited JSON-RPC 2.0 messages on standard input, writes one answer
line for each request on standard output and writes diagnostics only to
standard error. It stops when standard input closes.

Tool: test_pattern. It tests one Python regular expression against texts that
should match, texts that should not match and plain examples, and reports
matches, groups, misses, false matches and an optional replacement preview,
with size and time limits. The --root option is accepted so that every server
of this family shares one launch line; this server never reads it.

Python 3.10 or later, standard library only. Licence: MIT.
"""
from __future__ import annotations

import argparse
import json
import re
import signal
import sys

SERVER_NAME = "pattern_tester_server"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26")
MAX_LINE_BYTES = 1024 * 1024
# One answer line holds the result twice (escaped text and structured copy); the whole line stays within 256 KiB.
MAX_ANSWER_BYTES = 256 * 1024
SHOWN_CHARS = 80
GROUPS_SHOWN = 20
FINDALL_SHOWN = 20
ENGINE = f"Python re {sys.version_info.major}.{sys.version_info.minor}"
FLAG_VALUES = {"IGNORECASE": re.IGNORECASE, "MULTILINE": re.MULTILINE, "DOTALL": re.DOTALL, "ASCII": re.ASCII,
               "VERBOSE": re.VERBOSE}
TEXT_LIST = {"type": "array", "maxItems": 100, "items": {"type": "string", "maxLength": 10000}}

TOOL_NAME = "test_pattern"
INPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "pattern": {"type": "string", "minLength": 1, "maxLength": 2000,
                    "description": "One regular expression in Python re syntax, for example ^[0-9]{4}-[0-9]{2}$."},
        "should_match": {**TEXT_LIST, "description": "Texts the pattern must match."},
        "should_not_match": {**TEXT_LIST, "description": "Texts the pattern must not match."},
        "examples": {**TEXT_LIST, "description": "Texts to test without an expectation, for groups or replacements."},
        "mode": {"type": "string", "enum": ["fullmatch", "search", "findall"], "default": "fullmatch",
                 "description": "fullmatch: the whole text must match. search: a match anywhere. findall: every match."},
        "flags": {"type": "array", "maxItems": 5, "uniqueItems": True,
                  "items": {"type": "string", "enum": ["IGNORECASE", "MULTILINE", "DOTALL", "ASCII", "VERBOSE"]},
                  "description": "Regular expression flags."},
        "replacement": {"type": "string", "maxLength": 1000,
                        "description": "Optional replacement such as \\g<day>.\\g<month>.\\g<year>. fullmatch expands the one match; search and findall replace every match."},
        "time_limit_ms": {"type": "integer", "minimum": 100, "maximum": 10000, "default": 2000,
                          "description": "Stop the test after this many milliseconds."},
    },
    "required": ["pattern"],
    "additionalProperties": False,
}
TOOL = {
    "name": TOOL_NAME,
    "description": (
        "Test one Python regular expression against texts that should match, texts that should not match and "
        "plain examples, before a cleaning rule uses it. Returns passed, the misses (should match but did not), "
        "the false matches, and for each text the match span, groups and an optional replacement preview. Mode "
        "fullmatch (the default) requires the whole text to match. Up to 100 texts per list; work stops at "
        "time_limit_ms."),
    "inputSchema": INPUT_SCHEMA,
    "annotations": {"title": "Test a regular expression", "readOnlyHint": True, "destructiveHint": False,
                    "idempotentHint": True, "openWorldHint": False},
}
INSTRUCTIONS = "Call test_pattern with a pattern and texts that should and should not match before a rule uses it."
NARROWING_HINT = "Test fewer or shorter texts."
LISTS = ("should_match", "should_not_match", "examples")


class Refusal(Exception):
    """A tool-level refusal. The answer carries isError true and this message."""

    def __init__(self, message: str, **details) -> None:
        super().__init__(message)
        self.payload = {"error": message, **details}


class TimeLimit(Exception):
    """Raised by the timer signal when a test runs too long."""


# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------

def same_json(left, right) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    return left == right


def matches_type(name: str, value) -> bool:
    if name == "object":
        return isinstance(value, dict)
    if name == "array":
        return isinstance(value, list)
    if name == "string":
        return isinstance(value, str)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "null":
        return value is None
    if isinstance(value, bool):
        return False
    if name == "integer":
        return isinstance(value, int) or (isinstance(value, float) and value.is_integer())
    if name == "number":
        return isinstance(value, (int, float))
    return False


def argument_problems(schema: dict, value, where: str) -> list[str]:
    """Checks a value against the small schema subset used by INPUT_SCHEMA."""
    declared = schema.get("type")
    if declared is not None:
        names = declared if isinstance(declared, list) else [declared]
        if not any(matches_type(name, value) for name in names):
            return [f"{where} must be of type {' or '.join(names)}"]
    problems = []
    if "enum" in schema and not any(same_json(value, option) for option in schema["enum"]):
        problems.append(f"{where} must be one of {json.dumps(schema['enum'])}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            problems.append(f"{where} must hold at least {schema['minLength']} characters")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            problems.append(f"{where} must hold at most {schema['maxLength']} characters")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            problems.append(f"{where} must be at least {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            problems.append(f"{where} must be at most {schema['maximum']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            problems.append(f"{where} must hold at least {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            problems.append(f"{where} must hold at most {schema['maxItems']} items")
        if schema.get("uniqueItems"):
            seen = set()
            for item in value:
                key = json.dumps(item, sort_keys=True)
                if key in seen:
                    problems.append(f"{where} must not repeat an item")
                    break
                seen.add(key)
        if isinstance(schema.get("items"), dict):
            for index, item in enumerate(value):
                problems += argument_problems(schema["items"], item, f"{where}[{index}]")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in value:
                problems.append(f"{where}.{name} is required")
        for name, item in value.items():
            if name in properties:
                problems += argument_problems(properties[name], item, f"{where}.{name}")
            elif schema.get("additionalProperties") is False:
                problems.append(f"{where}.{name[:60]} is not a known argument")
    return problems


# ---------------------------------------------------------------------------
# Testing
# ---------------------------------------------------------------------------

def short(text):
    if text is None:
        return None
    return text if len(text) <= SHOWN_CHARS else text[:SHOWN_CHARS]


def describe(text: str) -> dict:
    shown = {"text": short(text)}
    if len(text) > SHOWN_CHARS:
        shown["text_chars"] = len(text)
    return shown


def match_details(match) -> dict:
    details = {"span": [match.start(), match.end()], "matched_text": short(match.group(0)),
               "groups": [short(group) for group in match.groups()[:GROUPS_SHOWN]]}
    named = {name: short(value) for name, value in match.groupdict().items()}
    if named:
        details["named"] = named
    return details


def apply_replacement(compiled, match, text: str, mode: str, replacement: str):
    try:
        if mode == "fullmatch":
            return short(match.expand(replacement)) if match else None
        return short(compiled.sub(replacement, text))
    except (re.error, IndexError) as error:
        raise Refusal(f"The replacement cannot be applied: {error}. Refer only to groups the pattern has, "
                      "as \\1 or \\g<name>.") from None


def pattern_notes(pattern: str, flags: int, mode: str, has_expectations: bool) -> list[str]:
    notes = []
    if mode != "fullmatch":
        notes.append(f"Mode {mode} finds the pattern anywhere in a text; use fullmatch when the whole value "
                     "must follow the pattern.")
    if not flags & re.ASCII and re.search(r"(?<!\\)\\[dw]", pattern):
        notes.append("\\d and \\w also match digits and letters of other scripts; use [0-9] or the ASCII flag "
                     "when only ASCII is allowed.")
    if pattern != pattern.strip() and not flags & re.VERBOSE:
        notes.append("The pattern starts or ends with a space, which must then appear in the text.")
    if not has_expectations:
        notes.append("Add should_match and should_not_match texts to get a pass or fail answer.")
    return notes


def test_pattern(arguments: dict) -> dict:
    lists = {name: arguments.get(name, []) for name in LISTS}
    if not any(lists.values()):
        raise Refusal("Give at least one text in should_match, should_not_match or examples.")
    mode = arguments.get("mode", "fullmatch")
    names = arguments.get("flags", [])
    flags = 0
    for name in names:
        flags |= FLAG_VALUES[name]
    pattern = arguments["pattern"]
    try:
        compiled = re.compile(pattern, flags)
    except (re.error, RecursionError, OverflowError, ValueError) as error:
        position = getattr(error, "pos", None)
        raise Refusal(f"The pattern does not compile in {ENGINE}: {getattr(error, 'msg', str(error))}"
                      + (f" at position {position}." if position is not None else "."),
                      position=position) from None
    replacement = arguments.get("replacement")
    results, misses, false_matches = [], [], []
    matched_count = 0
    for list_name in LISTS:
        for index, text in enumerate(lists[list_name]):
            entry = {"list": list_name, "index": index, **describe(text)}
            if mode == "findall":
                found = list(compiled.finditer(text))
                matched = bool(found)
                entry["matches"] = [match_details(match) for match in found[:FINDALL_SHOWN]]
                entry["match_count"] = len(found)
                first = found[0] if found else None
            else:
                first = compiled.fullmatch(text) if mode == "fullmatch" else compiled.search(text)
                matched = first is not None
                if first is not None:
                    entry.update(match_details(first))
            entry["matched"] = matched
            if replacement is not None:
                entry["replaced"] = apply_replacement(compiled, first, text, mode, replacement)
            matched_count += matched
            if list_name == "should_match" and not matched:
                misses.append({"index": index, **describe(text)})
            if list_name == "should_not_match" and matched:
                false_matches.append({"index": index, **describe(text),
                                      "matched_text": short(first.group(0)) if first else None})
            results.append(entry)
    has_expectations = bool(lists["should_match"] or lists["should_not_match"])
    return {
        "engine": ENGINE,
        "pattern": pattern,
        "mode": mode,
        "flags": names,
        "group_count": compiled.groups,
        "group_names": sorted(compiled.groupindex, key=compiled.groupindex.get),
        "passed": (not misses and not false_matches) if has_expectations else None,
        "summary": {"tested": len(results), "matched": matched_count, "misses": len(misses),
                    "false_matches": len(false_matches)},
        "misses": misses,
        "false_matches": false_matches,
        "results": results,
        "notes": pattern_notes(pattern, flags, mode, has_expectations),
    }


def run_with_time_limit(milliseconds: int, function, *arguments):
    if not hasattr(signal, "setitimer"):
        answer = function(*arguments)
        answer["notes"].append("The time limit is not enforced on this platform.")
        return answer

    def expire(signum, frame):
        raise TimeLimit()

    previous = signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, milliseconds / 1000.0)
    try:
        return function(*arguments)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

def is_valid_id(value) -> bool:
    return isinstance(value, str) or (isinstance(value, int) and not isinstance(value, bool))


def error_answer(ident, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": ident, "error": {"code": code, "message": message}}


def encode(payload) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def serialize(answer: dict) -> bytes:
    """The bytes of one answer line, without its newline, exactly as send() writes them."""
    try:
        return encode(answer).encode("utf-8")
    except UnicodeEncodeError:
        # A lone surrogate from a JSON escape cannot be written as UTF-8; escape every non-ASCII character instead.
        return json.dumps(answer, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def tool_result(ident, payload: dict, is_error: bool) -> dict:
    return {"jsonrpc": "2.0", "id": ident,
            "result": {"content": [{"type": "text", "text": encode(payload)}], "structuredContent": payload,
                       "isError": is_error}}


def tool_answer(ident, payload: dict, is_error: bool) -> dict:
    """Builds the answer and measures its whole line; a line above the limit becomes a short refusal."""
    answer = tool_result(ident, payload, is_error)
    size = len(serialize(answer)) + 1
    if size <= MAX_ANSWER_BYTES:
        return answer
    note = f"The answer would be {size} bytes, above the {MAX_ANSWER_BYTES} byte limit for one answer."
    if is_error and isinstance(payload.get("error"), str):
        return tool_result(ident, {"error": payload["error"][:1000], "detail": note + " Details were left out."},
                           True)
    return tool_result(ident, {"error": note + " " + NARROWING_HINT}, True)


def call_tool(ident, params: dict) -> dict:
    name = params.get("name")
    arguments = params.get("arguments")
    if not isinstance(name, str):
        return error_answer(ident, -32602, "Invalid params: name must be a string.")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        return error_answer(ident, -32602, "Invalid params: arguments must be an object.")
    if name != TOOL_NAME:
        return error_answer(ident, -32602, f"Unknown tool: {name[:80]}")
    problems = argument_problems(INPUT_SCHEMA, arguments, "arguments")
    if problems:
        return tool_answer(ident, {"error": "The arguments do not match the input schema.",
                                   "problems": problems[:20]}, True)
    limit = int(arguments.get("time_limit_ms", 2000))
    try:
        return tool_answer(ident, run_with_time_limit(limit, test_pattern, arguments), False)
    except Refusal as refusal:
        return tool_answer(ident, refusal.payload, True)
    except TimeLimit:
        return tool_answer(ident, {"error": f"The test passed the time limit of {limit} ms. The pattern probably "
                                            "backtracks too much, for example a nested repeat such as (a+)+. "
                                            "Rewrite it without nested repeats."}, True)
    except (MemoryError, RecursionError):
        return tool_answer(ident, {"error": "The test needs more memory or depth than this server has. "
                                            + NARROWING_HINT}, True)
    except Exception as error:  # noqa: BLE001 - a defect must not stop the server
        print(f"{SERVER_NAME}: unexpected {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        return tool_answer(ident, {"error": f"Unexpected internal error ({type(error).__name__}). "
                                            "Report it and do not repeat the same call."}, True)


def handle(message):
    if isinstance(message, list):
        return error_answer(None, -32600, "Batch requests are not supported; send one message per line.")
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return error_answer(None, -32600, "Invalid request: expected one JSON-RPC 2.0 object.")
    ident = message.get("id")
    if "method" not in message:
        if "result" in message or "error" in message:
            return None
        return error_answer(ident if is_valid_id(ident) else None, -32600, "Invalid request: method is missing.")
    method = message["method"]
    if not isinstance(method, str) or not method:
        return error_answer(ident if is_valid_id(ident) else None, -32600, "Invalid request: method must be a string.")
    if "id" not in message:
        return None
    if not is_valid_id(ident):
        return error_answer(None, -32600, "Invalid request: id must be a string or an integer.")
    params = message.get("params")
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return error_answer(ident, -32602, "Invalid params: params must be an object.")
    if method == "initialize":
        requested = params.get("protocolVersion")
        version = requested if requested in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
        return {"jsonrpc": "2.0", "id": ident, "result": {
            "protocolVersion": version, "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION}, "instructions": INSTRUCTIONS}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": ident, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": ident, "result": {"tools": [TOOL]}}
    if method == "tools/call":
        return call_tool(ident, params)
    return error_answer(ident, -32601, f"Method not found: {method[:80]}")


def refuse_constant(name: str):
    raise ValueError(f"nonstandard constant {name}")


def send(answer: dict) -> None:
    try:
        data = serialize(answer)
    except (TypeError, ValueError) as error:
        data = encode(error_answer(answer.get("id"), -32603,
                                   f"Internal error: the answer could not be encoded ({type(error).__name__}).")
                      ).encode("utf-8")
    sys.stdout.buffer.write(data + b"\n")
    sys.stdout.buffer.flush()


def serve() -> int:
    source = sys.stdin.buffer
    while True:
        line = source.readline(MAX_LINE_BYTES + 1)
        if not line:
            return 0
        if len(line) > MAX_LINE_BYTES and not line.endswith(b"\n"):
            while True:
                rest = source.readline(MAX_LINE_BYTES)
                if not rest or rest.endswith(b"\n"):
                    break
            send(error_answer(None, -32600, "Invalid request: the line is larger than 1 MiB and was not read."))
            continue
        if not line.strip():
            continue
        try:
            message = json.loads(line.decode("utf-8"), parse_constant=refuse_constant)
        except (UnicodeDecodeError, ValueError, RecursionError):
            send(error_answer(None, -32700, "Parse error: the line is not one valid UTF-8 JSON value."))
            continue
        answer = handle(message)
        if answer is not None:
            send(answer)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Local regular expression tester tool server (standard input and output).")
    parser.add_argument("--root", default=".", help="accepted for a shared launch line; this server opens no file")
    parser.parse_args(argv)
    try:
        return serve()
    except (BrokenPipeError, KeyboardInterrupt):
        return 0


if __name__ == "__main__":
    sys.exit(main())
