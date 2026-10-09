"""Record entry validator: check and normalize rows of records against declared field rules.

Rows come as CSV text with a header or as a list of objects. Each field rule names a type (string, integer, number,
date, boolean, email, phone), whether it is required, and optional allowed values, a pattern, numeric bounds, a
maximum length and normalization steps (trim, collapse_spaces, upper, lower, title, digits_only, iso_date). Values
are normalized first, then checked. Combined unique keys are checked across rows. The result counts errors by rule
and field, lists the first errors with row numbers, and returns the normalized rows. A pure function of its JSON
input; the command line reads standard input and writes standard output.
"""
from __future__ import annotations

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
    "duplicate_field_rule": "two field rules name the same field",
    "invalid_pattern": "a field pattern is not a valid regular expression",
    "missing_required_column": "a required field has no column at all",
    "unknown_unique_field": "a unique key names a field without a rule",
    "invalid_date_format": "a date format is not a strftime format with year, month and day",
}
TYPES = (STRING, INTEGER, NUMBER, DATE, BOOLEAN, EMAIL, PHONE) = (
    "string", "integer", "number", "date", "boolean", "email", "phone")
STEPS = ("trim", "collapse_spaces", "upper", "lower", "title", "digits_only", "iso_date")
INPUT_SCHEMA = {
    "type": "object", "required": ["fields"], "additionalProperties": False,
    "anyOf": [{"required": ["csv_text"]}, {"required": ["rows"]}],
    "properties": {
        "csv_text": {"type": "string", "maxLength": 5000000, "description": "CSV with a header row"},
        "rows": {"type": "array", "maxItems": 100000, "items": {"type": "object"},
                 "description": "records as objects, used when csv_text is absent"},
        "fields": {"type": "array", "minItems": 1, "maxItems": 300, "description":
                   "rules: name, type, required, allowed, pattern, minimum, maximum, max_length, normalize steps",
                   "items": {"type": "object", "required": ["name", "type"], "additionalProperties": False,
                             "properties": {"name": {"type": "string", "minLength": 1},
                                            "type": {"enum": list(TYPES)}, "required": {"type": "boolean"},
                                            "allowed": {"type": "array", "items": {"type": "string"}},
                                            "pattern": {"type": "string"}, "minimum": {"type": "number"},
                                            "maximum": {"type": "number"},
                                            "max_length": {"type": "integer", "minimum": 1},
                                            "normalize": {"type": "array", "items": {"enum": list(STEPS)}}}}},
        "unique": {"type": "array", "items": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                   "description": "lists of field names whose combined values must not repeat"},
        "date_formats": {"type": "array", "items": {"type": "string"}, "maxItems": 10,
                         "description": "strftime formats the iso_date step accepts (default %Y-%m-%d)"},
        "allow_extra_columns": {"type": "boolean", "description": "accept columns without a rule (default true)"},
        "max_errors": {"type": "integer", "minimum": 1, "maximum": 10000,
                       "description": "how many error rows to list (default 200); counts are always complete"},
        "return_rows": {"type": "boolean", "description": "include normalized rows in the result (default true)"},
    },
}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["summary", "columns", "errors"],
    "properties": {
        "summary": {"type": "object", "required": ["rows", "valid_rows", "invalid_rows", "errors_by_rule",
                                                   "errors_by_field"],
                    "description": "row and error counts"},
        "columns": {"type": "object", "description": "missing optional columns and extra columns"},
        "errors": {"type": "array", "description": "first errors: data row number (1 is the first data row), "
                                                   "field, rule and value",
                   "items": {"type": "object", "required": ["row", "field", "rule"]}},
        "rows": {"type": "array", "items": {"type": "object"}, "description": "normalized rows"},
    },
}
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_INTEGER = re.compile(r"^[+-]?\d+$")
_BOOLEAN = {"true": "true", "yes": "true", "y": "true", "1": "true", "false": "false", "no": "false", "n": "false",
            "0": "false"}


def read_rows(payload: dict) -> tuple:
    """(header, rows as dicts of text) from csv_text or rows."""
    if "csv_text" in payload:
        reader = csv.reader(io.StringIO(payload["csv_text"]))
        table = [row for row in reader if any(cell.strip() for cell in row)]
        if not table:
            raise KitRefusal("header_missing", "the CSV text is empty")
        header = [name.strip() for name in table[0]]
        rows = [{name: (row[index] if index < len(row) else "") for index, name in enumerate(header)}
                for row in table[1:]]
        return header, rows
    header = []
    for row in payload["rows"]:
        for name in row:
            if name not in header:
                header.append(name)
    rows = [{name: ("" if row.get(name) is None else str(row.get(name))) for name in header}
            for row in payload["rows"]]
    return header, rows


def normalize(value: str, steps: list, formats: list) -> tuple:
    """(normalized text, error rule or empty string)."""
    for step in steps:
        if step == "trim":
            value = value.strip()
        elif step == "collapse_spaces":
            value = re.sub(r"\s+", " ", value).strip()
        elif step == "upper":
            value = value.upper()
        elif step == "lower":
            value = value.lower()
        elif step == "title":
            value = " ".join(word[:1].upper() + word[1:].lower() for word in value.split(" "))
        elif step == "digits_only":
            value = re.sub(r"\D", "", value)
        elif step == "iso_date" and value.strip():
            for pattern in formats:
                try:
                    value = datetime.datetime.strptime(value.strip(), pattern).date().isoformat()
                    break
                except ValueError:
                    continue
            else:
                return value, "date_unparseable"
    return value, ""


def type_problem(value: str, kind: str) -> str:
    if kind == INTEGER and not _INTEGER.match(value):
        return "not_integer"
    if kind == NUMBER:
        try:
            if not math.isfinite(float(value)):
                return "not_number"
        except ValueError:
            return "not_number"
    if kind == DATE:
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            return "not_iso_date"
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            return "not_iso_date"
    if kind == BOOLEAN and value.lower() not in _BOOLEAN:
        return "not_boolean"
    if kind == EMAIL and not _EMAIL.match(value):
        return "not_email"
    if kind == PHONE and not 7 <= len(re.sub(r"\D", "", value)) <= 15:
        return "not_phone"
    return ""


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    rules = payload["fields"]
    names = [rule["name"] for rule in rules]
    if len(set(names)) != len(names):
        raise KitRefusal("duplicate_field_rule", "field rule names repeat")
    patterns = {}
    for rule in rules:
        if "pattern" in rule:
            try:
                patterns[rule["name"]] = re.compile(rule["pattern"])
            except re.error as error:
                raise KitRefusal("invalid_pattern", f"{rule['name']}: {error}") from None
    formats = payload.get("date_formats", ["%Y-%m-%d"])
    for pattern in formats:
        if not all(token in pattern for token in ("%Y", "%m", "%d")) and not all(
                token in pattern for token in ("%Y", "%b", "%d")):
            raise KitRefusal("invalid_date_format", pattern)
    for key in payload.get("unique", []):
        unknown = [name for name in key if name not in names]
        if unknown:
            raise KitRefusal("unknown_unique_field", ", ".join(unknown))
    header, rows = read_rows(payload)
    missing_required = [rule["name"] for rule in rules if rule.get("required") and rule["name"] not in header]
    if missing_required:
        raise KitRefusal("missing_required_column", ", ".join(missing_required))
    columns = {"missing_optional": [rule["name"] for rule in rules if rule["name"] not in header],
               "extra": [name for name in header if name not in names]}
    errors, by_rule, by_field, bad_rows, cleaned = [], {}, {}, set(), []
    limit = payload.get("max_errors", 200)

    def note(row_number, field, rule_name, value):
        by_rule[rule_name] = by_rule.get(rule_name, 0) + 1
        by_field[field] = by_field.get(field, 0) + 1
        bad_rows.add(row_number)
        if len(errors) < limit:
            errors.append({"row": row_number, "field": field, "rule": rule_name, "value": value})

    if not payload.get("allow_extra_columns", True):
        for name in columns["extra"]:
            note(0, name, "extra_column", "")
    for number, row in enumerate(rows, 1):
        out = dict(row)
        for rule in rules:
            name = rule["name"]
            if name not in row:
                continue
            value, problem = normalize(row[name], rule.get("normalize", []), formats)
            out[name] = value
            if problem:
                note(number, name, problem, row[name])
                continue
            if not value.strip():
                if rule.get("required"):
                    note(number, name, "required", value)
                continue
            if rule["type"] == BOOLEAN and value.lower() in _BOOLEAN:
                out[name] = value = _BOOLEAN[value.lower()]
            problem = type_problem(value, rule["type"])
            if problem:
                note(number, name, problem, value)
                continue
            if "allowed" in rule and value not in rule["allowed"]:
                note(number, name, "not_allowed", value)
            if name in patterns and not patterns[name].search(value):
                note(number, name, "pattern", value)
            if "max_length" in rule and len(value) > rule["max_length"]:
                note(number, name, "too_long", value)
            if rule["type"] in (INTEGER, NUMBER):
                number_value = float(value)
                if "minimum" in rule and number_value < rule["minimum"]:
                    note(number, name, "below_minimum", value)
                if "maximum" in rule and number_value > rule["maximum"]:
                    note(number, name, "above_maximum", value)
        cleaned.append(out)
    for key in payload.get("unique", []):
        seen = {}
        for number, row in enumerate(cleaned, 1):
            values = tuple(row.get(name, "").strip().lower() for name in key)
            if not any(values):
                continue
            if values in seen:
                note(number, "+".join(key), "duplicate_key", "|".join(row.get(name, "") for name in key))
            else:
                seen[values] = number
    data_rows = {number for number in bad_rows if number > 0}
    result = {"summary": {"rows": len(rows), "valid_rows": len(rows) - len(data_rows),
                          "invalid_rows": len(data_rows), "errors_by_rule": dict(sorted(by_rule.items())),
                          "errors_by_field": dict(sorted(by_field.items()))},
              "columns": columns, "errors": errors}
    if payload.get("return_rows", True):
        result["rows"] = cleaned
    return result


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
