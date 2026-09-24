"""Draft and check a cleaning plan for one table. Effects: reads files under --root; writes only a new profile, a new plan, or the evidence fields of that plan.

draft: profiles the first rows of one delimited UTF-8 table and writes two new files into the
output folder: table_profile.json (counts per column) and cleaning_plan.json (suggested rules,
each with evidence counted from the data, status proposed and an empty reason).
check: recounts the evidence of every rule, writes it into the plan when --write-evidence is
given, and lists what still blocks the plan. Neither command edits the table.

Usage:
  python3 -I -B plan_tool.py draft --table PATH --delimiter comma --max-rows N --out-dir DIR [--root DIR]
  python3 -I -B plan_tool.py check --table PATH --plan PATH [--write-evidence] [--root DIR]

Exit status: 0 done or passed, 1 findings, 2 refused input. Standard output holds one JSON
object. No network use, no subprocess and no model call. MIT licence.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath

MAX_TABLE_BYTES = 64 * 1024 * 1024
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_ROWS_LIMIT = 5_000_000
DELIMITERS = {"comma": ",", "semicolon": ";", "tab": "\t", "pipe": "|"}
OPERATIONS = ("trim_whitespace", "missing_tokens_to_empty", "map_values", "parse_number", "parse_date")
RANK = {"trim_whitespace": 0, "missing_tokens_to_empty": 1, "map_values": 2, "parse_number": 3, "parse_date": 3}
PARSE_OPERATIONS = ("parse_number", "parse_date")
MISSING_TOKENS = frozenset(("na", "n/a", "nan", "null", "none", "nil", "-", "--", "?", "missing", "unknown",
                            "not available", "#n/a"))
NUMBER_STYLES = ((".", ","), (",", "."), (",", " "), (".", " "), (".", "'"))
THOUSANDS = ("", ",", ".", " ", "'")
DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y", "%d-%m-%Y", "%m-%d-%Y", "%Y%m%d",
                "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y")
DATE_PARTS = {"%Y": "year", "%m": "month", "%b": "month", "%B": "month", "%d": "day"}
DATE_LITERALS = frozenset("-/., ")
PARSE_SHARE = 0.9
FORMAT_SHARE = 0.05
MAX_FORMATS = 4
MAX_MAP_DISTINCT = 30
MAX_EXAMPLES = 3
TOP = 5
PREVIEW = 60
PROFILE_NAME = "table_profile.json"
#: Version 2 added the leading-zero count of each number style; check reads it, so other versions are refused.
PROFILE_TYPE = "table_profile/v2"
PLAN_NAME = "cleaning_plan.json"
DIGITS = re.compile(r"[0-9]+")
WORDS = re.compile(r"[A-Za-z0-9]+")
DATE_SHAPE = re.compile(r"[0-9A-Za-z][0-9A-Za-z ,./-]{4,38}[0-9A-Za-z.]")
RULE_ID = re.compile(r"r[0-9]{1,4}")
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "contracts" / "output.schema.json"
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


def dump(value) -> bytes:
    return (json.dumps(value, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


def write_new(path: Path, data: bytes) -> None:
    with open(path, "xb") as stream:
        stream.write(data)


def replace_file(path: Path, data: bytes) -> None:
    partial = path.with_name(path.name + ".partial")
    if partial.exists() or partial.is_symlink():
        raise Refused(f"{partial.name} exists from an earlier failed write; move it away first")
    write_new(partial, data)
    os.replace(partial, path)


def preview(text: str) -> str:
    return text if len(text) <= PREVIEW else text[:PREVIEW - 3] + "..."


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


def load_schema() -> dict:
    if not SCHEMA_PATH.is_file():
        raise Refused(f"the plan schema is missing next to this script: {SCHEMA_PATH}")
    return strict_json(SCHEMA_PATH.read_bytes(), "the plan schema")


# Reading the table -----------------------------------------------------------------------------

def check_header(header: list[str]) -> None:
    seen = set()
    for index, name in enumerate(header, start=1):
        if not name.strip():
            raise Refused(f"header column {index} has no name")
        if len(name) > 200:
            raise Refused(f"header column {index} has a name longer than 200 characters")
        if name in seen:
            raise Refused(f"the column name {name!r} appears twice in the header")
        seen.add(name)


def read_table(path: Path, delimiter: str, max_rows: int):
    """Return header, the first max_rows data rows, whether more rows exist, blank lines, digest."""
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise Refused(f"the table is not UTF-8 text (first bad byte at offset {error.start})") from None
    if "\x00" in text:
        raise Refused("the table holds a NUL character, so it is not a text table")
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=DELIMITERS[delimiter], strict=True)
    rows, blank, capped = [], 0, False
    try:
        header = next(reader, None)
        if not header:
            raise Refused("the table has no header row")
        check_header(header)
        for record in reader:
            if not record:
                blank += 1
                continue
            if len(rows) >= max_rows:
                capped = True
                break
            if len(record) != len(header):
                raise Refused(f"data row {len(rows) + 1} has {len(record)} fields; the header has {len(header)}")
            rows.append(record)
    except csv.Error as error:
        raise Refused(f"the table is not valid delimited text near line {reader.line_num}: {error}") from None
    return header, rows, capped, blank, digest


# Rule operations (identical in the cleaning application packet) --------------------------------

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


def drops_leading_zero(text: str, decimal: str, thousands: str) -> bool:
    """True when parse_number reads the value and removes a leading 0, as it would from a code such as 01234."""
    try:
        parse_number(text, decimal, thousands)
    except Hold:
        return False
    whole = text.lstrip("+-").partition(decimal)[0]
    digits = "".join(character for character in whole if character.isdigit())
    return len(digits) > 1 and digits.startswith("0")


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


# Profile and suggestions ---------------------------------------------------------------------------

def shape_of(text: str) -> str:
    symbols = []
    for character in text[:80]:
        if character.isalpha():
            symbol = "a"
        elif character.isdigit():
            symbol = "9"
        elif character.isspace():
            symbol = " "
        else:
            symbol = character
        if not symbols or symbols[-1] != symbol or symbol not in "a9 ":
            symbols.append(symbol)
    return "".join(symbols)


def spelling_rank(spelling: str) -> int:
    """0 for mixed letter case such as Paris, 1 otherwise, so a tie prefers the usual written form."""
    letters = [character for character in spelling if character.isalpha()]
    mixed = any(letter.isupper() for letter in letters) and any(letter.islower() for letter in letters)
    return 0 if mixed else 1


def case_variants(candidates: Counter) -> list:
    if len(candidates) > MAX_MAP_DISTINCT:
        return []
    groups: dict[str, Counter] = {}
    for text, count in candidates.items():
        spelling = " ".join(text.split())
        groups.setdefault(spelling.casefold(), Counter())[spelling] += count
    variants = []
    for spellings in groups.values():
        if len(spellings) < 2:
            continue
        # The most common spelling wins; a tie prefers mixed case (Paris over PARIS and paris), then code point order.
        canonical = sorted(spellings.items(), key=lambda item: (-item[1], spelling_rank(item[0]), item[0]))[0][0]
        variants.append([canonical, sorted(spelling for spelling in spellings if spelling != canonical)])
    return sorted(variants)


def number_profile(candidates: Counter) -> dict:
    styles, outputs = [], []
    for decimal, thousands in NUMBER_STYLES:
        parsed = changed = zeros = 0
        results, zero_example = {}, ""
        for text, count in candidates.items():
            try:
                result = parse_number(text, decimal, thousands)
            except Hold:
                continue
            results[text] = result
            parsed += count
            changed += count if result != text else 0
            if drops_leading_zero(text, decimal, thousands):
                zeros += count
                zero_example = zero_example or text
        outputs.append(results)
        styles.append({"decimal_separator": decimal, "thousands_separator": thousands, "parsed": parsed,
                       "would_change": changed, "drops_leading_zero": zeros,
                       "leading_zero_example": preview(zero_example)})
    ambiguous, example = 0, ""
    for text, count in candidates.items():
        first, second = outputs[0].get(text), outputs[1].get(text)
        if first is not None and second is not None and first != second:
            ambiguous += count
            example = example or text
    return {"candidates": sum(candidates.values()), "styles": styles, "ambiguous": ambiguous,
            "ambiguous_example": preview(example)}


def date_profile(candidates: Counter) -> dict:
    total = sum(candidates.values())
    readings = {}
    for text in candidates:
        if not DATE_SHAPE.fullmatch(text) or not any(character.isdigit() for character in text):
            continue
        found = {}
        for pattern in DATE_FORMATS:
            try:
                found[pattern] = datetime.strptime(text, pattern).date().isoformat()
            except ValueError:
                continue
        if found:
            readings[text] = found
    formats = []
    for pattern in DATE_FORMATS:
        parsed = sum(candidates[text] for text, found in readings.items() if pattern in found)
        if parsed:
            only = sum(candidates[text] for text, found in readings.items() if list(found) == [pattern])
            formats.append({"format": pattern, "parsed": parsed, "only_this_format": only})
    ranked = sorted(formats, key=lambda item: (-item["parsed"], DATE_FORMATS.index(item["format"])))
    chosen = [item["format"] for item in ranked if item["parsed"] >= max(1.0, FORMAT_SHARE * total)][:MAX_FORMATS]
    covered = ambiguous = changed = 0
    example, pair = "", []
    for text, found in readings.items():
        dates = {found[pattern] for pattern in chosen if pattern in found}
        if not dates:
            continue
        count = candidates[text]
        covered += count
        if len(dates) > 1:
            ambiguous += count
            if not example:
                example, pair = text, [pattern for pattern in chosen if pattern in found]
        elif next(iter(dates)) != text:
            changed += count
    return {"candidates": total, "formats": formats, "chosen": chosen, "covered": covered, "would_change": changed,
            "ambiguous": ambiguous, "ambiguous_example": preview(example), "ambiguous_formats": pair}


def profile_column(name: str, counter: Counter, cells: int) -> dict:
    stripped: Counter = Counter()
    for value, count in counter.items():
        stripped[value.strip()] += count
    missing: dict[str, Counter] = {}
    candidates: Counter = Counter()
    for text, count in stripped.items():
        if not text:
            continue
        if text.casefold() in MISSING_TOKENS:
            missing.setdefault(text.casefold(), Counter())[text] += count
        else:
            candidates[text] += count
    missing_tokens = sorted(([spellings.most_common(1)[0][0], sum(spellings.values())] for spellings in missing.values()),
                            key=lambda item: (-item[1], item[0]))
    filled = Counter({text: count for text, count in stripped.items() if text})
    shapes: Counter = Counter()
    for text, count in filled.items():
        shapes[shape_of(text)] += count
    return {"name": name, "cells": cells, "empty": counter.get("", 0),
            "needs_trim": sum(count for value, count in counter.items() if value != " ".join(value.split())),
            "missing_tokens": missing_tokens, "distinct": len(filled),
            "top_values": [[preview(text), count] for text, count in filled.most_common(TOP)],
            "shapes": [[shape, count] for shape, count in shapes.most_common(3)],
            "case_variants": case_variants(candidates), "numbers": number_profile(candidates),
            "dates": date_profile(candidates)}


def suggest(profile: dict) -> tuple[list, list]:
    """Suggested (column, operation, parameters) and questions, from the profile alone."""
    suggestions, questions = [], []
    for column in profile["columns"]:
        name = column["name"]
        if column["needs_trim"]:
            suggestions.append((name, "trim_whitespace", {}))
        if column["missing_tokens"]:
            suggestions.append((name, "missing_tokens_to_empty",
                                {"tokens": [token for token, _count in column["missing_tokens"]]}))
        if column["case_variants"]:
            mapping = {variant: canonical for canonical, variants in column["case_variants"] for variant in variants}
            suggestions.append((name, "map_values", {"mapping": mapping, "unmapped": "keep"}))
        numbers, dates = column["numbers"], column["dates"]
        total = numbers["candidates"]
        best = max(numbers["styles"], key=lambda style: style["parsed"])
        number_share = best["parsed"] / total if total else 0.0
        date_share = dates["covered"] / total if total else 0.0
        number_fits = number_share >= PARSE_SHARE and best["would_change"] > 0
        # A date column also needs a rule when its only non-ISO values read two ways, such as 03/04/2024: the rule
        # holds them and the question below sends them to a person instead of letting them pass unseen.
        date_fits = bool(dates["chosen"]) and date_share >= PARSE_SHARE \
            and (dates["would_change"] > 0 or dates["ambiguous"] > 0)
        if number_fits and (not date_fits or number_share > date_share) and best["drops_leading_zero"]:
            # A code such as a postal code loses its leading 0 as a number, so ask instead of drafting a rule.
            questions.append(f"Column {name!r}: {best['drops_leading_zero']} values such as "
                             f"{best['leading_zero_example']!r} start with 0, which parse_number would drop, so no "
                             f"number rule was drafted. Is this column a quantity rather than a code such as a "
                             f"postal code?")
        elif number_fits and (not date_fits or number_share > date_share):
            suggestions.append((name, "parse_number", {"decimal_separator": best["decimal_separator"],
                                                       "thousands_separator": best["thousands_separator"]}))
            if numbers["ambiguous"] and best in numbers["styles"][:2]:
                questions.append(f"Column {name!r}: {numbers['ambiguous']} values such as "
                                 f"{numbers['ambiguous_example']!r} read as different numbers when the comma or the "
                                 f"dot is the decimal separator. Which separator does this column use?")
        elif date_fits:
            suggestions.append((name, "parse_date", {"formats": list(dates["chosen"])}))
            if dates["ambiguous"]:
                questions.append(f"Column {name!r}: {dates['ambiguous']} values such as {dates['ambiguous_example']!r} "
                                 f"read as different dates under {' and '.join(dates['ambiguous_formats'])}. "
                                 f"Which order do the values use?")
        if number_fits and date_fits:
            questions.append(f"Column {name!r} reads both as numbers and as dates. Which reading is right?")
    return suggestions, questions


# Evidence ----------------------------------------------------------------------------------------

def dry_run(counter: Counter, rules: list[PreparedRule]) -> dict:
    """Count per rule what the cleaning application step would do with these rules in this order.

    That step changes a cell only when no rule holds it. A held cell keeps its source value, so the
    changes that earlier rules made to it are not counted, and only the holding rule counts the cell.
    """
    stats = {rule.rule_id: {"changed": 0, "held": 0, "change_examples": [], "hold_examples": []} for rule in rules}
    for value, count in counter.items():
        working, steps, held = value, [], None
        for rule in rules:
            try:
                result = rule.apply(working)
            except Hold as hold:
                held = (rule.rule_id, working, hold.reason)
                break
            if result != working:
                steps.append((rule.rule_id, working, result))
                working = result
        if held is not None:
            entry = stats[held[0]]
            entry["held"] += count
            example = [preview(held[1]), held[2]]
            if len(entry["hold_examples"]) < MAX_EXAMPLES and example not in entry["hold_examples"]:
                entry["hold_examples"].append(example)
        elif working != value:
            for rule_id, before, after in steps:
                entry = stats[rule_id]
                entry["changed"] += count
                example = [preview(before), preview(after)]
                if len(entry["change_examples"]) < MAX_EXAMPLES and example not in entry["change_examples"]:
                    entry["change_examples"].append(example)
    return stats


def as_evidence(entry: dict, cells: int) -> dict:
    return {"cells_considered": cells, "would_change": entry["changed"], "would_hold": entry["held"],
            "change_examples": entry["change_examples"], "hold_examples": entry["hold_examples"]}


def recount(rules: list[dict], header: list[str], counters: dict, cells: int) -> dict:
    """Evidence by rule id: active rules run in plan order per column; dropped rules run alone."""
    evidence = {}
    for column in header:
        active = [PreparedRule(rule) for rule in rules if rule["column"] == column and rule.get("status") != "dropped"]
        for rule_id, entry in dry_run(counters[column], active).items():
            evidence[rule_id] = as_evidence(entry, cells)
        for rule in rules:
            if rule["column"] == column and rule.get("status") == "dropped":
                prepared = PreparedRule(rule)
                evidence[prepared.rule_id] = as_evidence(dry_run(counters[column], [prepared])[prepared.rule_id], cells)
    return evidence


def rule_problem(rule, header: list[str]) -> str:
    if not isinstance(rule, dict):
        return "a rule is an object"
    rule_id = rule.get("rule_id")
    if not isinstance(rule_id, str) or not RULE_ID.fullmatch(rule_id):
        return "rule_id is the letter r and digits, for example r7"
    if not isinstance(rule.get("column"), str) or rule["column"] not in header:
        return f"rule {rule_id}: column {rule.get('column')!r} is not in the table"
    if rule.get("operation") not in OPERATIONS:
        return f"rule {rule_id}: operation is one of {', '.join(OPERATIONS)}"
    problem = parameter_problem(rule["operation"], rule.get("parameters"))
    return f"rule {rule_id}: {problem}" if problem else ""


def semantic_findings(rules: list[dict], profile: dict, questions) -> list[str]:
    findings = []
    for rule in rules:
        rule_id = rule["rule_id"]
        if rule.get("status") not in ("proposed", "dropped"):
            findings.append(f"rule {rule_id}: this step writes only proposed or dropped; approval belongs to a reviewer")
        reason = rule.get("reason")
        if not isinstance(reason, str) or len(WORDS.findall(reason)) < 4:
            findings.append(f"rule {rule_id}: write a reason of at least four words about the column's meaning")
        evidence = rule.get("evidence")
        if rule.get("status") == "proposed" and isinstance(evidence, dict) \
                and evidence.get("would_change") == 0 and evidence.get("would_hold") == 0:
            findings.append(f"rule {rule_id}: it changes and holds nothing in the profiled rows; set its status to dropped")
        if rule["operation"] == "map_values":
            # This step only unifies spellings of one value; mapping one value to another is a decision for a person.
            for key, target in rule["parameters"]["mapping"].items():
                if target != " ".join(target.split()) or target.casefold() != key.casefold():
                    findings.append(f"rule {rule_id}: {key!r} maps to {target!r}; a mapping target may differ from "
                                    f"its spelling only in letter case, so use one of the column's spellings or "
                                    f"remove the entry and ask a question")
                    break
    active: dict[str, list] = {}
    for rule in rules:
        if rule.get("status") != "dropped":
            active.setdefault(rule["column"], []).append(rule["operation"])
    for column, operations in active.items():
        for operation in sorted(set(operations)):
            if operations.count(operation) > 1:
                findings.append(f"column {column!r}: more than one active {operation} rule")
        if sum(operation in PARSE_OPERATIONS for operation in operations) > 1:
            findings.append(f"column {column!r}: keep one parse rule and set the other to dropped")
        ranks = [RANK[operation] for operation in operations]
        if ranks != sorted(ranks):
            findings.append(f"column {column!r}: order its rules trim_whitespace, missing_tokens_to_empty, "
                            f"map_values, then the parse rule")
    present = {(rule["column"], rule["operation"]) for rule in rules}
    suggested, _questions = suggest(profile)
    for column, operation, _parameters in suggested:
        if (column, operation) not in present:
            findings.append(f"the draft suggested {operation} for column {column!r}; keep that rule with status "
                            f"dropped and a reason instead of deleting it")
    for index, question in enumerate(questions if isinstance(questions, list) else []):
        if isinstance(question, str) and not question.strip().endswith("?"):
            findings.append(f"questions[{index}]: write each question as one sentence that ends with a question mark")
    return findings


# Commands ----------------------------------------------------------------------------------------

def command_draft(options) -> dict:
    root = Path(options.root).resolve()
    table_rel = relative_path(options.table, "--table")
    out_rel = relative_path(options.out_dir, "--out-dir")
    if not 1 <= options.max_rows <= MAX_ROWS_LIMIT:
        raise Refused(f"--max-rows is between 1 and {MAX_ROWS_LIMIT}")
    table = existing_file(root, table_rel, "the table", MAX_TABLE_BYTES)
    out_dir = inside(root, out_rel, "--out-dir")
    if out_dir.exists() and not out_dir.is_dir():
        raise Refused(f"--out-dir {out_rel} exists and is not a folder")
    targets = (out_dir / PROFILE_NAME, out_dir / PLAN_NAME)
    for target in targets:
        if target.exists() or target.is_symlink():
            raise Refused(f"{out_rel}/{target.name} already exists; this step never overwrites. Use a new --out-dir")
    header, rows, capped, blank, digest = read_table(table, options.delimiter, options.max_rows)
    if not rows:
        raise Refused("the table has a header but no data rows")
    counters = {name: Counter(row[position] for row in rows) for position, name in enumerate(header)}
    table_section = {"path": table_rel, "sha256": digest, "delimiter": options.delimiter, "columns": header,
                     "rows_profiled": len(rows), "row_cap": options.max_rows, "row_cap_reached": capped}
    profile = {"record_type": PROFILE_TYPE, "table": {**table_section, "blank_lines_skipped": blank},
               "thresholds": {"parse_share": PARSE_SHARE, "format_share": FORMAT_SHARE, "max_formats": MAX_FORMATS,
                              "map_distinct_limit": MAX_MAP_DISTINCT, "missing_tokens": sorted(MISSING_TOKENS),
                              "date_formats_tried": list(DATE_FORMATS),
                              "number_styles_tried": [list(style) for style in NUMBER_STYLES]},
               "columns": [profile_column(name, counters[name], len(rows)) for name in header]}
    suggestions, questions = suggest(profile)
    rules = [{"rule_id": f"r{number}", "column": column, "operation": operation, "parameters": parameters,
              "status": "proposed", "reason": "", "evidence": {}}
             for number, (column, operation, parameters) in enumerate(suggestions, start=1)]
    evidence = recount(rules, header, counters, len(rows))
    for rule in rules:
        rule["evidence"] = evidence[rule["rule_id"]]
    out_dir.mkdir(parents=True, exist_ok=True)
    profile_bytes = dump(profile)
    write_new(targets[0], profile_bytes)
    plan = {"record_type": "cleaning_plan/v1", "table": table_section,
            "profile": {"path": f"{out_rel}/{PROFILE_NAME}", "sha256": hashlib.sha256(profile_bytes).hexdigest()},
            "rules": rules, "questions": questions}
    write_new(targets[1], dump(plan))
    return {"status": "drafted", "table": table_rel, "rows_profiled": len(rows), "row_cap_reached": capped,
            "blank_lines_skipped": blank, "profile": f"{out_rel}/{PROFILE_NAME}", "plan": f"{out_rel}/{PLAN_NAME}",
            "rules_suggested": len(rules), "questions": len(questions),
            "next": "Write a reason for every rule, drop rules that do not fit, then run check with --write-evidence."}


def command_check(options) -> tuple[dict, int]:
    root = Path(options.root).resolve()
    table_rel = relative_path(options.table, "--table")
    plan_rel = relative_path(options.plan, "--plan")
    plan_path = existing_file(root, plan_rel, "the plan", MAX_JSON_BYTES)
    try:
        plan = strict_json(plan_path.read_bytes(), "the plan")
    except Refused as error:
        # The model edits this file by hand, so a syntax slip is a finding it can fix, not a refusal.
        return {"status": "fail", "plan": plan_rel, "evidence_written": False, "rules": {"proposed": 0, "dropped": 0},
                "findings": [f"{error}. Fix the JSON syntax at that place, change nothing else, and run the check "
                             f"again"], "warnings": []}, 1
    if not isinstance(plan, dict) or not isinstance(plan.get("table"), dict) or not isinstance(plan.get("profile"), dict):
        raise Refused("the plan lost its table or profile section; run draft again into a new folder")
    table_info, profile_info = plan["table"], plan["profile"]
    if table_info.get("path") != table_rel:
        raise Refused(f"the plan describes {table_info.get('path')!r}, not {table_rel!r}")
    delimiter, row_cap = table_info.get("delimiter"), table_info.get("row_cap")
    if delimiter not in DELIMITERS or type(row_cap) is not int or not 1 <= row_cap <= MAX_ROWS_LIMIT:
        raise Refused("the plan's table section lost its delimiter or row cap; run draft again into a new folder")
    table = existing_file(root, table_rel, "the table", MAX_TABLE_BYTES)
    header, rows, _capped, _blank, digest = read_table(table, delimiter, row_cap)
    if digest != table_info.get("sha256"):
        raise Refused("the table changed after the draft, so the evidence no longer holds; run draft again into a new folder")
    if header != table_info.get("columns") or len(rows) != table_info.get("rows_profiled"):
        raise Refused("the plan's columns or row count differ from the table; run draft again into a new folder")
    profile_path = existing_file(root, relative_path(profile_info.get("path"), "the profile path"), "the profile",
                                 MAX_JSON_BYTES)
    profile_bytes = profile_path.read_bytes()
    if hashlib.sha256(profile_bytes).hexdigest() != profile_info.get("sha256"):
        raise Refused("the profile changed after the draft; run draft again into a new folder")
    profile = strict_json(profile_bytes, "the profile")
    if not isinstance(profile, dict) or profile.get("record_type") != PROFILE_TYPE:
        raise Refused(f"the profile is not {PROFILE_TYPE}, so another version of this step wrote it; run draft again "
                      f"into a new folder")
    schema = load_schema()
    findings, warnings = [], []
    rules = plan.get("rules")
    if not isinstance(rules, list):
        findings.append("rules must be a list")
        rules = []
    usable, seen = [], set()
    for index, rule in enumerate(rules):
        problem = rule_problem(rule, header)
        if not problem and rule["rule_id"] in seen:
            problem = f"rule id {rule['rule_id']} repeats"
        if problem:
            findings.append(f"rules[{index}]: {problem}")
            continue
        seen.add(rule["rule_id"])
        usable.append(rule)
    counters = {name: Counter(row[position] for row in rows) for position, name in enumerate(header)}
    evidence = recount(usable, header, counters, len(rows))
    if options.write_evidence:
        for rule in usable:
            rule["evidence"] = evidence[rule["rule_id"]]
        replace_file(plan_path, dump(plan))
    else:
        for rule in usable:
            if rule.get("evidence") != evidence[rule["rule_id"]]:
                findings.append(f"rule {rule['rule_id']}: evidence differs from the recount; run check with "
                                f"--write-evidence and never type evidence by hand")
    # A missing reason is reported once, by the clearer semantic finding below.
    findings += [f"shape: {error}" for error in schema_errors(plan, schema) if ".reason:" not in error]
    findings += semantic_findings(usable, profile, plan.get("questions"))
    if table_info.get("row_cap_reached"):
        warnings.append(f"the profile covers only the first {len(rows)} rows; later rows may hold other values")
    for rule in usable:
        held = evidence[rule["rule_id"]]["would_hold"]
        if held and rule.get("status") != "dropped":
            warnings.append(f"rule {rule['rule_id']} would hold {held} of {len(rows)} profiled cells; "
                            f"the application step lists held cells for a person")
        if rule["operation"] == "parse_number" and rule.get("status") != "dropped":
            decimal, thousands = rule["parameters"]["decimal_separator"], rule["parameters"]["thousands_separator"]
            padded = [(value.strip(), count) for value, count in counters[rule["column"]].items()
                      if drops_leading_zero(value.strip(), decimal, thousands)]
            if padded:
                warnings.append(f"rule {rule['rule_id']} would drop a leading 0 from "
                                f"{sum(count for _value, count in padded)} of {len(rows)} profiled cells, such as "
                                f"{preview(padded[0][0])!r}; keep it only if the column is a quantity, not a code")
    status = "pass" if not findings else "fail"
    result = {"status": status, "plan": plan_rel, "evidence_written": bool(options.write_evidence),
              "rules": {"proposed": sum(rule.get("status") == "proposed" for rule in usable),
                        "dropped": sum(rule.get("status") == "dropped" for rule in usable)},
              "findings": findings[:60], "warnings": warnings[:30]}
    return result, 0 if status == "pass" else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Draft and check a cleaning plan for one table.")
    commands = parser.add_subparsers(dest="command", required=True)
    draft = commands.add_parser("draft", help="profile the table and write a draft plan")
    draft.add_argument("--table", required=True)
    draft.add_argument("--delimiter", required=True, choices=sorted(DELIMITERS))
    draft.add_argument("--max-rows", required=True, type=int)
    draft.add_argument("--out-dir", required=True)
    draft.add_argument("--root", default=".")
    check = commands.add_parser("check", help="recount evidence and list what blocks the plan")
    check.add_argument("--table", required=True)
    check.add_argument("--plan", required=True)
    check.add_argument("--write-evidence", action="store_true")
    check.add_argument("--root", default=".")
    try:
        options = parser.parse_args(argv)
    except SystemExit as error:
        if error.code == 0:
            return 0
        print(json.dumps({"status": "refused", "reason": "the command line is invalid; see standard error"}))
        return 2
    try:
        if options.command == "draft":
            result, code = command_draft(options), 0
        else:
            result, code = command_check(options)
    except Refused as error:
        result, code = {"status": "refused", "reason": str(error)}, 2
    except OSError as error:
        result, code = {"status": "refused", "reason": f"file system error: {error}"}, 2
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
