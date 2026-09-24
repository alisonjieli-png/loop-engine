"""Reads SQLite database files under --root without changing them and answers tool calls on standard input and output; opens no network connection and starts no process.

sqlite_readonly_server is a small local Model Context Protocol server. It reads
newline-delimited JSON-RPC 2.0 messages on standard input, writes one answer
line for each request on standard output and writes diagnostics only to
standard error. It stops when standard input closes.

Tools:
- describe_sqlite lists the tables and views of one database with their columns,
  or only their names (names_only), or only the tables it is given (tables).
- query_sqlite runs one SELECT statement with row, time, size and memory limits.

Every database is opened read-only (mode=ro, or immutable=1 for a WAL database
with no pending changes, so SQLite creates no side files). An authorizer allows
only reading; writes, PRAGMA, ATTACH, temporary tables and extension loading
are refused before any effect.

Python 3.10 or later, standard library only. Licence: MIT.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sqlite3
import stat
import sys
import time
from pathlib import Path, PureWindowsPath

SERVER_NAME = "sqlite_readonly_server"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26")
MAX_LINE_BYTES = 1024 * 1024
# One answer line holds the result twice (escaped text and structured copy); the whole line stays within 256 KiB.
MAX_ANSWER_BYTES = 256 * 1024
HEAP_LIMIT_BYTES = 256 * 1024 * 1024
VALUE_LIMIT_BYTES = 1_000_000
MAX_TABLES_DESCRIBED = 200
MAX_NAMES_LISTED = 1000
SHORTENED_CELLS_LISTED = 100
SQLITE_HEADER = b"SQLite format 3\x00"
EXACT_INTEGER = 2 ** 53

PATH_PROPERTY = {
    "type": "string", "minLength": 1, "maxLength": 1024,
    "description": "Database file path relative to the workspace root, for example data/shop.sqlite3. "
                   "Absolute paths, '..' and links that leave the root are refused."}
TIME_PROPERTY = {
    "type": "integer", "minimum": 100, "maximum": 30000, "default": 5000,
    "description": "Stop the work after this many milliseconds."}
DESCRIBE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "path": PATH_PROPERTY,
        "tables": {"type": "array", "minItems": 1, "maxItems": MAX_TABLES_DESCRIBED,
                   "items": {"type": "string", "minLength": 1, "maxLength": 1000},
                   "description": "Describe only these tables and views. For a large database, call with "
                                  "names_only true first to see the names."},
        "names_only": {"type": "boolean", "default": False,
                       "description": f"true lists only the name and type of each table and view (at most "
                                      f"{MAX_NAMES_LISTED}), without columns."},
        "count_rows": {"type": "boolean", "default": False,
                       "description": "true adds the row count of each table (slow on large tables)."},
        "time_limit_ms": TIME_PROPERTY,
    },
    "required": ["path"],
    "additionalProperties": False,
}
QUERY_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "path": PATH_PROPERTY,
        "sql": {"type": "string", "minLength": 1, "maxLength": 20000,
                "description": "Exactly one statement that starts with SELECT, WITH or VALUES. Use ? for values."},
        "parameters": {"type": "array", "maxItems": 100,
                       "items": {"type": ["string", "number", "boolean", "null"]},
                       "description": "Values for the ? placeholders, in order."},
        "max_rows": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 100,
                     "description": "Return at most this many rows; more_rows says whether more exist."},
        "time_limit_ms": TIME_PROPERTY,
        "max_cell_chars": {"type": "integer", "minimum": 20, "maximum": 10000, "default": 500,
                           "description": "Longer text values are cut to this many characters and listed in shortened_cells."},
    },
    "required": ["path", "sql"],
    "additionalProperties": False,
}
ANNOTATIONS = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}
TOOLS = [
    {"name": "describe_sqlite",
     "description": ("List the tables and views of one SQLite database file under the workspace root, with each "
                     "column's name, declared type, NOT NULL flag, primary key position and foreign keys. For a "
                     "large database, call it with names_only true, then pass a few names in tables. It opens the "
                     "file read-only and changes nothing."),
     "inputSchema": DESCRIBE_SCHEMA, "annotations": {"title": "Describe SQLite database", **ANNOTATIONS}},
    {"name": "query_sqlite",
     "description": ("Run exactly one SELECT statement (it may start with WITH or VALUES) against one SQLite "
                     "database file under the workspace root, opened read-only. Every statement that writes, and "
                     "PRAGMA, ATTACH and temporary tables, is refused. Returns column names and at most max_rows "
                     "rows. Blobs are shown as their size. Work stops at time_limit_ms."),
     "inputSchema": QUERY_SCHEMA, "annotations": {"title": "Query SQLite read-only", **ANNOTATIONS}},
]
SCHEMAS = {tool["name"]: tool["inputSchema"] for tool in TOOLS}
INSTRUCTIONS = ("Call describe_sqlite first, then query_sqlite with one SELECT statement. "
                "Both open the database read-only and change nothing.")
HINTS = {"describe_sqlite": "Call describe_sqlite with names_only true to list the tables and views, then describe a "
                              "few at a time with tables.",
         "query_sqlite": "Select fewer columns or rows, or lower max_cell_chars."}
ALLOWED_ACTIONS = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION,
                   getattr(sqlite3, "SQLITE_RECURSIVE", 33)}
REFUSED_FUNCTIONS = frozenset({"load_extension", "fts3_tokenizer", "readfile", "writefile", "edit"})
LEADING_NOISE = re.compile(r"\A(?:\s+|--[^\n]*(?:\n|\Z)|/\*.*?\*/)*", re.DOTALL)
FIRST_WORD = re.compile(r"[A-Za-z]+")


class Refusal(Exception):
    """A tool-level refusal. The answer carries isError true and this message."""

    def __init__(self, message: str, **details) -> None:
        super().__init__(message)
        self.payload = {"error": message, **details}


class Context:
    def __init__(self, root: Path) -> None:
        self.root = root


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
    """Checks a value against the small schema subset used by the tool schemas."""
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
# Database files
# ---------------------------------------------------------------------------

def resolve_file(root: Path, relative: str) -> Path:
    """Resolves a relative path under root; refuses '..', absolute paths and links that leave root."""
    if "\x00" in relative:
        raise Refusal("The path holds a NUL character.")
    if Path(relative).is_absolute() or PureWindowsPath(relative).anchor:
        raise Refusal("Give the path relative to the workspace root, for example data/shop.sqlite3. "
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


def read_header(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise Refusal(f"The file cannot be opened ({type(error).__name__}).") from None
    with os.fdopen(descriptor, "rb") as stream:
        return stream.read(100)


def open_read_only(path: Path) -> sqlite3.Connection:
    """Opens the database so that SQLite can neither change it nor create side files next to it."""
    header = read_header(path)
    if not header.startswith(SQLITE_HEADER) or len(header) < 100:
        raise Refusal("The file is not an SQLite 3 database.")
    options = "mode=ro"
    if header[18] == 2 or header[19] == 2:
        pending = Path(str(path) + "-wal")
        if pending.exists() and pending.stat().st_size > 0:
            raise Refusal("The database is in WAL mode and its -wal file holds changes that are not in the main "
                          "file yet. Reading it would make SQLite write side files. Ask the owner for a "
                          "checkpointed copy of the database.")
        options = "mode=ro&immutable=1"
    try:
        connection = sqlite3.connect(f"{path.as_uri()}?{options}", uri=True, timeout=1.0, isolation_level=None)
    except sqlite3.Error as error:
        raise Refusal(f"SQLite could not open the database read-only: {error}.") from None
    connection.execute("PRAGMA query_only = ON")
    connection.execute("PRAGMA temp_store = MEMORY")
    connection.execute(f"PRAGMA hard_heap_limit = {HEAP_LIMIT_BYTES}")
    if hasattr(connection, "setlimit"):
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, VALUE_LIMIT_BYTES)
        connection.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
    if hasattr(connection, "enable_load_extension"):
        connection.enable_load_extension(False)
    return connection


class Deadline:
    """Progress handler that stops SQLite work after a time limit."""

    def __init__(self, milliseconds: int) -> None:
        self.milliseconds = milliseconds
        self.end = time.monotonic() + milliseconds / 1000.0

    def __call__(self) -> int:
        return 1 if time.monotonic() > self.end else 0


def reading_only(action, first, second, database, source) -> int:
    if action == sqlite3.SQLITE_FUNCTION:
        return sqlite3.SQLITE_DENY if str(second).lower() in REFUSED_FUNCTIONS else sqlite3.SQLITE_OK
    return sqlite3.SQLITE_OK if action in ALLOWED_ACTIONS else sqlite3.SQLITE_DENY


def explain_error(error: Exception, deadline: Deadline) -> Refusal:
    text = str(error)
    lowered = text.lower()
    if "interrupted" in lowered:
        return Refusal(f"The work passed the time limit of {deadline.milliseconds} ms. Add a WHERE clause or a "
                       "LIMIT, or raise time_limit_ms up to 30000.")
    if "not authorized" in lowered or "authorization denied" in lowered:
        return Refusal("The statement tries an action other than reading (for example a write, PRAGMA, ATTACH, a "
                       "temporary table or loading an extension). Only one SELECT statement is allowed.")
    if "readonly" in lowered:
        return Refusal("SQLite would have to write to read this database, for example to finish an interrupted "
                       "earlier write. Nothing was changed. Ask the owner for a clean copy of the database.")
    if "one statement" in lowered:
        return Refusal("Send exactly one statement; remove everything after the first semicolon.")
    if "too big" in lowered or "out of memory" in lowered or isinstance(error, MemoryError):
        return Refusal(f"The statement needs a value above {VALUE_LIMIT_BYTES} bytes or more than "
                       f"{HEAP_LIMIT_BYTES // (1024 * 1024)} MiB of working memory.")
    return Refusal(f"SQLite refused the statement: {text[:300]}")


def quote_name(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def describe_sqlite(arguments: dict, context: Context) -> dict:
    relative = arguments["path"]
    names_only = arguments.get("names_only", False)
    wanted = arguments.get("tables")
    if names_only and (wanted is not None or arguments.get("count_rows")):
        raise Refusal("names_only lists names only; leave out tables and count_rows, or set names_only false.")
    path = resolve_file(context.root, relative)
    deadline = Deadline(int(arguments.get("time_limit_ms", 5000)))
    connection = open_read_only(path)
    try:
        connection.set_progress_handler(deadline, 1000)
        objects = connection.execute(
            "SELECT type, name FROM sqlite_master WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite\\_%' "
            "ESCAPE '\\' ORDER BY name").fetchall()
        if names_only:
            listed = [{"name": name, "type": kind} for kind, name in objects[:MAX_NAMES_LISTED]]
            described = None
        else:
            listed = None
            described = [describe_one(connection, kind, name, bool(arguments.get("count_rows")), deadline)
                         for kind, name in choose_objects(objects, wanted)[:MAX_TABLES_DESCRIBED]]
    except (sqlite3.Error, MemoryError) as error:
        raise explain_error(error, deadline) from None
    finally:
        connection.close()
    result = {"file": {"path": relative, "bytes": path.stat().st_size}, "tables_total": len(objects)}
    if names_only:
        result["names"] = listed
        result["notes"] = ["Describe a few of these with tables. Names are listed in name order."]
        if len(objects) > MAX_NAMES_LISTED:
            result["notes"].append(f"Only the first {MAX_NAMES_LISTED} names are listed. For the rest, query "
                                   "sqlite_master with query_sqlite and a WHERE clause on name.")
        return result
    result["tables"] = described
    result["notes"] = ["declared_type is the type written in CREATE TABLE; SQLite does not enforce it by default."]
    if any("error" in entry for entry in described):
        result["notes"].append("An entry with error could not be read, for example a view that names a dropped "
                               "table. Every other entry is complete.")
    if wanted is None and len(objects) > MAX_TABLES_DESCRIBED:
        result["notes"].append(f"Only the first {MAX_TABLES_DESCRIBED} tables and views by name are described. "
                               "Use names_only and tables for the rest.")
    return result


def choose_objects(objects: list, wanted) -> list:
    """The (type, name) pairs to describe: all of them, or the ones named in tables (exact name, else any case)."""
    if wanted is None:
        return objects
    chosen, unknown = [], []
    for name in wanted:
        matches = [item for item in objects if item[1] == name] or \
                  [item for item in objects if item[1].casefold() == name.casefold()]
        if not matches:
            unknown.append(name)
        chosen.extend(item for item in matches if item not in chosen)
    if unknown:
        raise Refusal(f"These names are not tables or views of this database: {[name[:80] for name in unknown[:10]]}. "
                      "Call describe_sqlite with names_only true to list them.")
    return sorted(chosen, key=lambda item: item[1])


def describe_one(connection, kind: str, name: str, count_rows: bool, deadline: Deadline) -> dict:
    """Columns and foreign keys of one table or view; a read error is reported in this entry only."""
    entry = {"name": name, "type": kind, "columns": [], "foreign_keys": []}
    try:
        entry["columns"] = [{"name": row[1], "declared_type": row[2], "not_null": bool(row[3]), "default": row[4],
                             "primary_key_position": row[5]}
                            for row in connection.execute(
                                'SELECT cid, name, type, "notnull", dflt_value, pk FROM pragma_table_info(?) ORDER BY cid',
                                (name,))]
        entry["foreign_keys"] = [{"column": row[3], "references_table": row[2], "references_column": row[4]}
                                 for row in connection.execute(
                                     "SELECT id, seq, \"table\", \"from\", \"to\" FROM pragma_foreign_key_list(?) "
                                     "ORDER BY id, seq", (name,))]
        if count_rows and kind == "table":
            entry["row_count"] = connection.execute(f"SELECT count(*) FROM {quote_name(name)}").fetchone()[0]
    except sqlite3.Error as error:
        if deadline() or "interrupted" in str(error).lower():
            raise
        entry["error"] = f"SQLite could not read this {kind}: {str(error)[:200]}"
    return entry


def json_cell(value, limit: int, where: dict, shortened: list, counts: dict):
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if -EXACT_INTEGER <= value <= EXACT_INTEGER:
            return value
        counts["large_integers"] += 1
        return str(value)
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")
    if isinstance(value, bytes):
        return {"blob_bytes": len(value)}
    text = str(value)
    if len(text) > limit:
        counts["shortened"] += 1
        if len(shortened) < SHORTENED_CELLS_LISTED:
            shortened.append({**where, "chars": len(text)})
        return text[:limit]
    return text


def query_sqlite(arguments: dict, context: Context) -> dict:
    relative, sql = arguments["path"], arguments["sql"]
    parameters = arguments.get("parameters", [])
    max_rows = int(arguments.get("max_rows", 100))
    limit = int(arguments.get("max_cell_chars", 500))
    body = sql[LEADING_NOISE.match(sql).end():]
    word = FIRST_WORD.match(body)
    if word is None or word.group(0).upper() not in ("SELECT", "WITH", "VALUES"):
        raise Refusal("Only one SELECT statement is allowed; it may start with WITH or VALUES.")
    path = resolve_file(context.root, relative)
    deadline = Deadline(int(arguments.get("time_limit_ms", 5000)))
    connection = open_read_only(path)
    started = time.monotonic()
    try:
        connection.set_authorizer(reading_only)
        connection.set_progress_handler(deadline, 1000)
        cursor = connection.execute(sql, parameters)
        fetched = cursor.fetchmany(max_rows + 1)
        names = [item[0] for item in cursor.description or []]
    except (sqlite3.Error, sqlite3.Warning, MemoryError) as error:
        raise explain_error(error, deadline) from None
    except OverflowError:
        raise Refusal("A value in parameters is an integer outside the 64-bit range that SQLite stores. "
                      "Pass it as a string instead.") from None
    finally:
        connection.close()
    shortened: list = []
    counts = {"shortened": 0, "large_integers": 0}
    rows = [[json_cell(value, limit, {"row": number, "column": names[index]}, shortened, counts)
             for index, value in enumerate(row)]
            for number, row in enumerate(fetched[:max_rows], start=1)]
    result = {"file": {"path": relative}, "columns": names, "rows": rows, "row_count": len(rows),
              "more_rows": len(fetched) > max_rows, "elapsed_ms": round((time.monotonic() - started) * 1000),
              "shortened_cells": shortened, "shortened_cells_total": counts["shortened"], "notes": []}
    if counts["large_integers"]:
        result["notes"].append("Integers beyond 2^53 are given as strings so no digit is lost.")
    if result["more_rows"]:
        result["notes"].append(f"More rows exist; only the first {max_rows} are shown.")
    return result


HANDLERS = {"describe_sqlite": describe_sqlite, "query_sqlite": query_sqlite}


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


def tool_answer(ident, payload: dict, is_error: bool, hint: str = HINTS["query_sqlite"]) -> dict:
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
    if name not in HANDLERS:
        return error_answer(ident, -32602, f"Unknown tool: {name[:80]}")
    problems = argument_problems(SCHEMAS[name], arguments, "arguments")
    if problems:
        return tool_answer(ident, {"error": "The arguments do not match the input schema.",
                                   "problems": problems[:20]}, True)
    hint = HINTS[name]
    try:
        return tool_answer(ident, HANDLERS[name](arguments, context), False, hint)
    except Refusal as refusal:
        return tool_answer(ident, refusal.payload, True, hint)
    except MemoryError:
        return tool_answer(ident, {"error": "The work needs more memory than this server has. " + hint}, True, hint)
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
        return {"jsonrpc": "2.0", "id": ident, "result": {"tools": TOOLS}}
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
    parser = argparse.ArgumentParser(description="Local read-only SQLite query tool server (standard input and output).")
    parser.add_argument("--root", default=".", help="folder that every path argument is resolved under")
    options = parser.parse_args(argv)
    try:
        root = Path(options.root).resolve(strict=True)
    except (OSError, RuntimeError):
        print(f"{SERVER_NAME}: --root {options.root!r} does not exist", file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"{SERVER_NAME}: --root {options.root!r} is not a folder", file=sys.stderr)
        return 2
    try:
        return serve(Context(root))
    except (BrokenPipeError, KeyboardInterrupt):
        return 0


if __name__ == "__main__":
    sys.exit(main())
