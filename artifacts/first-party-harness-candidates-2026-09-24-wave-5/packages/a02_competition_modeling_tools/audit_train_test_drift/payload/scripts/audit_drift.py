"""Audit train and test column drift. Effects: reads two CSV files under --root, or one JSON pair from a file or standard input; writes nothing; prints one JSON object; no network.

For every column in both files the audit compares missing rates, values never seen
in training, numeric values outside the training range and a population stability
index (PSI). It also lists columns found in only one file and a target column that
appears in the test file. Numeric PSI uses a fixed-seed sample of at most 10,000
values per column and file, cut into up to 10 buckets of about equal training rows:
equal values always share a bucket, and a value that holds many rows, such as a 0
in a mostly zero column, gets a bucket of its own. Every other count is exact.

Exit status: 0 no findings, 1 findings listed, 2 refused input.
"""
from __future__ import annotations

import argparse
import bisect
import codecs
import csv
import hashlib
import io
import json
import math
import random
import re
import sys
from array import array
from collections import Counter
from pathlib import Path

RECORD_TYPE = "train_test_drift_report/v2"
DEFAULT_MAX_BYTES = 64 * 1024 * 1024
HARD_MAX_BYTES = 1024 * 1024 * 1024
DEFAULT_MISSING = ("", "NA", "N/A", "NaN", "nan", "null", "NULL", "None")
SAMPLE_SIZE = 10000
DISTINCT_CAP = 50000
NUMERIC_DISTINCT_CAP = 5000
NUMERIC_BUCKETS = 10
CATEGORY_BUCKETS = 30
PSI_FLOOR = 0.0001
MAX_DETAILED_COLUMNS = 200
MAX_EXAMPLES = 5
IDENTIFIER_MIN_ROWS = 20
IDENTIFIER_NEW_SHARE = 0.9
NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")


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
    if relative == "-":
        data = sys.stdin.buffer.read(limit + 1)
    else:
        path = under_root(root, relative)
        if not path.is_file():
            raise Refused("input_missing", relative)
        with open(path, "rb") as handle:
            data = handle.read(limit + 1)
    if len(data) > limit:
        raise Refused("input_too_large", f"{relative} is larger than {limit} bytes; raise --max-bytes on purpose")
    return data


def check_utf8(data: bytes, label: str) -> None:
    """Refuse bytes that are not UTF-8, decoding in pieces so no full copy of the text is kept."""
    decoder = codecs.getincrementaldecoder("utf-8")()
    view, step = memoryview(data), 1 << 20
    for start in range(0, max(len(data), 1), step):
        try:
            decoder.decode(view[start:start + step], final=start + step >= len(data))
        except UnicodeDecodeError as error:
            raise Refused("input_not_utf8", f"{label}: near byte {start + error.start}") from None


class Table:
    """A UTF-8 CSV text with one header row; rows are decoded and read on demand."""

    def __init__(self, data: bytes, label: str, limit: int) -> None:
        check_utf8(data, label)
        self.label = label
        self.blank_lines = 0
        csv.field_size_limit(max(limit, 131072))
        stream = io.TextIOWrapper(io.BytesIO(data), encoding="utf-8-sig", newline="")
        self._reader = csv.reader(stream, strict=True)
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
                yield row
        except csv.Error as error:
            raise Refused("malformed_csv", f"{self.label} line {self._reader.line_num}: {error}") from None


def parse_number(text: str):
    if not NUMBER.match(text):
        return None
    number = float(text)
    return number if math.isfinite(number) else None


class ColumnStats:
    """Counts for one column of one file; memory is bounded by the caps above.

    Distinct training values are kept for the unseen-value and identifier checks: up to
    DISTINCT_CAP for text, and up to NUMERIC_DISTINCT_CAP while every value so far is a
    number. The test file keeps no distinct values.
    """

    def __init__(self, seed: int, keep_values: bool = True) -> None:
        self.rows = 0
        self.missing = 0
        self.numeric = True
        self.all_integer = True
        self.count = 0
        self.mean = 0.0
        self.squares = 0.0
        self.low = math.inf
        self.high = -math.inf
        self.sample = array("d")
        self.random = random.Random(seed)
        self.keep_values = keep_values
        self.categories: Counter = Counter()
        self.saturated = False
        self.repeated = False
        self.text_examples: list[str] = []

    @property
    def present(self) -> int:
        return self.rows - self.missing

    def add(self, raw: str, missing_tokens: frozenset):
        """Record one cell; return the number, None for text, or False for a missing value."""
        self.rows += 1
        value = raw.strip()
        if value in missing_tokens:
            self.missing += 1
            return False
        if self.keep_values:
            if raw in self.categories:
                self.categories[raw] += 1
                self.repeated = True
            elif not self.saturated and len(self.categories) < (NUMERIC_DISTINCT_CAP if self.numeric else DISTINCT_CAP):
                self.categories[raw] = 1
            else:
                self.saturated = True
        number = parse_number(value)
        if number is None:
            if len(self.text_examples) < 3:
                self.text_examples.append(value[:40])
            if self.numeric:
                self.numeric = False
                self.sample = array("d")
            return None
        if self.numeric:
            self.count += 1
            delta = number - self.mean
            self.mean += delta / self.count
            self.squares += delta * (number - self.mean)
            self.low = min(self.low, number)
            self.high = max(self.high, number)
            if not number.is_integer():
                self.all_integer = False
            if len(self.sample) < SAMPLE_SIZE:
                self.sample.append(number)
            else:
                slot = self.random.randrange(self.count)
                if slot < SAMPLE_SIZE:
                    self.sample[slot] = number
        return number

    @property
    def spread(self) -> float:
        return math.sqrt(self.squares / self.count) if self.count else 0.0


def looks_like_identifier(before: ColumnStats, after: ColumnStats, kind: str, unseen: int, outside: int) -> bool:
    """No training value repeats and nearly every test value is new, as with a running number or a key."""
    if before.present < IDENTIFIER_MIN_ROWS or before.repeated or not after.present:
        return False
    if kind == "numeric" and not (before.all_integer and before.high - before.low + 1 <= 3 * before.count):
        return False
    if kind not in ("numeric", "categorical"):
        return False
    if not before.saturated:
        return unseen / after.present >= IDENTIFIER_NEW_SHARE
    if kind == "numeric":
        return outside / after.present >= IDENTIFIER_NEW_SHARE
    return True


def psi(expected: list[float], actual: list[float]) -> float:
    total = 0.0
    for share_before, share_after in zip(expected, actual):
        share_before, share_after = max(share_before, PSI_FLOOR), max(share_after, PSI_FLOOR)
        total += (share_after - share_before) * math.log(share_after / share_before)
    return total


def bucket_bounds(sample) -> list[float]:
    """Upper bounds of up to NUMERIC_BUCKETS buckets of about equal training rows.

    With at most NUMERIC_BUCKETS distinct values, each value is its own bucket. Otherwise
    equal values always share a bucket, and a value that holds at least one bucket's share
    of the remaining rows closes the open bucket and starts its own.
    """
    counts = Counter(sample)
    distinct = sorted(counts)
    if len(distinct) <= NUMERIC_BUCKETS:
        return distinct
    bounds, remaining_rows, remaining = [], len(sample), NUMERIC_BUCKETS
    current_rows, last = 0, None
    for value in distinct:
        if current_rows and remaining > 1:
            share = remaining_rows / remaining
            if current_rows >= share or counts[value] >= share:
                bounds.append(last)
                remaining_rows -= current_rows
                remaining -= 1
                current_rows = 0
        current_rows += counts[value]
        last = value
    bounds.append(last)
    return bounds


def numeric_psi(train_sample, test_sample) -> tuple[float, int]:
    """PSI over the training buckets; a value goes to the first bucket whose upper bound is not below it."""
    if not train_sample or not test_sample:
        return 0.0, 0
    bounds = bucket_bounds(train_sample)
    top = len(bounds) - 1
    before = Counter(min(bisect.bisect_left(bounds, value), top) for value in train_sample)
    after = Counter(min(bisect.bisect_left(bounds, value), top) for value in test_sample)
    buckets = range(len(bounds))
    return psi([before[b] / len(train_sample) for b in buckets],
               [after[b] / len(test_sample) for b in buckets]), len(bounds)


def rounded(value):
    return round(value, 6) if isinstance(value, float) and math.isfinite(value) else value


def load_tables(args, root: Path) -> tuple[Table, Table, dict]:
    if args.pair_json is not None:
        if args.train or args.test:
            raise Refused("bad_arguments", "give --pair-json or --train with --test, not both")
        data = read_input(root, args.pair_json, args.max_bytes)
        try:
            pair = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as error:
            raise Refused("pair_not_json", str(error)) from None
        if not isinstance(pair, dict) or set(pair) != {"train_csv", "test_csv"} \
                or not all(isinstance(value, str) for value in pair.values()):
            raise Refused("pair_shape", "the JSON object holds exactly the strings train_csv and test_csv")
        train_bytes, test_bytes = pair["train_csv"].encode("utf-8"), pair["test_csv"].encode("utf-8")
        labels = (f"{args.pair_json}:train_csv", f"{args.pair_json}:test_csv")
    else:
        if not args.train or not args.test:
            raise Refused("bad_arguments", "give --train and --test, or --pair-json")
        if "-" in (args.train, args.test):
            raise Refused("bad_arguments", "standard input is read only through --pair-json -")
        train_bytes = read_input(root, args.train, args.max_bytes)
        test_bytes = read_input(root, args.test, args.max_bytes)
        labels = (args.train, args.test)
    inputs = {"train": {"path": labels[0], "sha256": hashlib.sha256(train_bytes).hexdigest()},
              "test": {"path": labels[1], "sha256": hashlib.sha256(test_bytes).hexdigest()}}
    return Table(train_bytes, labels[0], args.max_bytes), Table(test_bytes, labels[1], args.max_bytes), inputs


def audit(train: Table, test: Table, args) -> dict:
    tokens = frozenset(args.missing_token) if args.missing_token else frozenset(DEFAULT_MISSING)
    ids = list(dict.fromkeys(args.id or []))
    for name in ids:
        if name not in train.header and name not in test.header:
            raise Refused("column_missing", f"--id {name!r} is in neither file")
    if args.target and args.target not in train.header:
        raise Refused("column_missing", f"--target {args.target!r} is not a column of the training file")
    excluded = set(ids) | ({args.target} if args.target else set())
    shared = [name for name in train.header if name in test.header and name not in excluded]
    train_stats = {name: ColumnStats(seed) for seed, name in enumerate(shared)}
    positions = {name: train.header.index(name) for name in shared}
    train_rows = 0
    for row in train.rows():
        train_rows += 1
        for name in shared:
            train_stats[name].add(row[positions[name]], tokens)
    top = {name: [value for value, _count in train_stats[name].categories.most_common(CATEGORY_BUCKETS)]
           for name in shared}
    top_sets = {name: set(values) for name, values in top.items()}
    test_stats = {name: ColumnStats(len(shared) + seed, keep_values=False) for seed, name in enumerate(shared)}
    test_positions = {name: test.header.index(name) for name in shared}
    unseen_rows, unseen_values = Counter(), {name: [] for name in shared}
    unseen_distinct = {name: set() for name in shared}
    outside, top_counts = Counter(), {name: Counter() for name in shared}
    test_rows = 0
    for row in test.rows():
        test_rows += 1
        for name in shared:
            raw = row[test_positions[name]]
            number = test_stats[name].add(raw, tokens)
            if number is False:
                continue
            reference = train_stats[name]
            if not reference.saturated and raw not in reference.categories:
                unseen_rows[name] += 1
                if len(unseen_distinct[name]) < 1000:
                    unseen_distinct[name].add(raw)
                if len(unseen_values[name]) < MAX_EXAMPLES and raw[:40] not in unseen_values[name]:
                    unseen_values[name].append(raw[:40])
            if reference.numeric and number is not None and (number < reference.low or number > reference.high):
                outside[name] += 1
            top_counts[name][raw if raw in top_sets[name] else None] += 1
    if not train_rows or not test_rows:
        raise Refused("input_has_no_rows", train.label if not train_rows else test.label)
    flagged, unflagged, notes = [], [], []
    for name in shared:
        before, after = train_stats[name], test_stats[name]
        findings = []
        rate_before, rate_after = before.missing / train_rows, after.missing / test_rows
        kind = "empty" if not before.present else "numeric" if before.numeric else "categorical"
        if kind == "empty":
            findings.append({"kind": "empty_in_train"})
        elif looks_like_identifier(before, after, kind, unseen_rows[name], outside[name]):
            findings.append({"kind": "identifier_like", "distinct_in_train": len(before.categories),
                             "saturated": before.saturated})
        else:
            if abs(rate_before - rate_after) >= args.missing_gap:
                findings.append({"kind": "missing_rate_shift", "train": rounded(rate_before), "test": rounded(rate_after)})
            if not before.saturated and len(before.categories) == 1:
                findings.append({"kind": "constant_in_train"})
            compare_as_categories = kind == "categorical"
            if kind == "numeric" and after.present and not after.numeric:
                findings.append({"kind": "type_mismatch", "train": "numeric", "test": "text",
                                 "test_examples": after.text_examples})
                compare_as_categories = True
            elif kind == "numeric" and after.present:
                share = outside[name] / after.present
                if share >= args.outside_share:
                    findings.append({"kind": "outside_train_range", "share": rounded(share),
                                     "train_min": rounded(before.low), "train_max": rounded(before.high),
                                     "test_min": rounded(after.low), "test_max": rounded(after.high)})
                value, bucket_count = numeric_psi(before.sample, after.sample)
                if value >= args.psi_limit:
                    shift = (after.mean - before.mean) / before.spread if before.spread else None
                    findings.append({"kind": "distribution_shift", "psi": rounded(value), "buckets": bucket_count,
                                     "train_mean": rounded(before.mean), "test_mean": rounded(after.mean),
                                     "mean_shift_in_train_std": rounded(shift) if shift is not None else None})
            if compare_as_categories and after.present:
                if before.saturated:
                    notes.append({"column": name, "note": f"unseen value check skipped: more than {DISTINCT_CAP} "
                                                          "distinct training values"})
                else:
                    share = unseen_rows[name] / after.present
                    if share >= args.unseen_share:
                        findings.append({"kind": "unseen_categories", "share": rounded(share),
                                         "distinct": len(unseen_distinct[name]), "examples": unseen_values[name]})
                buckets = top[name] + [None]
                counted = sum(before.categories[value] for value in top[name])
                expected = [before.categories[value] / before.present for value in top[name]]
                expected.append((before.present - counted) / before.present)
                actual = [top_counts[name][value] / after.present for value in buckets]
                value = psi(expected, actual)
                if value >= args.psi_limit:
                    findings.append({"kind": "distribution_shift", "psi": rounded(value)})
        if findings:
            flagged.append({"column": name, "kind": kind,
                            "missing_rate": {"train": rounded(rate_before), "test": rounded(rate_after)},
                            "findings": findings})
        else:
            unflagged.append(name)
    only_train = [name for name in train.header if name not in test.header and name not in excluded]
    only_test = [name for name in test.header if name not in train.header and name not in ids]
    target_in_test = bool(args.target) and args.target in test.header
    has_findings = bool(flagged or only_train or only_test or target_in_test)
    return {"record_type": RECORD_TYPE, "status": "findings" if has_findings else "pass",
            "rows": {"train": train_rows, "test": test_rows},
            "settings": {"target": args.target, "ids": ids, "missing_tokens": sorted(tokens),
                         "missing_gap": args.missing_gap, "unseen_share": args.unseen_share,
                         "outside_share": args.outside_share, "psi_limit": args.psi_limit,
                         "numeric_psi_sample_per_file": SAMPLE_SIZE,
                         "numeric_psi_buckets": f"up to {NUMERIC_BUCKETS} of about equal training rows; equal values "
                                                "share a bucket and a value with many rows gets its own"},
            "columns_only_in_train": only_train, "columns_only_in_test": only_test,
            "target_in_test": target_in_test, "shared_columns": len(shared),
            "flagged_count": len(flagged), "flagged_columns": flagged[:MAX_DETAILED_COLUMNS],
            "flagged_truncated": len(flagged) > MAX_DETAILED_COLUMNS, "unflagged_columns": unflagged,
            "notes": notes}


def build_parser() -> Parser:
    parser = Parser(description="Compare every shared column of a training and a test CSV. "
                                "Exit 0 no findings, 1 findings listed, 2 refused.")
    parser.add_argument("--root", default=".", help="folder that every path is relative to (default: current folder)")
    parser.add_argument("--train", help="training CSV, relative to --root")
    parser.add_argument("--test", help="test CSV, relative to --root")
    parser.add_argument("--pair-json",
                        help="instead of --train and --test: a JSON object with the strings train_csv and test_csv, "
                             "from a file under --root or from standard input with -")
    parser.add_argument("--target", help="label column; expected only in the training file")
    parser.add_argument("--id", action="append", help="identifier column to leave out; repeat for more")
    parser.add_argument("--missing-token", action="append",
                        help="a cell text that means missing; repeat for more; replaces the default list")
    parser.add_argument("--missing-gap", type=float, default=0.10,
                        help="flag a column when its missing rates differ by at least this (default 0.10)")
    parser.add_argument("--unseen-share", type=float, default=0.01,
                        help="flag when at least this share of test values never occurs in training (default 0.01)")
    parser.add_argument("--outside-share", type=float, default=0.01,
                        help="flag when at least this share of test numbers lies outside the training range (default 0.01)")
    parser.add_argument("--psi-limit", type=float, default=0.25,
                        help="flag a population stability index at or above this (default 0.25)")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES,
                        help=f"refuse inputs larger than this (default {DEFAULT_MAX_BYTES}, at most {HARD_MAX_BYTES})")
    return parser


def run(args) -> tuple[dict, int]:
    if not 1 <= args.max_bytes <= HARD_MAX_BYTES:
        raise Refused("bad_arguments", f"--max-bytes must be between 1 and {HARD_MAX_BYTES}")
    for name in ("missing_gap", "unseen_share", "outside_share", "psi_limit"):
        value = getattr(args, name)
        if not math.isfinite(value) or value <= 0:
            raise Refused("bad_arguments", f"--{name.replace('_', '-')} must be a number above 0")
    root = root_folder(args.root)
    train, test, inputs = load_tables(args, root)
    report = audit(train, test, args)
    report["inputs"] = inputs
    return report, 1 if report["status"] == "findings" else 0


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
