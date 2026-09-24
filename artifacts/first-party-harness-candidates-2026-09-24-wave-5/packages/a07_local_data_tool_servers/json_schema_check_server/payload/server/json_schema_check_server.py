"""Reads JSON files under --root and answers tool calls on standard input and output; writes no file, opens no network connection and starts no process.

json_schema_check_server is a small local Model Context Protocol server. It reads
newline-delimited JSON-RPC 2.0 messages on standard input, writes one answer
line for each request on standard output and writes diagnostics only to
standard error. It stops when standard input closes.

Tool: check_json_schema. It checks one JSON document, or every line of a JSON
Lines file, against a JSON Schema and returns every violation with the path of
the value and the path of the schema keyword. It supports a declared subset of
draft 2020-12 (and draft-07 array and reference rules) and refuses a schema
that uses any other keyword, so no rule is skipped without notice. Patterns are
read as ECMA-262 regular expressions, the dialect JSON Schema names for them,
and translated to Python's re module; a pattern that cannot keep its meaning
there is refused.

Python 3.10 or later, standard library only. Licence: MIT.
"""
from __future__ import annotations

import argparse
import datetime
import difflib
import hashlib
import json
import os
import re
import signal
import stat
import sys
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path, PureWindowsPath

SERVER_NAME = "json_schema_check_server"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26")
MAX_LINE_BYTES = 1024 * 1024
# One answer line holds the result twice (escaped text and structured copy); the whole line stays within 256 KiB.
MAX_ANSWER_BYTES = 256 * 1024
MAX_DOCUMENT_BYTES = 16 * 1024 * 1024
MAX_SCHEMA_BYTES = 1024 * 1024
MAX_DEPTH = 128
MAX_STEPS = 2_000_000
MAX_REFERENCE_HOPS = 64
TIME_LIMIT_SECONDS = 20
SHOWN_CHARS = 60

DRAFT_2020 = "2020-12"
DRAFT_07 = "draft-07"
SCHEMA_URIS = {
    "https://json-schema.org/draft/2020-12/schema": DRAFT_2020,
    "http://json-schema.org/draft-07/schema": DRAFT_07,
    "https://json-schema.org/draft-07/schema": DRAFT_07,
}
ANNOTATIONS = frozenset({"$schema", "$id", "$comment", "title", "description", "default", "examples", "deprecated",
                         "readOnly", "writeOnly", "contentMediaType", "contentEncoding", "contentSchema"})
SHARED = frozenset({"$ref", "$defs", "definitions", "type", "enum", "const", "properties", "required",
                    "additionalProperties", "patternProperties", "propertyNames", "minProperties", "maxProperties",
                    "items", "minItems", "maxItems", "uniqueItems", "contains", "minLength", "maxLength", "pattern",
                    "format", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "allOf",
                    "anyOf", "oneOf", "not", "if", "then", "else"})
SUPPORTED = {
    DRAFT_2020: SHARED | {"prefixItems", "dependentRequired", "dependentSchemas", "minContains",
                          "maxContains"},
    DRAFT_07: SHARED | {"additionalItems", "dependencies"},
}
TYPES = ("null", "boolean", "object", "array", "number", "integer", "string")
FORMATS = ("date", "date-time", "time", "email", "uuid", "ipv4", "uri")
SCHEMA_MAPS = ("properties", "patternProperties", "$defs", "definitions", "dependentSchemas")
SCHEMA_VALUES = ("additionalProperties", "propertyNames", "contains", "not", "if", "then", "else", "additionalItems")
SCHEMA_LISTS = ("allOf", "anyOf", "oneOf", "prefixItems")
COUNTS = ("minProperties", "maxProperties", "minItems", "maxItems", "minLength", "maxLength", "minContains",
          "maxContains")
BOUNDS = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum")

TOOL_NAME = "check_json_schema"
INPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "document_path": {
            "type": "string", "minLength": 1, "maxLength": 1024,
            "description": "JSON or JSON Lines file relative to the workspace root, for example out/result.json."},
        "document": {
            "description": "The JSON value to check, given inline. Give document or document_path, not both."},
        "schema_path": {
            "type": "string", "minLength": 1, "maxLength": 1024,
            "description": "JSON Schema file relative to the workspace root, for example contracts/output.schema.json."},
        "schema": {
            "type": ["object", "boolean"],
            "description": "The JSON Schema, given inline. Give schema or schema_path, not both."},
        "jsonl": {
            "type": "boolean", "default": False,
            "description": "true checks every nonempty line of document_path as its own JSON document."},
        "check_formats": {
            "type": "boolean", "default": True,
            "description": "true checks format for date, date-time, time, email, uuid, ipv4 and uri."},
        "allow_unchecked": {
            "type": "boolean", "default": False,
            "description": "true checks the supported keywords and lists the others in unchecked instead of refusing."},
        "max_violations": {
            "type": "integer", "minimum": 1, "maximum": 1000, "default": 100,
            "description": "List at most this many violations; violation_count still counts all of them."},
    },
    "additionalProperties": False,
}
TOOL = {
    "name": TOOL_NAME,
    "description": (
        "Check a JSON document (a file under the workspace root or an inline value, or each line of a JSON Lines "
        "file) against a JSON Schema and return every violation with the path of the value, the schema keyword "
        "and a message. Supports draft 2020-12 and draft-07 keywords for types, enums, objects, arrays, strings, "
        "numbers, combinations and local $ref. Patterns are read as ECMA-262 regular expressions. A schema with "
        "another keyword is refused unless allow_unchecked is true. It reads files and changes nothing."),
    "inputSchema": INPUT_SCHEMA,
    "annotations": {"title": "Check JSON against a schema", "readOnlyHint": True, "destructiveHint": False,
                    "idempotentHint": True, "openWorldHint": False},
}
INSTRUCTIONS = "Call check_json_schema with a document and a schema before handing a JSON output on."
NARROWING_HINT = "Lower max_violations or check a smaller document."

DATE = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})\Z")
TIME = re.compile(r"([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.[0-9]+)?(?:[Zz]|[+-]([0-9]{2}):([0-9]{2}))\Z")
EMAIL = re.compile(r"[^@\s]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+\Z")
UUID = re.compile(r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\Z")
IPV4 = re.compile(r"(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])(?:\.(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])){3}\Z")
URI = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:[^\s]*\Z")

# ECMA-262 WhiteSpace and LineTerminator code points, which \s matches there, written for a Python class.
ECMA_SPACE = "\\t\\n\\x0b\\x0c\\r\\x20\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000\\ufeff"
ECMA_LINE_BREAKS = "\\n\\r\\u2028\\u2029"
ECMA_QUANTIFIER = re.compile(r"\{([0-9]+)(?:,([0-9]*))?\}")
GROUP_NAME = re.compile(r"[A-Za-z_$\u00c0-\uffff][A-Za-z0-9_$\u00c0-\uffff]*>")
HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


class Refusal(Exception):
    """A tool-level refusal. The answer carries isError true and this message."""

    def __init__(self, message: str, **details) -> None:
        super().__init__(message)
        self.payload = {"error": message, **details}


class TimeLimit(Exception):
    """Raised by the timer signal when a check runs too long."""


class Context:
    def __init__(self, root: Path, time_limit: int) -> None:
        self.root = root
        self.time_limit = time_limit


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def pointer(parts) -> str:
    return "".join("/" + str(part).replace("~", "~0").replace("/", "~1") for part in parts)


def shown(value) -> str:
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= SHOWN_CHARS else text[:SHOWN_CHARS] + "..."


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


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
    if name == "integer":
        return is_number(value) and (isinstance(value, int) or value.is_integer())
    if name == "number":
        return is_number(value)
    return False


def type_name(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
        return "integer"
    if isinstance(value, float):
        return "number"
    return {str: "string", list: "array", dict: "object"}.get(type(value), "unknown")


def canonical(value):
    """A hashable form in which JSON-equal values are equal (1 equals 1.0, true differs from 1)."""
    if isinstance(value, bool) or value is None:
        return ("literal", value)
    if isinstance(value, float) and value.is_integer():
        return ("number", int(value))
    if is_number(value):
        return ("number", value)
    if isinstance(value, str):
        return ("string", value)
    if isinstance(value, list):
        return ("array", tuple(canonical(item) for item in value))
    return ("object", tuple(sorted((key, canonical(item)) for key, item in value.items())))


def depth_of(value) -> int:
    deepest, pending = 0, [(value, 1)]
    while pending:
        item, level = pending.pop()
        deepest = max(deepest, level)
        if level > MAX_DEPTH:
            return level
        if isinstance(item, dict):
            pending.extend((inner, level + 1) for inner in item.values())
        elif isinstance(item, list):
            pending.extend((inner, level + 1) for inner in item)
    return deepest


def strict_parse(text: str, where: str):
    duplicates: list[str] = []

    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                duplicates.append(key)
            seen[key] = value
        return seen

    def constant(name):
        raise ValueError(f"nonstandard constant {name}")

    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except RecursionError:
        raise Refusal(f"{where} is nested too deeply.") from None
    except ValueError as error:
        raise Refusal(f"{where} is not valid JSON: {str(error)[:200]}.") from None
    if duplicates:
        raise Refusal(f"{where} repeats the key {duplicates[0][:60]!r} inside one object; readers disagree on "
                      "which value counts. Remove the repeat first.")
    if depth_of(value) > MAX_DEPTH:
        raise Refusal(f"{where} is nested more than {MAX_DEPTH} levels deep.")
    return value


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

def resolve_file(root: Path, relative: str) -> Path:
    """Resolves a relative path under root; refuses '..', absolute paths and links that leave root."""
    if "\x00" in relative:
        raise Refusal("The path holds a NUL character.")
    if Path(relative).is_absolute() or PureWindowsPath(relative).anchor:
        raise Refusal("Give the path relative to the workspace root, for example out/result.json. "
                      "Absolute paths are refused.")
    parts = Path(relative).parts
    if ".." in parts or ".." in PureWindowsPath(relative).parts:
        raise Refusal("The path may not contain '..'.")
    try:
        resolved = root.joinpath(*parts).resolve(strict=True)
    except FileNotFoundError:
        raise Refusal(f"No file exists at {relative!r} under the workspace root.") from None
    except (OSError, RuntimeError) as error:
        raise Refusal(f"The path cannot be resolved ({type(error).__name__}).") from None
    if resolved != root and root not in resolved.parents:
        raise Refusal("The path leads outside the workspace root, for example through a symbolic link.")
    if not stat.S_ISREG(resolved.stat().st_mode):
        raise Refusal(f"{relative!r} is not a regular file.")
    return resolved


def read_text(root: Path, relative: str, limit: int) -> tuple[str, str]:
    path = resolve_file(root, relative)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise Refusal(f"The file cannot be opened ({type(error).__name__}).") from None
    with os.fdopen(descriptor, "rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise Refusal(f"{relative!r} is larger than the limit of {limit} bytes.")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        line = data.count(b"\n", 0, error.start) + 1
        raise Refusal(f"{relative!r} is not UTF-8 text (line {line}).") from None
    return text, hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Schema reading: supported keywords and well-formed values
# ---------------------------------------------------------------------------

class SchemaScan:
    """Reads a schema once: every keyword is supported, listed as unchecked or reported as a problem.

    Unchecked keywords are remembered by the identity of the schema object that holds them, so the validator
    skips them wherever it reaches that object, directly or through $ref. Every local $ref target is scanned
    too, so no schema the validator can reach goes unread.
    """

    def __init__(self, root, draft: str) -> None:
        self.root, self.draft = root, draft
        self.unchecked: list[dict] = []
        self.skipped: set[tuple[int, str]] = set()
        self.patterns: dict[str, re.Pattern] = {}
        self.problems: list[str] = []
        self.walked: set[int] = set()
        self.targets: list[tuple[object, list]] = []

    def scan(self) -> None:
        self.walk(self.root, [])
        while self.targets:
            target, parts = self.targets.pop()
            self.walk(target, parts)

    def leave_unchecked(self, schema: dict, parts: list, key: str, reason: str) -> None:
        self.unchecked.append({"schema_path": pointer(parts + [key]), "keyword": key, "reason": reason})
        self.skipped.add((id(schema), key))

    def walk(self, schema, parts: list) -> None:
        where = pointer(parts) or "/"
        if isinstance(schema, bool):
            return
        if not isinstance(schema, dict):
            self.problems.append(f"{where}: a schema must be an object or true or false")
            return
        if id(schema) in self.walked:
            return
        self.walked.add(id(schema))
        for key, value in schema.items():
            if key == "$id" and parts:
                self.leave_unchecked(schema, parts, key, "an $id below the root changes how references resolve")
            elif key not in ANNOTATIONS and key not in SUPPORTED[self.draft]:
                self.leave_unchecked(schema, parts, key, unknown_reason(key, self.draft))
            else:
                self.check_value(schema, key, value, parts)
        if self.draft == DRAFT_07 and "$ref" in schema:
            for key in sorted(set(schema) - ANNOTATIONS - {"$ref", "$defs", "definitions"}):
                if (id(schema), key) not in self.skipped:
                    self.leave_unchecked(schema, parts, key, "draft-07 ignores every keyword next to $ref")

    def check_value(self, schema: dict, key: str, value, parts: list) -> None:
        where = pointer(parts + [key])
        if key in SCHEMA_MAPS:
            if not isinstance(value, dict):
                self.problems.append(f"{where}: must be an object of schemas")
                return
            for name, item in value.items():
                if key == "patternProperties":
                    self.compile(name, where)
                self.walk(item, parts + [key, name])
        elif key in SCHEMA_VALUES:
            self.walk(value, parts + [key])
        elif key in SCHEMA_LISTS:
            if not isinstance(value, list) or not value:
                self.problems.append(f"{where}: must be a nonempty array of schemas")
                return
            for index, item in enumerate(value):
                self.walk(item, parts + [key, index])
        elif key == "items":
            if isinstance(value, list) and self.draft == DRAFT_07:
                for index, item in enumerate(value):
                    self.walk(item, parts + [key, index])
            elif isinstance(value, list):
                self.problems.append(f"{where}: in draft 2020-12 items is one schema; use prefixItems for a tuple")
            else:
                self.walk(value, parts + [key])
        elif key == "dependencies":
            if not isinstance(value, dict):
                self.problems.append(f"{where}: must be an object")
                return
            for name, item in value.items():
                if isinstance(item, list):
                    self.names(item, pointer(parts + [key, name]))
                else:
                    self.walk(item, parts + [key, name])
        elif key == "type":
            names = value if isinstance(value, list) else [value]
            if not names or any(name not in TYPES for name in names) or len(set(names)) != len(names):
                self.problems.append(f"{where}: must name types from {list(TYPES)}")
        elif key == "enum":
            if not isinstance(value, list):
                self.problems.append(f"{where}: must be an array")
        elif key in ("required",):
            self.names(value, where)
        elif key == "dependentRequired":
            if not isinstance(value, dict):
                self.problems.append(f"{where}: must be an object of name arrays")
                return
            for name, item in value.items():
                self.names(item, pointer(parts + [key, name]))
        elif key in COUNTS:
            if not (isinstance(value, int) and not isinstance(value, bool) and value >= 0):
                self.problems.append(f"{where}: must be a whole number of at least 0")
        elif key in BOUNDS:
            if not is_number(value):
                self.problems.append(f"{where}: must be a number")
        elif key == "multipleOf":
            if not is_number(value) or value <= 0:
                self.problems.append(f"{where}: must be a number above 0")
        elif key == "uniqueItems":
            if not isinstance(value, bool):
                self.problems.append(f"{where}: must be true or false")
        elif key == "pattern":
            if not isinstance(value, str):
                self.problems.append(f"{where}: must be a string")
            else:
                self.compile(value, where)
        elif key == "format":
            if not isinstance(value, str):
                self.problems.append(f"{where}: must be a string")
            elif value not in FORMATS:
                self.leave_unchecked(schema, parts, "format", f"format {value[:40]!r} is not one of {list(FORMATS)}")
        elif key == "$ref":
            if not isinstance(value, str) or not value.startswith("#"):
                self.leave_unchecked(schema, parts, "$ref", "only local references that start with # are supported")
            else:
                try:
                    target = resolve_reference(self.root, value)
                except LookupError:
                    self.problems.append(f"{where}: the reference {value[:80]!r} points nowhere in this schema")
                else:
                    self.targets.append((target, reference_parts(value)))

    def names(self, value, where: str) -> None:
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value) \
                or len(set(value)) != len(value):
            self.problems.append(f"{where}: must be an array of distinct strings")

    def compile(self, text: str, where: str) -> None:
        if text in self.patterns:
            return
        try:
            self.patterns[text] = re.compile(translate_pattern(text), re.ASCII)
        except PatternProblem as problem:
            self.problems.append(f"{where}: the pattern {text[:60]!r} {problem}")
        except (re.error, RecursionError, OverflowError) as error:
            self.problems.append(f"{where}: the pattern {text[:60]!r} cannot run in Python with its ECMA-262 "
                                 f"meaning ({error})")


def unknown_reason(key: str, draft: str) -> str:
    if key in KNOWN_ELSEWHERE:
        return f"not supported for {draft} by this tool"
    close = difflib.get_close_matches(key, sorted(SUPPORTED[draft] | ANNOTATIONS), n=1, cutoff=0.75)
    if close:
        return f"unknown keyword; did you mean {close[0]!r}?"
    return "unknown keyword"


def percent_decode(text: str) -> str:
    data = re.sub(rb"%([0-9A-Fa-f]{2})", lambda match: bytes([int(match.group(1), 16)]), text.encode("utf-8"))
    return data.decode("utf-8", "replace")


KNOWN_ELSEWHERE = frozenset({"unevaluatedProperties", "unevaluatedItems", "$anchor", "$dynamicRef", "$dynamicAnchor",
                             "$recursiveRef", "$recursiveAnchor", "$vocabulary", "dependencies", "additionalItems",
                             "prefixItems", "dependentRequired", "dependentSchemas", "minContains", "maxContains",
                             "id"})


def reference_parts(reference: str) -> list:
    """The JSON Pointer parts of a local reference such as #/$defs/rule."""
    fragment = percent_decode(reference[1:])
    if not fragment:
        return []
    return [raw.replace("~1", "/").replace("~0", "~") for raw in fragment[1:].split("/")]


def resolve_reference(root, reference: str):
    fragment = percent_decode(reference[1:])
    if fragment == "":
        return root
    if not fragment.startswith("/"):
        raise LookupError(reference)
    target = root
    for raw in fragment[1:].split("/"):
        part = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(target, dict) and part in target:
            target = target[part]
        elif isinstance(target, list) and part.isdigit() and int(part) < len(target):
            target = target[int(part)]
        else:
            raise LookupError(reference)
    if not isinstance(target, (dict, bool)):
        raise LookupError(reference)
    return target


# ---------------------------------------------------------------------------
# Patterns: ECMA-262 source translated to Python re
# ---------------------------------------------------------------------------

class PatternProblem(Exception):
    """A pattern that this tool cannot run with its ECMA-262 meaning."""


def char_escape(code: int) -> str:
    """One code point written so that Python's re reads it as that literal character, inside or outside a class."""
    if code < 0x80 and chr(code).isalnum():
        return chr(code)
    if code <= 0xFF:
        return f"\\x{code:02x}"
    if code <= 0xFFFF:
        return f"\\u{code:04x}"
    return f"\\U{code:08x}"


def hex_value(source: str, start: int, count: int) -> int:
    digits = source[start:start + count]
    if len(digits) != count or not set(digits) <= HEX_DIGITS:
        raise PatternProblem("has an incomplete \\x or \\u escape")
    return int(digits, 16)


def escaped_character(source: str, index: int, in_class: bool) -> tuple[int, int]:
    """Reads a character escape that starts at the backslash; returns its code point and the next index."""
    letter = source[index + 1]
    simple = {"t": 9, "n": 10, "v": 11, "f": 12, "r": 13}
    if letter in simple:
        return simple[letter], index + 2
    if letter == "b" and in_class:
        return 8, index + 2
    if letter == "0":
        if index + 2 < len(source) and source[index + 2].isdigit():
            raise PatternProblem("uses an octal escape such as \\01, which ECMA-262 refuses in patterns")
        return 0, index + 2
    if letter in "123456789":
        raise PatternProblem("uses a backreference such as \\1; Python and ECMA-262 match a group that took no "
                             "part differently, so backreferences are refused")
    if letter == "k":
        raise PatternProblem("uses a named backreference \\k<...>, which this tool refuses")
    if letter == "c":
        control = source[index + 2:index + 3]
        if not (control.isascii() and control.isalpha()):
            raise PatternProblem("has \\c without a letter after it")
        return ord(control) % 32, index + 3
    if letter == "x":
        return hex_value(source, index + 2, 2), index + 4
    if letter == "u":
        if source.startswith("{", index + 2):
            end = source.find("}", index + 3)
            digits = source[index + 3:end] if end != -1 else ""
            if not 1 <= len(digits) <= 6 or not set(digits) <= HEX_DIGITS or int(digits, 16) > 0x10FFFF:
                raise PatternProblem("has a \\u{...} escape that is not a Unicode code point")
            return int(digits, 16), end + 1
        code = hex_value(source, index + 2, 4)
        if 0xD800 <= code <= 0xDBFF and source.startswith("\\u", index + 6):
            try:
                low = hex_value(source, index + 8, 4)
            except PatternProblem:
                low = -1
            if 0xDC00 <= low <= 0xDFFF:
                return 0x10000 + ((code - 0xD800) << 10) + (low - 0xDC00), index + 12
        return code, index + 6
    if letter in "pP":
        raise PatternProblem("uses a Unicode property class \\p{...} or \\P{...}, which Python's re module "
                             "does not support")
    if letter.isascii() and letter.isalnum():
        raise PatternProblem(f"uses \\{letter}, which is not an ECMA-262 escape")
    return ord(letter), index + 2


def character_class(source: str, index: int) -> tuple[str, int]:
    """Translates the class that starts at [; returns Python text and the index after the closing ]."""
    index += 1
    negated = source.startswith("^", index)
    if negated:
        index += 1
    if source.startswith("]", index):
        return ("[\\x00-\\U0010ffff]" if negated else "(?!)"), index + 1
    members, not_space = [], False

    def add(atom) -> None:
        nonlocal not_space
        if atom[3] == "S":
            not_space = True
        else:
            members.append(atom[1])

    while True:
        if index >= len(source):
            raise PatternProblem("has a [ without its closing ]")
        if source[index] == "]":
            index += 1
            break
        first = class_atom(source, index)
        index = first[2]
        if source.startswith("-", index) and index + 1 < len(source) and source[index + 1] != "]":
            second = class_atom(source, index + 1)
            index = second[2]
            if first[0] is not None and second[0] is not None:
                if second[0] < first[0]:
                    raise PatternProblem("has a class range whose end comes before its start")
                members.append(f"{char_escape(first[0])}-{char_escape(second[0])}")
            else:
                # A class such as \d at either end: ECMA-262 without the u flag reads the three parts separately.
                add(first)
                members.append(char_escape(ord("-")))
                add(second)
            continue
        add(first)
    body = "".join(members)
    if not not_space:
        return f"[{'^' if negated else ''}{body}]", index
    if negated:
        return (f"(?:(?![{body}])[{ECMA_SPACE}])" if body else f"[{ECMA_SPACE}]"), index
    return (f"(?:[^{ECMA_SPACE}]|[{body}])" if body else f"[^{ECMA_SPACE}]"), index


def class_atom(source: str, index: int):
    """One member of a class: (code point or None, Python text, next index, kind)."""
    character = source[index]
    if character != "\\":
        return ord(character), char_escape(ord(character)), index + 1, None
    if index + 1 >= len(source):
        raise PatternProblem("ends with a lone backslash")
    letter = source[index + 1]
    if letter in "dDwW":
        return None, "\\" + letter, index + 2, None
    if letter == "s":
        return None, ECMA_SPACE, index + 2, None
    if letter == "S":
        return None, "", index + 2, "S"
    if letter == "B":
        raise PatternProblem("uses \\B inside a class, which ECMA-262 refuses")
    code, after = escaped_character(source, index, in_class=True)
    return code, char_escape(code), after, None


def after_quantifier(source: str, index: int, out: list) -> int:
    if source.startswith("?", index):
        out.append("?")
        index += 1
    if source.startswith("+", index):
        raise PatternProblem("puts + right after a quantifier; ECMA-262 has no possessive quantifiers")
    return index


def translate_pattern(source: str) -> str:
    """Python re source that matches exactly what the ECMA-262 pattern matches (Unicode mode, no flags).

    $ matches only at the end of the text, . stops at the four ECMA-262 line breaks, \\s and \\S use the
    ECMA-262 white space set, and \\d, \\w and \\b stay ASCII (the caller compiles with re.ASCII). Syntax that
    exists only in Python, and ECMA-262 forms Python cannot run with the same meaning, raise PatternProblem.
    """
    out: list[str] = []
    index = 0
    while index < len(source):
        character = source[index]
        if character == "\\":
            if index + 1 >= len(source):
                raise PatternProblem("ends with a lone backslash")
            letter = source[index + 1]
            if letter in "dDwWbB":
                out.append("\\" + letter)
                index += 2
            elif letter == "s":
                out.append(f"[{ECMA_SPACE}]")
                index += 2
            elif letter == "S":
                out.append(f"[^{ECMA_SPACE}]")
                index += 2
            else:
                code, index = escaped_character(source, index, in_class=False)
                out.append(char_escape(code))
        elif character == "[":
            piece, index = character_class(source, index)
            out.append(piece)
        elif character == "(":
            if not source.startswith("(?", index):
                out.append("(")
                index += 1
            elif source.startswith(("(?<=", "(?<!"), index):
                out.append(source[index:index + 4])
                index += 4
            elif source.startswith(("(?:", "(?=", "(?!"), index):
                out.append(source[index:index + 3])
                index += 3
            elif source.startswith("(?<", index):
                name = GROUP_NAME.match(source, index + 3)
                if name is None:
                    raise PatternProblem("has a group name that is not an identifier")
                out.append("(")
                index = name.end()
            else:
                raise PatternProblem(f"uses {source[index:index + 3]!r}, which is not ECMA-262 syntax")
        elif character == ".":
            out.append(f"[^{ECMA_LINE_BREAKS}]")
            index += 1
        elif character == "$":
            out.append("\\Z")
            index += 1
        elif character in "^|)":
            out.append(character)
            index += 1
        elif character in "*+?":
            out.append(character)
            index = after_quantifier(source, index + 1, out)
        elif character == "{":
            quantifier = ECMA_QUANTIFIER.match(source, index)
            if quantifier is None:
                out.append("\\{")
                index += 1
            else:
                out.append(quantifier.group(0))
                index = after_quantifier(source, quantifier.end(), out)
        else:
            out.append(char_escape(ord(character)))
            index += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def valid_format(name: str, text: str) -> bool:
    if name == "date":
        match = DATE.match(text)
        return bool(match) and real_date(match)
    if name == "date-time":
        head, separator, tail = text.partition("T") if "T" in text else text.partition("t")
        match = DATE.match(head)
        return bool(separator) and bool(match) and real_date(match) and valid_format("time", tail)
    if name == "time":
        match = TIME.match(text)
        if not match:
            return False
        hour, minute, second = int(match.group(1)), int(match.group(2)), int(match.group(3))
        offset_ok = match.group(4) is None or (int(match.group(4)) < 24 and int(match.group(5)) < 60)
        return hour < 24 and minute < 60 and second <= 60 and offset_ok
    if name == "email":
        return bool(EMAIL.match(text)) and ".." not in text.split("@")[0]
    if name == "uuid":
        return bool(UUID.match(text))
    if name == "ipv4":
        return bool(IPV4.match(text))
    if name == "uri":
        return bool(URI.match(text))
    return True


def exact_number(number) -> Fraction:
    """The exact value of a JSON number as written: whole numbers as they are, others by their shortest decimal."""
    if isinstance(number, int):
        return Fraction(number)
    return Fraction(Decimal(repr(number)))


def real_date(match) -> bool:
    try:
        datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return False
    return True


class Validator:
    def __init__(self, scan: SchemaScan, check_formats: bool) -> None:
        self.root, self.draft, self.patterns = scan.root, scan.draft, scan.patterns
        self.check_formats = check_formats
        self.skip = scan.skipped
        self.steps = 0

    def check(self, value, schema, where: list, at: list, hops: int = 0) -> list[dict]:
        self.steps += 1
        if self.steps > MAX_STEPS:
            raise Refusal(f"The check needs more than {MAX_STEPS} steps. Check a smaller document or a simpler schema.")
        if schema is True:
            return []
        if schema is False:
            return [self.violation(where, at, "false", "no value is allowed here")]
        found: list[dict] = []
        if "$ref" in schema and (id(schema), "$ref") not in self.skip:
            if hops >= MAX_REFERENCE_HOPS:
                raise Refusal("The schema's references go round in a circle without reaching a rule.")
            target = resolve_reference(self.root, schema["$ref"])
            found += self.check(value, target, where, at + ["$ref"], hops + 1)
            if self.draft == DRAFT_07:
                return found
        for keyword in schema:
            if keyword == "$ref" or (id(schema), keyword) in self.skip:
                continue
            method = getattr(self, "k_" + keyword.replace("$", "").replace("-", "_"), None)
            if method is not None:
                found += method(value, schema[keyword], schema, where, at + [keyword])
        return found

    def violation(self, where: list, at: list, keyword: str, message: str, **extra) -> dict:
        return {"instance_path": pointer(where), "schema_path": pointer(at), "keyword": keyword,
                "message": message, **extra}

    def passes(self, value, schema, where, at) -> bool:
        return not self.check(value, schema, where, at)

    # -- any type ---------------------------------------------------------
    def k_type(self, value, expected, schema, where, at):
        names = expected if isinstance(expected, list) else [expected]
        if any(matches_type(name, value) for name in names):
            return []
        return [self.violation(where, at, "type", f"expected {' or '.join(names)}, found {type_name(value)}")]

    def k_enum(self, value, options, schema, where, at):
        key = canonical(value)
        if any(canonical(option) == key for option in options):
            return []
        listing = shown(options) if len(options) <= 10 else f"one of {len(options)} allowed values"
        return [self.violation(where, at, "enum", f"{shown(value)} is not in {listing}")]

    def k_const(self, value, constant, schema, where, at):
        if canonical(value) == canonical(constant):
            return []
        return [self.violation(where, at, "const", f"{shown(value)} is not the required value {shown(constant)}")]

    def k_allOf(self, value, schemas, schema, where, at):
        found = []
        for index, item in enumerate(schemas):
            found += self.check(value, item, where, at + [index])
        return found

    def k_anyOf(self, value, schemas, schema, where, at):
        results = [self.check(value, item, where, at + [index]) for index, item in enumerate(schemas)]
        if any(not result for result in results):
            return []
        return [self.violation(where, at, "anyOf", f"matches none of the {len(schemas)} anyOf alternatives",
                               alternatives=[result[0]["message"] for result in results[:3]])]

    def k_oneOf(self, value, schemas, schema, where, at):
        results = [self.check(value, item, where, at + [index]) for index, item in enumerate(schemas)]
        matched = [index for index, result in enumerate(results) if not result]
        if len(matched) == 1:
            return []
        if not matched:
            return [self.violation(where, at, "oneOf", f"matches none of the {len(schemas)} oneOf alternatives",
                                   alternatives=[result[0]["message"] for result in results[:3]])]
        return [self.violation(where, at, "oneOf", f"matches alternatives {matched[:5]}; exactly one must match")]

    def k_not(self, value, inner, schema, where, at):
        if self.passes(value, inner, where, at):
            return [self.violation(where, at, "not", "matches the schema under not, which is forbidden")]
        return []

    def k_if(self, value, condition, schema, where, at):
        base = at[:-1]
        if self.passes(value, condition, where, at):
            return self.check(value, schema["then"], where, base + ["then"]) if "then" in schema else []
        return self.check(value, schema["else"], where, base + ["else"]) if "else" in schema else []

    # -- objects ------------------------------------------------------------
    def k_required(self, value, names, schema, where, at):
        if not isinstance(value, dict):
            return []
        return [self.violation(where, at, "required", f"missing required property {name!r}")
                for name in names if name not in value]

    def k_properties(self, value, properties, schema, where, at):
        if not isinstance(value, dict):
            return []
        found = []
        for name, inner in properties.items():
            if name in value:
                found += self.check(value[name], inner, where + [name], at + [name])
        return found

    def k_patternProperties(self, value, patterns, schema, where, at):
        if not isinstance(value, dict):
            return []
        found = []
        for text, inner in patterns.items():
            compiled = self.patterns[text]
            for name, item in value.items():
                if compiled.search(name):
                    found += self.check(item, inner, where + [name], at + [text])
        return found

    def k_additionalProperties(self, value, inner, schema, where, at):
        if not isinstance(value, dict):
            return []
        known = set(schema.get("properties", {}))
        patterns = [self.patterns[text] for text in schema.get("patternProperties", {})]
        found = []
        for name, item in value.items():
            if name in known or any(compiled.search(name) for compiled in patterns):
                continue
            if inner is False:
                found.append(self.violation(where + [name], at, "additionalProperties",
                                            f"property {name[:60]!r} is not allowed here"))
            else:
                found += self.check(item, inner, where + [name], at)
        return found

    def k_propertyNames(self, value, inner, schema, where, at):
        if not isinstance(value, dict):
            return []
        found = []
        for name in value:
            problems = self.check(name, inner, where + [name], at)
            if problems:
                found.append(self.violation(where + [name], at, "propertyNames",
                                            f"property name {name[:60]!r} is not allowed: {problems[0]['message']}"))
        return found

    def k_minProperties(self, value, limit, schema, where, at):
        if isinstance(value, dict) and len(value) < limit:
            return [self.violation(where, at, "minProperties", f"has {len(value)} properties, fewer than {limit}")]
        return []

    def k_maxProperties(self, value, limit, schema, where, at):
        if isinstance(value, dict) and len(value) > limit:
            return [self.violation(where, at, "maxProperties", f"has {len(value)} properties, more than {limit}")]
        return []

    def k_dependentRequired(self, value, rules, schema, where, at):
        if not isinstance(value, dict):
            return []
        return [self.violation(where, at + [name], "dependentRequired",
                               f"property {name!r} needs property {other!r}")
                for name, others in rules.items() if name in value for other in others if other not in value]

    def k_dependentSchemas(self, value, rules, schema, where, at):
        if not isinstance(value, dict):
            return []
        found = []
        for name, inner in rules.items():
            if name in value:
                found += self.check(value, inner, where, at + [name])
        return found

    def k_dependencies(self, value, rules, schema, where, at):
        if not isinstance(value, dict):
            return []
        found = []
        for name, rule in rules.items():
            if name not in value:
                continue
            if isinstance(rule, list):
                found += [self.violation(where, at + [name], "dependencies",
                                         f"property {name!r} needs property {other!r}")
                          for other in rule if other not in value]
            else:
                found += self.check(value, rule, where, at + [name])
        return found

    # -- arrays -------------------------------------------------------------
    def k_prefixItems(self, value, schemas, schema, where, at):
        if not isinstance(value, list):
            return []
        found = []
        for index, inner in enumerate(schemas[:len(value)]):
            found += self.check(value[index], inner, where + [index], at + [index])
        return found

    def k_items(self, value, inner, schema, where, at):
        if not isinstance(value, list):
            return []
        found = []
        if isinstance(inner, list):
            for index, item_schema in enumerate(inner[:len(value)]):
                found += self.check(value[index], item_schema, where + [index], at + [index])
            return found
        start = len(schema.get("prefixItems", [])) if self.draft == DRAFT_2020 else 0
        for index in range(start, len(value)):
            found += self.check(value[index], inner, where + [index], at)
        return found

    def k_additionalItems(self, value, inner, schema, where, at):
        if not isinstance(value, list) or not isinstance(schema.get("items"), list):
            return []
        found = []
        for index in range(len(schema["items"]), len(value)):
            found += self.check(value[index], inner, where + [index], at)
        return found

    def k_minItems(self, value, limit, schema, where, at):
        if isinstance(value, list) and len(value) < limit:
            return [self.violation(where, at, "minItems", f"has {len(value)} items, fewer than {limit}")]
        return []

    def k_maxItems(self, value, limit, schema, where, at):
        if isinstance(value, list) and len(value) > limit:
            return [self.violation(where, at, "maxItems", f"has {len(value)} items, more than {limit}")]
        return []

    def k_uniqueItems(self, value, required, schema, where, at):
        if not required or not isinstance(value, list):
            return []
        first: dict = {}
        for index, item in enumerate(value):
            key = canonical(item)
            if key in first:
                return [self.violation(where, at, "uniqueItems", f"items {first[key]} and {index} are equal")]
            first[key] = index
        return []

    def k_contains(self, value, inner, schema, where, at):
        if not isinstance(value, list):
            return []
        matches = sum(1 for index, item in enumerate(value) if self.passes(item, inner, where + [index], at))
        low = schema.get("minContains", 1) if self.draft == DRAFT_2020 else 1
        high = schema.get("maxContains") if self.draft == DRAFT_2020 else None
        if matches < low:
            return [self.violation(where, at, "contains", f"{matches} items match contains, fewer than {low}")]
        if high is not None and matches > high:
            return [self.violation(where, at, "contains", f"{matches} items match contains, more than {high}")]
        return []

    # -- strings ------------------------------------------------------------
    def k_minLength(self, value, limit, schema, where, at):
        if isinstance(value, str) and len(value) < limit:
            return [self.violation(where, at, "minLength", f"text has {len(value)} characters, fewer than {limit}")]
        return []

    def k_maxLength(self, value, limit, schema, where, at):
        if isinstance(value, str) and len(value) > limit:
            return [self.violation(where, at, "maxLength", f"text has {len(value)} characters, more than {limit}")]
        return []

    def k_pattern(self, value, text, schema, where, at):
        if isinstance(value, str) and not self.patterns[text].search(value):
            return [self.violation(where, at, "pattern", f"{shown(value)} does not match the pattern {text[:80]}")]
        return []

    def k_format(self, value, name, schema, where, at):
        if self.check_formats and isinstance(value, str) and not valid_format(name, value):
            return [self.violation(where, at, "format", f"{shown(value)} is not a valid {name}")]
        return []

    # -- numbers ------------------------------------------------------------
    def compare(self, value, limit, keyword, where, at, failed, words):
        if is_number(value) and failed(value, limit):
            return [self.violation(where, at, keyword, f"{shown(value)} is {words} {shown(limit)}")]
        return []

    def k_minimum(self, value, limit, schema, where, at):
        return self.compare(value, limit, "minimum", where, at, lambda a, b: a < b, "less than the minimum")

    def k_maximum(self, value, limit, schema, where, at):
        return self.compare(value, limit, "maximum", where, at, lambda a, b: a > b, "more than the maximum")

    def k_exclusiveMinimum(self, value, limit, schema, where, at):
        return self.compare(value, limit, "exclusiveMinimum", where, at, lambda a, b: a <= b,
                            "not above the exclusive minimum")

    def k_exclusiveMaximum(self, value, limit, schema, where, at):
        return self.compare(value, limit, "exclusiveMaximum", where, at, lambda a, b: a >= b,
                            "not below the exclusive maximum")

    def k_multipleOf(self, value, step, schema, where, at):
        if not is_number(value):
            return []
        try:
            ratio = exact_number(value) / exact_number(step)
        except (InvalidOperation, ValueError, OverflowError, ZeroDivisionError):
            return [self.violation(where, at, "multipleOf", f"{shown(value)} cannot be checked against {step}")]
        if ratio.denominator != 1:
            return [self.violation(where, at, "multipleOf", f"{shown(value)} is not a multiple of {shown(step)}")]
        return []


# ---------------------------------------------------------------------------
# The tool
# ---------------------------------------------------------------------------

def load_schema(arguments: dict, context: Context):
    if ("schema" in arguments) == ("schema_path" in arguments):
        raise Refusal("Give exactly one of schema (inline) or schema_path (a file).")
    if "schema" in arguments:
        return arguments["schema"], {"source": "inline"}
    text, digest = read_text(context.root, arguments["schema_path"], MAX_SCHEMA_BYTES)
    schema = strict_parse(text, "The schema file")
    if not isinstance(schema, (dict, bool)):
        raise Refusal("The schema file must hold one JSON object (or true or false).")
    return schema, {"source": arguments["schema_path"], "sha256": digest}


def load_documents(arguments: dict, context: Context):
    if ("document" in arguments) == ("document_path" in arguments):
        raise Refusal("Give exactly one of document (inline) or document_path (a file).")
    if "document" in arguments:
        if arguments.get("jsonl"):
            raise Refusal("jsonl applies to document_path only.")
        if depth_of(arguments["document"]) > MAX_DEPTH:
            raise Refusal(f"The document is nested more than {MAX_DEPTH} levels deep.")
        return [(None, arguments["document"])], {"source": "inline", "format": "json"}
    text, digest = read_text(context.root, arguments["document_path"], MAX_DOCUMENT_BYTES)
    info = {"source": arguments["document_path"], "sha256": digest, "format": "jsonl" if arguments.get("jsonl") else "json"}
    if not arguments.get("jsonl"):
        return [(None, strict_parse(text, "The document"))], info
    documents = []
    for number, line in enumerate(text.split("\n"), start=1):
        if line.strip():
            documents.append((number, strict_parse(line, f"Line {number} of the document")))
    if not documents:
        raise Refusal("The JSON Lines file holds no documents.")
    return documents, info


def draft_of(schema) -> str:
    declared = schema.get("$schema") if isinstance(schema, dict) else None
    if declared is None:
        return DRAFT_2020
    draft = SCHEMA_URIS.get(str(declared).rstrip("#"))
    if draft is None:
        raise Refusal(f"The schema declares $schema {str(declared)[:100]!r}. This tool supports draft 2020-12 and "
                      "draft-07.")
    return draft


def check_json_schema(arguments: dict, context: Context) -> dict:
    schema, schema_info = load_schema(arguments, context)
    documents, document_info = load_documents(arguments, context)
    draft = draft_of(schema)
    scan = SchemaScan(schema, draft)
    scan.scan()
    if scan.problems:
        raise Refusal("The schema itself is not well formed.", schema_problems=scan.problems[:30])
    if scan.unchecked and not arguments.get("allow_unchecked", False):
        raise Refusal("The schema uses keywords this tool does not check. Fix a mistyped keyword, or call again "
                      "with allow_unchecked true to check everything else.", unchecked=scan.unchecked[:50])
    validator = Validator(scan, arguments.get("check_formats", True))
    limit = int(arguments.get("max_violations", 100))
    shown_violations, total = [], 0
    for line, document in documents:
        for item in validator.check(document, schema, [], []):
            total += 1
            if len(shown_violations) < limit:
                shown_violations.append({"line": line, **item} if line is not None else item)
    result = {
        "valid": total == 0,
        "documents_checked": len(documents),
        "violation_count": total,
        "violations": shown_violations,
        "more_violations": total > len(shown_violations),
        "schema": {**schema_info, "draft": draft},
        "document": document_info,
        "formats_checked": bool(arguments.get("check_formats", True)),
        "unchecked": scan.unchecked[:50],
        "notes": ["instance_path points into the document and schema_path into the schema, as JSON Pointers.",
                  "Patterns follow ECMA-262, the dialect JSON Schema names for them: $ matches only at the end, "
                  ". stops at line breaks, \\s includes no-break and other Unicode spaces, and \\d and \\w are "
                  "ASCII. Forms Python cannot run the same way, such as \\p{...} and backreferences, are refused "
                  "when the schema is read."],
    }
    if scan.unchecked:
        result["notes"].append("valid covers the checked keywords only; see unchecked.")
    return result


def run_with_time_limit(seconds: int, function, *arguments):
    if not hasattr(signal, "setitimer"):
        return function(*arguments)

    def expire(signum, frame):
        raise TimeLimit()

    previous = signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return function(*arguments)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


# ---------------------------------------------------------------------------
# Arguments of the tool call
# ---------------------------------------------------------------------------

def argument_problems(arguments: dict) -> list[str]:
    """Checks the tool arguments against INPUT_SCHEMA with the validator above."""
    scan = SchemaScan(INPUT_SCHEMA, DRAFT_2020)
    scan.scan()
    problems = []
    for item in Validator(scan, True).check(arguments, INPUT_SCHEMA, [], []):
        where = item["instance_path"].lstrip("/") or "arguments"
        problems.append(f"{where}: {item['message']}")
    return problems


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


def call_tool(ident, params: dict, context: Context) -> dict:
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
    problems = argument_problems(arguments)
    if problems:
        return tool_answer(ident, {"error": "The arguments do not match the input schema.",
                                   "problems": problems[:20]}, True)
    try:
        return tool_answer(ident, run_with_time_limit(context.time_limit, check_json_schema, arguments, context), False)
    except Refusal as refusal:
        return tool_answer(ident, refusal.payload, True)
    except TimeLimit:
        return tool_answer(ident, {"error": f"The check passed the time limit of {context.time_limit} seconds, "
                                            "often because a pattern backtracks too much. Simplify the pattern or "
                                            "check a smaller document."}, True)
    except (MemoryError, RecursionError):
        return tool_answer(ident, {"error": "The check needs more memory or depth than this server has. "
                                            + NARROWING_HINT}, True)
    except Exception as error:  # noqa: BLE001 - a defect must not stop the server
        print(f"{SERVER_NAME}: unexpected {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        return tool_answer(ident, {"error": f"Unexpected internal error ({type(error).__name__}). "
                                            "Report it and do not repeat the same call."}, True)


def handle(message, context: Context):
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
        return call_tool(ident, params, context)
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


def serve(context: Context) -> int:
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
        answer = handle(message, context)
        if answer is not None:
            send(answer)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Local JSON schema check tool server (standard input and output).")
    parser.add_argument("--root", default=".", help="folder that every path argument is resolved under")
    parser.add_argument("--time-limit-seconds", type=int, default=TIME_LIMIT_SECONDS,
                        help="stop one check after this many seconds (1 to 300)")
    options = parser.parse_args(argv)
    if not 1 <= options.time_limit_seconds <= 300:
        print(f"{SERVER_NAME}: --time-limit-seconds must be between 1 and 300", file=sys.stderr)
        return 2
    try:
        root = Path(options.root).resolve(strict=True)
    except (OSError, RuntimeError):
        print(f"{SERVER_NAME}: --root {options.root!r} does not exist", file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"{SERVER_NAME}: --root {options.root!r} is not a folder", file=sys.stderr)
        return 2
    try:
        return serve(Context(root, options.time_limit_seconds))
    except (BrokenPipeError, KeyboardInterrupt):
        return 0


if __name__ == "__main__":
    sys.exit(main())
