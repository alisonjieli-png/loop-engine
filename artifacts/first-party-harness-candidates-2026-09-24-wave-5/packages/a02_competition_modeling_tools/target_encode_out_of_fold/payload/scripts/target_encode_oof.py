"""Target-encode categories out of fold. Effects: reads CSV files under --root, writes one or two new CSV files under --root, prints one JSON object; no network.

For a training row in fold f, the value for its category uses only the rows of the
other folds: (their target sum + m * their target mean) / (their row count + m),
where m is the smoothing. A test row uses every training row in the same way. A
category that those rows do not hold gets their target mean. An empty cell is its
own category. Before anything is written, a second count that skips each fold in
turn recomputes every training value, and both counts must agree. At most 100 folds
are accepted. With --check-group-column, the group column of a fold file must match
the named training column row by row, so a fold file made for other rows is refused.

Exit status: 0 pass, 1 a check failed, 2 refused input. When the two counts disagree,
nothing is written; when a written file fails its recheck, the report says not to use it.
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
from collections import Counter, defaultdict
from pathlib import Path

RECORD_TYPE = "out_of_fold_target_encoding_report/v1"
DEFAULT_MAX_BYTES = 64 * 1024 * 1024
HARD_MAX_BYTES = 1024 * 1024 * 1024
DISTINCT_CAP = 5000
LIST_COLUMNS_CAP = 300
MAX_COLUMNS = 50
MAX_FOLDS = 100
NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")
ROW_NUMBER = re.compile(r"[0-9]{1,12}\Z")


class Refused(Exception):
    """An input or argument this script will not use."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = str(detail)[:300]


class Parser(argparse.ArgumentParser):
    """Argument parser that reports bad arguments as a refused input in JSON."""

    def error(self, message: str):
        raise Refused("bad_arguments", message)


def root_folder(value: str) -> Path:
    try:
        root = Path(value).resolve(strict=True)
    except (OSError, RuntimeError):
        raise Refused("root_missing", value) from None
    if not root.is_dir():
        raise Refused("root_not_a_folder", value)
    return root


def under_root(root: Path, relative: str) -> Path:
    """Join a relative path to the root; refuse absolute paths, '..' and symbolic links."""
    if not relative or relative.startswith("/") or "\x00" in relative:
        raise Refused("path_not_relative", relative)
    parts = [part for part in relative.split("/") if part not in ("", ".")]
    if not parts or ".." in parts:
        raise Refused("path_leaves_root", relative)
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise Refused("path_has_symbolic_link", relative)
    return current


def read_input(root: Path, relative: str, limit: int) -> bytes:
    path = under_root(root, relative)
    if not path.is_file():
        raise Refused("input_missing", relative)
    with open(path, "rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise Refused("input_too_large", f"{relative} is larger than {limit} bytes; raise --max-bytes on purpose")
    return data


class Table:
    """A UTF-8 CSV file with one header row; rows are read on demand."""

    def __init__(self, data: bytes, label: str, limit: int) -> None:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise Refused("input_not_utf8", f"{label}: byte {error.start}") from None
        self.label = label
        self.blank_lines = 0
        csv.field_size_limit(max(limit, 131072))
        self._reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        try:
            header = next(self._reader, None)
        except csv.Error as error:
            raise Refused("malformed_csv", f"{label} line 1: {error}") from None
        if not header:
            raise Refused("input_empty", label)
        self.header = [name.strip() for name in header]
        if any(not name for name in self.header):
            raise Refused("blank_column_name", label)
        repeated = sorted(name for name, count in Counter(self.header).items() if count > 1)
        if repeated:
            raise Refused("duplicate_column_name", f"{label}: {repeated[:5]}")

    def index(self, name: str) -> int:
        if name not in self.header:
            raise Refused("column_missing", f"{name!r} is not a column of {self.label}; columns: {self.header[:40]}")
        return self.header.index(name)

    def rows(self):
        width = len(self.header)
        try:
            for row in self._reader:
                if not row:
                    self.blank_lines += 1
                    continue
                if len(row) != width:
                    raise Refused("row_width_mismatch",
                                  f"{self.label} line {self._reader.line_num}: {len(row)} fields, header has {width}")
                yield self._reader.line_num, row
        except csv.Error as error:
            raise Refused("malformed_csv", f"{self.label} line {self._reader.line_num}: {error}") from None


def parse_number(text: str):
    value = text.strip()
    if not NUMBER.match(value):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def list_columns(table: Table, digest: str) -> dict:
    shown = table.header[:LIST_COLUMNS_CAP]
    seen = [set() for _ in shown]
    over = [False for _ in shown]
    empty = [0 for _ in shown]
    count = 0
    for _line, row in table.rows():
        count += 1
        for position in range(len(shown)):
            value = row[position]
            if not value.strip():
                empty[position] += 1
            if not over[position]:
                seen[position].add(value)
                if len(seen[position]) > DISTINCT_CAP:
                    over[position] = True
                    seen[position] = set()
    columns = [{"name": name, "distinct": f"more than {DISTINCT_CAP}" if over[i] else len(seen[i]),
                "empty": empty[i]} for i, name in enumerate(shown)]
    return {"record_type": RECORD_TYPE, "status": "pass", "mode": "list_columns",
            "input": {"path": table.label, "sha256": digest, "rows": count, "blank_lines_skipped": table.blank_lines},
            "columns": columns, "columns_not_shown": max(0, len(table.header) - LIST_COLUMNS_CAP)}


def read_fold_file(root: Path, relative: str, rows: int, limit: int, groups=None) -> tuple[list[str], str]:
    """Read row and fold; with `groups`, the fold file's group column must match them after removing spaces."""
    data = read_input(root, relative, limit)
    table = Table(data, relative, limit)
    row_index, fold_index = table.index("row"), table.index("fold")
    group_index = table.index("group") if groups is not None else None
    folds: list = [None] * rows
    for line, row in table.rows():
        text = row[row_index].strip()
        if not ROW_NUMBER.match(text) or not 1 <= int(text) <= rows:
            raise Refused("fold_file_rows_mismatch", f"{relative} line {line}: row {text[:20]!r} is not 1 to {rows}")
        if folds[int(text) - 1] is not None:
            raise Refused("fold_file_rows_mismatch", f"{relative} line {line}: row {text} appears twice")
        if group_index is not None and row[group_index].strip() != groups[int(text) - 1].strip():
            raise Refused("fold_file_group_mismatch",
                          f"{relative} line {line}: group {row[group_index][:40]!r} but training row {text} "
                          f"holds {groups[int(text) - 1][:40]!r}; the fold file was made for other rows")
        fold = row[fold_index].strip()
        if not fold:
            raise Refused("fold_value_missing", f"{relative} line {line}")
        folds[int(text) - 1] = fold
    missing = [position for position, fold in enumerate(folds, start=1) if fold is None]
    if missing:
        raise Refused("fold_file_rows_mismatch", f"{relative} has no fold for {len(missing)} rows, first row {missing[0]}")
    return folds, hashlib.sha256(data).hexdigest()


def smoothed(total: float, count: int, prior: float, smoothing: float) -> float:
    return (total + smoothing * prior) / (count + smoothing) if count + smoothing > 0 else prior


def encode_out_of_fold(values: list, targets: list, folds: list, smoothing: float) -> list[float]:
    """Fast path: whole-file sums minus the sums of the row's own fold."""
    fold_sum, fold_count = defaultdict(float), Counter()
    value_sum, value_count = defaultdict(float), Counter()
    pair_sum, pair_count = defaultdict(float), Counter()
    for value, target, fold in zip(values, targets, folds):
        fold_sum[fold] += target
        fold_count[fold] += 1
        value_sum[value] += target
        value_count[value] += 1
        pair_sum[(value, fold)] += target
        pair_count[(value, fold)] += 1
    total, rows = math.fsum(targets), len(targets)
    encoded = []
    for value, fold in zip(values, folds):
        prior = (total - fold_sum[fold]) / (rows - fold_count[fold])
        encoded.append(smoothed(value_sum[value] - pair_sum[(value, fold)],
                                value_count[value] - pair_count[(value, fold)], prior, smoothing))
    return encoded


def recount_out_of_fold(values: list, targets: list, folds: list, smoothing: float) -> list[float]:
    """Independent path: for each fold, count only the rows of the other folds from scratch."""
    encoded = [0.0] * len(values)
    for held in sorted(set(folds)):
        value_sum, value_count = defaultdict(float), Counter()
        others = [target for target, fold in zip(targets, folds) if fold != held]
        for value, target, fold in zip(values, targets, folds):
            if fold != held:
                value_sum[value] += target
                value_count[value] += 1
        prior = math.fsum(others) / len(others)
        for position, (value, fold) in enumerate(zip(values, folds)):
            if fold == held:
                encoded[position] = smoothed(value_sum[value], value_count[value], prior, smoothing)
    return encoded


def encode_test(train_values: list, targets: list, test_values: list, smoothing: float) -> list[float]:
    value_sum, value_count = defaultdict(float), Counter()
    for value, target in zip(train_values, targets):
        value_sum[value] += target
        value_count[value] += 1
    prior = math.fsum(targets) / len(targets)
    return [smoothed(value_sum[value], value_count[value], prior, smoothing) for value in test_values]


def table_text(names: list, columns: list) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["row", *names])
    for position, values in enumerate(zip(*columns), start=1):
        writer.writerow([position, *(repr(value) for value in values)])
    return buffer.getvalue()


def write_new_file(path: Path, text: str) -> str:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise Refused("output_folder_invalid", str(error)) from None
    try:
        with open(path, "x", encoding="utf-8", newline="") as handle:
            handle.write(text)
    except FileExistsError:
        raise Refused("output_exists", f"{path.name} exists; choose a new name") from None
    except OSError as error:
        raise Refused("output_not_writable", str(error)) from None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_written_file(path: Path, names: list, columns: list) -> bool:
    """Read a written file again and confirm every row number and value."""
    reader = csv.reader(io.StringIO(path.read_bytes().decode("utf-8"), newline=""))
    if next(reader, None) != ["row", *names]:
        return False
    count = 0
    for count, row in enumerate(reader, start=1):
        if count > len(columns[0]) or row[0] != str(count) or len(row) != len(names) + 1:
            return False
        if any(float(text) != column[count - 1] for text, column in zip(row[1:], columns)):
            return False
    return count == len(columns[0])


def build_parser() -> Parser:
    parser = Parser(description="Target-encode categorical columns out of fold. Exit 0 pass, 1 check failed, 2 refused.")
    parser.add_argument("--root", default=".", help="folder that every path is relative to (default: current folder)")
    parser.add_argument("--train", required=True, help="training CSV with a header row, relative to --root")
    parser.add_argument("--list-columns", action="store_true",
                        help="print column names, row count, distinct and empty counts, then exit")
    parser.add_argument("--target", help="numeric target column, for example 0 and 1 labels")
    parser.add_argument("--column", action="append", help="categorical column to encode; repeat for more")
    parser.add_argument("--fold-column", help="column of the training file that holds each row's fold")
    parser.add_argument("--fold-file", help="CSV with the columns row and fold; row counts data rows from 1")
    parser.add_argument("--check-group-column",
                        help="with --fold-file: training column that the fold file's group column must match row by row")
    parser.add_argument("--test", help="optional test CSV holding the same categorical columns")
    parser.add_argument("--smoothing", type=float, default=20.0,
                        help="weight of the mean for rare values; 0 means no smoothing (default 20)")
    parser.add_argument("--output-train", help="new CSV for the training encodings; it must not exist yet")
    parser.add_argument("--output-test", help="new CSV for the test encodings; needed with --test")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                        help=f"refuse inputs larger than this (default {DEFAULT_MAX_BYTES}, at most {HARD_MAX_BYTES})")
    return parser


def run(args) -> tuple[dict, int]:
    if not 1 <= args.max_bytes <= HARD_MAX_BYTES:
        raise Refused("bad_arguments", f"--max-bytes must be between 1 and {HARD_MAX_BYTES}")
    root = root_folder(args.root)
    data = read_input(root, args.train, args.max_bytes)
    digest = hashlib.sha256(data).hexdigest()
    table = Table(data, args.train, args.max_bytes)
    if args.list_columns:
        return list_columns(table, digest), 0
    if not args.target or not args.column or not args.output_train:
        raise Refused("bad_arguments", "--target, --column and --output-train are required unless --list-columns is given")
    if bool(args.fold_column) == bool(args.fold_file):
        raise Refused("bad_arguments", "give exactly one of --fold-column and --fold-file")
    if bool(args.test) != bool(args.output_test):
        raise Refused("bad_arguments", "--test and --output-test go together")
    if args.check_group_column and not args.fold_file:
        raise Refused("bad_arguments", "--check-group-column needs --fold-file")
    if not math.isfinite(args.smoothing) or args.smoothing < 0:
        raise Refused("bad_arguments", "--smoothing must be a number of at least 0")
    columns = list(dict.fromkeys(args.column))
    if len(columns) > MAX_COLUMNS:
        raise Refused("bad_arguments", f"at most {MAX_COLUMNS} columns per run")
    if args.target in columns or (args.fold_column and args.fold_column in columns):
        raise Refused("bad_arguments", "the target and the fold column are not encoded")
    outputs = [under_root(root, args.output_train)] + ([under_root(root, args.output_test)] if args.test else [])
    if len(outputs) == 2 and outputs[0] == outputs[1]:
        raise Refused("bad_arguments", "--output-train and --output-test must differ")
    for path, name in zip(outputs, (args.output_train, args.output_test)):
        if path.exists():
            raise Refused("output_exists", f"{name} exists; choose a new name")
    target_index = table.index(args.target)
    positions = [table.index(name) for name in columns]
    fold_index = table.index(args.fold_column) if args.fold_column else None
    group_index = table.index(args.check_group_column) if args.check_group_column else None
    targets, values, folds, groups = [], [[] for _ in columns], [], []
    for line, row in table.rows():
        number = parse_number(row[target_index])
        if number is None:
            reason = "target_value_missing" if not row[target_index].strip() else "target_not_numeric"
            raise Refused(reason, f"{args.train} line {line}: {row[target_index][:40]!r}; make a 0 or 1 column first")
        targets.append(number)
        for slot, position in enumerate(positions):
            values[slot].append(row[position])
        if group_index is not None:
            groups.append(row[group_index])
        if fold_index is not None:
            fold = row[fold_index].strip()
            if not fold:
                raise Refused("fold_value_missing", f"{args.train} line {line}")
            folds.append(fold)
    if not targets:
        raise Refused("input_has_no_rows", args.train)
    fold_source = {"kind": "fold_column", "name": args.fold_column}
    if args.fold_file:
        folds, fold_digest = read_fold_file(root, args.fold_file, len(targets), args.max_bytes,
                                            groups if group_index is not None else None)
        fold_source = {"kind": "fold_file", "path": args.fold_file, "sha256": fold_digest,
                       "group_column_checked": args.check_group_column}
    fold_ids = sorted(set(folds))
    if len(fold_ids) < 2:
        raise Refused("fewer_than_two_folds", f"{len(fold_ids)} distinct fold value")
    if len(fold_ids) > MAX_FOLDS:
        raise Refused("too_many_folds", f"{len(fold_ids)} distinct fold values; at most {MAX_FOLDS}. "
                                        "Check that the fold column names the folds, not the rows")
    test_values, test_digest, test_rows = None, None, 0
    if args.test:
        test_data = read_input(root, args.test, args.max_bytes)
        test_digest = hashlib.sha256(test_data).hexdigest()
        test_table = Table(test_data, args.test, args.max_bytes)
        test_positions = [test_table.index(name) for name in columns]
        test_values = [[] for _ in columns]
        for _line, row in test_table.rows():
            test_rows += 1
            for slot, position in enumerate(test_positions):
                test_values[slot].append(row[position])
    encoded, test_encoded, summaries = [], [], []
    largest_difference = 0.0
    for slot, name in enumerate(columns):
        fast = encode_out_of_fold(values[slot], targets, folds, args.smoothing)
        slow = recount_out_of_fold(values[slot], targets, folds, args.smoothing)
        largest_difference = max([largest_difference] + [abs(a - b) / max(1.0, abs(b)) for a, b in zip(fast, slow)])
        encoded.append(fast)
        counts = Counter(values[slot])
        pair_counts = Counter(zip(values[slot], folds))
        summary = {"column": name, "output_column": f"{name}_te", "categories": len(counts),
                   "single_row_categories": sum(1 for count in counts.values() if count == 1),
                   "train_rows_with_no_other_fold_rows": sum(1 for value, fold in zip(values[slot], folds)
                                                             if counts[value] == pair_counts[(value, fold)]),
                   "train_min": round(min(fast), 6), "train_max": round(max(fast), 6)}
        if test_values is not None:
            test_column = encode_test(values[slot], targets, test_values[slot], args.smoothing)
            test_encoded.append(test_column)
            summary["test_rows_unseen"] = sum(1 for value in test_values[slot] if value not in counts)
            summary["test_categories_unseen"] = len({value for value in test_values[slot] if value not in counts})
        summaries.append(summary)
    agree = largest_difference <= 1e-9
    checks = [{"name": "every_train_row_has_a_fold", "passed": len(folds) == len(targets)},
              {"name": "encoding_uses_only_other_folds", "passed": agree,
               "detail": "a second count that skips each row's own fold gave the same values",
               "largest_relative_difference": largest_difference}]
    report = {"record_type": RECORD_TYPE, "status": "pass",
              "input": {"path": args.train, "sha256": digest, "rows": len(targets),
                        "blank_lines_skipped": table.blank_lines},
              "test_input": {"path": args.test, "sha256": test_digest, "rows": test_rows} if args.test else None,
              "settings": {"target": args.target, "columns": columns, "fold_source": fold_source,
                           "folds": len(fold_ids), "fold_ids": fold_ids[:50], "smoothing": args.smoothing,
                           "target_mean": round(math.fsum(targets) / len(targets), 6),
                           "empty_cell": "its own category"},
              "fold_rows": {fold: folds.count(fold) for fold in fold_ids[:50]},
              "columns": summaries, "checks": checks, "outputs": None}
    if not agree:
        report["status"] = "check_failed"
        report["note"] = "The two counts disagree, so nothing was written. Do not use any earlier output."
        return report, 1
    names = [f"{name}_te" for name in columns]
    written = [{"path": args.output_train, "rows": len(targets), "columns": ["row", *names],
                "sha256": write_new_file(outputs[0], table_text(names, encoded))}]
    if args.test:
        written.append({"path": args.output_test, "rows": test_rows, "columns": ["row", *names],
                        "sha256": write_new_file(outputs[1], table_text(names, test_encoded))})
    report["outputs"] = written
    report["row_numbering"] = "data rows counted from 1 in input order, header excluded"
    matches = check_written_file(outputs[0], names, encoded) and (
        not args.test or check_written_file(outputs[1], names, test_encoded))
    checks.append({"name": "written_files_match", "passed": matches})
    if not matches:
        report["status"] = "check_failed"
        report["note"] = "A written file did not match the computed values. Do not use it."
        return report, 1
    return report, 0


def main(argv=None) -> int:
    try:
        args = build_parser().parse_args(argv)
        report, status = run(args)
    except Refused as error:
        report, status = {"record_type": RECORD_TYPE, "status": "refused", "reason": error.reason,
                          "detail": error.detail}, 2
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return status


if __name__ == "__main__":
    sys.exit(main())
