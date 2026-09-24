"""Check a CSV file against a JSON column contract. Effects: reads the named files under --root or one JSON bundle; prints one JSON object; writes nothing, starts no process and uses no network.

Exit status: 0 every contract rule held, 1 at least one rule broke, 2 no verdict (refused input or an
internal error). Only rules written in the contract are applied. An unknown contract key or type is
refused, so that a typing error in the contract cannot switch a rule off.

Usage:
    python3 -I -B check_column_contract.py --csv TABLE.csv --contract CONTRACT.json [--root DIR]
        [--delimiter comma|tab|semicolon|pipe] [--max-examples N] [--no-values] [--max-bytes N]
    python3 -I -B check_column_contract.py --bundle FILE_OR_DASH

A bundle is one JSON object with the members "csv" (the table text) and "contract" (an object or its
text). A member replaces the file of the same name; "-" reads the bundle from standard input.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

RECORD_TYPE = "column_contract_check/v1"
CONTRACT_TYPE = "column_contract/v1"
DEFAULT_MAX_BYTES = 64 * 1024 * 1024
HARD_MAX_BYTES = 1024 * 1024 * 1024
DELIMITERS = {"comma": ",", "tab": "\t", "semicolon": ";", "pipe": "|"}
TYPES = ("string", "integer", "decimal", "boolean", "date", "datetime")
DEFAULT_FORMATS = {"date": "%Y-%m-%d", "datetime": "%Y-%m-%dT%H:%M:%S"}
INTEGER = re.compile(r"[+-]?[0-9]{1,4000}")
DECIMAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,6})?")
CONTRACT_KEYS = {"record_type", "description", "columns", "empty_values", "extra_columns", "column_order",
                 "row_count", "unique_together"}
COLUMN_KEYS = {"name", "type", "required", "empty", "max_empty_share", "allowed", "min", "max", "min_length",
               "max_length", "unique", "format", "true_values", "false_values", "trimmed", "description"}
BUNDLE_MEMBERS = {"csv", "contract"}
PER_RULE_EXAMPLES = 3
EXCERPT = 60


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


def strict_json(data: bytes, label: str):
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
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except UnicodeDecodeError as error:
        raise Refused("not_utf8", f"{label}: byte {error.start} is not UTF-8") from None
    except ValueError as error:
        raise Refused("json_invalid", f"{label}: {error}") from None


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
            data = sys.stdin.buffer.read(limit + 1) if bundle == "-" else self.read_file(bundle)
            if len(data) > limit:
                raise Refused("input_too_large", f"the bundle is larger than {limit} bytes")
            value = strict_json(data, "the bundle")
            if not isinstance(value, dict):
                raise Refused("bundle_invalid", "the bundle is one JSON object")
            unknown = sorted(set(value) - BUNDLE_MEMBERS)
            if unknown:
                raise Refused("bundle_invalid", f"unknown bundle members {unknown}; allowed {sorted(BUNDLE_MEMBERS)}")
            self.bundle = value

    def read_file(self, value: str) -> bytes:
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
        return data

    def get(self, name: str, path: str | None, json_allowed: bool) -> tuple[str, bytes]:
        if self.bundle is not None and name in self.bundle:
            if path is not None:
                raise Refused("bad_arguments", f"--{name} and the bundle member {name!r} were both given; use one")
            value = self.bundle[name]
            if json_allowed and isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False, indent=1)
            if not isinstance(value, str):
                raise Refused("bundle_invalid", f"bundle member {name!r} must hold the file text")
            try:
                return f"bundle:{name}", value.encode("utf-8")
            except UnicodeEncodeError:
                raise Refused("not_utf8", f"bundle member {name!r} holds text that is not valid UTF-8") from None
        if path is None:
            raise Refused("bad_arguments", f"--{name} is required (or a bundle member {name!r})")
        return path, self.read_file(path)


class Table:
    """A UTF-8 CSV text with one header row; data records are read on demand."""

    def __init__(self, label: str, data: bytes, delimiter: str, limit: int) -> None:
        self.label = label
        self.sha256 = hashlib.sha256(data).hexdigest()
        self.bom = data.startswith(b"\xef\xbb\xbf")
        if data[:2] == b"\x1f\x8b" or data[:4] == b"PK\x03\x04":
            raise Refused("compressed_input", f"{label} is a compressed file; check the unpacked CSV")
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise Refused("not_utf8", f"{label}: byte {error.start} is not UTF-8") from None
        if "\x00" in text:
            raise Refused("not_text", f"{label} holds a NUL character")
        csv.field_size_limit(max(limit, 131072))
        self._reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
        self._end = 0
        self.blank_lines = 0
        first = self._next()
        if first is None:
            raise Refused("input_empty", f"{label} has no header row")
        if not first[1]:
            raise Refused("header_missing", f"{label}: line 1 is blank; the first line must be the header")
        self.header = first[1]
        if len(self.header) == 1:
            for name, mark in (("semicolon", ";"), ("tab", "\t"), ("pipe", "|")):
                if mark in self.header[0] and mark != delimiter:
                    self.hint = f"the header is one column that holds {name} marks; try --delimiter {name}"
                    break
            else:
                self.hint = ""
        else:
            self.hint = ""

    def _next(self):
        try:
            fields = next(self._reader)
        except StopIteration:
            return None
        except csv.Error as error:
            raise Refused("malformed_csv", f"{self.label} near line {self._reader.line_num}: {error}") from None
        start = self._end + 1
        self._end = self._reader.line_num
        return start, fields

    def records(self):
        """Yield (data row number counted from 1, first line of the record, fields).

        A blank line in a table of one column is one empty value; in a wider table it is skipped and counted.
        """
        number = 0
        while True:
            item = self._next()
            if item is None:
                return
            line, fields = item
            if not fields:
                if len(self.header) != 1:
                    self.blank_lines += 1
                    continue
                fields = [""]
            number += 1
            yield number, line, fields


def excerpt(value: str, hide: bool):
    if hide:
        return {"characters": len(value)}
    return value if len(value) <= EXCERPT else value[:EXCERPT - 3] + "..."


# Contract --------------------------------------------------------------------------------------------

def contract_error(where: str, message: str):
    raise Refused("contract_invalid", f"{where}: {message}")


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def string_list(value, where: str, allow_empty_strings: bool, maximum: int) -> list[str]:
    if not isinstance(value, list) or not 1 <= len(value) <= maximum \
            or any(not isinstance(item, str) for item in value) or len(set(value)) != len(value):
        contract_error(where, f"a list of 1 to {maximum} distinct strings")
    if not allow_empty_strings and any(item == "" for item in value):
        contract_error(where, "values are nonempty strings")
    return value


def parse_time(text: str, form: str, kind: str):
    """Parse with the declared format and accept only text written exactly as the format writes it."""
    try:
        moment = datetime.strptime(text, form)
    except ValueError:
        return None
    if moment.strftime(form) != text:
        return None
    return moment.date() if kind == "date" else moment


class ColumnRule:
    def __init__(self, spec, index: int) -> None:
        where = f"columns[{index}]"
        if not isinstance(spec, dict):
            contract_error(where, "each column is a JSON object")
        unknown = sorted(set(spec) - COLUMN_KEYS)
        if unknown:
            contract_error(where, f"unknown keys {unknown}; allowed keys are {sorted(COLUMN_KEYS)}")
        name = spec.get("name")
        if not isinstance(name, str) or not name or len(name) > 200:
            contract_error(f"{where}.name", "a nonempty string of at most 200 characters")
        where = f"columns[{index}] ({name})"
        self.name = name
        self.type = spec.get("type")
        if self.type not in TYPES:
            contract_error(f"{where}.type", f"{self.type!r} is not one of {list(TYPES)}")
        self.required = spec.get("required", True)
        self.unique = spec.get("unique", False)
        self.trimmed = spec.get("trimmed", False)
        for key in ("required", "unique", "trimmed"):
            if not isinstance(spec.get(key, False), bool):
                contract_error(f"{where}.{key}", "true or false")
        if "trimmed" in spec and self.type != "string":
            contract_error(f"{where}.trimmed", "applies to string columns only")
        self.empty = spec.get("empty", "allowed")
        if self.empty not in ("allowed", "never"):
            contract_error(f"{where}.empty", "\"allowed\" or \"never\"")
        self.max_empty_share = spec.get("max_empty_share")
        if self.max_empty_share is not None:
            if not is_number(self.max_empty_share) or not 0 <= self.max_empty_share <= 1:
                contract_error(f"{where}.max_empty_share", "a number from 0 to 1")
            if self.empty == "never":
                contract_error(f"{where}.max_empty_share", "cannot be combined with \"empty\": \"never\"")
        self.allowed = None
        if "allowed" in spec:
            if self.type == "boolean":
                contract_error(f"{where}.allowed", "boolean columns use true_values and false_values")
            self.allowed = set(string_list(spec["allowed"], f"{where}.allowed", True, 10000))
        self.format = spec.get("format", DEFAULT_FORMATS.get(self.type))
        if "format" in spec:
            if self.type not in ("date", "datetime"):
                contract_error(f"{where}.format", "applies to date and datetime columns only")
            if not isinstance(self.format, str) or "%" not in self.format or len(self.format) > 100:
                contract_error(f"{where}.format", "a strptime format such as %Y-%m-%d")
        self.true_values, self.false_values = {"true"}, {"false"}
        if "true_values" in spec or "false_values" in spec:
            if self.type != "boolean":
                contract_error(f"{where}.true_values", "applies to boolean columns only")
            self.true_values = set(string_list(spec.get("true_values", ["true"]), f"{where}.true_values", False, 20))
            self.false_values = set(string_list(spec.get("false_values", ["false"]), f"{where}.false_values", False, 20))
            if self.true_values & self.false_values:
                contract_error(f"{where}", "true_values and false_values share a value")
        self.minimum = self.bound(spec, "min", where)
        self.maximum = self.bound(spec, "max", where)
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            contract_error(where, "min is larger than max")
        self.min_length = self.length(spec, "min_length", where)
        self.max_length = self.length(spec, "max_length", where)
        if self.min_length is not None and self.max_length is not None and self.min_length > self.max_length:
            contract_error(where, "min_length is larger than max_length")

    def bound(self, spec, key: str, where: str):
        if key not in spec:
            return None
        value = spec[key]
        if self.type == "integer":
            if isinstance(value, int) and not isinstance(value, bool):
                return value
            if isinstance(value, str) and INTEGER.fullmatch(value):
                return int(value)
            contract_error(f"{where}.{key}", "a whole number")
        if self.type == "decimal":
            if is_number(value):
                return Decimal(str(value))
            if isinstance(value, str) and DECIMAL.fullmatch(value):
                return Decimal(value)
            contract_error(f"{where}.{key}", "a number")
        if self.type in ("date", "datetime"):
            parsed = parse_time(value, self.format, self.type) if isinstance(value, str) else None
            if parsed is None:
                contract_error(f"{where}.{key}", f"a {self.type} written in the format {self.format}")
            return parsed
        contract_error(f"{where}.{key}", f"ranges apply to integer, decimal, date and datetime columns, not {self.type}")

    def length(self, spec, key: str, where: str):
        if key not in spec:
            return None
        if self.type != "string":
            contract_error(f"{where}.{key}", "applies to string columns only")
        value = spec[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            contract_error(f"{where}.{key}", "a whole number of 0 or more")
        return value

    def typed(self, text: str):
        """Return (True, canonical value) when the text is a valid value of the column type."""
        if self.type == "string":
            return True, text
        if self.type == "integer":
            return (True, int(text)) if INTEGER.fullmatch(text) else (False, None)
        if self.type == "decimal":
            return (True, Decimal(text)) if DECIMAL.fullmatch(text) else (False, None)
        if self.type == "boolean":
            if text in self.true_values:
                return True, True
            if text in self.false_values:
                return True, False
            return False, None
        parsed = parse_time(text, self.format, self.type)
        return (parsed is not None), parsed

    def expected_type(self) -> str:
        if self.type == "boolean":
            return "one of " + ", ".join(sorted(self.true_values | self.false_values))
        if self.type in ("date", "datetime"):
            return f"a {self.type} written exactly as {self.format}"
        return {"string": "text", "integer": "a whole number such as 42", "decimal": "a number such as 12.5"}[self.type]


class Contract:
    def __init__(self, value) -> None:
        if not isinstance(value, dict):
            contract_error("contract", "one JSON object")
        unknown = sorted(set(value) - CONTRACT_KEYS)
        if unknown:
            contract_error("contract", f"unknown keys {unknown}; allowed keys are {sorted(CONTRACT_KEYS)}")
        if value.get("record_type") != CONTRACT_TYPE:
            contract_error("record_type", f"must be {CONTRACT_TYPE!r}")
        columns = value.get("columns")
        if not isinstance(columns, list) or not 1 <= len(columns) <= 1000:
            contract_error("columns", "a list of 1 to 1000 column objects")
        self.columns = [ColumnRule(spec, index) for index, spec in enumerate(columns)]
        names = [rule.name for rule in self.columns]
        repeated = sorted({name for name in names if names.count(name) > 1})
        if repeated:
            contract_error("columns", f"column names repeat: {repeated}")
        self.empty_values = set(string_list(value.get("empty_values", [""]), "empty_values", True, 50))
        self.extra_columns = value.get("extra_columns", "allowed")
        if self.extra_columns not in ("allowed", "not_allowed"):
            contract_error("extra_columns", "\"allowed\" or \"not_allowed\"")
        self.column_order = value.get("column_order", "any")
        if self.column_order not in ("any", "as_listed"):
            contract_error("column_order", "\"any\" or \"as_listed\"")
        self.row_count = value.get("row_count")
        if self.row_count is not None:
            if not isinstance(self.row_count, dict) or not self.row_count or set(self.row_count) - {"min", "max"} \
                    or any(not isinstance(item, int) or isinstance(item, bool) or item < 0
                           for item in self.row_count.values()):
                contract_error("row_count", "an object with a whole-number min, max or both")
            if self.row_count.get("min", 0) > self.row_count.get("max", self.row_count.get("min", 0)):
                contract_error("row_count", "min is larger than max")
        self.unique_together = value.get("unique_together", [])
        if not isinstance(self.unique_together, list):
            contract_error("unique_together", "a list of column-name lists")
        for index, group in enumerate(self.unique_together):
            if not isinstance(group, list) or not 2 <= len(group) <= 10 or len(set(map(str, group))) != len(group) \
                    or any(name not in names for name in group):
                contract_error(f"unique_together[{index}]", "2 to 10 distinct names of contract columns")
        if "description" in value and not isinstance(value["description"], str):
            contract_error("description", "a string")


# Checking --------------------------------------------------------------------------------------------

class Findings:
    def __init__(self, limit: int, hide: bool) -> None:
        self.limit, self.hide = limit, hide
        self.total = 0
        self.counts: dict[str, int] = {}
        self.by_column: dict[str, dict[str, int]] = {}
        self.shown: list[dict] = []
        self._per_rule: dict[tuple, int] = {}

    def add(self, check: str, rule: str, column: str | None, **details) -> None:
        self.total += 1
        self.counts[check] = self.counts.get(check, 0) + 1
        if column is not None:
            per = self.by_column.setdefault(column, {})
            per[rule] = per.get(rule, 0) + 1
        key = (column, rule)
        if len(self.shown) < self.limit and self._per_rule.get(key, 0) < PER_RULE_EXAMPLES:
            self._per_rule[key] = self._per_rule.get(key, 0) + 1
            item = {"rule": rule}
            if column is not None:
                item["column"] = column
            for name, value in details.items():
                item[name] = excerpt(value, self.hide) if name == "value" and isinstance(value, str) else value
            self.shown.append(item)


def fold_name(name: str) -> str:
    return " ".join(name.split()).casefold()


def check_header(table: Table, contract: Contract, findings: Findings) -> dict[str, int]:
    header = table.header
    positions: dict[str, int] = {}
    for position, name in enumerate(header):
        if name in positions:
            findings.add("header", "duplicate_column_name", name, position=position + 1)
        else:
            positions[name] = position
    duplicated = {name for name in header if header.count(name) > 1}
    folded = {fold_name(name): name for name in header}
    for rule in contract.columns:
        if rule.name in positions:
            continue
        if not rule.required:
            continue
        near = folded.get(fold_name(rule.name))
        hint = f"the header has {near!r}, which differs only in spaces or letter case" if near is not None else ""
        if table.hint:
            hint = table.hint
        findings.add("header", "required_column_missing", rule.name, hint=hint)
    listed = {rule.name for rule in contract.columns}
    if contract.extra_columns == "not_allowed":
        for name in header:
            if name not in listed:
                findings.add("header", "extra_column", name)
    if contract.column_order == "as_listed":
        found = [name for name in header if name in listed]
        expected = [rule.name for rule in contract.columns if rule.name in positions]
        if found != expected:
            findings.add("header", "column_order", None, expected=expected[:50], found=found[:50])
    return {name: position for name, position in positions.items() if name not in duplicated}


def check_rows(table: Table, contract: Contract, positions: dict[str, int], findings: Findings) -> dict:
    width = len(table.header)
    active = [(rule, positions[rule.name]) for rule in contract.columns if rule.name in positions]
    empties = {rule.name: 0 for rule, _ in active}
    seen: dict[str, dict] = {rule.name: {} for rule, _ in active if rule.unique}
    together = [(group, [positions.get(name) for name in group], {}) for group in contract.unique_together]
    rows = wrong_width = 0
    for number, line, fields in table.records():
        rows += 1
        if len(fields) != width:
            wrong_width += 1
            findings.add("field_count", "field_count", None, row=number, line=line,
                         expected=width, found=len(fields))
            continue
        for rule, position in active:
            text = fields[position]
            if text in contract.empty_values:
                empties[rule.name] += 1
                if rule.empty == "never":
                    findings.add("empty", "empty", rule.name, row=number, line=line, value=text,
                                 expected="a value; this column is never empty")
                continue
            valid, value = rule.typed(text)
            if not valid:
                findings.add("type", "type", rule.name, row=number, line=line, value=text,
                             expected=rule.expected_type())
            if rule.trimmed and text != text.strip():
                findings.add("trimmed", "trimmed", rule.name, row=number, line=line, value=text,
                             expected="no spaces at the start or end")
            if rule.allowed is not None and text not in rule.allowed:
                shown = sorted(rule.allowed)
                findings.add("allowed", "allowed", rule.name, row=number, line=line, value=text,
                             expected="one of " + ", ".join(shown[:12]) + (" and more" if len(shown) > 12 else ""))
            if valid and rule.minimum is not None and value < rule.minimum:
                findings.add("range", "min", rule.name, row=number, line=line, value=text,
                             expected=f"at least {rule.minimum}")
            if valid and rule.maximum is not None and value > rule.maximum:
                findings.add("range", "max", rule.name, row=number, line=line, value=text,
                             expected=f"at most {rule.maximum}")
            if rule.min_length is not None and len(text) < rule.min_length:
                findings.add("length", "min_length", rule.name, row=number, line=line, value=text,
                             expected=f"at least {rule.min_length} characters")
            if rule.max_length is not None and len(text) > rule.max_length:
                findings.add("length", "max_length", rule.name, row=number, line=line, value=text,
                             expected=f"at most {rule.max_length} characters")
            if rule.unique:
                key = (1, value) if valid else (0, text)
                first = seen[rule.name].get(key)
                if first is None:
                    seen[rule.name][key] = number
                else:
                    findings.add("unique", "unique", rule.name, row=number, line=line, value=text, first_row=first)
        for group, where, first_rows in together:
            if any(position is None for position in where):
                continue
            parts = tuple(fields[position] for position in where)
            if any(part in contract.empty_values for part in parts):
                continue
            first = first_rows.get(parts)
            if first is None:
                first_rows[parts] = number
            else:
                findings.add("unique_together", "unique_together", None, columns=group, row=number, line=line,
                             first_row=first)
    checked = rows - wrong_width
    for rule, _position in active:
        if rule.max_empty_share is not None and checked:
            share = empties[rule.name] / checked
            if share > rule.max_empty_share:
                findings.add("empty_share", "max_empty_share", rule.name, value_share=round(share, 6),
                             expected=f"at most {rule.max_empty_share}")
    if contract.row_count is not None:
        low, high = contract.row_count.get("min"), contract.row_count.get("max")
        if (low is not None and rows < low) or (high is not None and rows > high):
            findings.add("row_count", "row_count", None, rows=rows, expected=contract.row_count)
    return {"rows": rows, "rows_with_wrong_field_count": wrong_width,
            "empty_cells": {name: count for name, count in empties.items() if count}}


def applied_checks(contract: Contract) -> list[str]:
    names = ["header", "field_count"]
    rules = contract.columns
    if contract.row_count is not None:
        names.append("row_count")
    if any(rule.empty == "never" for rule in rules):
        names.append("empty")
    if any(rule.type != "string" for rule in rules):
        names.append("type")
    for check, used in (("trimmed", any(rule.trimmed for rule in rules)),
                        ("allowed", any(rule.allowed is not None for rule in rules)),
                        ("range", any(rule.minimum is not None or rule.maximum is not None for rule in rules)),
                        ("length", any(rule.min_length is not None or rule.max_length is not None for rule in rules)),
                        ("unique", any(rule.unique for rule in rules)),
                        ("unique_together", bool(contract.unique_together)),
                        ("empty_share", any(rule.max_empty_share is not None for rule in rules))):
        if used:
            names.append(check)
    return names


def build_parser() -> Parser:
    parser = Parser(description="Check a CSV file against a JSON column contract. Exit 0 pass, 1 fail, 2 no verdict.")
    parser.add_argument("--csv", help="the table to check, relative to --root")
    parser.add_argument("--contract", help="the column contract (column_contract/v1 JSON), relative to --root")
    parser.add_argument("--bundle", help="one JSON object with the members csv and contract; - reads standard input")
    parser.add_argument("--root", default=".", help="folder that every path is relative to (default: current folder)")
    parser.add_argument("--delimiter", default="comma", help="comma (default), tab, semicolon, pipe or one character")
    parser.add_argument("--max-examples", type=int, default=30, help="violations listed in full, 1 to 500 (default 30)")
    parser.add_argument("--no-values", action="store_true", help="show the length of a violating value, not its text")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                        help=f"refuse a file larger than this (default {DEFAULT_MAX_BYTES})")
    return parser


def run(args) -> tuple[dict, int]:
    if not 1 <= args.max_bytes <= HARD_MAX_BYTES:
        raise Refused("bad_arguments", f"--max-bytes is between 1 and {HARD_MAX_BYTES}")
    if not 1 <= args.max_examples <= 500:
        raise Refused("bad_arguments", "--max-examples is between 1 and 500")
    delimiter = DELIMITERS.get(args.delimiter, args.delimiter)
    if len(delimiter) != 1 or delimiter in "\"\r\n":
        raise Refused("bad_arguments", "--delimiter is comma, tab, semicolon, pipe or one character")
    inputs = Inputs(args.root, args.bundle, args.max_bytes)
    contract_label, contract_bytes = inputs.get("contract", args.contract, json_allowed=True)
    if len(contract_bytes) > 1024 * 1024:
        raise Refused("input_too_large", "the contract is larger than 1 MiB")
    contract = Contract(strict_json(contract_bytes, contract_label))
    table_label, table_bytes = inputs.get("csv", args.csv, json_allowed=False)
    table = Table(table_label, table_bytes, delimiter, args.max_bytes)
    findings = Findings(args.max_examples, args.no_values)
    positions = check_header(table, contract, findings)
    summary = check_rows(table, contract, positions, findings)
    checks = {name: findings.counts.get(name, 0) for name in applied_checks(contract)}
    absent = [rule.name for rule in contract.columns if rule.name not in positions]
    status = "pass" if findings.total == 0 else "fail"
    report = {
        "record_type": RECORD_TYPE, "status": status,
        "csv": {"path": table_label, "sha256": table.sha256, "rows": summary["rows"], "columns": len(table.header),
                "byte_order_mark": table.bom, "blank_lines_skipped": table.blank_lines},
        "contract": {"path": contract_label, "sha256": hashlib.sha256(contract_bytes).hexdigest(),
                     "columns": len(contract.columns)},
        "checks": checks,
        "failed_checks": [name for name, count in checks.items() if count],
        "violations_total": findings.total,
        "violations_by_column": findings.by_column,
        "violations": findings.shown,
        "violations_shown": len(findings.shown),
        "contract_columns_not_checked": absent,
        "empty_cells": summary["empty_cells"],
        "numbering": "row counts data rows from 1 without the header; line is the file line where the record starts",
    }
    if absent:
        report["note"] = "Columns in contract_columns_not_checked are absent or repeated in the header; their rules did not run."
    return report, 0 if status == "pass" else 1


def emit(report: dict) -> None:
    sys.stdout.buffer.write((json.dumps(report, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))


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
