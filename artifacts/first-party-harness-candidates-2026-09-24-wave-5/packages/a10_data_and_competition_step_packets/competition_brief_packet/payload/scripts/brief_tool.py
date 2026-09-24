"""Start and check a structured competition brief. Effects: reads pages and data files under --root; writes only a new brief file (start).

start: lists the saved competition pages (.md and .txt files) and the CSV data files, records
their digests and the data file headers, and writes a new brief whose facts are all empty.
check: verifies the filled brief. Every fact needs a quote that appears word for word in a page,
or it stays empty and has a question in unknowns. Column and file facts must agree with the
headers of the data files, and the metric direction must fit the metric. Values are compared with
the data and the quotes: the target type with the distinct training values of the target columns,
the prediction value type with the sample submission's values, the numbers of the deadline with
its quote, and "yes" for outside data with a quote that forbids it. Wording that may not fit a
value gives a warning.

Usage:
  python3 -I -B brief_tool.py start --pages DIR --data DIR --brief PATH [--root DIR]
  python3 -I -B brief_tool.py check --pages DIR --data DIR --brief PATH [--root DIR]

Exit status: 0 started or passed, 1 findings, 2 refused input. Standard output holds one JSON
object. No network use, no subprocess and no model call. MIT licence.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import unicodedata
from pathlib import Path, PurePosixPath

MAX_PAGE_BYTES = 1024 * 1024
MAX_PAGES = 40
MAX_DATA_FILES = 50
MAX_COUNTED_BYTES = 64 * 1024 * 1024
MAX_HEADER_BYTES = 1024 * 1024
MAX_JSON_BYTES = 4 * 1024 * 1024
PAGE_SUFFIXES = (".md", ".txt")
TARGET_TYPES = ("binary", "multiclass", "regression", "multilabel", "ranking", "other")
VALUE_TYPES = ("probability", "class_label", "real_number", "integer", "text", "other")
METRIC_DIRECTION = {"rmse": "minimize", "mse": "minimize", "mae": "minimize", "rmsle": "minimize",
                    "log_loss": "minimize", "mape": "minimize", "smape": "minimize", "auc": "maximize",
                    "accuracy": "maximize", "f1": "maximize", "macro_f1": "maximize", "map_at_k": "maximize",
                    "quadratic_weighted_kappa": "maximize", "r2": "maximize"}
METRIC_PATTERNS = {
    "rmse": r"\brmse\b|root[ -]mean[ -]squared?[ -]error",
    "mse": r"\bmse\b|(?<!root )mean[ -]squared?[ -]error",
    "mae": r"\bmae\b|mean[ -]absolute[ -]error",
    "rmsle": r"\brmsle\b|root[ -]mean[ -]squared?[ -]log(?:arithmic)?[ -]error",
    "log_loss": r"log[ -]?loss|logarithmic[ -]loss|cross[ -]entropy",
    "mape": r"\bmape\b|mean[ -]absolute[ -]percentage[ -]error",
    "smape": r"\bsmape\b|symmetric[ -]mean[ -]absolute[ -]percentage[ -]error",
    "auc": r"\bauc\b|area under the (?:roc|receiver operating)|\broc\b",
    "accuracy": r"\baccuracy\b",
    "f1": r"\bf1\b|\bf[ -]score\b|\bf[ -]measure\b",
    "macro_f1": r"macro[ -](?:averaged[ -])?f1|macro[ -]f[ -]score",
    "map_at_k": r"\bmap@\s*(?:\d+|k)\b|mean[ -]average[ -]precision",
    "quadratic_weighted_kappa": r"quadratic[ -]weighted[ -]kappa|\bqwk\b|\bkappa\b",
    "r2": r"\br2\b|r\^2|r[ -]squared|coefficient of determination",
}
NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
                "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty")
RECORD_TYPE = "competition_brief/v2"
FACTS = {"task": "text", "target_columns": "columns", "target_type": "choice", "metric": "metric",
         "metric_direction": "direction", "id_column": "column", "prediction_columns": "columns",
         "prediction_value_type": "choice", "train_file": "file", "test_file": "file",
         "sample_submission_file": "file", "external_data_allowed": "choice", "daily_submission_limit": "count",
         "team_size_limit": "count", "deadline": "text"}
QUOTE_MARKS = {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u00a0": " "}
#: ASCII decimal notation only, the same rule as the submission assembly step.
PLAIN_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
DISTINCT_CAP = 1000
MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december")
MONTH_NUMBER = {**{name: str(index) for index, name in enumerate(MONTHS, start=1)},
                **{name[:3]: str(index) for index, name in enumerate(MONTHS, start=1)}, "sept": "9"}
#: Words that say outside data is not freely allowed; "yes" cannot rest on a quote that holds one.
PROHIBITION = re.compile(r"\b(?:not\s+(?:be\s+)?(?:allowed|permitted|used)|prohibited|forbidden|disallowed|banned|"
                         r"may\s+not|must\s+not|cannot|can't|no\s+(?:external|outside|additional|extra|other)|"
                         r"only\s+(?:the\s+)?(?:provided|supplied|given|competition))\b", re.IGNORECASE)
LIMIT_WORDS = re.compile(r"\b(?:not|no|never|only|without|except|unless|limited|restricted)\b", re.IGNORECASE)
PROBABILITY_WORDS = re.compile(r"probabilit|likelihood|\blikely\b|\bchance\b|\bconfidence\b|\b0 to 1\b|"
                               r"\bbetween 0 and 1\b", re.IGNORECASE)
LINE_MARKS = re.compile(r"^(?:#{1,6}\s+|[-*+]\s+|\d{1,3}[.)]\s+|>\s*)+")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
TOKENS = re.compile(r"[a-z0-9]+")
HINT_FLOOR = 0.2
HINT_LENGTH = 300
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "contracts" / "output.schema.json"
SCHEMA_KEYWORDS = frozenset(("$schema", "$id", "$comment", "title", "description", "$defs", "$ref", "type",
                             "properties", "required", "additionalProperties", "items", "minItems", "maxItems",
                             "uniqueItems", "enum", "const", "minimum", "maximum", "minLength", "maxLength",
                             "pattern"))


class Refused(Exception):
    """Input this script will not work on (exit status 2)."""


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


def folder(root: Path, relative: str, label: str) -> Path:
    path = inside(root, relative, label)
    if not path.is_dir():
        raise Refused(f"{label} is not an existing folder: {relative}")
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


# Pages and data files --------------------------------------------------------------------------

def normalize(text: str) -> str:
    """Compare text after Unicode folding, straight quotes, no emphasis marks and single spaces."""
    text = unicodedata.normalize("NFKC", text)
    for mark, plain in QUOTE_MARKS.items():
        text = text.replace(mark, plain)
    text = text.replace("*", "").replace("`", "")
    return " ".join(text.split())


def page_sentences(raw: str, normalized: str) -> list[str]:
    """Sentences of one page in the compared form; each one is a word-for-word part of the normalized page."""
    found = []
    for line in raw.splitlines():
        for piece in SENTENCE_END.split(LINE_MARKS.sub("", line.strip())):
            sentence = normalize(piece)
            if len(sentence) >= 8 and sentence in normalized and sentence not in found:
                found.append(sentence)
    return found


def closeness(quote: str, sentence: str) -> float:
    """Share of distinct words that the quote and the sentence have in common."""
    left, right = set(TOKENS.findall(quote.casefold())), set(TOKENS.findall(sentence.casefold()))
    return len(left & right) / len(left | right) if left and right else 0.0


def quote_finding(name: str, page: str, quote: str, texts: dict, sentences: dict) -> str:
    """Say where the words are: on another page, in the closest sentence of the named page, or nowhere close."""
    holders = [other for other in sorted(texts) if other != page and len(quote) >= 8 and quote in texts[other]]
    if holders:
        return (f"{name}: the quote is not found word for word in {page}, but it is in {holders[0]}; "
                f"set source.file to {holders[0]}")
    ranked = sorted(((closeness(quote, sentence), index, sentence)
                     for index, sentence in enumerate(sentences.get(page, []))), key=lambda item: (-item[0], item[1]))
    if ranked and ranked[0][0] >= HINT_FLOOR:
        sentence = ranked[0][2]
        shown = sentence if len(sentence) <= HINT_LENGTH else sentence[:HINT_LENGTH - 3] + "..."
        return (f'{name}: the quote is not found word for word in {page}; the closest sentence there is "{shown}"; '
                f"copy the exact words")
    return f"{name}: the quote is not found word for word in {page}; no sentence there is close, so read the page again"


def read_pages(root: Path, pages_rel: str) -> tuple[list, dict, dict]:
    pages_dir = folder(root, pages_rel, "--pages")
    entries, texts, sentences = [], {}, {}
    for path in sorted(pages_dir.iterdir(), key=lambda item: item.name):
        if path.name.startswith(".") or path.suffix.lower() not in PAGE_SUFFIXES:
            continue
        if path.is_symlink() or not path.is_file():
            raise Refused(f"page {path.name} is not a regular file")
        if path.stat().st_size > MAX_PAGE_BYTES:
            raise Refused(f"page {path.name} is larger than {MAX_PAGE_BYTES} bytes; split it or shorten it first")
        data = path.read_bytes()
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise Refused(f"page {path.name} is not UTF-8 text") from None
        texts[path.name] = normalize(text)
        sentences[path.name] = page_sentences(text, texts[path.name])
        entries.append({"file": path.name, "sha256": hashlib.sha256(data).hexdigest(),
                        "words": len(text.split())})
    if not entries:
        raise Refused(f"{pages_rel} holds no .md or .txt page; save the pages as text first")
    if len(entries) > MAX_PAGES:
        raise Refused(f"{pages_rel} holds more than {MAX_PAGES} pages")
    return entries, texts, sentences


def data_file_entry(path: Path) -> dict:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        first = stream.read(MAX_HEADER_BYTES)
        digest.update(first)
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    header, rows = None, None
    line_end = first.find(b"\n")
    if line_end >= 0 or len(first) < MAX_HEADER_BYTES:
        line = first[:line_end] if line_end >= 0 else first
        try:
            header = next(csv.reader([line.decode("utf-8-sig").rstrip("\r")]), None)
        except (UnicodeDecodeError, csv.Error):
            header = None
    size = path.stat().st_size
    if header is not None and size <= MAX_COUNTED_BYTES:
        try:
            text = path.read_bytes().decode("utf-8-sig")
            reader = csv.reader(io.StringIO(text, newline=""))
            next(reader, None)
            rows = sum(1 for record in reader if record)
        except (UnicodeDecodeError, csv.Error):
            rows = None
    return {"file": path.name, "sha256": digest.hexdigest(), "size_bytes": size, "header": header, "rows": rows}


def read_data_files(root: Path, data_rel: str) -> list:
    data_dir = folder(root, data_rel, "--data")
    entries = []
    for path in sorted(data_dir.iterdir(), key=lambda item: item.name):
        if path.name.startswith(".") or path.suffix.lower() != ".csv":
            continue
        if path.is_symlink() or not path.is_file():
            raise Refused(f"data file {path.name} is not a regular file")
        entries.append(data_file_entry(path))
    if len(entries) > MAX_DATA_FILES:
        raise Refused(f"{data_rel} holds more than {MAX_DATA_FILES} CSV files")
    return entries


# Fact checks ---------------------------------------------------------------------------------

def mentions_count(quote: str, value: int) -> bool:
    if re.search(rf"(?<![0-9]){value}(?![0-9])", quote):
        return True
    return value < len(NUMBER_WORDS) and re.search(rf"\b{NUMBER_WORDS[value]}\b", quote, re.IGNORECASE) is not None


def date_numbers(text: str) -> list[str]:
    """Numbers of a date or time in order: digit groups without leading zeros, and month names as month numbers."""
    found = []
    for token in re.findall(r"[0-9]+|[A-Za-z]+", text):
        if token[0].isdigit():
            number = token.lstrip("0") or "0"
        else:
            number = MONTH_NUMBER.get(token.casefold().rstrip("."), "")
        if number and number not in found:
            found.append(number)
    return found


def deadline_missing(value: str, quote: str) -> list[str]:
    """Numbers of the deadline value that its quote does not hold, so an invented date cannot pass."""
    available = set(date_numbers(quote))
    return [number for number in date_numbers(value) if number not in available]


def quoted_value_findings(name: str, value, quote: str) -> tuple[list, list]:
    """Checks of one value against its own verified quote."""
    findings, warnings = [], []
    if name == "deadline" and isinstance(value, str):
        missing = deadline_missing(value, quote)
        if missing:
            findings.append(f"deadline: the quote does not contain {', '.join(missing)} from the value; copy the date "
                            f"and time as the page writes them")
    if name == "external_data_allowed":
        prohibited = PROHIBITION.search(quote)
        if value == "yes" and prohibited:
            findings.append(f"external_data_allowed: the quote says {prohibited.group(0)!r}, which does not fit yes; use "
                            f"no, or with_conditions when the page allows some outside data")
        if value == "no" and not prohibited and not LIMIT_WORDS.search(quote):
            warnings.append("external_data_allowed: the quote does not say that outside data is limited; read it again")
    if name == "prediction_value_type":
        if value != "probability" and re.search(r"probabilit", quote, re.IGNORECASE):
            warnings.append(f"prediction_value_type: the quote mentions a probability, but the value is {value}; read "
                            f"the quote again")
        if value == "probability" and not PROBABILITY_WORDS.search(quote):
            warnings.append("prediction_value_type: the quote names no probability and no range from 0 to 1; read the "
                            "quote again")
    return findings, warnings


def column_values(path: Path, columns: list) -> dict | None:
    """Distinct nonempty values of the named columns in first-seen order, at most DISTINCT_CAP + 1 each.

    None means the file was not read: it is larger than the counted size or it is not valid UTF-8 CSV.
    """
    if path.stat().st_size > MAX_COUNTED_BYTES:
        return None
    try:
        reader = csv.reader(io.StringIO(path.read_bytes().decode("utf-8-sig"), newline=""))
        header = next(reader, None) or []
        positions = {name: header.index(name) for name in columns if name in header}
        found = {name: {} for name in positions}
        for record in reader:
            for name, position in positions.items():
                cell = record[position].strip() if position < len(record) else ""
                if cell and len(found[name]) <= DISTINCT_CAP:
                    found[name].setdefault(cell, None)
    except (UnicodeDecodeError, csv.Error):
        return None
    return {name: list(values) for name, values in found.items()}


def distinct_count(values: list) -> int:
    """Distinct values, where number text counts by its value, so 1 and 1.0 are one value."""
    if values and all(PLAIN_NUMBER.fullmatch(value) for value in values):
        return len({float(value) for value in values})
    return len(values)


def target_type_findings(target_type, values_by_column: dict) -> list:
    """The target type must fit the distinct values of each target column in the training file."""
    findings = []
    for column, values in values_by_column.items():
        count = distinct_count(values)
        shown = f"more than {DISTINCT_CAP}" if len(values) > DISTINCT_CAP else str(count)
        numbers = [float(value) for value in values if PLAIN_NUMBER.fullmatch(value)]
        if not values:
            findings.append(f"target_columns: {column!r} holds no value in the training file")
        elif target_type == "binary" and count != 2:
            findings.append(f"target_type: binary needs exactly two distinct values in {column!r}, but the training "
                            f"file holds {shown}, such as {', '.join(repr(value) for value in values[:3])}")
        elif target_type == "regression" and len(numbers) != len(values):
            text = next(value for value in values if not PLAIN_NUMBER.fullmatch(value))
            findings.append(f"target_type: regression needs numbers, but {column!r} holds {text!r}")
        elif target_type == "regression" and count == 2:
            findings.append(f"target_type: {column!r} holds only the two values {values[0]!r} and {values[1]!r}, "
                            f"which makes a binary target, not regression")
        elif target_type == "multiclass" and count <= 2:
            findings.append(f"target_type: multiclass needs more than two classes, but {column!r} holds {shown}; two "
                            f"classes make a binary target")
        elif target_type == "multiclass" and len(numbers) == len(values) \
                and any(not number.is_integer() for number in numbers):
            text = next(value for value, number in zip(values, numbers) if not number.is_integer())
            findings.append(f"target_type: multiclass classes are labels or whole numbers, but {column!r} holds "
                            f"{text!r}, which fits regression")
        elif target_type == "multilabel" and len(values_by_column) > 1 and count > 2:
            findings.append(f"target_type: multilabel target columns hold at most two values each, but {column!r} "
                            f"holds {shown}")
    return findings


def value_type_findings(value_type, values_by_column: dict) -> list:
    """The prediction value type must fit the values that the sample submission shows."""
    for column, values in values_by_column.items():
        for value in values:
            number = float(value) if PLAIN_NUMBER.fullmatch(value) else None
            problem = ""
            if value_type in ("probability", "real_number", "integer") and number is None:
                problem = "which is not a number"
            elif value_type == "probability" and not 0.0 <= number <= 1.0:
                problem = "which is outside 0 to 1"
            elif value_type in ("class_label", "integer") and number is not None and not number.is_integer():
                problem = "which is not a class label" if value_type == "class_label" else "which is not a whole number"
            if problem:
                return [f"prediction_value_type: the sample submission holds {value!r} in {column!r}, {problem}; read "
                        f"the page about the submission format again"]
    return []


def fact_findings(brief: dict, texts: dict, files: dict, sentences: dict, data_dir: Path) -> tuple[list, list]:
    findings, warnings = [], []
    facts = brief.get("facts", {})
    unknowns = brief.get("unknowns", [])
    asked = [item.get("fact") for item in unknowns if isinstance(item, dict)]
    for name in sorted(set(asked)):
        if name not in FACTS:
            findings.append(f"unknowns names {name!r}, which is not a fact of this brief")
        elif asked.count(name) > 1:
            findings.append(f"unknowns names {name} more than once")
    for item in unknowns:
        if isinstance(item, dict) and not str(item.get("question", "")).strip().endswith("?"):
            findings.append(f"unknowns: the question for {item.get('fact')} must end with a question mark")
    for name, kind in FACTS.items():
        fact = facts.get(name)
        if not isinstance(fact, dict):
            continue
        value, source = fact.get("value"), fact.get("source")
        if value is None or source is None:
            if value is not None or source is not None:
                findings.append(f"{name}: set both value and source, or leave both null")
            elif name not in asked:
                findings.append(f"{name}: no value and no question; quote a page or add it to unknowns")
            continue
        if name in asked:
            findings.append(f"{name}: has a value, so remove it from unknowns")
        if not isinstance(source, dict):
            continue
        page, quote = source.get("file"), normalize(str(source.get("quote", "")))
        if page not in texts:
            holders = [other for other in sorted(texts) if len(quote) >= 8 and quote in texts[other]]
            findings.append(f"{name}: source.file {page!r} is not one of the pages"
                            + (f"; the quote is in {holders[0]}" if holders else ""))
            continue
        if len(quote) < 8 or quote not in texts[page]:
            findings.append(quote_finding(name, page, quote, texts, sentences))
            continue
        if kind == "column" and isinstance(value, str) and value not in quote:
            findings.append(f"{name}: the quote does not contain the column name {value!r}")
        if kind == "columns" and isinstance(value, list) and not any(str(item) in quote for item in value):
            findings.append(f"{name}: the quote contains none of the named columns")
        if kind == "file" and isinstance(value, str):
            if value not in files:
                findings.append(f"{name}: {value!r} is not one of the data files {sorted(files)}")
            elif value not in quote:
                findings.append(f"{name}: the quote does not contain the file name {value!r}")
        if kind == "count" and isinstance(value, int) and not mentions_count(quote, value):
            findings.append(f"{name}: the quote does not state the number {value}")
        if kind == "metric" and value in METRIC_PATTERNS and not re.search(METRIC_PATTERNS[value], quote, re.IGNORECASE):
            findings.append(f"{name}: the quote does not name the metric {value}; check the metric")
        quoted_findings, quoted_warnings = quoted_value_findings(name, value, quote)
        findings += quoted_findings
        warnings += quoted_warnings
    metric, direction = facts.get("metric", {}).get("value"), facts.get("metric_direction", {}).get("value")
    if metric in METRIC_DIRECTION and direction is not None and direction != METRIC_DIRECTION[metric]:
        findings.append(f"metric_direction: {metric} is scored with {METRIC_DIRECTION[metric]}, not {direction}")
    findings += header_findings(facts, files)
    findings += data_value_findings(facts, files, data_dir, warnings)
    target_type, value_type = facts.get("target_type", {}).get("value"), facts.get("prediction_value_type", {}).get("value")
    if target_type == "regression" and metric in ("auc", "log_loss", "accuracy", "f1", "macro_f1"):
        warnings.append(f"a regression target with the metric {metric} is unusual; read the evaluation page again")
    if value_type == "probability" and metric in ("rmse", "mae", "rmsle", "mape", "smape", "r2"):
        warnings.append(f"probability predictions with the metric {metric} are unusual; read the evaluation page again")
    return findings, warnings


def fact_value(facts: dict, name: str):
    fact = facts.get(name)
    return fact.get("value") if isinstance(fact, dict) else None


def data_value_findings(facts: dict, files: dict, data_dir: Path, warnings: list) -> list:
    """Compare the target type and the prediction value type with the values in the data files."""
    findings = []
    checks = (("target_type", "train_file", "target_columns", target_type_findings),
              ("prediction_value_type", "sample_submission_file", "prediction_columns", value_type_findings))
    for fact, file_fact, columns_fact, compare in checks:
        chosen, file_name, columns = fact_value(facts, fact), fact_value(facts, file_fact), fact_value(facts, columns_fact)
        if chosen is None or not isinstance(file_name, str) or file_name not in files or not isinstance(columns, list):
            continue
        values = column_values(data_dir / file_name, columns)
        if values is None:
            warnings.append(f"{fact}: the values of {file_name} were not read, because the file is larger than "
                            f"{MAX_COUNTED_BYTES} bytes or is not UTF-8 CSV; check {fact} by reading the page again")
            continue
        findings += compare(chosen, values)
    return findings


def header_findings(facts: dict, files: dict) -> list:
    """Column facts must agree with the data file headers, as the files define the task."""
    findings = []

    def header(name):
        entry = files.get(fact_value(facts, name)) if isinstance(fact_value(facts, name), str) else None
        return entry.get("header") if entry else None

    train, test, sample = header("train_file"), header("test_file"), header("sample_submission_file")
    targets, identity = fact_value(facts, "target_columns"), fact_value(facts, "id_column")
    predictions = fact_value(facts, "prediction_columns")
    for target in targets if isinstance(targets, list) else []:
        if train is not None and target not in train:
            findings.append(f"target_columns: {target!r} is not a column of the training file")
        if test is not None and target in test:
            findings.append(f"target_columns: {target!r} is also a column of the test file, so it is a feature, "
                            f"not a target")
    if isinstance(identity, str):
        for label, columns in (("test", test), ("sample submission", sample)):
            if columns is not None and identity not in columns:
                findings.append(f"id_column: {identity!r} is not a column of the {label} file")
    if isinstance(predictions, list) and sample is not None:
        missing = [column for column in predictions if column not in sample]
        if missing:
            findings.append(f"prediction_columns: {missing} are not columns of the sample submission")
        elif isinstance(identity, str) and set(sample) != {identity, *predictions}:
            findings.append(f"prediction_columns: the sample submission has the columns {sample}, which is not "
                            f"the id column plus the prediction columns")
    return findings


# Commands ----------------------------------------------------------------------------------------

def skeleton(pages: list, data_files: list) -> dict:
    return {"record_type": RECORD_TYPE, "pages": pages, "data_files": data_files,
            "facts": {name: {"value": None, "source": None} for name in FACTS}, "unknowns": []}


def command_start(options) -> dict:
    root = Path(options.root).resolve()
    pages_rel = relative_path(options.pages, "--pages")
    data_rel = relative_path(options.data, "--data")
    brief_rel = relative_path(options.brief, "--brief")
    brief_path = inside(root, brief_rel, "--brief")
    if brief_path.exists() or brief_path.is_symlink():
        raise Refused(f"{brief_rel} already exists; this step never overwrites. Use a new --brief path")
    pages, _texts, _sentences = read_pages(root, pages_rel)
    data_files = read_data_files(root, data_rel)
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    with open(brief_path, "x", encoding="utf-8", newline="") as stream:
        stream.write(json.dumps(skeleton(pages, data_files), indent=1, ensure_ascii=False) + "\n")
    return {"status": "started", "brief": brief_rel,
            "pages": [{"file": page["file"], "words": page["words"]} for page in pages],
            "data_files": [{"file": entry["file"], "header": entry["header"], "rows": entry["rows"]}
                           for entry in data_files],
            "facts_to_fill": list(FACTS),
            "next": "Read every page, fill each fact with a value and an exact quote, or add a question to unknowns."}


def command_check(options) -> tuple[dict, int]:
    root = Path(options.root).resolve()
    pages_rel = relative_path(options.pages, "--pages")
    data_rel = relative_path(options.data, "--data")
    brief_rel = relative_path(options.brief, "--brief")
    brief_path = inside(root, brief_rel, "--brief")
    if not brief_path.is_file():
        raise Refused(f"{brief_rel} does not exist; run start first")
    if brief_path.stat().st_size > MAX_JSON_BYTES:
        raise Refused(f"{brief_rel} is larger than {MAX_JSON_BYTES} bytes")
    try:
        brief = strict_json(brief_path.read_bytes(), "the brief")
    except Refused as error:
        # The model edits this file by hand, so a syntax slip is a finding it can fix, not a refusal.
        return {"status": "fail", "brief": brief_rel, "facts_filled": 0, "unknowns": 0,
                "findings": [f"{error}. Fix the JSON syntax at that place, change nothing else, and run the check "
                             f"again"], "warnings": []}, 1
    if not SCHEMA_PATH.is_file():
        raise Refused(f"the brief schema is missing next to this script: {SCHEMA_PATH}")
    schema = strict_json(SCHEMA_PATH.read_bytes(), "the brief schema")
    pages, texts, sentences = read_pages(root, pages_rel)
    data_files = read_data_files(root, data_rel)
    data_dir = folder(root, data_rel, "--data")
    findings = [f"shape: {error}" for error in schema_errors(brief, schema)]
    warnings = []
    if isinstance(brief, dict) and not findings:
        if brief["pages"] != pages or brief["data_files"] != data_files:
            findings.append("the pages or data_files section no longer matches the files; restore it, or run start "
                            "again with a new brief path if a file changed")
        fact_problems, warnings = fact_findings(brief, texts, {entry["file"]: entry for entry in data_files}, sentences,
                                                data_dir)
        findings += fact_problems
    filled = sum(1 for fact in (brief.get("facts") or {}).values() if isinstance(fact, dict)
                 and fact.get("value") is not None) if isinstance(brief, dict) else 0
    status = "pass" if not findings else "fail"
    return {"status": status, "brief": brief_rel, "facts_filled": filled,
            "unknowns": len(brief.get("unknowns") or []) if isinstance(brief, dict) else 0,
            "findings": findings[:60], "warnings": warnings}, 0 if status == "pass" else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Start and check a structured competition brief.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("start", "check"):
        command = commands.add_parser(name)
        command.add_argument("--pages", required=True)
        command.add_argument("--data", required=True)
        command.add_argument("--brief", required=True)
        command.add_argument("--root", default=".")
    try:
        options = parser.parse_args(argv)
    except SystemExit as error:
        if error.code == 0:
            return 0
        print(json.dumps({"status": "refused", "reason": "the command line is invalid; see standard error"}))
        return 2
    try:
        if options.command == "start":
            result, code = command_start(options), 0
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
