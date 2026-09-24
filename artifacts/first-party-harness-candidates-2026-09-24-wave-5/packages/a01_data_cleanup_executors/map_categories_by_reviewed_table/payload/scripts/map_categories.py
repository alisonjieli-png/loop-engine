"""Map one CSV category column through a reviewed mapping table only. Effects: reads_fs (the input CSV and the table under --root); writes_fs only with --output (one new file, never an existing one); no network; no subprocess.

Usage, from the workspace folder (SKILL_DIR is the folder that holds SKILL.md):

    python3 -I -B SKILL_DIR/scripts/map_categories.py --input data/orders.csv --column status \
        --mapping data/status-mapping.json [--table-sha256 HEX] [--output data/orders.mapped.csv]

Values and table entries are compared after one normalization: Unicode NFC, letter case folded one
letter at a time (each letter becomes exactly one lower-case letter, so the German sharp s never
becomes "ss"), and runs of spaces collapsed to one space with the ends trimmed. A value is mapped only
through an entry of the table, or to a target of the table when the table sets
targets_map_to_themselves. Every other value is listed with its count. The table itself is refused
when it names no review, is not meant for the column, holds conflicting or chained entries, or, with
--table-sha256, differs from the reviewed bytes.

Exit 0: every non-empty value was mapped.
Exit 1: the report lists unmapped values for a person to review.
Exit 2: the input, the table or the arguments were refused; nothing was written.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import re
import stat
import sys
import unicodedata
from pathlib import Path

TOOL = "map_categories_by_reviewed_table"
VERSION = "0.2.0"
TABLE_RECORD = "category_mapping_table/v1"
MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_TABLE_BYTES = 8 * 1024 * 1024
MAX_ENTRIES = 100_000
MAX_TEXT = 200
MAX_LISTED = 1000
MAX_UNUSED_LISTED = 200
MAX_ROWS_SHOWN = 5
MAX_SPELLINGS_SHOWN = 5
MAX_SHOWN_CHARACTERS = 120
EXIT_DONE, EXIT_REVIEW, EXIT_REFUSED = 0, 1, 2
TABLE_KEYS = {"record_type", "columns", "reviewed_by", "reviewed_on", "targets_map_to_themselves", "entries"}

#: Why a whole run is refused. references/mapping-table.md explains each one.
REFUSAL_REASONS = (
    "arguments_invalid", "delimiter_invalid", "root_missing", "path_invalid", "path_outside_root",
    "input_missing", "input_not_a_file", "input_too_large", "input_not_text", "input_not_utf8",
    "csv_malformed", "header_missing", "row_width_differs", "column_missing", "column_repeated",
    "table_invalid", "table_digest_differs", "table_not_reviewed", "table_not_for_this_column", "table_empty",
    "table_conflicting_entries", "table_chained_entries", "table_targets_collide", "output_exists",
    "output_is_input", "output_folder_missing", "output_column_exists", "internal_error",
)
SHA256_TEXT = re.compile(r"[0-9a-f]{64}")
DELIMITERS = {",": ",", "comma": ",", ";": ";", "semicolon": ";", "|": "|", "pipe": "|", "tab": "\t",
              "\\t": "\t", "\t": "\t"}


class Refusal(Exception):
    """The run is refused. Nothing is written."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


class Arguments(argparse.ArgumentParser):
    """Report argument errors as one JSON refusal instead of a usage message."""

    def error(self, message: str):  # type: ignore[override]
        raise Refusal("arguments_invalid", message)


def fold_letter_case(text: str) -> str:
    """Fold letter case one letter at a time, each letter to exactly one letter.

    str.casefold() alone also turns the German sharp s into "ss" and splits ligatures such as the
    one-character fi, which would make different spellings share a key. A letter whose folded form is
    longer than one letter keeps its one-letter lower-case form, or itself.
    """
    folded = text.casefold()
    if len(folded) == len(text):
        return folded  # no letter grew, so every letter was folded to exactly one letter
    pieces = []
    for character in text:
        single = character.casefold()
        if len(single) != 1:
            single = character.lower()
            if len(single) != 1:
                single = character
        pieces.append(single)
    return "".join(pieces)


def key_of(value: str) -> str:
    """The comparison key: NFC, letter case folded letter by letter, spaces collapsed and trimmed."""
    folded = unicodedata.normalize("NFC", fold_letter_case(unicodedata.normalize("NFC", value)))
    return " ".join(folded.split())


class Table:
    """A reviewed mapping table, validated before any value is mapped."""

    def __init__(self, document: object, column: str) -> None:
        if not isinstance(document, dict) or set(document) != TABLE_KEYS:
            present = sorted(document) if isinstance(document, dict) else []
            raise Refusal("table_invalid", f"the table is one JSON object with exactly the keys {sorted(TABLE_KEYS)}; "
                                           f"found {present}")
        if document["record_type"] != TABLE_RECORD:
            raise Refusal("table_invalid", f"record_type is {TABLE_RECORD!r}")
        reviewer, reviewed_on = document["reviewed_by"], document["reviewed_on"]
        if not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer) > MAX_TEXT:
            raise Refusal("table_not_reviewed", "reviewed_by names the person or step that reviewed the table")
        if not isinstance(reviewed_on, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", reviewed_on):
            raise Refusal("table_not_reviewed", "reviewed_on is the review date written YYYY-MM-DD")
        try:
            dt.date.fromisoformat(reviewed_on)
        except ValueError:
            raise Refusal("table_not_reviewed", "reviewed_on is a real date written YYYY-MM-DD") from None
        columns = document["columns"]
        if not isinstance(columns, list) or not columns or any(not isinstance(item, str) or not item
                                                               for item in columns):
            raise Refusal("table_invalid", "columns is a nonempty list of column names")
        if column not in columns:
            raise Refusal("table_not_for_this_column", f"the table was reviewed for {columns!r}, not {column!r}")
        if not isinstance(document["targets_map_to_themselves"], bool):
            raise Refusal("table_invalid", "targets_map_to_themselves is true or false")
        entries = document["entries"]
        if not isinstance(entries, list) or len(entries) > MAX_ENTRIES:
            raise Refusal("table_invalid", f"entries is a list of at most {MAX_ENTRIES} objects")
        if not entries:
            raise Refusal("table_empty", "the table has no entries")
        self.reviewed_by, self.reviewed_on = reviewer, reviewed_on
        self.self_mapping = document["targets_map_to_themselves"]
        self.entries: list[tuple[str, str]] = []
        explicit: dict[str, str] = {}
        self.duplicates = 0
        for position, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict) or not {"from", "to"} <= set(entry) <= {"from", "to", "note"}:
                raise Refusal("table_invalid", f"entry {position} has from, to and an optional note")
            source, target = entry["from"], entry["to"]
            for label, text in (("from", source), ("to", target)):
                if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
                    raise Refusal("table_invalid", f"entry {position}: {label} is nonempty text of at most "
                                                   f"{MAX_TEXT} characters")
            if "note" in entry and not isinstance(entry["note"], str):
                raise Refusal("table_invalid", f"entry {position}: note is text")
            key = key_of(source)
            if key in explicit:
                if explicit[key] != target:
                    raise Refusal("table_conflicting_entries", f"entry {position} maps {source!r} to {target!r}, "
                                                               f"but another entry maps it to {explicit[key]!r}")
                self.duplicates += 1
                continue
            explicit[key] = target
            self.entries.append((source, target))
        targets: dict[str, str] = {}
        for target in explicit.values():
            other = targets.setdefault(key_of(target), target)
            if other != target:
                raise Refusal("table_targets_collide", f"targets {other!r} and {target!r} differ only in case "
                                                       "or spacing")
        for target_key, target in targets.items():
            if target_key in explicit and explicit[target_key] != target:
                reason = "table_conflicting_entries" if self.self_mapping else "table_chained_entries"
                raise Refusal(reason, f"{target!r} is a target, but an entry maps it on to "
                                      f"{explicit[target_key]!r}; one pass and two passes would differ")
        self.lookup: dict[str, tuple[str, str]] = {}
        if self.self_mapping:
            self.lookup.update({target_key: (target, "target_itself") for target_key, target in targets.items()})
        self.lookup.update({key: (target, "entry") for key, target in explicit.items()})
        self.targets = sorted(targets.values())


def delimiter_of(value: str) -> str:
    if value not in DELIMITERS:
        raise Refusal("delimiter_invalid", "--delimiter is comma, semicolon, pipe or tab")
    return DELIMITERS[value]


def root_of(value: str) -> Path:
    try:
        root = Path(value).resolve(strict=True)
    except (OSError, RuntimeError):
        raise Refusal("root_missing", "--root is not an existing folder") from None
    if not root.is_dir():
        raise Refusal("root_missing", "--root is not an existing folder")
    return root


def confined(root: Path, value: str, label: str) -> tuple[Path, Path]:
    """Return the path as written and its resolved form; refuse any path that leaves the root."""
    if not value or "\x00" in value:
        raise Refusal("path_invalid", f"{label} is empty or holds a NUL character")
    written = Path(value)
    if ".." in written.parts:
        raise Refusal("path_outside_root", f"{label} may not use '..'")
    joined = written if written.is_absolute() else root / written
    try:
        resolved = joined.resolve()
    except (OSError, RuntimeError):
        raise Refusal("path_invalid", f"{label} cannot be resolved") from None
    if resolved != root and not resolved.is_relative_to(root):
        raise Refusal("path_outside_root", f"{label} resolves outside --root, for example through a symbolic link")
    return joined, resolved


def read_file(root: Path, value: str, label: str, limit: int) -> tuple[Path, bytes]:
    _written, resolved = confined(root, value, label)
    try:
        info = resolved.stat()
    except OSError:
        raise Refusal("input_missing", f"{label} does not name an existing file") from None
    if not stat.S_ISREG(info.st_mode):
        raise Refusal("input_not_a_file", f"{label} is not a regular file")
    if info.st_size > limit:
        raise Refusal("input_too_large", f"{label} is larger than {limit} bytes")
    with open(resolved, "rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise Refusal("input_too_large", f"{label} is larger than {limit} bytes")
    return resolved, data


def strict_json(data: bytes) -> object:
    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                raise ValueError(f"key {key!r} appears twice")
            seen[key] = value
        return seen

    def constant(name):
        raise ValueError(f"{name} is not a JSON value")

    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeDecodeError, ValueError) as error:
        raise Refusal("table_invalid", f"the table is not strict UTF-8 JSON: {error}. --mapping must name a "
                                       f"{TABLE_RECORD} JSON file; a CSV sheet or a plain list is not read, and "
                                       "writing the table from one is a separate step with its own "
                                       "review") from None


def parse_table(data: bytes, delimiter: str) -> tuple[list[str], list[list[str]], str]:
    if b"\x00" in data:
        raise Refusal("input_not_text", "the input holds a NUL byte")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise Refusal("input_not_utf8", f"the input is not UTF-8 text (byte {error.start})") from None
    first_break = text.find("\n")
    newline = "\r\n" if first_break > 0 and text[first_break - 1] == "\r" else "\n"
    csv.field_size_limit(MAX_INPUT_BYTES)
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    try:
        rows = list(reader)
    except csv.Error as error:
        raise Refusal("csv_malformed", f"CSV line {reader.line_num}: {error}") from None
    if not rows or not any(cell.strip() for cell in rows[0]):
        raise Refusal("header_missing", "the first row must be a header row")
    header, body = rows[0], rows[1:]
    for number, row in enumerate(body, start=1):
        if not row and len(header) == 1:
            body[number - 1] = [""]  # a blank line in a one-column file is one empty value
        elif not row:
            raise Refusal("row_width_differs", f"data row {number} is a blank line; a file with {len(header)} "
                                               "columns has no blank rows, and a stray line break cannot be told "
                                               "apart from a lost row, so the file is refused")
        elif len(row) != len(header):
            raise Refusal("row_width_differs", f"data row {number} has {len(row)} fields; the header has "
                                               f"{len(header)}")
    return header, body, newline


def column_index(header: list[str], name: str) -> int:
    positions = [index for index, cell in enumerate(header) if cell == name]
    if not positions:
        raise Refusal("column_missing", f"no header cell equals {name!r}; header cells are {header[:50]!r}")
    if len(positions) > 1:
        raise Refusal("column_repeated", f"{len(positions)} header cells equal {name!r}")
    return positions[0]


def prepare_output(root: Path, value: str, input_path: Path) -> Path:
    written, resolved = confined(root, value, "--output")
    if os.path.lexists(written) or os.path.lexists(resolved):
        raise Refusal("output_exists", "--output names an existing path; the copy never replaces a file")
    if resolved == input_path:
        raise Refusal("output_is_input", "--output must differ from --input")
    if not resolved.parent.is_dir():
        raise Refusal("output_folder_missing", "the folder of --output does not exist")
    return resolved


def write_copy(target: Path, header: list[str], rows: list[list[str]], delimiter: str, newline: str) -> dict:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=delimiter, lineterminator=newline)
    writer.writerow(header)
    writer.writerows(rows)
    payload = buffer.getvalue().encode("utf-8")
    try:
        stream = open(target, "xb")
    except FileExistsError:
        raise Refusal("output_exists", "--output appeared while the script ran; nothing was replaced") from None
    try:
        with stream:
            stream.write(payload)
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}


def shown(value: str) -> str:
    return value if len(value) <= MAX_SHOWN_CHARACTERS else value[:MAX_SHOWN_CHARACTERS] + "...[cut]"


def arguments() -> Arguments:
    parser = Arguments(prog="map_categories.py", description="Map category values through a reviewed table only.")
    parser.add_argument("--input", required=True, help="CSV file, relative to --root")
    parser.add_argument("--column", required=True, help="exact header name of the category column")
    parser.add_argument("--mapping", required=True, help="reviewed category_mapping_table/v1 JSON file, relative to --root")
    parser.add_argument("--table-sha256", default=None,
                        help="SHA-256 of the reviewed table as the task gives it; other table bytes are refused")
    parser.add_argument("--root", default=".", help="folder that every path must stay inside (default: .)")
    parser.add_argument("--delimiter", default=",", help="comma (default), semicolon, pipe or tab")
    parser.add_argument("--output", default=None, help="new CSV copy to write, relative to --root")
    parser.add_argument("--output-column", default=None, help="name of the added column (default: COLUMN_mapped)")
    return parser


def run(argv: list[str] | None) -> tuple[dict, int]:
    options = arguments().parse_args(argv)
    delimiter = delimiter_of(options.delimiter)
    expected = None
    if options.table_sha256 is not None:
        expected = options.table_sha256.strip().lower()
        if not SHA256_TEXT.fullmatch(expected):
            raise Refusal("arguments_invalid", "--table-sha256 is the table's SHA-256 as 64 hexadecimal characters")
    root = root_of(options.root)
    _table_path, table_bytes = read_file(root, options.mapping, "--mapping", MAX_TABLE_BYTES)
    table_digest = hashlib.sha256(table_bytes).hexdigest()
    if expected is not None and table_digest != expected:
        raise Refusal("table_digest_differs", f"the table's SHA-256 is {table_digest}, but --table-sha256 names "
                                              f"{expected}; these are not the reviewed bytes, so nothing is mapped")
    table = Table(strict_json(table_bytes), options.column)
    input_path, data = read_file(root, options.input, "--input", MAX_INPUT_BYTES)
    header, rows, newline = parse_table(data, delimiter)
    index = column_index(header, options.column)
    target = output_column = None
    if options.output is not None:
        output_column = options.output_column or f"{options.column}_mapped"
        if output_column in header:
            raise Refusal("output_column_exists", f"the header already has a column named {output_column!r}")
        target = prepare_output(root, options.output, input_path)

    mapped_cells: list[str] = []
    empty = mapped = unmapped = changed = 0
    mapped_by = {"entry": 0, "target_itself": 0}
    target_counts: dict[str, int] = {}
    used: set[str] = set()
    missing: dict[str, dict] = {}
    for number, row in enumerate(rows, start=1):
        value = row[index]
        if not value.strip():
            empty += 1
            mapped_cells.append("")
            continue
        key = key_of(value)
        found = table.lookup.get(key)
        if found is None:
            unmapped += 1
            mapped_cells.append("")
            record = missing.setdefault(key, {"count": 0, "spellings": [], "first_data_rows": []})
            record["count"] += 1
            if value not in record["spellings"] and len(record["spellings"]) < MAX_SPELLINGS_SHOWN:
                record["spellings"].append(value)
            if len(record["first_data_rows"]) < MAX_ROWS_SHOWN:
                record["first_data_rows"].append(number)
            continue
        result, source = found
        mapped += 1
        mapped_by[source] += 1
        changed += result != value
        target_counts[result] = target_counts.get(result, 0) + 1
        if source == "entry":
            used.add(key)
        mapped_cells.append(result)

    unmapped_values = [{"key": shown(key), "count": record["count"],
                        "spellings": [shown(item) for item in record["spellings"]],
                        "first_data_rows": record["first_data_rows"]}
                       for key, record in sorted(missing.items(), key=lambda item: (-item[1]["count"], item[0]))]
    unused = [{"from": source, "to": result} for source, result in table.entries if key_of(source) not in used]

    output = None
    if target is not None:
        copied = [row + [cell] for row, cell in zip(rows, mapped_cells)]
        written = write_copy(target, header + [output_column], copied, delimiter, newline)
        output = {"path": options.output, "column": output_column, "data_rows": len(rows), **written}

    document = {
        "tool": TOOL, "version": VERSION, "status": "values_unmapped" if unmapped else "all_mapped",
        "input": {"path": options.input, "sha256": hashlib.sha256(data).hexdigest(), "column": options.column,
                  "delimiter": delimiter},
        "table": {"path": options.mapping, "sha256": table_digest, "sha256_pinned": expected is not None,
                  "reviewed_by": table.reviewed_by, "reviewed_on": table.reviewed_on,
                  "entries": len(table.entries), "duplicate_entries": table.duplicates,
                  "targets": len(table.targets), "targets_map_to_themselves": table.self_mapping},
        "counts": {"data_rows": len(rows), "empty": empty, "mapped": mapped, "unmapped": unmapped},
        "mapped_by": mapped_by,
        "mapped_values_changed": changed,
        "target_counts": dict(sorted(target_counts.items())),
        "unused_entries": unused[:MAX_UNUSED_LISTED],
        "unused_entries_total": len(unused),
        "unmapped_values": unmapped_values[:MAX_LISTED],
        "unmapped_values_distinct": len(unmapped_values),
        "unmapped_values_complete": len(unmapped_values) <= MAX_LISTED,
        "output": output,
    }
    return document, EXIT_REVIEW if unmapped else EXIT_DONE


def render(document: dict) -> str:
    """One JSON object: one line per top-level key and one line per listed entry."""
    lines = []
    keys = list(document)
    for position, key in enumerate(keys):
        value, tail = document[key], "," if position + 1 < len(keys) else ""
        if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            inner = ",\n".join("  " + json.dumps(item, ensure_ascii=False) for item in value)
            lines.append(f" {json.dumps(key)}: [\n{inner}\n ]{tail}")
        else:
            lines.append(f" {json.dumps(key)}: {json.dumps(value, ensure_ascii=False)}{tail}")
    return "{\n" + "\n".join(lines) + "\n}\n"


def emit(document: dict) -> None:
    sys.stdout.buffer.write(render(document).encode("utf-8"))
    sys.stdout.buffer.flush()


def main(argv: list[str] | None = None) -> int:
    try:
        document, code = run(argv)
    except Refusal as refusal:
        document, code = {"tool": TOOL, "version": VERSION, "status": "refused", "reason": refusal.reason,
                          "detail": refusal.detail}, EXIT_REFUSED
    except Exception as error:  # noqa: BLE001 - report instead of a bare traceback
        document, code = {"tool": TOOL, "version": VERSION, "status": "refused", "reason": "internal_error",
                          "detail": f"{type(error).__name__}: {error}"}, EXIT_REFUSED
    emit(document)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
