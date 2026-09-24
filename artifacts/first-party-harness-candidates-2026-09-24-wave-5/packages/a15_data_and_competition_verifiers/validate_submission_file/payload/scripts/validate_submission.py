"""Validate a submission file against the sample submission. Effects: reads the named files under --root or one JSON bundle; prints one JSON object; writes nothing, starts no process, uses no network and uploads nothing.

Exit status: 0 the submission has the sample's exact header, id set and row count, and every
prediction is present and valid for the task type, 1 at least one check failed, 2 no verdict
(refused input or an internal error).

Usage:
    python3 -I -B validate_submission.py --submission SUBMISSION.csv --sample SAMPLE.csv --task TYPE
        [--id-column NAME] [--labels A B ...] [--min X] [--max X] [--sum-tolerance 0.001]
        [--require-same-order] [--root DIR] [--delimiter comma|tab|semicolon|pipe]
        [--max-examples N] [--max-bytes N]
    python3 -I -B validate_submission.py --bundle FILE_OR_DASH --task TYPE ...

Task types: probability, class_probabilities, label, number and text, described in
references/task-types.md. A bundle is one JSON object with the members "submission" and "sample",
each holding the text of that file; "-" reads the bundle from standard input.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import sys
from pathlib import Path

RECORD_TYPE = "submission_validation/v1"
DEFAULT_MAX_BYTES = 64 * 1024 * 1024
HARD_MAX_BYTES = 1024 * 1024 * 1024
DELIMITERS = {"comma": ",", "tab": "\t", "semicolon": ";", "pipe": "|"}
BUNDLE_MEMBERS = ("submission", "sample")
TASKS = ("probability", "class_probabilities", "label", "number", "text")
NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,4})?")
MISSING_TOKENS = frozenset({"na", "n/a", "nan", "null", "none", "inf", "+inf", "-inf", "infinity", "+infinity",
                            "-infinity"})
INDEX_NAMES = frozenset({"", "index", "unnamed: 0"})
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
        raise Refused("compressed_input", f"{label} is a compressed file; unpack it and check the CSV it holds")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise Refused("not_utf8", f"{label}: byte {error.start} is not UTF-8") from None
    if "\x00" in text:
        raise Refused("not_text", f"{label} holds a NUL character")
    return text


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
            value = strict_json(decode(data, "the bundle"), "the bundle")
            if not isinstance(value, dict):
                raise Refused("bundle_invalid", "the bundle is one JSON object")
            unknown = sorted(set(value) - set(BUNDLE_MEMBERS))
            if unknown:
                raise Refused("bundle_invalid", f"unknown bundle members {unknown}; allowed {list(BUNDLE_MEMBERS)}")
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

    def get(self, name: str, path: str | None):
        if self.bundle is not None and name in self.bundle:
            if path is not None:
                raise Refused("bad_arguments", f"--{name} and the bundle member {name!r} were both given; use one")
            value = self.bundle[name]
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
    """A UTF-8 delimited text with one header row; rows keep their field lists as read."""

    def __init__(self, label: str, data: bytes, delimiter: str, limit: int) -> None:
        self.label = label
        self.sha256 = hashlib.sha256(data).hexdigest()
        self.byte_order_mark = data.startswith(b"\xef\xbb\xbf")
        text = decode(data, label)
        csv.field_size_limit(max(limit, 131072))
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
        records, end = [], 0
        try:
            for fields in reader:
                records.append((end + 1, fields))
                end = reader.line_num
        except csv.Error as error:
            raise Refused("malformed_csv", f"{label} near line {reader.line_num}: {error}") from None
        if not records or not records[0][1]:
            raise Refused("header_missing", f"{label}: the first line must be the header row")
        self.header = records[0][1]
        width = len(self.header)
        self.rows: list = []
        self.blank_lines = 0
        for line, fields in records[1:]:
            if not fields:
                if width != 1:
                    self.blank_lines += 1
                    continue
                fields = [""]
            self.rows.append((len(self.rows) + 1, line, fields))


def shown(value: str) -> str:
    return value if len(value) <= EXCERPT else value[:EXCERPT - 3] + "..."


class Findings:
    """Complete counts for every check, and a bounded list of examples."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
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
            if value is not None:
                item[name] = shown(value) if isinstance(value, str) else value
        self.examples.append(item)


def number_of(text: str):
    if not NUMBER.fullmatch(text):
        return None
    value = float(text)
    return value if math.isfinite(value) else None


def loose_id(text: str) -> str:
    """A form of an id that ignores spaces and number formatting, used only for hints."""
    stripped = text.strip()
    value = number_of(stripped)
    if value is not None and value == int(value) and abs(value) < 2 ** 53:
        return str(int(value))
    return stripped


def fold_name(name: str) -> str:
    return " ".join(name.split()).casefold()


def build_parser() -> Parser:
    parser = Parser(description="Validate a submission against the sample submission. Exit 0 pass, 1 fail, "
                    "2 no verdict. Nothing is uploaded.")
    parser.add_argument("--submission", help="the file to upload later, relative to --root")
    parser.add_argument("--sample", help="the sample submission from the competition, relative to --root")
    parser.add_argument("--bundle", help="one JSON object with the members submission and sample; - reads standard input")
    parser.add_argument("--root", default=".", help="folder that every path is relative to (default: current folder)")
    parser.add_argument("--task", choices=TASKS, help="what each prediction value must be")
    parser.add_argument("--id-column", help="the id column (default: the first column of the sample)")
    parser.add_argument("--labels", nargs="+", help="every allowed value for --task label")
    parser.add_argument("--min", type=float, help="smallest allowed value for --task number")
    parser.add_argument("--max", type=float, help="largest allowed value for --task number")
    parser.add_argument("--sum-tolerance", type=float, default=0.001,
                        help="for --task class_probabilities: allowed distance of a row sum from 1 (default 0.001)")
    parser.add_argument("--require-same-order", action="store_true",
                        help="fail when the ids are not in the order of the sample")
    parser.add_argument("--delimiter", default="comma", help="comma (default), tab, semicolon, pipe or one character")
    parser.add_argument("--max-examples", type=int, default=30, help="violations listed in full, 1 to 500 (default 30)")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                        help=f"refuse a file larger than this (default {DEFAULT_MAX_BYTES})")
    return parser


def check_arguments(args) -> str:
    if not 1 <= args.max_bytes <= HARD_MAX_BYTES:
        raise Refused("bad_arguments", f"--max-bytes is between 1 and {HARD_MAX_BYTES}")
    if not 1 <= args.max_examples <= 500:
        raise Refused("bad_arguments", "--max-examples is between 1 and 500")
    delimiter = DELIMITERS.get(args.delimiter, args.delimiter)
    if len(delimiter) != 1 or delimiter in "\"\r\n":
        raise Refused("bad_arguments", "--delimiter is comma, tab, semicolon, pipe or one character")
    if args.task is None:
        raise Refused("bad_arguments", f"--task is required: one of {list(TASKS)}, from the competition rules")
    if args.task == "label":
        if not args.labels or len(set(args.labels)) != len(args.labels):
            raise Refused("bad_arguments", "--task label needs --labels with every allowed value, each once")
        if any(label.strip() == "" for label in args.labels):
            raise Refused("bad_arguments", "--labels holds an empty value; an empty cell is a missing value, not a label")
    elif args.labels:
        raise Refused("bad_arguments", "--labels applies to --task label only")
    if (args.min is not None or args.max is not None) and args.task != "number":
        raise Refused("bad_arguments", "--min and --max apply to --task number only")
    for value in (args.min, args.max):
        if value is not None and not math.isfinite(value):
            raise Refused("bad_arguments", "--min and --max are finite numbers")
    if args.min is not None and args.max is not None and args.min > args.max:
        raise Refused("bad_arguments", "--min is larger than --max")
    if not (math.isfinite(args.sum_tolerance) and 0 <= args.sum_tolerance < 1):
        raise Refused("bad_arguments", "--sum-tolerance is at least 0 and below 1")
    return delimiter


def run(args) -> tuple:
    delimiter = check_arguments(args)
    inputs = Inputs(args.root, args.bundle, args.max_bytes)
    sample = Table(*inputs.get("sample", args.sample), delimiter, args.max_bytes)
    submission = Table(*inputs.get("submission", args.submission), delimiter, args.max_bytes)
    findings = Findings(args.max_examples)
    warnings, hints = [], []

    # The sample is the authority; refuse a sample that cannot serve as one.
    expected = sample.header
    repeated = sorted({name for name in expected if expected.count(name) > 1})
    if repeated:
        raise Refused("sample_header_repeats", f"the sample header repeats {repeated[:10]}")
    id_name = args.id_column if args.id_column is not None else expected[0]
    if id_name not in expected:
        raise Refused("id_column_missing", f"--id-column {id_name!r} is not a column of the sample; its columns are "
                      f"{expected[:40]}")
    predicted = [name for name in expected if name != id_name]
    if not predicted:
        raise Refused("no_prediction_columns", "the sample has no column besides the id column")
    sample_id_at = expected.index(id_name)
    sample_ids, sample_values = [], {}
    for number, line, fields in sample.rows:
        if len(fields) != len(expected):
            raise Refused("sample_ragged", f"{sample.label} line {line} has {len(fields)} fields and its header has "
                          f"{len(expected)}")
        identity = fields[sample_id_at]
        if identity in sample_values:
            raise Refused("sample_ids_repeat", f"the sample repeats an id on line {line}; check --id-column")
        sample_values[identity] = fields
        sample_ids.append(identity)
    if not sample_ids:
        raise Refused("sample_has_no_rows", f"{sample.label} holds a header and no data rows, so it names no ids; "
                      "check that it is the sample submission of this competition")

    # Header.
    found = submission.header
    if found != expected:
        detail = {"expected": expected[:50], "found": found[:50],
                  "missing": [name for name in expected if name not in found][:50],
                  "extra": [name for name in found if name not in expected][:50]}
        findings.add("header", **detail)
        if len(found) == len(expected) and found[sample_id_at] in sample_values:
            hints.append("the first line holds data, not the header; write the sample header as the first line")
        elif len(found) == len(expected) + 1 and found[1:] == expected and found[0].strip().casefold() in INDEX_NAMES:
            hints.append("the first column looks like a written row index; write the file without the index")
        elif sorted(found) == sorted(expected):
            hints.append("the header has the right names in another order; write the columns in the sample order")
        elif [fold_name(name) for name in found] == [fold_name(name) for name in expected]:
            hints.append("the header names differ from the sample only in letter case or spaces")
    if submission.byte_order_mark and not sample.byte_order_mark:
        warnings.append("the submission starts with a byte order mark and the sample does not; some readers keep it "
                        "as part of the first column name")
    if submission.blank_lines:
        warnings.append(f"{submission.blank_lines} blank lines were skipped")

    width = len(found)
    position = {}
    for index, name in enumerate(found):
        position.setdefault(name, index)
    id_at = position.get(id_name)
    usable = []
    for number, line, fields in submission.rows:
        if len(fields) != width:
            findings.add("field_count", row=number, line=line, expected=width, found=len(fields))
        else:
            usable.append((number, line, fields))
    if len(submission.rows) != len(sample.rows):
        findings.add("row_count", expected=len(sample.rows), found=len(submission.rows))

    # Ids.
    seen: dict[str, int] = {}
    order = []
    if id_at is None:
        hints.append(f"the submission has no column named {id_name!r}, so its ids were not compared")
    else:
        for number, line, fields in usable:
            identity = fields[id_at]
            if identity in seen:
                findings.add("duplicate_id", id=identity, row=number, line=line, first_row=seen[identity])
                continue
            seen[identity] = number
            order.append(identity)
        missing = [identity for identity in sample_ids if identity not in seen]
        extra = [identity for identity in order if identity not in sample_values]
        for identity in missing:
            findings.add("missing_id", id=identity)
        for identity in extra:
            findings.add("extra_id", id=identity, row=seen[identity])
        if missing and extra:
            loose_missing = sorted(loose_id(identity) for identity in missing)
            if loose_missing == sorted(loose_id(identity) for identity in extra):
                hints.append("the ids differ from the sample only in spaces or number format, such as 17.0 against "
                             "17; write each id exactly as the sample writes it")
        if not missing and not extra and order != sample_ids:
            if args.require_same_order:
                first = next(index for index, (mine, theirs) in enumerate(zip(order, sample_ids)) if mine != theirs)
                findings.add("row_order", first_different_row=first + 1)
            else:
                warnings.append("the rows are not in the sample order; add --require-same-order if the rules ask "
                                "for the sample order")

    # Values.
    columns = [(name, position[name]) for name in predicted if name in position]
    all_values = []
    same_as_sample = 0
    for number, line, fields in usable:
        row_values = []
        for name, at in columns:
            text = fields[at]
            problem = value_problem(args, text)
            if problem is not None:
                rule, expectation = problem
                findings.add(rule, row=number, line=line, column=name, value=text, expected=expectation)
            row_values.append(text)
            all_values.append(text)
        if args.task == "class_probabilities" and len(columns) == len(predicted):
            numbers = [number_of(text) for text in row_values]
            if all(value is not None for value in numbers):
                total = math.fsum(numbers)
                if abs(total - 1) > args.sum_tolerance + 1e-12:
                    findings.add("row_sum", row=number, line=line, found=round(total, 9),
                                 expected=f"1 within {args.sum_tolerance}")
        if id_at is not None and fields[id_at] in sample_values:
            reference = sample_values[fields[id_at]]
            if all(fields[at] == reference[expected.index(name)] for name, at in columns):
                same_as_sample += 1
    if args.task == "text":
        tokens = sum(1 for text in all_values if text.strip().casefold() in MISSING_TOKENS)
        if tokens:
            warnings.append(f"{tokens} predictions hold a token such as NA or null; check that the rules allow it")
    if args.task in ("probability", "class_probabilities") and all_values:
        numbers = [number_of(text) for text in all_values]
        if all(value in (0.0, 1.0) for value in numbers):
            warnings.append("every prediction is 0 or 1; the task asks for probabilities, so the file may hold "
                            "class labels")
    if len(usable) > 1 and len(set(all_values)) == 1:
        warnings.append("every prediction holds the same value")
    if usable and same_as_sample == len(usable) and columns:
        warnings.append("every prediction equals the value the sample holds for that id; the sample values are "
                        "usually placeholders")

    applied = ["header", "field_count", "row_count", "missing_id", "extra_id", "duplicate_id", "missing_value"]
    if args.require_same_order:
        applied.append("row_order")
    applied += {"probability": ["not_a_number", "out_of_range"],
                "class_probabilities": ["not_a_number", "out_of_range", "row_sum"],
                "label": ["not_allowed_label"],
                "number": ["not_a_number", "out_of_range"] if args.min is not None or args.max is not None
                else ["not_a_number"],
                "text": []}[args.task]
    checks = {name: findings.counts.get(name, 0) for name in applied}
    failed = [name for name, count in checks.items() if count]
    report = {
        "record_type": RECORD_TYPE,
        "status": "fail" if failed else "pass",
        "task": args.task,
        "submission": {"path": submission.label, "sha256": submission.sha256, "rows": len(submission.rows),
                       "columns": len(found)},
        "sample": {"path": sample.label, "sha256": sample.sha256, "rows": len(sample.rows), "columns": len(expected)},
        "id_column": id_name,
        "prediction_columns": predicted,
        "checks": checks,
        "failed_checks": failed,
        "violations_total": sum(checks.values()),
        "violations": findings.examples,
        "violations_shown": len(findings.examples),
        "hints": hints,
        "warnings": warnings,
        "upload": "not attempted; this script only reads files",
        "numbering": "row counts data rows of the submission from 1 without the header; line is the file line",
    }
    return report, 1 if failed else 0


def value_problem(args, text: str):
    """Return (rule, what was expected) when one prediction value is not valid for the task, else None."""
    missing = text.strip() == "" or text.strip().casefold() in MISSING_TOKENS
    if args.task == "text":
        return ("missing_value", "nonempty text") if text.strip() == "" else None
    if args.task == "label":
        if text in args.labels:
            return None
        if missing:
            return "missing_value", "one of the allowed labels"
        shown_labels = ", ".join(args.labels[:12]) + (" and more" if len(args.labels) > 12 else "")
        return "not_allowed_label", f"one of {shown_labels}"
    if missing:
        return "missing_value", "a number"
    value = number_of(text)
    if value is None:
        return "not_a_number", "a plain number such as 0.25 or 1e-4"
    if args.task in ("probability", "class_probabilities"):
        return None if 0 <= value <= 1 else ("out_of_range", "a probability from 0 to 1")
    if args.min is not None and value < args.min:
        return "out_of_range", f"at least {args.min}"
    if args.max is not None and value > args.max:
        return "out_of_range", f"at most {args.max}"
    return None


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
