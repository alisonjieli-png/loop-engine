"""Read one table of a Kaggle dataset from a file the caller supplies and check every row against the dataset's
schema. Standard library only; nothing is fetched, written or run.

The kaggle_public_good supply line writes DATASET, TABLES and DATA_FILES for each dataset between the generated
markers below and keeps the rest of this module byte for byte, so every dataset package shares one reviewed reader.
Here they are empty, so the module can be imported and tested on its own.

```text
TABLES[name]
├── files: the dataset's file names that hold this table (shards of one family share one table)
├── format: delimited_text (with its delimiter), json_lines or json (an array of objects)
├── fields: each column with the JSON types its values take ("null" when a value may be empty) and an ISO 8601
│   format (date or date-time) when every value has one
└── required: the columns every row holds
```

A delimited cell is typed by its column: integer, number, boolean (true or false), an ISO date or date-time, or
text; an empty cell is None where the column is nullable. A row that lacks a required column, names a column the
table does not declare, holds a value of another type, or has a different number of cells than the header is
refused with SchemaError and a reason from REASONS.
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

#: <generated> The supply line replaces these three assignments with the dataset's own values.
DATASET = {}
TABLES = {}
DATA_FILES = {}
#: </generated>

REASONS = ("unknown_table", "file_unreadable", "not_utf8", "header_missing", "missing_column", "unknown_column",
           "repeated_column", "ragged_record", "wrong_type", "missing_value", "not_json", "not_an_object",
           "changed_file", "unknown_data_file")
DELIMITED, JSON_LINES, JSON_DOCUMENT = "delimited_text", "json_lines", "json"
#: The JSON types a column declares.
STRING, INTEGER, NUMBER, BOOLEAN, NULL, ARRAY, OBJECT = JSON_TYPES = (
    "string", "integer", "number", "boolean", "null", "array", "object")
#: The command line option that lists the tables instead of checking a file.
TABLES_OPTION = "--tables"
DATE_FORMAT, DATE_TIME_FORMAT = "date", "date-time"
#: The largest delimited field read; a column holding a whole document is still read.
FIELD_CHARACTERS = 16 * 1024 * 1024
_INTEGER = re.compile(r"[+-]?(?:0|[1-9][0-9]*)")
_NUMBER = re.compile(r"[+-]?(?:[0-9]+\.[0-9]*|\.[0-9]+|[0-9]+)(?:[eE][+-]?[0-9]+)?")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_DATE_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}(?::[0-9]{2}(?:\.[0-9]{1,9})?)?"
                        r"(?:Z|[+-][0-9]{2}:?[0-9]{2})?")
_BOOLEANS = {"true": True, "false": False}
_NOT_CONVERTED = object()


class SchemaError(ValueError):
    """A table file or a row that breaks the dataset's schema; ``reason`` is one of REASONS."""

    def __init__(self, reason: str, detail: str = "", *, table=None, row=None, column=None) -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason, self.detail, self.table, self.row, self.column = reason, detail, table, row, column

    def to_dict(self) -> dict:
        return {"refused": True, "reason": self.reason, "detail": self.detail, "table": self.table, "row": self.row,
                "column": self.column}


def table_names() -> list:
    """The tables this dataset declares, in name order."""
    return sorted(TABLES)


def table_spec(table: str) -> dict:
    """The declaration of one table; SchemaError unknown_table for a name the dataset does not declare."""
    if table not in TABLES:
        raise SchemaError("unknown_table", f"{table!r} is not one of {table_names()}", table=table)
    return TABLES[table]


def table_for_file(name: str):
    """The table a file of the dataset belongs to, by its file name, or None."""
    base = Path(str(name)).name
    for table, spec in TABLES.items():
        if base in spec["files"]:
            return table
    return None


def _valid_date(text: str) -> bool:
    try:
        datetime.date.fromisoformat(text[:10])
    except ValueError:
        return False
    return True


def _format_holds(value: str, form) -> bool:
    if form == DATE_FORMAT:
        return bool(_DATE.fullmatch(value)) and _valid_date(value)
    if form == DATE_TIME_FORMAT:
        return bool(_DATE.fullmatch(value) or _DATE_TIME.fullmatch(value)) and _valid_date(value)
    return True


def _convert(kind: str, form, text: str):
    if kind == INTEGER and _INTEGER.fullmatch(text):
        return int(text)
    if kind == NUMBER and _NUMBER.fullmatch(text):
        return int(text) if _INTEGER.fullmatch(text) else float(text)
    if kind == BOOLEAN and text.lower() in _BOOLEANS:
        return _BOOLEANS[text.lower()]
    if kind == STRING and _format_holds(text, form):
        return text
    return _NOT_CONVERTED


#: The Python types of each JSON type other than the numbers, which exclude booleans.
_PYTHON_TYPES = {BOOLEAN: bool, STRING: str, ARRAY: list, OBJECT: dict, NULL: type(None)}


def _is(kind: str, value) -> bool:
    if kind == INTEGER:
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == NUMBER:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _PYTHON_TYPES.get(kind, ()))


def parse_cell(table: str, column: str, text: str):
    """The typed value of one delimited cell of ``column``: None for an empty cell of a nullable column."""
    spec = table_spec(table)
    field = spec["fields"].get(column)
    if field is None:
        raise SchemaError("unknown_column", f"{column!r} is not a column of {table}", table=table, column=column)
    if not text:
        if NULL in field["type"]:
            return None
        raise SchemaError("missing_value", f"{column} is empty", table=table, column=column)
    for kind in field["type"]:
        value = _convert(kind, field.get("format"), text)
        if value is not _NOT_CONVERTED:
            return value
    wanted = " or ".join(kind for kind in field["type"] if kind != NULL)
    raise SchemaError("wrong_type", f"{column}: {text[:60]!r} is not {wanted}", table=table, column=column)


def check_value(table: str, column: str, value):
    """One JSON value of ``column`` against the column's types and format; the value when it holds."""
    field = table_spec(table)["fields"].get(column)
    if field is None:
        raise SchemaError("unknown_column", f"{column!r} is not a column of {table}", table=table, column=column)
    for kind in field["type"]:
        if _is(kind, value) and (kind != STRING or _format_holds(value, field.get("format"))):
            return value
    wanted = " or ".join(field["type"])
    raise SchemaError("wrong_type", f"{column}: {type(value).__name__} is not {wanted}", table=table, column=column)


def check_row(table: str, row, *, number=None) -> dict:
    """A row (a dict of values) against the table: required columns present, no unknown column, typed values."""
    spec = table_spec(table)
    if not isinstance(row, dict):
        raise SchemaError("not_an_object", "a row is an object", table=table, row=number)
    missing = [column for column in spec["required"] if column not in row]
    if missing:
        raise SchemaError("missing_column", f"lacks {missing[:5]}", table=table, row=number, column=missing[0])
    for column, value in row.items():
        if column not in spec["fields"]:
            raise SchemaError("unknown_column", f"{column!r} is not a column of {table}", table=table, row=number,
                              column=column)
        try:
            check_value(table, column, value)
        except SchemaError as error:
            error.row = number
            raise
    return row


def _check_header(table: str, spec: dict, header: list) -> None:
    repeated = sorted({name for name in header if header.count(name) > 1})
    if repeated:
        raise SchemaError("repeated_column", f"{repeated[:5]} repeat", table=table, column=repeated[0])
    missing = [column for column in spec["required"] if column not in header]
    if missing:
        raise SchemaError("missing_column", f"the header lacks {missing[:5]}", table=table, column=missing[0])
    unknown = [column for column in header if column not in spec["fields"]]
    if unknown:
        raise SchemaError("unknown_column", f"the header names {unknown[:5]}", table=table, column=unknown[0])


def _delimited_rows(table: str, spec: dict, path: Path, limit):
    saved = csv.field_size_limit()
    csv.field_size_limit(FIELD_CHARACTERS)
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle, delimiter=spec["delimiter"])
            try:
                header = next(reader)
            except StopIteration:
                raise SchemaError("header_missing", f"{Path(path).name} is empty", table=table) from None
            _check_header(table, spec, header)
            count = 0
            for number, record in enumerate(reader, 1):
                if not record:
                    continue
                if len(record) != len(header):
                    raise SchemaError("ragged_record", f"{len(record)} cells under {len(header)} columns",
                                      table=table, row=number)
                row = {}
                for column, text in zip(header, record):
                    try:
                        row[column] = parse_cell(table, column, text)
                    except SchemaError as error:
                        error.row = number
                        raise
                yield row
                count += 1
                if limit is not None and count >= limit:
                    return
    except UnicodeDecodeError as error:
        raise SchemaError("not_utf8", str(error)[:120], table=table) from None
    finally:
        csv.field_size_limit(saved)


def _json_line_rows(table: str, path: Path, limit):
    count = 0
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except ValueError as error:
                    raise SchemaError("not_json", str(error)[:120], table=table, row=number) from None
                yield check_row(table, row, number=number)
                count += 1
                if limit is not None and count >= limit:
                    return
    except UnicodeDecodeError as error:
        raise SchemaError("not_utf8", str(error)[:120], table=table) from None


def _json_array_rows(table: str, path: Path, limit):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except UnicodeDecodeError as error:
        raise SchemaError("not_utf8", str(error)[:120], table=table) from None
    except ValueError as error:
        raise SchemaError("not_json", str(error)[:120], table=table) from None
    if not isinstance(value, list):
        raise SchemaError("not_an_object", "the file is not an array of objects", table=table)
    for number, row in enumerate(value[:limit] if limit is not None else value, 1):
        yield check_row(table, row, number=number)


def read_rows(table: str, path, *, limit=None):
    """Every row of one table file as a dict of typed values, in file order; the first row that breaks the schema
    raises SchemaError. ``limit`` stops after that many rows."""
    spec = table_spec(table)
    path = Path(path)
    if not path.is_file():
        raise SchemaError("file_unreadable", f"{path.name} is not a file", table=table)
    if spec["format"] == DELIMITED:
        return _delimited_rows(table, spec, path, limit)
    if spec["format"] == JSON_LINES:
        return _json_line_rows(table, path, limit)
    return _json_array_rows(table, path, limit)


def read_table(table: str, path, *, limit=None) -> list:
    """The rows of one table file as a list (read_rows, collected)."""
    return list(read_rows(table, path, limit=limit))


def validate_file(table: str, path) -> dict:
    """Read a whole table file under the schema and report its rows and columns; SchemaError at the first fault."""
    rows, columns = 0, set()
    for row in read_rows(table, path):
        rows += 1
        columns.update(row)
    return {"table": table, "file": Path(path).name, "rows": rows, "columns": sorted(columns)}


def check_data_file(path) -> str:
    """The SHA-256 of a data file this package carries, which must be the recorded one."""
    path = Path(path)
    recorded = DATA_FILES.get(path.name)
    if recorded is None:
        raise SchemaError("unknown_data_file", f"{path.name} is not a data file of this package")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != recorded["sha256"]:
        raise SchemaError("changed_file", f"{path.name} is not the recorded file (SHA-256 {recorded['sha256']})")
    return digest


def main(argv=None, stdout=None) -> int:
    """``python <module>.py TABLE PATH`` checks one table file and prints a JSON summary (exit 0) or a refusal
    (exit 2); ``--tables`` lists the tables."""
    argv = list(sys.argv[1:] if argv is None else argv)
    stdout = sys.stdout if stdout is None else stdout
    if argv == [TABLES_OPTION]:
        stdout.write(json.dumps({"dataset": DATASET.get("identity"), "tables": table_names()}, indent=1) + "\n")
        return 0
    if len(argv) != 2:
        stdout.write(json.dumps(SchemaError("unknown_table", "usage: TABLE PATH or --tables").to_dict()) + "\n")
        return 2
    try:
        result = validate_file(argv[0], argv[1])
    except SchemaError as error:
        stdout.write(json.dumps(error.to_dict(), indent=1) + "\n")
        return 2
    stdout.write(json.dumps(result, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
