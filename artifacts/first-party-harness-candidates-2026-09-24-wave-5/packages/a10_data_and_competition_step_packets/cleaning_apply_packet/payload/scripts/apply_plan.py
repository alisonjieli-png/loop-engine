"""Apply the approved rules of a cleaning plan to a copy of one table. Effects: reads the table and the plan under --root; creates new files in --out-dir only.

The source table is never opened for writing. The command creates four new files in the output
folder: cleaned plus the table's extension (the copy), changes.jsonl (one line per changed cell),
holds.jsonl (one line per held cell) and apply_summary.json, which is written last and only when
every self-check passed. With --check-only it validates the inputs and writes nothing.

Usage:
  python3 -I -B apply_plan.py --table PATH --plan PATH --out-dir DIR [--check-only] [--root DIR]

Exit status: 0 applied or ready, 1 a self-check failed, 2 refused input. Standard output holds one
JSON object. No network use, no subprocess and no model call. MIT licence.
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
from itertools import zip_longest
from pathlib import Path, PurePosixPath

MAX_TABLE_BYTES = 64 * 1024 * 1024
MAX_JSON_BYTES = 8 * 1024 * 1024
DELIMITERS = {"comma": ",", "semicolon": ";", "tab": "\t", "pipe": "|"}
OPERATIONS = ("trim_whitespace", "missing_tokens_to_empty", "map_values", "parse_number", "parse_date")
RANK = {"trim_whitespace": 0, "missing_tokens_to_empty": 1, "map_values": 2, "parse_number": 3, "parse_date": 3}
PARSE_OPERATIONS = ("parse_number", "parse_date")
THOUSANDS = ("", ",", ".", " ", "'")
DATE_PARTS = {"%Y": "year", "%m": "month", "%b": "month", "%B": "month", "%d": "day"}
DATE_LITERALS = frozenset("-/., ")
DIGITS = re.compile(r"[0-9]+")
SUFFIX = re.compile(r"\.[A-Za-z0-9]{1,8}")
BOM = b"\xef\xbb\xbf"
PLAN_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "contracts" / "plan.schema.json"
SCHEMA_KEYWORDS = frozenset(("$schema", "$id", "$comment", "title", "description", "$defs", "$ref", "type",
                             "properties", "required", "additionalProperties", "items", "minItems", "maxItems",
                             "uniqueItems", "enum", "const", "minimum", "maximum", "minLength", "maxLength",
                             "pattern"))


class Refused(Exception):
    """Input this script will not work on (exit status 2)."""


class Hold(Exception):
    """A value that a rule cannot change safely; the cell keeps its source value."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


# Paths and files -----------------------------------------------------------------------------

def relative_path(value, label: str) -> str:
    """Return a clean workspace-relative POSIX path or refuse it."""
    if not isinstance(value, str) or not value.strip() or value.startswith(("/", "~")) or "\\" in value \
            or "\x00" in value:
        raise Refused(f"{label} must be a path relative to the workspace root, not {value!r}")
    parts = [part for part in PurePosixPath(value).parts if part != "."]
    if not parts or ".." in parts:
        raise Refused(f"{label} must stay inside the workspace root, not {value!r}")
    return "/".join(parts)


def inside(root: Path, relative: str, label: str) -> Path:
    """Join a relative path to the root, refusing symbolic links and any escape."""
    current = root
    for part in relative.split("/"):
        current = current / part
        if current.is_symlink():
            raise Refused(f"{label} passes through a symbolic link: {relative}")
    resolved = current.resolve()
    if resolved != root and root not in resolved.parents:
        raise Refused(f"{label} leaves the workspace root: {relative}")
    return current


def existing_file(root: Path, relative: str, label: str, limit: int) -> Path:
    path = inside(root, relative, label)
    if not path.is_file():
        raise Refused(f"{label} is not an existing regular file: {relative}")
    size = path.stat().st_size
    if size > limit:
        raise Refused(f"{label} is {size} bytes, above the limit of {limit}; this step refuses instead of truncating")
    return path


def strict_json(data: bytes, label: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key {key!r}")
            result[key] = value
        return result

    def constant(name):
        raise ValueError(f"non-standard number {name}")

    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeDecodeError, ValueError) as error:
        raise Refused(f"{label} is not strict JSON: {error}") from None


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# JSON Schema subset used by the contracts of this packet ----------------------------------------

def type_matches(value, name: str) -> bool:
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
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    raise ValueError(f"unknown schema type {name!r}")


def same_json(left, right) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    return left == right


def schema_errors(value, schema: dict, root: dict | None = None, where: str = "$") -> list[str]:
    """Validate value against the JSON Schema subset these contracts use; unknown keywords raise."""
    root = schema if root is None else root
    unknown = set(schema) - SCHEMA_KEYWORDS
    if unknown:
        raise ValueError(f"schema keywords not supported by this checker: {sorted(unknown)}")
    if "$ref" in schema:
        reference = schema["$ref"]
        if not reference.startswith("#/$defs/"):
            raise ValueError(f"only local $defs references are supported, not {reference}")
        return schema_errors(value, root["$defs"][reference[len("#/$defs/"):]], root, where)
    if "type" in schema:
        names = [schema["type"]] if isinstance(schema["type"], str) else schema["type"]
        if not any(type_matches(value, name) for name in names):
            return [f"{where}: expected {' or '.join(names)}"]
    errors = []
    if "const" in schema and not same_json(value, schema["const"]):
        errors.append(f"{where}: must be {json.dumps(schema['const'])}")
    if "enum" in schema and not any(same_json(value, option) for option in schema["enum"]):
        errors.append(f"{where}: must be one of {json.dumps(schema['enum'])}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{where}: shorter than {schema['minLength']} characters")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{where}: longer than {schema['maxLength']} characters")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{where}: does not match {schema['pattern']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{where}: below {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{where}: above {schema['maximum']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{where}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{where}: more than {schema['maxItems']} items")
        if schema.get("uniqueItems"):
            seen = [json.dumps(item, sort_keys=True) for item in value]
            if len(set(seen)) != len(seen):
                errors.append(f"{where}: items repeat")
        if "items" in schema:
            for index, item in enumerate(value):
                errors += schema_errors(item, schema["items"], root, f"{where}[{index}]")
    if isinstance(value, dict):
        for name in schema.get("required", []):
            if name not in value:
                errors.append(f"{where}: missing {name}")
        properties = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for name, item in value.items():
            if name in properties:
                errors += schema_errors(item, properties[name], root, f"{where}.{name}")
            elif extra is False:
                errors.append(f"{where}: unexpected field {name}")
            elif isinstance(extra, dict):
                errors += schema_errors(item, extra, root, f"{where}.{name}")
    return errors


# Rule operations (identical in the cleaning plan packet) ----------------------------------------

def parse_number(text: str, decimal: str, thousands: str) -> str:
    """Return one number with a dot decimal separator and no grouping, or raise Hold."""
    body = text
    if thousands == " ":
        body = body.replace("\u00a0", " ").replace("\u202f", " ")
    sign = ""
    if body[:1] in ("+", "-"):
        sign = "-" if body[0] == "-" else ""
        body = body[1:]
    whole, found, fraction = body.partition(decimal)
    if found and not DIGITS.fullmatch(fraction):
        raise Hold("not_a_number")
    if thousands and thousands in whole:
        groups = whole.split(thousands)
        if not 1 <= len(groups[0]) <= 3 or any(len(group) != 3 for group in groups[1:]):
            raise Hold("not_a_number")
        whole = "".join(groups)
    if whole == "" and found:
        whole = "0"
    if not DIGITS.fullmatch(whole):
        raise Hold("not_a_number")
    whole = whole.lstrip("0") or "0"
    return sign + whole + ("." + fraction if found else "")


def parse_date(text: str, formats) -> str:
    """Return YYYY-MM-DD when the declared formats agree on one date, or raise Hold."""
    found = {}
    for pattern in formats:
        try:
            moment = datetime.strptime(text, pattern)
        except ValueError:
            continue
        found.setdefault(moment.date().isoformat(), pattern)
    if not found:
        raise Hold("no_format_matches")
    if len(found) > 1:
        raise Hold("formats_disagree")
    return next(iter(found))


def date_format_problem(pattern) -> str:
    if not isinstance(pattern, str) or not pattern or len(pattern) > 40:
        return "a date format is a short nonempty string"
    parts = []
    for token in re.findall(r"%.|%$|[^%]", pattern):
        if token.startswith("%"):
            if token not in DATE_PARTS:
                return f"date format {pattern!r} uses {token!r}; allowed are %Y, %m, %d, %b and %B"
            parts.append(DATE_PARTS[token])
        elif token not in DATE_LITERALS:
            return f"date format {pattern!r} uses {token!r}; allowed separators are - / . , and space"
    if sorted(parts) != ["day", "month", "year"]:
        return f"date format {pattern!r} needs one %Y, one month (%m, %b or %B) and one %d"
    return ""


def parameter_problem(operation, parameters) -> str:
    if not isinstance(parameters, dict):
        return "parameters must be an object"
    if operation == "trim_whitespace":
        return "" if parameters == {} else "trim_whitespace takes no parameters"
    if operation == "missing_tokens_to_empty":
        tokens = parameters.get("tokens")
        if set(parameters) != {"tokens"} or not isinstance(tokens, list) or not 1 <= len(tokens) <= 50 \
                or any(not isinstance(token, str) or not token.strip() for token in tokens):
            return "missing_tokens_to_empty needs tokens, a list of 1 to 50 nonempty strings"
        folded = [token.strip().casefold() for token in tokens]
        return "" if len(set(folded)) == len(folded) else "missing value tokens repeat"
    if operation == "map_values":
        mapping, unmapped = parameters.get("mapping"), parameters.get("unmapped")
        if set(parameters) != {"mapping", "unmapped"} or not isinstance(mapping, dict) \
                or not 1 <= len(mapping) <= 1000 or unmapped not in ("keep", "hold"):
            return "map_values needs mapping (1 to 1000 entries) and unmapped (keep or hold)"
        for key, target in mapping.items():
            if not key or key != " ".join(key.split()) or len(key) > 200 or not isinstance(target, str) \
                    or len(target) > 200:
                return "map_values keys have no outer or repeated spaces, and values are strings"
        return ""
    if operation == "parse_number":
        decimal, thousands = parameters.get("decimal_separator"), parameters.get("thousands_separator")
        if set(parameters) != {"decimal_separator", "thousands_separator"} or decimal not in (".", ",") \
                or thousands not in THOUSANDS or thousands == decimal:
            return "parse_number needs decimal_separator . or , and a different thousands_separator"
        return ""
    if operation == "parse_date":
        formats = parameters.get("formats")
        if set(parameters) != {"formats"} or not isinstance(formats, list) or not 1 <= len(formats) <= 8 \
                or len({json.dumps(item) for item in formats}) != len(formats):
            return "parse_date needs formats, a list of 1 to 8 distinct formats"
        for pattern in formats:
            problem = date_format_problem(pattern)
            if problem:
                return problem
        return ""
    return f"unknown operation {operation!r}"


class PreparedRule:
    """One validated rule with its parameters ready for repeated use."""

    def __init__(self, rule: dict) -> None:
        parameters = rule["parameters"]
        self.rule_id = rule["rule_id"]
        self.operation = rule["operation"]
        self.tokens = frozenset(token.strip().casefold() for token in parameters.get("tokens", ()))
        self.mapping = dict(parameters.get("mapping", {}))
        self.hold_unmapped = parameters.get("unmapped") == "hold"
        self.decimal = parameters.get("decimal_separator", ".")
        self.thousands = parameters.get("thousands_separator", "")
        self.formats = tuple(parameters.get("formats", ()))

    def apply(self, value: str) -> str:
        if self.operation == "trim_whitespace":
            return " ".join(value.split())
        stripped = value.strip()
        if self.operation == "missing_tokens_to_empty":
            return "" if stripped and stripped.casefold() in self.tokens else value
        if not stripped:
            return value
        if self.operation == "map_values":
            key = " ".join(value.split())
            if key in self.mapping:
                return self.mapping[key]
            if self.hold_unmapped:
                raise Hold("unmapped_value")
            return value
        if self.operation == "parse_number":
            return parse_number(stripped, self.decimal, self.thousands)
        return parse_date(stripped, self.formats)


# Reading the table -----------------------------------------------------------------------------

def decode_table(data: bytes) -> str:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise Refused(f"the table is not UTF-8 text (first bad byte at offset {error.start})") from None
    if "\x00" in text:
        raise Refused("the table holds a NUL character, so it is not a text table")
    return text


def records(text: str, delimiter: str):
    """Yield the header, then every non-blank record, refusing rows of the wrong width."""
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    try:
        header = next(reader, None)
        if not header:
            raise Refused("the table has no header row")
        yield header
        number = 0
        for record in reader:
            if not record:
                continue
            number += 1
            if len(record) != len(header):
                raise Refused(f"data row {number} has {len(record)} fields; the header has {len(header)}")
            yield record
    except csv.Error as error:
        raise Refused(f"the table is not valid delimited text near line {reader.line_num}: {error}") from None


def scan_table(path: Path, delimiter: str) -> dict:
    """Digest, header, row count, blank lines, line ending and byte order mark of the whole table."""
    data = path.read_bytes()
    text = decode_table(data)
    stream = records(text, delimiter)
    header = next(stream)
    rows = sum(1 for _record in stream)
    blank = 0
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    for record in reader:
        blank += 0 if record else 1
    first_break = text.find("\n")
    newline = "\r\n" if first_break > 0 and text[first_break - 1] == "\r" else "\n"
    return {"digest": hashlib.sha256(data).hexdigest(), "header": header, "rows": rows, "blank": blank,
            "bom": data.startswith(BOM), "newline": newline}


# Plan ----------------------------------------------------------------------------------------------

def load_plan(root: Path, plan_rel: str, table_rel: str) -> tuple[dict, str]:
    plan_path = existing_file(root, plan_rel, "the plan", MAX_JSON_BYTES)
    data = plan_path.read_bytes()
    plan = strict_json(data, "the plan")
    if not PLAN_SCHEMA_PATH.is_file():
        raise Refused(f"the plan schema is missing next to this script: {PLAN_SCHEMA_PATH}")
    errors = schema_errors(plan, strict_json(PLAN_SCHEMA_PATH.read_bytes(), "the plan schema"))
    if errors:
        raise Refused("the plan does not follow contracts/plan.schema.json: " + "; ".join(errors[:6]))
    if plan["table"]["path"] != table_rel:
        raise Refused(f"the plan was made for {plan['table']['path']!r}, not {table_rel!r}")
    return plan, hashlib.sha256(data).hexdigest()


def select_rules(plan: dict, header: list[str]) -> tuple[dict, list, dict]:
    """Return approved rules by column, their ids in plan order, and the rules not applied."""
    rules = plan["rules"]
    identities = [rule["rule_id"] for rule in rules]
    if len(set(identities)) != len(identities):
        raise Refused("rule ids repeat in the plan")
    waiting = [rule["rule_id"] for rule in rules if rule["status"] == "proposed"]
    if waiting:
        raise Refused(f"rules {', '.join(waiting)} are still proposed; the review is not finished")
    for rule in rules:
        if rule["status"] in ("approved", "rejected") and not str(rule.get("reviewed_by", "")).strip():
            raise Refused(f"rule {rule['rule_id']} is {rule['status']} but names no reviewer in reviewed_by")
    approved = [rule for rule in rules if rule["status"] == "approved"]
    if not approved:
        raise Refused("no rule is approved, so there is nothing to apply")
    by_column: dict[str, list] = {}
    for rule in approved:
        if rule["column"] not in header:
            raise Refused(f"rule {rule['rule_id']} names the column {rule['column']!r}, which the table lacks")
        problem = parameter_problem(rule["operation"], rule["parameters"])
        if problem:
            raise Refused(f"rule {rule['rule_id']}: {problem}")
        by_column.setdefault(rule["column"], []).append(rule)
    for column, column_rules in by_column.items():
        operations = [rule["operation"] for rule in column_rules]
        ranks = [RANK[operation] for operation in operations]
        if len(set(operations)) != len(operations) or sum(item in PARSE_OPERATIONS for item in operations) > 1 \
                or ranks != sorted(ranks):
            raise Refused(f"the approved rules for column {column!r} repeat an operation, hold two parse rules, or "
                          f"are out of order; send the plan back to the plan step")
    prepared = {column: [PreparedRule(rule) for rule in column_rules] for column, column_rules in by_column.items()}
    not_applied = {rule["rule_id"]: rule["status"] for rule in rules if rule["status"] != "approved"}
    return prepared, [rule["rule_id"] for rule in approved], not_applied


# Application and self-check ----------------------------------------------------------------------

def apply_rules(text: str, delimiter: str, scan: dict, prepared: dict, targets: dict, counts: dict) -> dict:
    header = scan["header"]
    positions = [(index, prepared[name]) for index, name in enumerate(header) if name in prepared]
    changed = held = 0
    encoding = "utf-8-sig" if scan["bom"] else "utf-8"
    with open(targets["table"], "x", encoding=encoding, newline="") as table_stream, \
            open(targets["changes"], "x", encoding="utf-8", newline="") as change_stream, \
            open(targets["holds"], "x", encoding="utf-8", newline="") as hold_stream:
        writer = csv.writer(table_stream, delimiter=delimiter, lineterminator=scan["newline"])
        stream = records(text, delimiter)
        writer.writerow(next(stream))
        for number, record in enumerate(stream, start=1):
            output = list(record)
            for index, rules in positions:
                source = record[index]
                working, touched, stopped = source, [], None
                for rule in rules:
                    try:
                        result = rule.apply(working)
                    except Hold as hold:
                        stopped = (rule.rule_id, hold.reason)
                        break
                    if result != working:
                        touched.append(rule.rule_id)
                        working = result
                if stopped:
                    counts[stopped[0]]["held"] += 1
                    held += 1
                    hold_stream.write(json.dumps({"row": number, "column": header[index], "value": source,
                                                  "rule": stopped[0], "reason": stopped[1]}, ensure_ascii=False) + "\n")
                elif working != source:
                    for rule_id in touched:
                        counts[rule_id]["changed"] += 1
                    changed += 1
                    output[index] = working
                    change_stream.write(json.dumps({"row": number, "column": header[index], "before": source,
                                                    "after": working, "rules": touched}, ensure_ascii=False) + "\n")
            writer.writerow(output)
    return {"changed": changed, "held": held}


def self_check(source_text: str, copy_path: Path, change_path: Path, delimiter: str, header: list[str]) -> dict:
    """Compare the copy with the source cell by cell; every difference must be logged exactly."""
    index_of = {name: index for index, name in enumerate(header)}
    source_rows = records(source_text, delimiter)
    source_header = next(source_rows)
    copy_reader = csv.reader(io.StringIO(copy_path.read_bytes().decode("utf-8-sig"), newline=""),
                             delimiter=delimiter, strict=True)
    copy_header = next(copy_reader, None)
    copy_rows = (record for record in copy_reader if record)
    entries = (json.loads(line) for line in change_path.read_text(encoding="utf-8").splitlines() if line)
    pending = next(entries, None)
    rows_equal, unlogged, mismatched = True, 0, 0
    number = 0
    for number, (source, copy) in enumerate(zip_longest(source_rows, copy_rows), start=1):
        if source is None or copy is None or len(copy) != len(header):
            rows_equal = False
            break
        logged = {}
        while pending is not None and pending.get("row") == number:
            logged[index_of.get(pending.get("column"), -1)] = pending
            pending = next(entries, None)
        for index, (before, after) in enumerate(zip(source, copy)):
            entry = logged.pop(index, None)
            if entry is None:
                unlogged += before != after
            elif entry.get("before") != before or entry.get("after") != after:
                mismatched += 1
        mismatched += len(logged)
    if pending is not None:
        mismatched += 1
    return {"header_equal": copy_header == source_header, "row_count_equal": rows_equal,
            "every_difference_logged": unlogged == 0, "log_matches_cells": mismatched == 0}


# Command ---------------------------------------------------------------------------------------

def run(options) -> tuple[dict, int]:
    root = Path(options.root).resolve()
    table_rel = relative_path(options.table, "--table")
    plan_rel = relative_path(options.plan, "--plan")
    out_rel = relative_path(options.out_dir, "--out-dir")
    plan, plan_digest = load_plan(root, plan_rel, table_rel)
    delimiter = DELIMITERS[plan["table"]["delimiter"]]
    table = existing_file(root, table_rel, "the table", MAX_TABLE_BYTES)
    scan = scan_table(table, delimiter)
    if scan["digest"] != plan["table"]["sha256"]:
        raise Refused("the table changed after the plan was made; make and review a new plan first")
    if scan["header"] != plan["table"]["columns"]:
        raise Refused("the table's header differs from the columns in the plan")
    prepared, applied, not_applied = select_rules(plan, scan["header"])
    out_dir = inside(root, out_rel, "--out-dir")
    if out_dir.exists() and not out_dir.is_dir():
        raise Refused(f"--out-dir {out_rel} exists and is not a folder")
    suffix = PurePosixPath(table_rel).suffix
    names = {"table": "cleaned" + (suffix if SUFFIX.fullmatch(suffix) else ".csv"), "changes": "changes.jsonl",
             "holds": "holds.jsonl", "summary": "apply_summary.json"}
    targets = {key: out_dir / name for key, name in names.items()}
    for key, target in targets.items():
        if target.exists() or target.is_symlink():
            raise Refused(f"{out_rel}/{names[key]} already exists; this step never overwrites. Use a new --out-dir")
    relative = {key: f"{out_rel}/{name}" for key, name in names.items()}
    if options.check_only:
        return {"status": "ready", "table": {"path": table_rel, "sha256": scan["digest"], "rows": scan["rows"]},
                "plan": {"path": plan_rel, "sha256": plan_digest}, "will_apply": applied,
                "not_applied": not_applied, "will_write": list(relative.values())}, 0
    out_dir.mkdir(parents=True, exist_ok=True)
    text = decode_table(table.read_bytes())
    counts = {rule_id: {"changed": 0, "held": 0} for rule_id in applied}
    cells = apply_rules(text, delimiter, scan, prepared, targets, counts)
    checks = self_check(text, targets["table"], targets["changes"], delimiter, scan["header"])
    checks["source_unchanged"] = sha256_file(table) == scan["digest"]
    if not all(checks.values()):
        return {"status": "self_check_failed", "checks": checks,
                "note": "The copy, change log and hold list were written but do not agree; no summary was written."}, 1
    summary = {"record_type": "cleaning_apply_summary/v1", "status": "applied",
               "source": {"path": table_rel, "sha256": scan["digest"], "rows": scan["rows"], "columns": scan["header"],
                          "blank_lines_skipped": scan["blank"], "unchanged_after_run": checks["source_unchanged"]},
               "plan": {"path": plan_rel, "sha256": plan_digest, "applied_rules": applied, "not_applied": not_applied},
               "outputs": {"table": {"path": relative["table"], "sha256": sha256_file(targets["table"]),
                                     "rows": scan["rows"]},
                           "change_log": {"path": relative["changes"], "sha256": sha256_file(targets["changes"]),
                                          "entries": cells["changed"]},
                           "hold_list": {"path": relative["holds"], "sha256": sha256_file(targets["holds"]),
                                         "entries": cells["held"]}},
               "rule_counts": counts, "checks": checks}
    with open(targets["summary"], "x", encoding="utf-8", newline="") as stream:
        stream.write(json.dumps(summary, indent=1, ensure_ascii=False) + "\n")
    return summary, 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Apply the approved rules of a cleaning plan to a copy of a table.")
    parser.add_argument("--table", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--root", default=".")
    try:
        options = parser.parse_args(argv)
    except SystemExit as error:
        if error.code == 0:
            return 0
        print(json.dumps({"status": "refused", "reason": "the command line is invalid; see standard error"}))
        return 2
    try:
        result, code = run(options)
    except Refused as error:
        result, code = {"status": "refused", "reason": str(error)}, 2
    except OSError as error:
        result, code = {"status": "refused", "reason": f"file system error: {error}"}, 2
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
