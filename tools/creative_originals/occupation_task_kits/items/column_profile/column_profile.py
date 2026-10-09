"""Column profile: summarize every column of a CSV table without any rules declared in advance.

For each column: missing values, distinct values, the narrowest type every present value fits (boolean, integer,
number, date, string), the most frequent values, value shapes (digits become 9, letters A or a), text lengths, and
for numbers the minimum, quartiles, median, maximum, mean, population standard deviation and outliers outside the
interquartile fences. For dates the earliest and latest. Table-level checks report exact duplicate rows, constant
columns and columns mostly empty. A pure function of its JSON input; the command line reads standard input and
writes standard output.
"""
from __future__ import annotations

import collections
import csv
import datetime
import io
import math
import re

from kit_schema import KitRefusal, check, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "header_missing": "the CSV text has no header row",
    "duplicate_column_name": "two columns share a name",
    "ragged_rows": "a row has a different number of cells than the header",
}
INPUT_SCHEMA = {
    "type": "object", "required": ["csv_text"], "additionalProperties": False,
    "properties": {
        "csv_text": {"type": "string", "minLength": 1, "maxLength": 5000000, "description": "CSV with a header row"},
        "top_values": {"type": "integer", "minimum": 1, "maximum": 50,
                       "description": "most frequent values listed per column (default 5)"},
        "outlier_factor": {"type": "number", "exclusiveMinimum": 0, "maximum": 10,
                           "description": "interquartile range multiple for outlier fences (default 1.5)"},
        "missing_markers": {"type": "array", "items": {"type": "string"}, "maxItems": 20,
                            "description": "cell values treated as missing besides empty text (default NA, N/A, null)"},
    },
}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["table", "columns"],
    "properties": {
        "table": {"type": "object", "required": ["rows", "columns", "duplicate_rows", "constant_columns",
                                                 "mostly_missing_columns"],
                  "description": "row and column counts and table-level findings"},
        "columns": {"type": "array", "description": "one profile per column in header order",
                    "items": {"type": "object", "required": ["name", "inferred_type", "present", "missing",
                                                             "missing_share", "distinct", "top_values", "shapes"]}},
    },
}
_INTEGER = re.compile(r"^[+-]?\d+$")
_NUMBER = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_BOOLEANS = {"true", "false", "yes", "no", "y", "n"}
#: The column types infer_type reports: empty when no value is present, otherwise the narrowest type every value fits.
INFERRED_TYPES = (EMPTY, BOOLEAN, INTEGER, NUMBER, DATE, STRING) = (
    "empty", "boolean", "integer", "number", "date", "string")


def shape(value: str) -> str:
    return re.sub(r"[a-z]", "a", re.sub(r"[A-Z]", "A", re.sub(r"\d", "9", value)))


def percentile(ordered: list, share: float) -> float:
    """Linear interpolation between closest ranks on sorted values."""
    if len(ordered) == 1:
        return ordered[0]
    position = share * (len(ordered) - 1)
    low = math.floor(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def infer_type(values: list) -> str:
    if not values:
        return EMPTY
    if all(value.lower() in _BOOLEANS for value in values):
        return BOOLEAN
    if all(_INTEGER.match(value) for value in values):
        return INTEGER
    if all(_NUMBER.match(value) and math.isfinite(float(value)) for value in values):
        return NUMBER
    if all(_DATE.match(value) for value in values):
        try:
            for value in values:
                datetime.date.fromisoformat(value)
            return DATE
        except ValueError:
            pass
    return STRING


def number(value: float):
    value = round(value, 6)
    return int(value) if float(value).is_integer() else value


def profile_column(name: str, cells: list, markers: set, top: int, factor: float) -> dict:
    present = [cell.strip() for cell in cells if cell.strip() and cell.strip() not in markers]
    counts = collections.Counter(present)
    kind = infer_type(present)
    row = {"name": name, "inferred_type": kind, "present": len(present), "missing": len(cells) - len(present),
           "missing_share": round((len(cells) - len(present)) / len(cells), 4) if cells else 0.0,
           "distinct": len(counts),
           "top_values": [{"value": value, "count": count}
                          for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:top]],
           "shapes": [{"shape": value, "count": count} for value, count in
                      sorted(collections.Counter(shape(value) for value in present).items(),
                             key=lambda item: (-item[1], item[0]))[:5]]}
    if present:
        lengths = [len(value) for value in present]
        row["length"] = {"min": min(lengths), "max": max(lengths)}
    if kind in (INTEGER, NUMBER) and present:
        numbers = sorted(float(value) for value in present)
        mean = sum(numbers) / len(numbers)
        q1, median, q3 = (percentile(numbers, share) for share in (0.25, 0.5, 0.75))
        low, high = q1 - factor * (q3 - q1), q3 + factor * (q3 - q1)
        row["numeric"] = {"min": number(numbers[0]), "q1": number(q1), "median": number(median), "q3": number(q3),
                          "max": number(numbers[-1]), "mean": number(mean),
                          "std": number(math.sqrt(sum((value - mean) ** 2 for value in numbers) / len(numbers))),
                          "outliers": sum(1 for value in numbers if value < low or value > high),
                          "fences": [number(low), number(high)]}
    if kind == DATE:
        row["date_range"] = {"min": min(present), "max": max(present)}
    return row


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    table = [row for row in csv.reader(io.StringIO(payload["csv_text"])) if any(cell.strip() for cell in row)]
    if not table:
        raise KitRefusal("header_missing", "no rows")
    header = [name.strip() for name in table[0]]
    if len(set(header)) != len(header) or not all(header):
        raise KitRefusal("duplicate_column_name", "column names must be distinct and not empty")
    body = table[1:]
    ragged = [index + 2 for index, row in enumerate(body) if len(row) != len(header)]
    if ragged:
        raise KitRefusal("ragged_rows", "CSV line numbers " + ", ".join(str(line) for line in ragged[:10]))
    markers = set(payload.get("missing_markers", ["NA", "N/A", "null"]))
    top, factor = payload.get("top_values", 5), payload.get("outlier_factor", 1.5)
    columns = [profile_column(name, [row[index] for row in body], markers, top, factor)
               for index, name in enumerate(header)]
    seen = collections.Counter(tuple(cell.strip() for cell in row) for row in body)
    return {"table": {"rows": len(body), "columns": len(header),
                      "duplicate_rows": sum(count - 1 for count in seen.values() if count > 1),
                      "constant_columns": [column["name"] for column in columns if column["distinct"] == 1
                                           and column["missing"] == 0],
                      "mostly_missing_columns": [column["name"] for column in columns
                                                 if column["missing_share"] > 0.5]},
            "columns": columns}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
