"""Verify that fold assignments keep groups apart. Effects: reads the named files under --root or one JSON bundle; prints one JSON object; writes nothing, starts no process and uses no network.

Exit status: 0 every check passed, 1 at least one check failed, 2 no verdict (refused input or an
internal error). The checks: every row has exactly one fold, no group has rows in two folds, and,
when a label column is named, the label share of every fold stays within the tolerance of the
share over all rows.

Usage:
    python3 -I -B verify_folds.py --folds FOLDS.csv --group-column GROUP [--fold-column fold]
        [--train TRAIN.csv (--id-column ID | --row-column ROW)] [--label-column LABEL]
        [--label-tolerance 0.05] [--label-bins N] [--expected-folds K] [--root DIR]
        [--delimiter comma|tab|semicolon|pipe] [--max-examples N] [--no-values] [--max-bytes N]
    python3 -I -B verify_folds.py --bundle FILE_OR_DASH --group-column GROUP ...

A bundle is one JSON object with the member "folds" and, when needed, "train", each holding the
text of that file. A member replaces the file of the same name; "-" reads the bundle from
standard input.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

RECORD_TYPE = "fold_separation_check/v1"
DEFAULT_MAX_BYTES = 64 * 1024 * 1024
HARD_MAX_BYTES = 1024 * 1024 * 1024
DELIMITERS = {"comma": ",", "tab": "\t", "semicolon": ";", "pipe": "|"}
BUNDLE_MEMBERS = ("folds", "train")
ROW_NUMBER = re.compile(r"[0-9]{1,12}")
NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,4})?")
MAX_LABEL_VALUES = 50
PER_RULE_EXAMPLES = 3
EXCERPT = 60
SLACK = 1e-12


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

    def get(self, name: str, path: str | None, required: bool):
        """Return (label, bytes) for one input, or None for an optional input that was not given."""
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
            if required:
                raise Refused("bad_arguments", f"--{name} is required (or a bundle member {name!r})")
            return None
        return path, self.read_file(path)


class Table:
    """A UTF-8 delimited text with one header row, read completely."""

    def __init__(self, label: str, data: bytes, delimiter: str, limit: int) -> None:
        self.label = label
        self.sha256 = hashlib.sha256(data).hexdigest()
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
                              f"{width}; check the table structure first")
            self.rows.append((len(self.rows) + 1, line, fields))
        self.position = {name: index for index, name in enumerate(self.header)}

    def column(self, name: str, option: str) -> int:
        if name not in self.position:
            raise Refused("column_missing", f"{option} {name!r} is not a column of {self.label}; its columns are "
                          f"{self.header[:40]}")
        return self.position[name]


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
            if value is not None:
                item[name] = value
        self.examples.append(item)


def number_of(text: str):
    if not NUMBER.fullmatch(text):
        return None
    value = float(text)
    return value if value == value and abs(value) != float("inf") else None


def fold_order(folds) -> list:
    folds = list(folds)
    if all(number_of(fold) is not None for fold in folds):
        return sorted(folds, key=lambda fold: (number_of(fold), fold))
    return sorted(folds)


def build_parser() -> Parser:
    parser = Parser(description="Verify that fold assignments keep groups apart. Exit 0 pass, 1 fail, 2 no verdict.")
    parser.add_argument("--folds", help="the fold assignment file, relative to --root")
    parser.add_argument("--train", help="the training table the folds belong to, relative to --root")
    parser.add_argument("--bundle", help="one JSON object with the members folds and train; - reads standard input")
    parser.add_argument("--root", default=".", help="folder that every path is relative to (default: current folder)")
    parser.add_argument("--fold-column", default="fold", help="column of the fold file that holds the fold (default fold)")
    parser.add_argument("--group-column", help="column that names the entity a fold must keep whole")
    parser.add_argument("--id-column", help="id column present in the fold file and the training table")
    parser.add_argument("--row-column", help="column of the fold file that holds training data row numbers from 1")
    parser.add_argument("--label-column", help="label column whose shares per fold are compared")
    parser.add_argument("--label-tolerance", type=float, default=0.05,
                        help="largest allowed gap between a label share in a fold and in all rows (default 0.05)")
    parser.add_argument("--label-bins", type=int, help="cut a numeric label into this many bins of about equal size")
    parser.add_argument("--expected-folds", type=int, help="the number of folds the plan asks for")
    parser.add_argument("--delimiter", default="comma", help="comma (default), tab, semicolon, pipe or one character")
    parser.add_argument("--max-examples", type=int, default=30, help="violations listed in full, 1 to 500 (default 30)")
    parser.add_argument("--no-values", action="store_true", help="show the length of ids, groups and labels, not their text")
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
    if not args.group_column:
        raise Refused("bad_arguments", "name the entity column with --group-column; the task says which one")
    if args.id_column and args.row_column:
        raise Refused("bad_arguments", "give --id-column or --row-column, not both")
    if not 0 <= args.label_tolerance <= 1:
        raise Refused("bad_arguments", "--label-tolerance is a share from 0 to 1")
    if args.label_bins is not None and (args.label_column is None or not 2 <= args.label_bins <= 100):
        raise Refused("bad_arguments", "--label-bins is 2 to 100 and needs --label-column")
    if args.expected_folds is not None and not 2 <= args.expected_folds <= 1000:
        raise Refused("bad_arguments", "--expected-folds is 2 to 1000")
    return delimiter


def run(args) -> tuple:
    delimiter = check_arguments(args)
    inputs = Inputs(args.root, args.bundle, args.max_bytes)
    folds = Table(*inputs.get("folds", args.folds, True), delimiter, args.max_bytes)
    given_train = inputs.get("train", args.train, False)
    train = Table(*given_train, delimiter, args.max_bytes) if given_train else None
    rule = "id" if args.id_column else "row" if args.row_column else "position"
    if train is not None and rule == "position":
        raise Refused("match_rule_missing", "say how fold rows match training rows: --id-column NAME when both files "
                      "hold an id, or --row-column NAME when the fold file holds training row numbers")
    hide = args.no_values
    findings = Findings(args.max_examples, hide)
    fold_at = folds.column(args.fold_column, "--fold-column")
    reference_at = folds.column(args.id_column or args.row_column, "--id-column" if args.id_column else "--row-column") \
        if rule != "position" else None

    # The training rows the fold file must cover.
    lookup = None
    if train is not None:
        lookup = {}
        if rule == "id":
            train_id_at = train.column(args.id_column, "--id-column")
            for number, line, fields in train.rows:
                value = fields[train_id_at]
                if value == "":
                    raise Refused("empty_id_in_train", f"{train.label} row {number} (line {line}) has an empty id")
                if value in lookup:
                    raise Refused("duplicate_id_in_train", f"{train.label} rows {lookup[value]} and {number} share an id")
                lookup[value] = number
        else:
            lookup = {number: number for number, _line, _fields in train.rows}

    def reference(value):
        return value if rule != "id" else shown(value, hide)

    # Fold records.
    records, assigned, empty_fold = [], {}, set()
    for number, line, fields in folds.rows:
        if rule == "position":
            ref = number
        elif rule == "row":
            text = fields[reference_at]
            if not ROW_NUMBER.fullmatch(text) or int(text) < 1:
                raise Refused("row_value_invalid", f"{folds.label} line {line}: {args.row_column} must hold a training "
                              "data row number counted from 1")
            ref = int(text)
        else:
            ref = fields[reference_at]
        fold = fields[fold_at]
        if fold == "":
            empty_fold.add(ref)
            findings.add("row_without_fold", row=reference(ref), fold_file_row=number, line=line)
            continue
        if rule == "id" and ref == "":
            findings.add("unknown_row", fold_file_row=number, line=line, reason="the fold record has an empty id")
            continue
        if lookup is not None and ref not in lookup:
            findings.add("unknown_row", row=reference(ref), fold_file_row=number, line=line)
            continue
        assigned.setdefault(ref, []).append((fold, number))
        records.append((ref, fold, number, fields))
    for ref, items in assigned.items():
        if len(items) > 1:
            seen = fold_order({fold for fold, _number in items})
            findings.add("row_listed_twice" if len(seen) == 1 else "row_in_two_folds", row=reference(ref), folds=seen,
                         fold_file_rows=[number for _fold, number in items][:10])
    if lookup is not None:
        for ref, number in lookup.items():
            if ref not in assigned and ref not in empty_fold:
                findings.add("row_without_fold", row=reference(ref), train_row=number)
    elif rule == "row":
        for ref in range(1, max(list(assigned) + list(empty_fold), default=0) + 1):
            if ref not in assigned and ref not in empty_fold:
                findings.add("row_without_fold", row=ref, reason="no fold record holds this row number")

    def source_of(name: str, option: str) -> str:
        if train is not None and name in train.position:
            return "train"
        if name in folds.position:
            return "folds"
        where = folds.label + (f" or {train.label}" if train is not None else "")
        raise Refused("column_missing", f"{option} {name!r} is not a column of {where}")

    def values_of(name: str, option: str, copy_rule: str) -> tuple:
        """Return the value of a column for every fold record, read from the training table first."""
        origin = source_of(name, option)
        values = []
        in_folds = folds.position.get(name)
        in_train = train.position.get(name) if train is not None else None
        for ref, _fold, number, fields in records:
            if origin == "train":
                value = train.rows[lookup[ref] - 1][2][in_train]
                if in_folds is not None and fields[in_folds] != value:
                    findings.add(copy_rule, row=reference(ref), fold_file_row=number, column=name,
                                 train_value=shown(value, hide), fold_file_value=shown(fields[in_folds], hide))
            else:
                value = fields[in_folds]
            values.append(value)
        return origin, values

    # Groups.
    group_origin, groups = values_of(args.group_column, "--group-column", "group_copy_differs")
    spread: dict[str, dict[str, int]] = {}
    fold_rows: dict[str, int] = {}
    fold_groups: dict[str, set] = {}
    for (ref, fold, number, _fields), group in zip(records, groups):
        fold_rows[fold] = fold_rows.get(fold, 0) + 1
        if group == "":
            findings.add("row_without_group", row=reference(ref), fold_file_row=number)
            continue
        counts = spread.setdefault(group, {})
        counts[fold] = counts.get(fold, 0) + 1
        fold_groups.setdefault(fold, set()).add(group)
    split = {group: counts for group, counts in spread.items() if len(counts) > 1}
    for group, counts in sorted(split.items(), key=lambda item: (-sum(item[1].values()), item[0])):
        findings.add("group_in_two_folds", group=shown(group, hide),
                     rows_per_fold={fold: counts[fold] for fold in fold_order(counts)})

    # Label shares.
    label_origin, gap_max, label_report, empty_labels = None, None, None, 0
    if args.label_column:
        label_origin, labels = values_of(args.label_column, "--label-column", "label_copy_differs")
        pairs = []
        for (_ref, fold, _number, _fields), label in zip(records, labels):
            if label == "":
                empty_labels += 1
            else:
                pairs.append((fold, label))
        if args.label_bins:
            numbers = []
            for index, (_fold, label) in enumerate(pairs):
                value = number_of(label)
                if value is None:
                    raise Refused("label_not_numeric", f"--label-bins needs numeric labels; label number {index + 1} "
                                  "with a value is not a plain finite number")
                numbers.append(value)
            ordered = sorted(numbers)
            edges = [ordered[(len(ordered) * step) // args.label_bins] for step in range(1, args.label_bins)]
            names = [f"bin {step + 1} of {args.label_bins}" for step in range(args.label_bins)]
            pairs = [(fold, names[bisect.bisect_right(edges, value)]) for (fold, _label), value in zip(pairs, numbers)]
            label_report = {"bins": args.label_bins, "lower_edges_of_bins_2_and_up": edges}
        else:
            distinct = {label for _fold, label in pairs}
            if len(distinct) > MAX_LABEL_VALUES:
                raise Refused("too_many_label_values", f"the label has {len(distinct)} values; shares of single values "
                              f"mean little above {MAX_LABEL_VALUES}; add --label-bins 10 for a numeric label")
        overall: dict[str, int] = {}
        per_fold: dict[str, dict[str, int]] = {}
        for fold, label in pairs:
            overall[label] = overall.get(label, 0) + 1
            per_fold.setdefault(fold, {})
            per_fold[fold][label] = per_fold[fold].get(label, 0) + 1
        total = len(pairs)
        gap_max = 0.0
        shares_by_fold = {}
        for fold in fold_order(per_fold):
            counts = per_fold[fold]
            size = sum(counts.values())
            shares_by_fold[fold] = {}
            for label in sorted(overall):
                share, whole = counts.get(label, 0) / size, overall[label] / total
                gap = abs(share - whole)
                gap_max = max(gap_max, gap)
                shares_by_fold[fold][label] = round(share, 6)
                if gap > args.label_tolerance + SLACK:
                    findings.add("label_share_gap", fold=fold, label=label if args.label_bins else shown(label, hide),
                                 fold_share=round(share, 6), overall_share=round(whole, 6), gap=round(gap, 6))
        label_report = {**(label_report or {}), "overall_shares": {
            (label if args.label_bins or not hide else f"value {index + 1}"): round(overall[label] / total, 6)
            for index, label in enumerate(sorted(overall))}, "shares_by_fold": shares_by_fold if not hide else None}

    distinct_folds = fold_order(fold_rows)
    if args.expected_folds is not None and len(distinct_folds) != args.expected_folds:
        findings.add("fold_count", expected=args.expected_folds, found=len(distinct_folds), folds=distinct_folds[:50])

    applied = ["row_without_fold", "row_in_two_folds", "row_listed_twice", "unknown_row", "row_without_group",
               "group_in_two_folds"]
    if group_origin == "train" and args.group_column in folds.position:
        applied.append("group_copy_differs")
    if args.label_column:
        if label_origin == "train" and args.label_column in folds.position:
            applied.append("label_copy_differs")
        applied.append("label_share_gap")
    if args.expected_folds is not None:
        applied.append("fold_count")
    checks = {name: findings.counts.get(name, 0) for name in applied}
    failed = [name for name, count in checks.items() if count]
    sizes = [fold_rows[fold] for fold in distinct_folds]
    report = {
        "record_type": RECORD_TYPE,
        "status": "fail" if failed else "pass",
        "folds_file": {"path": folds.label, "sha256": folds.sha256, "rows": len(folds.rows),
                       "blank_lines_skipped": folds.blank_lines},
        "train_file": None if train is None else {"path": train.label, "sha256": train.sha256, "rows": len(train.rows),
                                                  "blank_lines_skipped": train.blank_lines},
        "match": {"rule": rule, "column": args.id_column or args.row_column},
        "group_column": {"name": args.group_column, "read_from": group_origin},
        "label_column": None if not args.label_column else {"name": args.label_column, "read_from": label_origin},
        "label_tolerance": args.label_tolerance if args.label_column else None,
        "summary": {
            "fold_records_used": len(records), "folds": len(distinct_folds),
            "rows_per_fold": {fold: fold_rows[fold] for fold in distinct_folds},
            "largest_to_smallest_fold": round(max(sizes) / min(sizes), 6) if sizes else None,
            "groups": len(spread), "groups_in_two_folds": len(split),
            "rows_in_split_groups": sum(sum(counts.values()) for counts in split.values()),
            "groups_per_fold": {fold: len(fold_groups.get(fold, ())) for fold in distinct_folds},
            "max_label_share_gap": None if gap_max is None else round(gap_max, 6),
            "rows_without_label": empty_labels if args.label_column else None,
        },
        "labels": label_report,
        "checks": checks,
        "failed_checks": failed,
        "violations_total": sum(checks.values()),
        "violations": findings.examples,
        "violations_shown": len(findings.examples),
        "numbering": "row counts training data rows from 1 without the header when rows match by number; "
                     "fold_file_row counts data rows of the fold file the same way; line is the file line",
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
