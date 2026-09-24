"""Build time-ordered validation splits. Effects: reads one or two CSV files under --root, writes one new CSV under --root, prints one JSON object; no network.

The distinct times of the training file are cut into N + 1 blocks of about equal
row counts; rows with the same time always stay in one block. Split i validates on
block i and trains on the earlier blocks, keeping only training rows whose time is
at least the declared gap before the first validation time. Rows inside the gap are
marked `gap`. Gaps are compared in seconds (or in the column's own unit for numeric
times) before any rounding for display. After writing, the script reads its own
output again and checks it.

Exit status: 0 pass, 1 a check failed, 2 refused input. When a check fails before writing, no
split file is written; when the written file fails its recheck, the report says not to use it.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import io
import itertools
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

RECORD_TYPE = "time_splits_report/v2"
DEFAULT_MAX_BYTES = 64 * 1024 * 1024
HARD_MAX_BYTES = 1024 * 1024 * 1024
DISTINCT_CAP = 5000
LIST_COLUMNS_CAP = 300
UNITS = {"days": 86400.0, "hours": 3600.0, "minutes": 60.0, "seconds": 1.0}
SHOWN_DECIMALS = 9
NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")
ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,6}))?)?"
                 r"(Z|[+-]\d{2}:\d{2})?)?\Z")
EPOCH = datetime(1970, 1, 1)
PARTS = ("train", "validation", "gap", "unused")


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


def parse_time(text: str, kind: str):
    """Return (seconds or number, has_zone) or None when the value does not parse."""
    value = text.strip()
    if kind == "number":
        if not NUMBER.match(value):
            return None
        number = float(value)
        return (number, False) if math.isfinite(number) else None
    match = ISO.match(value)
    if not match:
        return None
    year, month, day, hour, minute, second, fraction, zone = match.groups()
    try:
        moment = datetime(int(year), int(month), int(day), int(hour or 0), int(minute or 0), int(second or 0),
                          int((fraction or "0").ljust(6, "0")))
    except ValueError:
        return None
    if zone is None:
        return (moment - EPOCH).total_seconds(), False
    if zone == "Z":
        offset = timedelta(0)
    else:
        sign = 1 if zone[0] == "+" else -1
        offset = sign * timedelta(hours=int(zone[1:3]), minutes=int(zone[4:6]))
    return (moment.replace(tzinfo=timezone(offset)) - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds(), True


def read_times(table: Table, column: str, kind: str) -> tuple[list[float], bool]:
    position = table.index(column)
    times, zones = [], set()
    bad, bad_example, missing = [], "", []
    for line, row in table.rows():
        value = row[position]
        if not value.strip():
            missing.append(line)
            continue
        parsed = parse_time(value, kind)
        if parsed is None:
            if not bad:
                bad_example = value[:40]
            bad.append(line)
            continue
        times.append(parsed[0])
        zones.add(parsed[1])
    if missing:
        raise Refused("time_value_missing", f"{table.label}: {len(missing)} rows, first on line {missing[0]}")
    if bad:
        raise Refused("time_not_parsed", f"{table.label}: {len(bad)} rows, first on line {bad[0]}: {bad_example!r}; "
                                         f"--time-kind {kind} expects " + ("numbers" if kind == "number" else
                                         "YYYY-MM-DD or YYYY-MM-DDTHH:MM[:SS[.ffffff]][Z|+HH:MM]"))
    if len(zones) > 1:
        raise Refused("time_zone_mixed", f"{table.label}: some times have a zone offset and some do not")
    if not times:
        raise Refused("input_has_no_rows", table.label)
    return times, bool(zones and zones.pop())


def tolerance(value: float) -> float:
    return 1e-9 * max(1.0, abs(value))


def plain(value: float):
    """A whole number without a decimal point, other numbers as they are."""
    return int(value) if float(value).is_integer() and abs(value) < 1e15 else value


def suggest_gap(after: float, kind: str) -> dict:
    """The --gap that matches a test gap exactly: the largest unit that states it in at most 6 decimals,
    preferring a value of at least 1. When no unit states it exactly, the value is rounded up, never down."""
    units = [("column units", 1.0)] if kind == "number" else list(UNITS.items())
    exact = [(unit, round(after / size, 6)) for unit, size in units
             if abs(round(after / size, 6) * size - after) <= tolerance(after)]
    readable = [(unit, value) for unit, value in exact if value >= 1]
    if readable or exact:
        unit, value = (readable or exact)[0]
    else:
        unit, size = units[-1]
        value = math.ceil(after / size * 1e6) / 1e6
    value = plain(value)
    arguments = ["--gap", str(value)] + ([] if kind == "number" else ["--gap-unit", unit])
    return {"gap": value, "gap_unit": unit, "arguments": arguments}


def shown(value: float, kind: str, zoned: bool):
    if kind == "number":
        return value
    if zoned:
        return datetime.fromtimestamp(value, timezone.utc).isoformat()
    return (EPOCH + timedelta(seconds=value)).isoformat()


def block_cuts(unique: list, counts: Counter, splits: int) -> list[int]:
    """Positions in the sorted distinct times where blocks 1 to N start; every block holds at least one time."""
    cumulative = list(itertools.accumulate(counts[value] for value in unique))
    total = cumulative[-1]
    cuts, previous = [], 0
    for block in range(1, splits + 1):
        position = bisect.bisect_left(cumulative, block * total / (splits + 1)) + 1
        position = max(position, previous + 1)
        position = min(position, len(unique) - (splits + 1 - block))
        cuts.append(position)
        previous = position
    return cuts


def assign_parts(times: list, block_of: dict, starts: list, splits: int, gap: float, window) -> list[list[str]]:
    """Return one list of parts per split: train, validation, gap or unused for every row."""
    columns = []
    for split in range(1, splits + 1):
        first_block = 0 if window is None else max(0, split - window)
        valid_start = starts[split]
        parts = []
        for value in times:
            block = block_of[value]
            if block == split:
                parts.append("validation")
            elif first_block <= block < split:
                parts.append("train" if valid_start - value >= gap else "gap")
            else:
                parts.append("unused")
        columns.append(parts)
    return columns


def split_facts(times: list, parts: list, gap: float, slack: float) -> dict:
    train = [value for value, part in zip(times, parts) if part == "train"]
    valid = [value for value, part in zip(times, parts) if part == "validation"]
    facts = {"train_rows": len(train), "validation_rows": len(valid), "gap_rows": parts.count("gap"),
             "unused_rows": parts.count("unused")}
    facts["passed"] = bool(train and valid) and min(valid) - max(train) >= gap - slack
    facts["train_first"] = min(train) if train else None
    facts["train_last"] = max(train) if train else None
    facts["validation_first"] = min(valid) if valid else None
    facts["validation_last"] = max(valid) if valid else None
    facts["gap_observed"] = (min(valid) - max(train)) if train and valid else None
    return facts


def split_file_text(parts_by_split: list) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["row"] + [f"split_{number}" for number in range(1, len(parts_by_split) + 1)])
    for position, parts in enumerate(zip(*parts_by_split), start=1):
        writer.writerow([position, *parts])
    return buffer.getvalue()


def write_new_file(path: Path, text: str) -> None:
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


def check_written_file(path: Path, times: list, splits: int, gap: float, slack: float) -> tuple[bool, str, str]:
    """Read the written split file again and confirm every split from the times alone."""
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    reader = csv.reader(io.StringIO(data.decode("utf-8"), newline=""))
    if next(reader, None) != ["row"] + [f"split_{number}" for number in range(1, splits + 1)]:
        return False, "header differs", digest
    columns = [[] for _ in range(splits)]
    count = 0
    for count, row in enumerate(reader, start=1):
        if len(row) != splits + 1 or row[0] != str(count) or any(part not in PARTS for part in row[1:]):
            return False, f"line {count + 1} is not a valid split row", digest
        for number, part in enumerate(row[1:]):
            columns[number].append(part)
    if count != len(times):
        return False, f"{count} rows written, {len(times)} expected", digest
    previous_end = None
    for number, parts in enumerate(columns, start=1):
        facts = split_facts(times, parts, gap, slack)
        if not facts["passed"]:
            return False, f"split_{number} breaks the time order or the gap", digest
        if previous_end is not None and facts["validation_first"] <= previous_end:
            return False, f"split_{number} validation does not start after the previous one", digest
        previous_end = facts["validation_last"]
    return True, "", digest


def build_parser() -> Parser:
    parser = Parser(description="Build time-ordered validation splits with a declared gap. "
                                "Exit 0 pass, 1 check failed, 2 refused.")
    parser.add_argument("--root", default=".", help="folder that every path is relative to (default: current folder)")
    parser.add_argument("--train", required=True, help="training CSV with a header row, relative to --root")
    parser.add_argument("--list-columns", action="store_true",
                        help="print column names, row count, distinct and empty counts, then exit")
    parser.add_argument("--time", help="time column")
    parser.add_argument("--time-kind", choices=("iso", "number"), default="iso",
                        help="iso: YYYY-MM-DD or YYYY-MM-DDTHH:MM[:SS]; number: plain numbers (default iso)")
    parser.add_argument("--gap", type=float,
                        help="least time between the last training row and the first validation row, in "
                             "--gap-unit for iso times and in the column's own unit for numbers; 0 is allowed")
    parser.add_argument("--gap-unit", choices=tuple(UNITS),
                        help="unit of --gap for iso times: days (default), hours, minutes or seconds")
    parser.add_argument("--splits", type=int, default=3, help="number of validation windows, 1 to 50 (default 3)")
    parser.add_argument("--train-blocks", type=int,
                        help="train only on this many blocks before each validation block (default: all earlier)")
    parser.add_argument("--test", help="optional test CSV with the same time column, relative to --root")
    parser.add_argument("--output", help="new split CSV, relative to --root; it must not exist yet")
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
    for name in ("time", "gap", "output"):
        if getattr(args, name) is None:
            raise Refused("bad_arguments", f"--{name} is required unless --list-columns is given")
    if not math.isfinite(args.gap) or args.gap < 0:
        raise Refused("bad_arguments", "--gap must be a number of at least 0")
    if args.time_kind == "number" and args.gap_unit is not None:
        raise Refused("bad_arguments", "--gap-unit is only for --time-kind iso; numeric times use their own unit")
    if not 1 <= args.splits <= 50:
        raise Refused("bad_arguments", "--splits must be between 1 and 50")
    if args.train_blocks is not None and not 1 <= args.train_blocks <= 50:
        raise Refused("bad_arguments", "--train-blocks must be between 1 and 50")
    output = under_root(root, args.output)
    if output.exists():
        raise Refused("output_exists", f"{args.output} exists; choose a new name")
    times, zoned = read_times(table, args.time, args.time_kind)
    unit = "column units" if args.time_kind == "number" else (args.gap_unit or "days")
    scale = UNITS.get(unit, 1.0)
    gap = args.gap * scale
    slack = tolerance(gap)
    counts = Counter(times)
    unique = sorted(counts)
    if len(unique) < args.splits + 1:
        raise Refused("too_few_distinct_times", f"{len(unique)} distinct times for {args.splits + 1} blocks")
    cuts = block_cuts(unique, counts, args.splits)
    bounds = [0, *cuts, len(unique)]
    block_of = {}
    for block in range(args.splits + 1):
        for value in unique[bounds[block]:bounds[block + 1]]:
            block_of[value] = block
    starts = [unique[bounds[block]] for block in range(args.splits + 1)]
    parts_by_split = assign_parts(times, block_of, starts, args.splits, gap, args.train_blocks)
    splits, checks, observed = [], [], []
    ordered, previous_last = True, None
    for number, parts in enumerate(parts_by_split, start=1):
        facts = split_facts(times, parts, gap, slack)
        checks.append({"name": f"split_{number}_validation_after_training_by_gap", "passed": facts["passed"]})
        entry = {"split": number, **{key: facts[key] for key in ("train_rows", "validation_rows", "gap_rows",
                                                                  "unused_rows")}}
        for key in ("train_first", "train_last", "validation_first", "validation_last"):
            entry[key] = shown(facts[key], args.time_kind, zoned) if facts[key] is not None else None
        entry["gap_observed"] = None
        if facts["gap_observed"] is not None:
            observed.append(facts["gap_observed"])
            entry["gap_observed"] = plain(round(facts["gap_observed"] / scale, SHOWN_DECIMALS))
        if facts["validation_first"] is None or (previous_last is not None and facts["validation_first"] <= previous_last):
            ordered = False
        previous_last = facts["validation_last"]
        splits.append(entry)
    checks.append({"name": "validation_windows_move_forward", "passed": ordered})
    warnings, test_period, suggestion = [], None, None
    if args.test:
        test_data = read_input(root, args.test, args.max_bytes)
        test_table = Table(test_data, args.test, args.max_bytes)
        test_times, test_zoned = read_times(test_table, args.time, args.time_kind)
        if test_zoned != zoned:
            raise Refused("time_zone_mixed", "the training and test files differ in time zone offsets")
        after = min(test_times) - max(times)
        test_period = {"path": args.test, "sha256": hashlib.sha256(test_data).hexdigest(), "rows": len(test_times),
                       "first": shown(min(test_times), args.time_kind, zoned),
                       "last": shown(max(test_times), args.time_kind, zoned),
                       "gap_after_training": plain(round(after / scale, SHOWN_DECIMALS)), "unit": unit}
        if min(test_times) <= max(times):
            warnings.append("the test period starts before the last training time; forward time splits may not "
                            "match how the test rows were chosen")
        elif observed and after - min(observed) > 10 * tolerance(after):
            suggestion = suggest_gap(after, args.time_kind)
            warnings.append(f"validation starts {plain(round(min(observed) / scale, SHOWN_DECIMALS))} {unit} after "
                            f"training, but the test starts {test_period['gap_after_training']} {unit} after "
                            f"training; {' '.join(suggestion['arguments'])} matches the test")
    report = {"record_type": RECORD_TYPE, "status": "pass",
              "input": {"path": args.train, "sha256": digest, "rows": len(times), "blank_lines_skipped": table.blank_lines},
              "settings": {"time": args.time, "time_kind": args.time_kind, "gap": args.gap, "gap_unit": unit,
                           "splits": args.splits, "train_blocks": args.train_blocks},
              "time_range": {"first": shown(unique[0], args.time_kind, zoned),
                             "last": shown(unique[-1], args.time_kind, zoned), "distinct_times": len(unique)},
              "splits": splits, "test_period": test_period, "warnings": warnings, "suggested_gap": suggestion,
              "checks": checks, "output": None}
    if not all(check["passed"] for check in checks):
        report["status"] = "check_failed"
        report["note"] = ("No split file was written. A split without training rows usually means the gap is "
                          "too large for the data; use fewer splits or a smaller gap only when the task allows it.")
        return report, 1
    write_new_file(output, split_file_text(parts_by_split))
    matches, problem, written_digest = check_written_file(output, times, args.splits, gap, slack)
    checks.append({"name": "written_file_matches", "passed": matches, "detail": problem})
    report["output"] = {"path": args.output, "sha256": written_digest,
                        "columns": ["row"] + [f"split_{number}" for number in range(1, args.splits + 1)],
                        "values": list(PARTS),
                        "row_numbering": "data rows counted from 1 in input order, header excluded"}
    if not matches:
        report["status"] = "check_failed"
        report["note"] = "The written file did not match the splits. Do not use it."
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
