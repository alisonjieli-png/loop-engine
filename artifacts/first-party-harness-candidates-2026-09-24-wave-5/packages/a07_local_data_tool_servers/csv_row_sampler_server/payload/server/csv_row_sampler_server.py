"""Reads CSV files under --root and answers tool calls on standard input and output; writes no file, opens no network connection and starts no process.

csv_row_sampler_server is a small local Model Context Protocol server. It reads
newline-delimited JSON-RPC 2.0 messages on standard input, writes one answer
line for each request on standard output and writes diagnostics only to
standard error. It stops when standard input closes.

Tool: sample_csv_rows. It returns a seeded, bounded sample of rows from one
CSV file, either overall or a fixed number for each value of one column, so a
model sees representative rows instead of the first rows of a sorted file.
The same file, seed and arguments give the same rows: the choice draws only
from random(), whose sequence Python documents as stable for the same integer
seed across versions (checked here on Python 3.10 and 3.14).

Python 3.10 or later, standard library only. Licence: MIT.
"""
from __future__ import annotations

import argparse
import codecs
import csv
import hashlib
import io
import json
import os
import random
import stat
import sys
from pathlib import Path, PureWindowsPath

SERVER_NAME = "csv_row_sampler_server"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26")
MAX_LINE_BYTES = 1024 * 1024
# One answer line holds the result twice (escaped text and structured copy); the whole line stays within 256 KiB.
MAX_ANSWER_BYTES = 256 * 1024
DEFAULT_MAX_FILE_MIB = 64
MAX_RETURNED_ROWS = 500
SHORTENED_CELLS_LISTED = 100
HEADER_NAMES_SHOWN = 300
SNIFF_BYTES = 64 * 1024

TOOL_NAME = "sample_csv_rows"
INPUT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "path": {
            "type": "string", "minLength": 1, "maxLength": 1024,
            "description": "CSV file path relative to the workspace root, for example data/orders.csv. "
                           "Absolute paths, '..' and links that leave the root are refused."},
        "rows": {
            "type": "integer", "minimum": 1, "maximum": 200, "default": 20,
            "description": "How many rows to return when group_by is not given."},
        "seed": {
            "type": "integer", "minimum": 0, "maximum": 2147483647, "default": 0,
            "description": "Seed of the random choice. The same file, seed and arguments give the same rows."},
        "group_by": {
            "type": "string", "minLength": 1, "maxLength": 256,
            "description": "Column name. When given, return up to per_group rows for each distinct value of it."},
        "per_group": {
            "type": "integer", "minimum": 1, "maximum": 50, "default": 3,
            "description": "Rows for each value of group_by."},
        "max_groups": {
            "type": "integer", "minimum": 1, "maximum": 200, "default": 50,
            "description": "Refuse when group_by has more distinct values than this."},
        "columns": {
            "type": "array", "minItems": 1, "maxItems": 100, "uniqueItems": True,
            "items": {"type": "string", "minLength": 1, "maxLength": 256},
            "description": "Return only these columns. The group_by column is always returned."},
        "delimiter": {
            "type": "string", "enum": ["auto", ",", ";", "\t", "|"], "default": "auto",
            "description": "Field separator. auto picks the one that gives the most rows of equal width."},
        "encoding": {
            "type": "string", "enum": ["utf-8", "latin-1", "cp1252"], "default": "utf-8",
            "description": "Text encoding. utf-8 also accepts a byte order mark."},
        "has_header": {
            "type": "boolean", "default": True,
            "description": "true when the first row holds column names. When false, columns are named column_1, column_2 and so on."},
        "max_cell_chars": {
            "type": "integer", "minimum": 20, "maximum": 2000, "default": 200,
            "description": "Longer cell values and group values are cut to this many characters. Cut cells are "
                           "listed in shortened_cells; a cut group value carries its full length in chars."},
    },
    "required": ["path"],
    "additionalProperties": False,
}
TOOL = {
    "name": TOOL_NAME,
    "description": (
        "Return a seeded random sample of rows from one CSV file under the workspace root, either overall "
        "(rows) or up to per_group rows for each value of one column (group_by). Rows keep their line numbers "
        "and are listed in file order. The same seed gives the same rows. It reads the file and changes "
        "nothing. At most 500 rows are returned; files above the size limit (64 MiB unless the host set "
        "another) are refused."),
    "inputSchema": INPUT_SCHEMA,
    "annotations": {"title": "Sample CSV rows", "readOnlyHint": True, "destructiveHint": False,
                    "idempotentHint": True, "openWorldHint": False},
}
INSTRUCTIONS = "Call sample_csv_rows with a CSV path relative to the workspace root. It reads the file and changes nothing."
ROWS_HINT = "Lower rows, pass fewer names in columns, or lower max_cell_chars."
GROUPS_HINT = ("Lower per_group or max_groups, pass fewer names in columns, or lower max_cell_chars, which also cuts "
               "long group values.")


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


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------

class Reservoir:
    """Keeps a uniform random choice of up to size items from a stream (reservoir sampling).

    It draws only from generator.random(). Python documents that random() gives the same sequence for the same
    integer seed across versions, which it does not promise for randrange().
    """

    def __init__(self, size: int) -> None:
        self.size = size
        self.seen = 0
        self.kept: list = []

    def offer(self, item, generator: random.Random) -> None:
        self.seen += 1
        if len(self.kept) < self.size:
            self.kept.append(item)
            return
        slot = int(generator.random() * self.seen)
        if slot < self.size:
            self.kept[slot] = item


def unique_names(header: list[str]) -> tuple[list[str], dict]:
    names, used, renamed = [], set(), {}
    for index, name in enumerate(header):
        candidate, number = name, 2
        while candidate in used:
            candidate, number = f"{name}_{number}", number + 1
        if candidate != name:
            renamed[candidate] = index
        used.add(candidate)
        names.append(candidate)
    return names, renamed


def find_column(names: list[str], name: str):
    if name in names:
        return names.index(name)
    folded = [index for index, item in enumerate(names) if item.strip().casefold() == name.strip().casefold()]
    return folded[0] if len(folded) == 1 else None


def sample_csv_rows(arguments: dict, context: Context) -> dict:
    relative = arguments["path"]
    encoding = arguments.get("encoding", "utf-8")
    delimiter = arguments.get("delimiter", "auto")
    has_header = arguments.get("has_header", True)
    seed = int(arguments.get("seed", 0))
    group_by = arguments.get("group_by")
    per_group = int(arguments.get("per_group", 3))
    max_groups = int(arguments.get("max_groups", 50))
    wanted_rows = int(arguments.get("rows", 20))
    max_cell_chars = int(arguments.get("max_cell_chars", 200))
    if group_by is None and ("per_group" in arguments or "max_groups" in arguments):
        raise Refusal("per_group and max_groups only apply together with group_by.")
    if group_by is not None and "rows" in arguments:
        raise Refusal("Use per_group, not rows, together with group_by.")

    path, info = resolve_file(context.root, relative)
    if info.st_size > context.max_file_bytes:
        raise Refusal(f"The file is {info.st_size} bytes, above this server's limit of {context.max_file_bytes} bytes. "
                      "Sample a smaller extract or ask the host to raise --max-file-mib.")
    data = read_bounded(path, context.max_file_bytes)
    if not data.strip():
        raise Refusal("The file is empty.")
    codec = "utf-8-sig" if encoding == "utf-8" else encoding
    detected = delimiter == "auto"
    if detected:
        sample = codecs.getincrementaldecoder(codec)(errors="replace").decode(data[:SNIFF_BYTES], final=False)
        delimiter = detect_delimiter(sample)
    stream = io.TextIOWrapper(io.BytesIO(data), encoding=codec, errors="strict", newline="")
    cursor = RecordCursor(csv.reader(stream, delimiter=delimiter, quotechar='"', doublequote=True, strict=False))

    generator = random.Random(seed)
    groups: dict[str, Reservoir] = {}
    overall = Reservoir(wanted_rows)
    rows = blank_lines = missing_rows = extra_rows = 0
    width_lines: list[int] = []
    try:
        first = None
        for start, record in cursor:
            if record:
                first = (start, record)
                break
            blank_lines += 1
        if first is None:
            raise Refusal("The file holds no rows.")
        header = first[1] if has_header else [f"column_{number}" for number in range(1, len(first[1]) + 1)]
        names, renamed = unique_names(header)
        group_index = None
        if group_by is not None:
            group_index = find_column(names, group_by)
            if group_index is None:
                raise Refusal(f"group_by {group_by!r} is not a column name.", header=names[:HEADER_NAMES_SHOWN])
        selected = choose_columns(names, arguments.get("columns"), group_index)
        width = len(header)
        for start, record in data_records(first, cursor, has_header):
            if not record:
                blank_lines += 1
                continue
            rows += 1
            if len(record) != width:
                if len(record) < width:
                    missing_rows += 1
                else:
                    extra_rows += 1
                if len(width_lines) < 10:
                    width_lines.append(start)
            item = (start, rows, record)
            if group_index is None:
                overall.offer(item, generator)
                continue
            key = record[group_index] if group_index < len(record) else ""
            reservoir = groups.get(key)
            if reservoir is None:
                if len(groups) >= max_groups:
                    raise Refusal(f"Column {names[group_index]!r} has more than {max_groups} distinct values "
                                  f"(found by line {start}). Choose a column with fewer values or raise max_groups "
                                  "up to 200.")
                reservoir = groups[key] = Reservoir(per_group)
            reservoir.offer(item, generator)
    except UnicodeDecodeError:
        raise Refusal(f"The file is not valid {encoding} at line {decode_error_line(data, codec)}. "
                      "Pass the right encoding (latin-1 or cp1252) or convert the file first.") from None
    except csv.Error as error:
        raise Refusal(f"The CSV reader stopped at the record that starts on line {cursor.start}: {error}.") from None

    chosen = list(overall.kept) if group_index is None else [item for bucket in groups.values() for item in bucket.kept]
    if len(chosen) > MAX_RETURNED_ROWS:
        raise Refusal(f"The sample would hold {len(chosen)} rows, above the limit of {MAX_RETURNED_ROWS}. "
                      "Lower per_group or choose a column with fewer values.")
    chosen.sort()
    shortened, shortened_total, cut_groups = [], 0, 0
    sample = []
    for start, number, record in chosen:
        values = {}
        for index in selected:
            if index >= len(record):
                values[names[index]] = None
                continue
            cell = record[index]
            if len(cell) > max_cell_chars:
                shortened_total += 1
                if len(shortened) < SHORTENED_CELLS_LISTED:
                    shortened.append({"line": start, "column": names[index], "chars": len(cell)})
                cell = cell[:max_cell_chars]
            values[names[index]] = cell
        entry = {"line": start, "row": number, "values": values}
        if len(record) != width:
            entry["field_count"] = len(record)
        sample.append(entry)
    result = {
        "file": {"path": relative, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                 "encoding": encoding, "delimiter": delimiter, "delimiter_detected": detected,
                 "has_header": has_header},
        "seed": seed,
        "rows_read": rows,
        "blank_lines": blank_lines,
        "columns": [names[index] for index in selected],
        "renamed_duplicate_columns": sorted(renamed),
        "group_by": None if group_index is None else names[group_index],
        "groups": None,
        "sample": sample,
        "shortened_cells": shortened,
        "shortened_cells_total": shortened_total,
        "width_problems": {"rows_with_missing_fields": missing_rows, "rows_with_extra_fields": extra_rows,
                           "first_lines": width_lines},
        "notes": ["line is the physical line where a record starts; row counts data rows from 1.",
                  "Rows were chosen by reservoir sampling with the given seed and are listed in file order."],
    }
    if group_index is not None:
        listed = []
        for key, bucket in sorted(groups.items(), key=lambda item: (-item[1].seen, item[0])):
            entry = {"value": key[:max_cell_chars], "rows": bucket.seen, "sampled": len(bucket.kept)}
            if len(key) > max_cell_chars:
                entry["chars"] = len(key)
                cut_groups += 1
            listed.append(entry)
        result["groups"] = listed
        if cut_groups:
            result["notes"].append(f"{cut_groups} group values are longer than max_cell_chars and were cut; "
                                   "chars gives the full length.")
    if group_index is None and rows <= wanted_rows:
        result["notes"].append("The file holds no more rows than requested, so every row is returned.")
    return result


def choose_columns(names: list[str], wanted, group_index) -> list[int]:
    if wanted is None:
        if len(names) > 100:
            raise Refusal(f"The file has {len(names)} columns; pass at most 100 names in columns.",
                          header=names[:HEADER_NAMES_SHOWN])
        return list(range(len(names)))
    chosen, unknown = [], []
    for name in wanted:
        index = find_column(names, name)
        if index is None:
            unknown.append(name)
        elif index not in chosen:
            chosen.append(index)
    if unknown:
        raise Refusal(f"These column names are not in the header: {unknown[:10]}.", header=names[:HEADER_NAMES_SHOWN])
    if group_index is not None and group_index not in chosen:
        chosen.insert(0, group_index)
    return sorted(chosen)


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


def tool_answer(ident, payload: dict, is_error: bool, hint: str = ROWS_HINT) -> dict:
    """Builds the answer and measures its whole line; a line above the limit becomes a short refusal."""
    answer = tool_result(ident, payload, is_error)
    size = len(serialize(answer)) + 1
    if size <= MAX_ANSWER_BYTES:
        return answer
    note = f"The answer would be {size} bytes, above the {MAX_ANSWER_BYTES} byte limit for one answer."
    if is_error and isinstance(payload.get("error"), str):
        return tool_result(ident, {"error": payload["error"][:1000], "detail": note + " Details were left out."},
                           True)
    return tool_result(ident, {"error": note + " " + hint}, True)


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
    hint = GROUPS_HINT if "group_by" in arguments else ROWS_HINT
    try:
        return tool_answer(ident, sample_csv_rows(arguments, context), False, hint)
    except Refusal as refusal:
        return tool_answer(ident, refusal.payload, True, hint)
    except MemoryError:
        return tool_answer(ident, {"error": "The file needs more memory than this server has. " + hint}, True, hint)
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
    parser = argparse.ArgumentParser(description="Local CSV row sampler tool server (standard input and output).")
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
