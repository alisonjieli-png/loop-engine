"""Reads CSV files under --root and answers tool calls on standard input and output; writes no file, opens no network connection and starts no process.

csv_profile_server is a small local Model Context Protocol server. It reads
newline-delimited JSON-RPC 2.0 messages on standard input, writes one answer
line for each request on standard output and writes diagnostics only to
standard error. It stops when standard input closes.

Tool: profile_csv. For each column of one CSV file it reports the inferred
type, empty and distinct counts, the most common values and character shapes,
and the values that break the dominant type, with their line numbers. With
include_values false it leaves out common values, examples and the numeric
range, and a shape shows no letter or digit of the data.

Python 3.10 or later, standard library only. Licence: MIT.
"""
from __future__ import annotations

import argparse
import codecs
import csv
import datetime
import hashlib
import io
import json
import os
import re
import stat
import string
import sys
import unicodedata
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path, PureWindowsPath

SERVER_NAME = "csv_profile_server"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26")
MAX_LINE_BYTES = 1024 * 1024
# One answer line holds the result twice (escaped text and structured copy); the whole line stays within 256 KiB.
MAX_ANSWER_BYTES = 256 * 1024
DEFAULT_MAX_FILE_MIB = 64
MAX_COLUMNS_PER_CALL = 100
HEADER_NAMES_SHOWN = 300
TRACKED_VALUE_BUDGET = 200_000
LONG_VALUE_CHARS = 200
DISPLAY_CHARS = 60
SHAPE_MAX_CHARS = 40
SHAPE_BUDGET = 1000
EXAMPLES_PER_COLUMN = 5
SNIFF_BYTES = 64 * 1024

TOOL_NAME = "profile_csv"
INPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "path": {
            "type": "string", "minLength": 1, "maxLength": 1024,
            "description": "CSV file path relative to the workspace root, for example data/orders.csv. "
                           "Absolute paths, '..' and links that leave the root are refused."},
        "delimiter": {
            "type": "string", "enum": ["auto", ",", ";", "\t", "|"], "default": "auto",
            "description": "Field separator. auto picks the one that gives the most rows of equal width."},
        "encoding": {
            "type": "string", "enum": ["utf-8", "latin-1", "cp1252"], "default": "utf-8",
            "description": "Text encoding. utf-8 also accepts a byte order mark."},
        "has_header": {
            "type": "boolean", "default": True,
            "description": "true when the first row holds column names. When false, columns are named column_1, column_2 and so on."},
        "columns": {
            "type": "array", "minItems": 1, "maxItems": MAX_COLUMNS_PER_CALL, "uniqueItems": True,
            "items": {"type": "string", "minLength": 1, "maxLength": 256},
            "description": "Profile only these column names. Needed when the file has more than 100 columns."},
        "top_values": {
            "type": "integer", "minimum": 0, "maximum": 20, "default": 5,
            "description": "How many of the most common values to list for each column."},
        "include_values": {
            "type": "boolean", "default": True,
            "description": "false leaves out common values, examples and the numeric range, and keeps counts, types and "
                           "shapes. A shape writes each letter of any script as A or a, each digit as 9 and each other "
                           "character as _, except ASCII punctuation and spaces, which stay visible."},
        "max_rows": {
            "type": "integer", "minimum": 1, "maximum": 100000000,
            "description": "Read only the first max_rows data rows. The answer then says complete false. Default: every row."},
    },
    "required": ["path"],
    "additionalProperties": False,
}
TOOL = {
    "name": TOOL_NAME,
    "description": (
        "Profile the columns of one CSV file under the workspace root. For each column it returns the inferred "
        "type (integer, decimal, boolean, date, datetime, text, empty or mixed), empty and distinct counts, the "
        "most common values and character shapes, and for a mixed column the values and line numbers that break "
        "the dominant type. It reads the file and changes nothing. Files above the size limit (64 MiB unless "
        "the host set another) are refused."),
    "inputSchema": INPUT_SCHEMA,
    "annotations": {"title": "Profile CSV columns", "readOnlyHint": True, "destructiveHint": False,
                    "idempotentHint": True, "openWorldHint": False},
}
INSTRUCTIONS = "Call profile_csv with a CSV path relative to the workspace root. It reads the file and changes nothing."
NARROWING_HINT = "Pass fewer names in columns or a smaller top_values."

TYPE_ORDER = ("integer", "decimal", "boolean", "date", "datetime", "text")
INTEGER = re.compile(r"[+-]?[0-9]+\Z")
DECIMAL = re.compile(r"[+-]?(?:[0-9]+\.[0-9]*|\.[0-9]+|[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
DATE = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})\Z")
DATETIME = re.compile(r"([0-9]{4})-([0-9]{2})-([0-9]{2})[Tt ]([0-9]{2}):([0-9]{2})(?::([0-9]{2})(?:\.[0-9]{1,9})?)?"
                      r"(?:[Zz]|[+-][0-9]{2}:?[0-9]{2})?\Z")
BOOLEAN_WORDS = frozenset({"true", "false", "yes", "no"})
SHAPE_KEPT = frozenset(string.punctuation + " ")


class ShapeTable(dict):
    """Table for str.translate that turns a value into its shape, for letters and digits of every script.

    An upper-case or title-case letter becomes A, any other letter a, any decimal digit 9. ASCII punctuation and
    the space stay as they are. Every other character (other spaces, marks, symbols, controls) becomes _. So no
    letter or digit of a value appears in its shape.
    """

    def __missing__(self, code: int) -> str:
        character = chr(code)
        category = unicodedata.category(character)
        if category in ("Lu", "Lt"):
            shape = "A"
        elif category.startswith("L"):
            shape = "a"
        elif category == "Nd":
            shape = "9"
        elif character in SHAPE_KEPT:
            shape = character
        else:
            shape = "_"
        self[code] = shape
        return shape


SHAPE_TABLE = ShapeTable()


class Refusal(Exception):
    """A tool-level refusal. The answer carries isError true and this message."""

    def __init__(self, message: str, **details) -> None:
        super().__init__(message)
        self.payload = {"error": message, **details}


class Context:
    def __init__(self, root: Path, max_file_bytes: int) -> None:
        self.root = root
        self.max_file_bytes = max_file_bytes


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
# Files
# ---------------------------------------------------------------------------

def resolve_file(root: Path, relative: str):
    """Resolves a relative path under root; refuses '..', absolute paths and links that leave root."""
    if "\x00" in relative:
        raise Refusal("The path holds a NUL character.")
    if Path(relative).is_absolute() or PureWindowsPath(relative).anchor:
        raise Refusal("Give the path relative to the workspace root, for example data/orders.csv. "
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
    info = resolved.stat()
    if not stat.S_ISREG(info.st_mode):
        raise Refusal(f"{relative!r} is not a regular file.")
    return resolved, info


def read_bounded(path: Path, limit: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise Refusal(f"The file cannot be opened ({type(error).__name__}).") from None
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise Refusal("The path is not a regular file.")
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise Refusal(f"The file is larger than this server's limit of {limit} bytes.")
    return data


# ---------------------------------------------------------------------------
# Profiling
# ---------------------------------------------------------------------------

def classify(text: str) -> str:
    """Type of one stripped, nonempty value."""
    if INTEGER.fullmatch(text):
        return "integer"
    if DECIMAL.fullmatch(text):
        return "decimal"
    if text.casefold() in BOOLEAN_WORDS:
        return "boolean"
    match = DATE.fullmatch(text)
    if match:
        return "date" if real_date(match) else "text"
    match = DATETIME.fullmatch(text)
    if match and real_date(match):
        hour, minute, second = int(match.group(4)), int(match.group(5)), int(match.group(6) or 0)
        if hour < 24 and minute < 60 and second < 60:
            return "datetime"
    return "text"


def real_date(match) -> bool:
    try:
        datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return False
    return True


def conforms(value_type: str, dominant: str) -> bool:
    return value_type == dominant or (dominant == "decimal" and value_type == "integer")


def display(value: str) -> dict:
    shown = {"value": value[:DISPLAY_CHARS]}
    if len(value) > DISPLAY_CHARS:
        shown["chars"] = len(value)
    return shown


class ColumnProfile:
    def __init__(self, name: str, index: int, cap: int) -> None:
        self.name, self.index, self.cap = name, index, cap
        self.non_empty = self.empty = self.missing_field = self.padded = self.leading_zero = self.long_text = 0
        self.values: dict = {}
        self.overflow = False
        self.type_counts = dict.fromkeys(TYPE_ORDER, 0)
        self.examples: dict[str, list] = {name: [] for name in TYPE_ORDER}
        self.shapes: dict[str, int] = {}
        self.shape_overflow = False
        self.min_length = self.max_length = None
        self.low = self.high = None
        self.low_text = self.high_text = ""

    def add(self, raw: str, line: int) -> None:
        text = raw.strip()
        if not text:
            self.empty += 1
            return
        self.non_empty += 1
        if text != raw:
            self.padded += 1
        key = raw if len(raw) <= LONG_VALUE_CHARS else ("long", len(raw), hashlib.blake2b(
            raw.encode("utf-8", "surrogatepass"), digest_size=16).digest())
        entry = self.values.get(key)
        if entry is not None:
            entry[0] += 1
            self.type_counts[entry[1]] += 1
            self.leading_zero += entry[6]
            if entry[3] is not None:
                self.count_shape(entry[3])
            else:
                self.long_text += 1
            return
        value_type = classify(text)
        shape = text.translate(SHAPE_TABLE) if len(text) <= SHAPE_MAX_CHARS else None
        digits = text.lstrip("+-")
        leading_zero = int(value_type == "integer" and len(digits) > 1 and digits[0] == "0")
        if len(self.values) < self.cap:
            self.values[key] = [1, value_type, line, shape, raw[:DISPLAY_CHARS], len(raw), leading_zero]
        else:
            self.overflow = True
        self.type_counts[value_type] += 1
        self.leading_zero += leading_zero
        if shape is not None:
            self.count_shape(shape)
        else:
            self.long_text += 1
        self.first_sight(raw, text, value_type, line)

    def count_shape(self, shape: str) -> None:
        if shape in self.shapes:
            self.shapes[shape] += 1
        elif len(self.shapes) < SHAPE_BUDGET:
            self.shapes[shape] = 1
        else:
            self.shape_overflow = True

    def first_sight(self, raw: str, text: str, value_type: str, line: int) -> None:
        """Updates the statistics that only depend on distinct values."""
        length = len(raw)
        self.min_length = length if self.min_length is None else min(self.min_length, length)
        self.max_length = length if self.max_length is None else max(self.max_length, length)
        examples = self.examples[value_type]
        if len(examples) < EXAMPLES_PER_COLUMN and all(item[1] != raw for item in examples):
            examples.append((line, raw))
        if value_type in ("integer", "decimal"):
            try:
                number = Decimal(text)
            except (InvalidOperation, ValueError):
                return
            if self.low is None or number < self.low:
                self.low, self.low_text = number, text
            if self.high is None or number > self.high:
                self.high, self.high_text = number, text

    def summary(self, top_values: int, include_values: bool) -> dict:
        counted = {name: count for name, count in self.type_counts.items() if count}
        effective = {name: count + (self.type_counts["integer"] if name == "decimal" else 0)
                     for name, count in counted.items()}
        if not effective:
            inferred, dominant, share = "empty", None, None
        else:
            dominant = max(TYPE_ORDER, key=lambda name: (effective.get(name, 0), -TYPE_ORDER.index(name)))
            conforming = effective[dominant]
            share = round(conforming / self.non_empty, 4)
            inferred = dominant if conforming == self.non_empty else "mixed"
        odd = []
        if dominant is not None:
            for name in TYPE_ORDER:
                if not conforms(name, dominant):
                    odd.extend(self.examples[name])
            odd.sort()
        result = {
            "name": self.name, "index": self.index,
            "non_empty": self.non_empty, "empty": self.empty, "missing_field": self.missing_field,
            "whitespace_padded": self.padded,
            "distinct": len(self.values), "distinct_exact": not self.overflow,
            "inferred_type": inferred, "dominant_type": dominant, "dominant_share": share,
            "type_counts": counted,
            "nonconforming_examples": [
                ({"line": line, **display(raw)} if include_values else {"line": line})
                for line, raw in odd[:EXAMPLES_PER_COLUMN]],
            "top_shapes": [{"shape": shape, "count": count} for shape, count in
                           sorted(self.shapes.items(), key=lambda item: (-item[1], item[0]))[:3]],
            "shapes_exact": not self.shape_overflow,
            "long_text_values": self.long_text,
            "length_range": None if self.min_length is None else [self.min_length, self.max_length],
            "leading_zero_integers": self.leading_zero,
        }
        if include_values:
            ranked = sorted(self.values.values(), key=lambda entry: (-entry[0], entry[2]))[:top_values]
            result["top_values"] = [{**({"value": entry[4]} if entry[5] <= DISPLAY_CHARS else
                                        {"value": entry[4], "chars": entry[5]}), "count": entry[0]}
                                    for entry in ranked]
            result["top_values_exact"] = not self.overflow
            result["numeric_range"] = None if self.low is None else [self.low_text, self.high_text]
        return result


def detect_delimiter(sample: str) -> str:
    best, best_score = ",", None
    for candidate in (",", ";", "\t", "|"):
        try:
            widths = [len(row) for row in csv.reader(io.StringIO(sample), delimiter=candidate) if row][:200]
        except csv.Error:
            continue
        if widths[1:]:
            widths = widths[:-1]  # the sample may end inside the last record
        if not widths:
            continue
        common = max(sorted(set(widths)), key=widths.count)
        score = (common > 1, widths.count(common), common)
        if best_score is None or score > best_score:
            best, best_score = candidate, score
    return best if best_score and best_score[0] else ","


def profile_csv(arguments: dict, context: Context) -> dict:
    relative = arguments["path"]
    encoding = arguments.get("encoding", "utf-8")
    delimiter = arguments.get("delimiter", "auto")
    has_header = arguments.get("has_header", True)
    wanted = arguments.get("columns")
    top_values = int(arguments.get("top_values", 5))
    include_values = arguments.get("include_values", True)
    max_rows = int(arguments["max_rows"]) if "max_rows" in arguments else None

    path, info = resolve_file(context.root, relative)
    if info.st_size > context.max_file_bytes:
        raise Refusal(f"The file is {info.st_size} bytes, above this server's limit of {context.max_file_bytes} bytes. "
                      "Profile a smaller extract or ask the host to raise --max-file-mib.")
    data = read_bounded(path, context.max_file_bytes)
    if not data.strip():
        raise Refusal("The file is empty.")
    codec = "utf-8-sig" if encoding == "utf-8" else encoding
    byte_order_mark = data.startswith(codecs.BOM_UTF8) and encoding == "utf-8"
    detected = delimiter == "auto"
    if detected:
        sample = codecs.getincrementaldecoder(codec)(errors="replace").decode(data[:SNIFF_BYTES], final=False)
        delimiter = detect_delimiter(sample)
    stream = io.TextIOWrapper(io.BytesIO(data), encoding=codec, errors="strict", newline="")
    cursor = RecordCursor(csv.reader(stream, delimiter=delimiter, quotechar='"', doublequote=True, strict=False))

    blank_lines = rows = 0
    width_lines: list[int] = []
    missing_rows = extra_rows = 0
    complete = True
    columns: list[ColumnProfile] = []
    header: list[str] = []
    try:
        first = None
        for start, record in cursor:
            if record:
                first = (start, record)
                break
            blank_lines += 1
        if first is None:
            raise Refusal("The file holds no rows.")
        if has_header:
            header = first[1]
        else:
            header = [f"column_{number}" for number in range(1, len(first[1]) + 1)]
        selected = select_columns(header, wanted)
        cap = max(1000, min(50_000, TRACKED_VALUE_BUDGET // max(1, len(selected))))
        columns = [ColumnProfile(header[index], index, cap) for index in selected]
        width = len(header)
        for start, record in data_records(first, cursor, has_header):
            if not record:
                blank_lines += 1
                continue
            if max_rows is not None and rows >= max_rows:
                complete = False
                break
            rows += 1
            if len(record) != width:
                if len(record) < width:
                    missing_rows += 1
                else:
                    extra_rows += 1
                if len(width_lines) < 10:
                    width_lines.append(start)
            for column in columns:
                if column.index < len(record):
                    column.add(record[column.index], start)
                else:
                    column.missing_field += 1
    except UnicodeDecodeError:
        raise Refusal(f"The file is not valid {encoding} at line {decode_error_line(data, codec)}. "
                      "Pass the right encoding (latin-1 or cp1252) or convert the file first.") from None
    except csv.Error as error:
        raise Refusal(f"The CSV reader stopped at the record that starts on line {cursor.start}: {error}.") from None

    duplicates = sorted(name for name, count in Counter(header).items() if count > 1)
    result = {
        "file": {"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                 "encoding": encoding, "byte_order_mark": byte_order_mark,
                 "delimiter": delimiter, "delimiter_detected": detected, "has_header": has_header},
        "rows_profiled": rows,
        "complete": complete,
        "blank_lines": blank_lines,
        "column_count": len(header),
        "header": header[:HEADER_NAMES_SHOWN] if has_header else None,
        "duplicate_header_names": duplicates,
        "width_problems": {"rows_with_missing_fields": missing_rows, "rows_with_extra_fields": extra_rows,
                           "first_lines": width_lines},
        "include_values": include_values,
        "columns": [column.summary(top_values, include_values) for column in columns],
        "notes": [
            "line is the physical line where a record starts; the header is line 1 when has_header is true.",
            "Types come from the text: integer and decimal use digits with an optional sign, point and "
            "exponent; date is YYYY-MM-DD; datetime is YYYY-MM-DD then a time; boolean is true, false, yes or no.",
            "In a shape, A is an upper-case letter, a any other letter and 9 any decimal digit (digits of other "
            "scripts too, which the type rules count as text); ASCII punctuation and spaces stay as they are, and "
            "every other character becomes _.",
        ],
    }
    if not complete:
        result["notes"].append(f"Only the first {rows} data rows were read because max_rows was given; "
                               "counts do not cover the whole file.")
    return result


class RecordCursor:
    """Yields (line where the record starts, record) and remembers the start of the record being read."""

    def __init__(self, reader) -> None:
        self.reader = reader
        self.start = 1

    def __iter__(self):
        return self

    def __next__(self):
        self.start = self.reader.line_num + 1
        return self.start, next(self.reader)


def data_records(first, cursor: RecordCursor, has_header: bool):
    if not has_header:
        yield first
    yield from cursor


def decode_error_line(data: bytes, codec: str) -> int:
    try:
        data.decode(codec)
    except UnicodeDecodeError as error:
        return data.count(b"\n", 0, error.start) + 1
    return 1


def select_columns(header: list[str], wanted) -> list[int]:
    if wanted is None:
        if len(header) > MAX_COLUMNS_PER_CALL:
            raise Refusal(f"The file has {len(header)} columns; pass at most {MAX_COLUMNS_PER_CALL} names in "
                          "columns and call again for the rest.",
                          column_count=len(header), header=header[:HEADER_NAMES_SHOWN])
        return list(range(len(header)))
    exact: dict[str, list[int]] = {}
    folded: dict[str, list[int]] = {}
    for index, item in enumerate(header):
        exact.setdefault(item, []).append(index)
        folded.setdefault(item.strip().casefold(), []).append(index)
    chosen: list[int] = []
    taken: set[int] = set()
    unknown = []
    for name in wanted:
        matches = exact.get(name) or folded.get(name.strip().casefold(), [])
        if not matches:
            unknown.append(name)
        for index in matches:
            if index not in taken:
                taken.add(index)
                chosen.append(index)
    if unknown:
        raise Refusal(f"These column names are not in the header: {unknown[:10]}.",
                      header=header[:HEADER_NAMES_SHOWN])
    if len(chosen) > MAX_COLUMNS_PER_CALL:
        raise Refusal(f"The names match {len(chosen)} columns; at most {MAX_COLUMNS_PER_CALL} fit in one call.")
    return chosen


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
    problems = argument_problems(INPUT_SCHEMA, arguments, "arguments")
    if problems:
        return tool_answer(ident, {"error": "The arguments do not match the input schema.",
                                   "problems": problems[:20]}, True)
    try:
        return tool_answer(ident, profile_csv(arguments, context), False)
    except Refusal as refusal:
        return tool_answer(ident, refusal.payload, True)
    except MemoryError:
        return tool_answer(ident, {"error": "The file needs more memory than this server has. " + NARROWING_HINT}, True)
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
    parser = argparse.ArgumentParser(description="Local CSV profile tool server (standard input and output).")
    parser.add_argument("--root", default=".", help="folder that every path argument is resolved under")
    parser.add_argument("--max-file-mib", type=int, default=DEFAULT_MAX_FILE_MIB,
                        help="largest CSV file to read, in MiB (1 to 1024)")
    options = parser.parse_args(argv)
    if not 1 <= options.max_file_mib <= 1024:
        print(f"{SERVER_NAME}: --max-file-mib must be between 1 and 1024", file=sys.stderr)
        return 2
    try:
        root = Path(options.root).resolve(strict=True)
    except (OSError, RuntimeError):
        print(f"{SERVER_NAME}: --root {options.root!r} does not exist", file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"{SERVER_NAME}: --root {options.root!r} is not a folder", file=sys.stderr)
        return 2
    csv.field_size_limit(16 * 1024 * 1024)
    try:
        return serve(Context(root, options.max_file_mib * 1024 * 1024))
    except (BrokenPipeError, KeyboardInterrupt):
        return 0


if __name__ == "__main__":
    sys.exit(main())
