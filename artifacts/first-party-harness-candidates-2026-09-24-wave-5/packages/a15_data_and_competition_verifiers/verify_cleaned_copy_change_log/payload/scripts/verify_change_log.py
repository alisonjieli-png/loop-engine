"""Verify a cleaned copy of a table against its change log. Effects: reads the named files under --root or one JSON bundle; prints one JSON object; writes nothing, starts no process and uses no network.

Exit status: 0 every difference between the source table and its cleaned copy has a matching log
entry and every log entry matches both tables, 1 at least one check failed, 2 no verdict (refused
input or an internal error).

Rows are matched by the key columns named with --key. A log entry names a row by its key in the
source table ("key") or by its data row number in the source table ("row", counted from 1 without
the header). The log is JSON Lines, one JSON array of objects, or a comma-separated file with a
header row.

Usage:
    python3 -I -B verify_change_log.py --source RAW.csv --cleaned CLEAN.csv --log CHANGES.jsonl
        --key ID [--key SECOND_ID] [--root DIR] [--delimiter comma|tab|semicolon|pipe]
        [--source-sha256 HEX] [--max-examples N] [--no-values] [--max-bytes N]
    python3 -I -B verify_change_log.py --bundle FILE_OR_DASH --key ID

A bundle is one JSON object with the members "source", "cleaned" and "log", each holding the text
of that file. A member replaces the file of the same name; "-" reads the bundle from standard input.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

RECORD_TYPE = "change_log_verification/v1"
DEFAULT_MAX_BYTES = 64 * 1024 * 1024
HARD_MAX_BYTES = 1024 * 1024 * 1024
DELIMITERS = {"comma": ",", "tab": "\t", "semicolon": ";", "pipe": "|"}
BUNDLE_MEMBERS = ("source", "cleaned", "log")
CHANGES = ("cell", "row_removed", "row_added", "column_added", "column_removed")
LOG_FIELDS = ("change", "key", "row", "column", "before", "after")
ROW_NUMBER = re.compile(r"[0-9]{1,12}")
SHA256 = re.compile(r"[0-9a-fA-F]{64}")
MAX_KEY_COLUMNS = 10
PER_RULE_EXAMPLES = 3
EXCERPT = 60
VALUE_FIELDS = ("source_value", "cleaned_value", "logged_before", "logged_after")
CHECKS = (
    "row_removed_without_log", "row_added_without_log", "cell_changed_without_log",
    "column_removed_without_log", "column_added_without_log", "empty_key_in_cleaned",
    "duplicate_key_in_cleaned", "log_before_mismatch", "log_after_mismatch", "log_row_not_in_source",
    "log_removed_row_still_present", "log_added_row_not_new", "log_added_row_missing",
    "log_column_claim_wrong", "log_column_not_in_both_tables", "duplicate_log_entry", "logged_keys_collide",
)


class Refused(Exception):
    """An input or argument the script will not check; reported with exit code 2."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = str(detail)[:400]


class Parser(argparse.ArgumentParser):
    """Argument parser that reports a bad argument as a refused input in JSON."""

    def error(self, message: str):
        raise Refused("bad_arguments", message)


def strict_json(text: str, label: str):
    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                raise ValueError(f"duplicate key {key!r}")
            seen[key] = value
        return seen

    def constant(name):
        raise ValueError(f"{name} is not allowed in JSON")

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except RecursionError:
        raise Refused("json_invalid", f"{label}: nested too deeply") from None
    except ValueError as error:
        raise Refused("json_invalid", f"{label}: {error}") from None


def decode(data: bytes, label: str) -> str:
    if data[:2] == b"\x1f\x8b" or data[:4] == b"PK\x03\x04":
        raise Refused("compressed_input", f"{label} is a compressed file; check the unpacked text")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise Refused("not_utf8", f"{label}: byte {error.start} is not UTF-8") from None
    if "\x00" in text:
        raise Refused("not_text", f"{label} holds a NUL character")
    return text


def csv_records(text: str, delimiter: str, label: str, limit: int) -> list:
    """Return (first line, fields) for every record, blank lines included as empty field lists."""
    csv.field_size_limit(max(limit, 131072))
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    records, end = [], 0
    try:
        for fields in reader:
            records.append((end + 1, fields))
            end = reader.line_num
    except csv.Error as error:
        raise Refused("malformed_csv", f"{label} near line {reader.line_num}: {error}") from None
    return records


class Inputs:
    """Named inputs read from files under --root, or from members of one JSON bundle."""

    def __init__(self, root: str, bundle: str | None, limit: int) -> None:
        self.limit = limit
        try:
            self.root = Path(root).resolve(strict=True)
        except (OSError, RuntimeError):
            raise Refused("root_missing", root) from None
        if not self.root.is_dir():
            raise Refused("root_not_a_folder", root)
        self.bundle = None
        if bundle is not None:
            data = sys.stdin.buffer.read(limit + 1) if bundle == "-" else self.read_file(bundle)[1]
            if len(data) > limit:
                raise Refused("input_too_large", f"the bundle is larger than {limit} bytes")
            value = strict_json(decode(data, "the bundle"), "the bundle")
            if not isinstance(value, dict):
                raise Refused("bundle_invalid", "the bundle is one JSON object")
            unknown = sorted(set(value) - set(BUNDLE_MEMBERS))
            if unknown:
                raise Refused("bundle_invalid", f"unknown bundle members {unknown}; allowed {list(BUNDLE_MEMBERS)}")
            self.bundle = value

    def read_file(self, value: str):
        if not value or "\x00" in value:
            raise Refused("path_invalid", repr(value))
        given = Path(value)
        if ".." in given.parts:
            raise Refused("path_leaves_root", f"{value}: a path may not contain '..'")
        candidate = given if given.is_absolute() else self.root / given
        try:
            real = candidate.resolve(strict=True)
        except FileNotFoundError:
            raise Refused("input_missing", value) from None
        except (OSError, RuntimeError) as error:
            raise Refused("input_unreadable", f"{value}: {error}") from None
        if real != self.root and self.root not in real.parents:
            raise Refused("path_leaves_root", f"{value} resolves to a place outside --root")
        if not real.is_file():
            raise Refused("not_a_regular_file", value)
        try:
            with open(real, "rb") as handle:
                data = handle.read(self.limit + 1)
        except OSError as error:
            raise Refused("input_unreadable", f"{value}: {error.strerror}") from None
        if len(data) > self.limit:
            raise Refused("input_too_large", f"{value} is larger than {self.limit} bytes; raise --max-bytes on purpose")
        return real, data

    def get(self, name: str, path: str | None):
        """Return (label, bytes, resolved path or None) for one required input."""
        if self.bundle is not None and name in self.bundle:
            if path is not None:
                raise Refused("bad_arguments", f"--{name} and the bundle member {name!r} were both given; use one")
            value = self.bundle[name]
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            if not isinstance(value, str):
                raise Refused("bundle_invalid", f"bundle member {name!r} must hold the file text")
            try:
                return f"bundle:{name}", value.encode("utf-8"), None
            except UnicodeEncodeError:
                raise Refused("not_utf8", f"bundle member {name!r} holds text that is not valid UTF-8") from None
        if path is None:
            raise Refused("bad_arguments", f"--{name} is required (or a bundle member {name!r})")
        real, data = self.read_file(path)
        return path, data, real


class Table:
    """A UTF-8 delimited text with one header row, read completely."""

    def __init__(self, label: str, data: bytes, delimiter: str, limit: int) -> None:
        self.label = label
        self.sha256 = hashlib.sha256(data).hexdigest()
        self.byte_order_mark = data.startswith(b"\xef\xbb\xbf")
        records = csv_records(decode(data, label), delimiter, label, limit)
        if not records or not records[0][1]:
            raise Refused("header_missing", f"{label}: the first line must be the header row")
        self.header = records[0][1]
        repeated = sorted({name for name in self.header if self.header.count(name) > 1})
        if repeated:
            raise Refused("duplicate_column_name", f"{label}: column names repeat: {repeated[:10]}")
        width = len(self.header)
        self.rows: list = []
        self.blank_lines = 0
        for line, fields in records[1:]:
            if not fields:
                if width != 1:
                    self.blank_lines += 1
                    continue
                fields = [""]
            if len(fields) != width:
                raise Refused("ragged_rows", f"{label} line {line} has {len(fields)} fields and the header has "
                              f"{width}; check the table structure before this comparison")
            self.rows.append((len(self.rows) + 1, line, fields))
        self.position = {name: index for index, name in enumerate(self.header)}


def shown(value: str, hide: bool):
    if hide:
        return {"characters": len(value)}
    return value if len(value) <= EXCERPT else value[:EXCERPT - 3] + "..."


class Findings:
    """Complete counts for every check, and a bounded list of examples."""

    def __init__(self, limit: int, hide: bool) -> None:
        self.limit, self.hide = limit, hide
        self.counts: dict[str, int] = {}
        self.examples: list[dict] = []
        self.per_rule: dict[str, int] = {}

    def add(self, rule: str, **details) -> None:
        self.counts[rule] = self.counts.get(rule, 0) + 1
        if len(self.examples) >= self.limit or self.per_rule.get(rule, 0) >= PER_RULE_EXAMPLES:
            return
        self.per_rule[rule] = self.per_rule.get(rule, 0) + 1
        item = {"rule": rule}
        for name, value in details.items():
            if value is None:
                continue
            if name in VALUE_FIELDS:
                item[name] = shown(value, self.hide)
            elif name == "key":
                item[name] = [shown(part, self.hide) for part in value]
            else:
                item[name] = value
        self.examples.append(item)


class Entry:
    """One change log entry after its members were checked."""

    def __init__(self, number: int, line: int | None, change: str) -> None:
        self.number, self.line, self.change = number, line, change
        self.key = None
        self.row = None
        self.column = None
        self.before = None
        self.after = None
        self.used = False

    def place(self) -> dict:
        place = {"log_entry": self.number}
        if self.line is not None:
            place["log_line"] = self.line
        return place


def absent(value) -> bool:
    return value is None or value == ""


def cell_text(value, where: str, member: str) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    raise Refused("log_invalid", f"{where}: {member} is the exact cell text as a JSON string, such as \"12.50\", "
                  f"or null for an empty cell; found {type(value).__name__}")


def key_value(value, where: str, keys: list) -> tuple:
    if isinstance(value, str):
        if len(keys) != 1:
            raise Refused("log_invalid", f"{where}: the key has {len(keys)} columns; write it as a list or an object")
        return (value,)
    if isinstance(value, list) and len(value) == len(keys) and all(isinstance(part, str) for part in value):
        return tuple(value)
    if isinstance(value, dict) and set(value) == set(keys) and all(isinstance(part, str) for part in value.values()):
        return tuple(value[name] for name in keys)
    raise Refused("log_invalid", f"{where}: key is the key text, a list of {len(keys)} texts, or an object with "
                  f"the members {keys}")


def row_value(value, where: str) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 1:
        return value
    if isinstance(value, str) and ROW_NUMBER.fullmatch(value) and int(value) >= 1:
        return int(value)
    raise Refused("log_invalid", f"{where}: row is a data row number of the source table, counted from 1")


def make_entry(item, number: int, line: int | None, keys: list) -> Entry:
    where = f"log entry {number}" + (f" on line {line}" if line is not None else "")
    if not isinstance(item, dict):
        raise Refused("log_invalid", f"{where}: each entry is one JSON object")
    change = "cell" if absent(item.get("change")) else item.get("change")
    if change not in CHANGES:
        raise Refused("log_invalid", f"{where}: change {change!r} is not one of {list(CHANGES)}")
    entry = Entry(number, line, change)
    has_key, has_row = not absent(item.get("key")), not absent(item.get("row"))
    if change in ("column_added", "column_removed"):
        if has_key or has_row:
            raise Refused("log_invalid", f"{where}: a {change} entry names a column and no row")
    elif change == "row_added":
        if has_row or not has_key:
            raise Refused("log_invalid", f"{where}: a row_added entry names the new row by its key; a row number "
                          "can only name a row of the source")
    elif has_key == has_row:
        raise Refused("log_invalid", f"{where}: name the row with key or with row, exactly one of them")
    if change in ("cell", "column_added", "column_removed"):
        column = item.get("column")
        if not isinstance(column, str) or not column:
            raise Refused("log_invalid", f"{where}: a {change} entry names its column")
        entry.column = column
    if change == "cell":
        if "before" not in item or "after" not in item:
            raise Refused("log_invalid", f"{where}: a cell entry holds before and after")
        entry.before = cell_text(item["before"], where, "before")
        entry.after = cell_text(item["after"], where, "after")
    if has_key:
        entry.key = key_value(item["key"], where, keys)
    if has_row:
        entry.row = row_value(item["row"], where)
    return entry


def read_log(label: str, data: bytes, keys: list, limit: int) -> tuple:
    text = decode(data, label)
    start = text.lstrip()
    if not start:
        return "empty", []
    if start[0] == "[":
        value = strict_json(text, label)
        if not isinstance(value, list):
            raise Refused("log_invalid", f"{label}: a JSON log is one array of entry objects")
        return "json_array", [make_entry(item, index + 1, None, keys) for index, item in enumerate(value)]
    if start[0] == "{":
        entries = []
        for number, line in enumerate(text.split("\n"), start=1):
            if line.strip():
                item = strict_json(line, f"{label} line {number} (JSON Lines hold one complete object per line)")
                entries.append(make_entry(item, len(entries) + 1, number, keys))
        return "json_lines", entries
    records = csv_records(text, ",", label, limit)
    header = records[0][1]
    if "column" not in header and "change" not in header:
        raise Refused("log_invalid", f"{label}: a CSV log starts with a header row that names fields from "
                      f"{list(LOG_FIELDS)}")
    if len(set(header)) != len(header):
        raise Refused("log_invalid", f"{label}: the header row repeats a field name")
    entries = []
    for line, fields in records[1:]:
        if not fields:
            continue
        if len(fields) != len(header):
            raise Refused("log_invalid", f"{label} line {line} has {len(fields)} fields and the header has {len(header)}")
        item = {name: value for name, value in zip(header, fields) if name in LOG_FIELDS}
        if not absent(item.get("key")) and len(keys) > 1:
            raise Refused("log_invalid", f"{label} line {line}: a CSV log names rows of a key with several columns by "
                          "row number only; use JSON Lines to write key values")
        entries.append(make_entry(item, len(entries) + 1, line, keys))
    return "csv", entries


def build_parser() -> Parser:
    parser = Parser(description="Verify a cleaned copy against its change log. Exit 0 pass, 1 fail, 2 no verdict.")
    parser.add_argument("--source", help="the table before cleaning, relative to --root")
    parser.add_argument("--cleaned", help="the cleaned copy, relative to --root")
    parser.add_argument("--log", help="the change log: JSON Lines, a JSON array or a CSV file, relative to --root")
    parser.add_argument("--key", action="append", default=[],
                        help="a key column that identifies a row; give one --key for each key column")
    parser.add_argument("--bundle", help="one JSON object with the members source, cleaned and log; - reads standard input")
    parser.add_argument("--root", default=".", help="folder that every path is relative to (default: current folder)")
    parser.add_argument("--delimiter", default="comma", help="delimiter of both tables: comma (default), tab, semicolon, "
                        "pipe or one character; a CSV log always uses commas")
    parser.add_argument("--source-sha256", help="the SHA-256 digest of the source recorded before cleaning")
    parser.add_argument("--max-examples", type=int, default=30, help="violations listed in full, 1 to 500 (default 30)")
    parser.add_argument("--no-values", action="store_true", help="show the length of each key and cell value, not its text")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                        help=f"refuse a file larger than this (default {DEFAULT_MAX_BYTES})")
    return parser


def run(args) -> tuple:
    if not 1 <= args.max_bytes <= HARD_MAX_BYTES:
        raise Refused("bad_arguments", f"--max-bytes is between 1 and {HARD_MAX_BYTES}")
    if not 1 <= args.max_examples <= 500:
        raise Refused("bad_arguments", "--max-examples is between 1 and 500")
    delimiter = DELIMITERS.get(args.delimiter, args.delimiter)
    if len(delimiter) != 1 or delimiter in "\"\r\n":
        raise Refused("bad_arguments", "--delimiter is comma, tab, semicolon, pipe or one character")
    keys = args.key
    if not keys:
        raise Refused("bad_arguments", "name the key columns with --key; the task or the cleaning plan says which")
    if len(set(keys)) != len(keys) or len(keys) > MAX_KEY_COLUMNS or "" in keys:
        raise Refused("bad_arguments", f"--key names 1 to {MAX_KEY_COLUMNS} distinct nonempty columns")
    expected_digest = args.source_sha256
    if expected_digest is not None and not SHA256.fullmatch(expected_digest):
        raise Refused("bad_arguments", "--source-sha256 is 64 hexadecimal characters")
    inputs = Inputs(args.root, args.bundle, args.max_bytes)
    source_label, source_bytes, source_real = inputs.get("source", args.source)
    cleaned_label, cleaned_bytes, cleaned_real = inputs.get("cleaned", args.cleaned)
    log_label, log_bytes, _log_real = inputs.get("log", args.log)
    if source_real is not None and source_real == cleaned_real:
        raise Refused("same_file", "--source and --cleaned name one file; a table cleaned in place has no source "
                      "to compare with")
    source = Table(source_label, source_bytes, delimiter, args.max_bytes)
    cleaned = Table(cleaned_label, cleaned_bytes, delimiter, args.max_bytes)
    log_format, entries = read_log(log_label, log_bytes, keys, args.max_bytes)
    for table in (source, cleaned):
        missing = [name for name in keys if name not in table.position]
        if missing:
            raise Refused("key_column_missing", f"{missing} is not a column of {table.label}; its columns are "
                          f"{table.header[:40]}")
    findings = Findings(args.max_examples, args.no_values)

    # Source keys must identify every row, or no row can be matched.
    source_at = [source.position[name] for name in keys]
    source_keys, source_index = [], {}
    for number, line, fields in source.rows:
        key = tuple(fields[index] for index in source_at)
        if "" in key:
            raise Refused("empty_key_in_source", f"{source.label} row {number} (line {line}) has an empty key; choose "
                          "key columns that identify every source row")
        if key in source_index:
            raise Refused("duplicate_key_in_source", f"{source.label} rows {source_index[key]} and {number} share one "
                          "key; choose key columns that identify every source row")
        source_index[key] = number
        source_keys.append(key)
    cleaned_at = [cleaned.position[name] for name in keys]
    cleaned_index = {}
    for number, line, fields in cleaned.rows:
        key = tuple(fields[index] for index in cleaned_at)
        if "" in key:
            findings.add("empty_key_in_cleaned", cleaned_row=number, line=line)
        elif key in cleaned_index:
            findings.add("duplicate_key_in_cleaned", key=key, cleaned_row=number, first_cleaned_row=cleaned_index[key])
        else:
            cleaned_index[key] = number

    # Sort the entries by what they claim, and refuse none of them silently.
    cells, removed, added, columns_added, columns_removed = {}, {}, {}, {}, {}
    for entry in entries:
        if entry.change in ("column_added", "column_removed"):
            book = columns_added if entry.change == "column_added" else columns_removed
            if entry.column in book:
                findings.add("duplicate_log_entry", column=entry.column, first_log_entry=book[entry.column].number,
                             **entry.place())
            else:
                book[entry.column] = entry
            continue
        if entry.row is not None:
            if entry.row > len(source_keys):
                findings.add("log_row_not_in_source", row=entry.row, **entry.place())
                continue
            entry.key = source_keys[entry.row - 1]
        if entry.change == "row_added":
            if entry.key in added:
                findings.add("duplicate_log_entry", key=entry.key, first_log_entry=added[entry.key].number,
                             **entry.place())
            else:
                added[entry.key] = entry
            continue
        if entry.key not in source_index:
            findings.add("log_row_not_in_source", key=entry.key, **entry.place())
            continue
        book, slot = (removed, entry.key) if entry.change == "row_removed" else (cells, (entry.key, entry.column))
        if slot in book:
            findings.add("duplicate_log_entry", key=entry.key, column=entry.column, first_log_entry=book[slot].number,
                         **entry.place())
        else:
            book[slot] = entry

    # Columns.
    for name in source.header:
        if name not in cleaned.position and name not in columns_removed:
            findings.add("column_removed_without_log", column=name)
    for name in cleaned.header:
        if name not in source.position and name not in columns_added:
            findings.add("column_added_without_log", column=name)
    for name, entry in columns_removed.items():
        if name not in source.position or name in cleaned.position:
            findings.add("log_column_claim_wrong", column=name, change="column_removed", **entry.place())
    for name, entry in columns_added.items():
        if name not in cleaned.position or name in source.position:
            findings.add("log_column_claim_wrong", column=name, change="column_added", **entry.place())
    common = [name for name in source.header if name in cleaned.position]

    # A logged change of a key column moves the match to the new key.
    expected = {}
    for number, key in enumerate(source_keys, start=1):
        parts = list(key)
        for index, name in enumerate(keys):
            entry = cells.get((key, name))
            if entry is not None:
                parts[index] = entry.after
        target = tuple(parts)
        if target in expected:
            findings.add("logged_keys_collide", key=key, row=number, other_row=expected[target][1])
            continue
        expected[target] = (key, number)

    # Rows.
    matched, claimed, rows_removed = [], set(), 0
    for target, (key, number) in expected.items():
        cleaned_number = cleaned_index.get(target)
        if cleaned_number is None:
            rows_removed += 1
            if key not in removed:
                findings.add("row_removed_without_log", key=key, row=number)
            continue
        claimed.add(target)
        if key in removed:
            findings.add("log_removed_row_still_present", key=key, row=number, cleaned_row=cleaned_number,
                         **removed[key].place())
        matched.append((key, number, cleaned_number))
    rows_added = 0
    for key, number in cleaned_index.items():
        if key in claimed:
            continue
        rows_added += 1
        if key not in added:
            findings.add("row_added_without_log", key=key, cleaned_row=number)
    for key, entry in added.items():
        if key in claimed:
            findings.add("log_added_row_not_new", key=key, cleaned_row=cleaned_index[key], **entry.place())
        elif key not in cleaned_index:
            findings.add("log_added_row_missing", key=key, **entry.place())

    # Cells of the columns both tables have.
    source_column = {name: source.position[name] for name in common}
    cleaned_column = {name: cleaned.position[name] for name in common}
    compared = changed = no_effect = 0
    changed_by_column: dict[str, int] = {}
    for key, number, cleaned_number in matched:
        before_fields = source.rows[number - 1][2]
        after_fields = cleaned.rows[cleaned_number - 1][2]
        for name in common:
            old, new = before_fields[source_column[name]], after_fields[cleaned_column[name]]
            compared += 1
            if old != new:
                changed += 1
                changed_by_column[name] = changed_by_column.get(name, 0) + 1
            entry = cells.get((key, name))
            if entry is None:
                if old != new:
                    findings.add("cell_changed_without_log", key=key, row=number, cleaned_row=cleaned_number,
                                 column=name, source_value=old, cleaned_value=new)
                continue
            entry.used = True
            if entry.before != old:
                findings.add("log_before_mismatch", key=key, row=number, column=name, source_value=old,
                             logged_before=entry.before, **entry.place())
            if entry.after != new:
                findings.add("log_after_mismatch", key=key, row=number, cleaned_row=cleaned_number, column=name,
                             cleaned_value=new, logged_after=entry.after, **entry.place())
            if entry.before == entry.after:
                no_effect += 1
    on_missing_rows = 0
    for (key, name), entry in cells.items():
        if entry.used:
            continue
        if name not in source.position or name not in cleaned.position:
            findings.add("log_column_not_in_both_tables", key=key, column=name, **entry.place())
        else:
            on_missing_rows += 1

    order = [cleaned_number for _key, _number, cleaned_number in matched]
    checks = {name: findings.counts.get(name, 0) for name in CHECKS}
    if expected_digest is not None:
        if expected_digest.lower() != source.sha256:
            findings.add("source_digest_differs", expected=expected_digest.lower(), found=source.sha256)
        checks["source_digest_differs"] = findings.counts.get("source_digest_differs", 0)
    failed = [name for name, count in checks.items() if count]
    report = {
        "record_type": RECORD_TYPE,
        "status": "fail" if failed else "pass",
        "source": {"path": source.label, "sha256": source.sha256, "rows": len(source.rows),
                   "columns": len(source.header), "blank_lines_skipped": source.blank_lines},
        "cleaned": {"path": cleaned.label, "sha256": cleaned.sha256, "rows": len(cleaned.rows),
                    "columns": len(cleaned.header), "blank_lines_skipped": cleaned.blank_lines},
        "log": {"path": log_label, "sha256": hashlib.sha256(log_bytes).hexdigest(), "format": log_format,
                "entries": len(entries)},
        "key_columns": keys,
        "summary": {
            "rows_matched": len(matched), "rows_removed": rows_removed, "rows_added": rows_added,
            "columns_removed": [name for name in source.header if name not in cleaned.position],
            "columns_added": [name for name in cleaned.header if name not in source.position],
            "cells_compared": compared, "cells_changed": changed, "cells_changed_by_column": changed_by_column,
            "row_order_changed": any(later < earlier for earlier, later in zip(order, order[1:])),
            "column_order_changed": [name for name in cleaned.header if name in source.position] != common,
        },
        "checks": checks,
        "failed_checks": failed,
        "violations_total": sum(checks.values()),
        "violations": findings.examples,
        "violations_shown": len(findings.examples),
        "warnings": {"log_entries_that_change_nothing": no_effect,
                     "log_cell_entries_on_rows_not_in_cleaned": on_missing_rows},
        "numbering": "row counts data rows of the source from 1 without the header, cleaned_row counts data rows "
                     "of the cleaned copy the same way, and line is the file line where a record starts",
    }
    return report, 1 if failed else 0


def emit(report: dict) -> None:
    sys.stdout.buffer.write((json.dumps(report, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))


def main(argv=None) -> int:
    try:
        report, status = run(build_parser().parse_args(argv))
    except Refused as error:
        report, status = {"record_type": RECORD_TYPE, "status": "refused", "reason": error.reason,
                          "detail": error.detail}, 2
    except Exception as error:  # noqa: BLE001 - an internal error must not look like a failed check
        report, status = {"record_type": RECORD_TYPE, "status": "error", "reason": "internal_error",
                          "detail": f"{type(error).__name__}: {error}"[:400]}, 2
    emit(report)
    return status


if __name__ == "__main__":
    sys.exit(main())
