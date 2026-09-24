"""Build group-aware stratified folds. Effects: reads one CSV under --root, writes one new CSV under --root, prints one JSON object; no network.

Every data row of the training file gets a fold number from 0 to K-1. All rows of
one group get the same fold, and the label shares of each fold stay close to the
shares of the whole file. Group values are compared after removing surrounding
spaces. A numeric label can be cut into bins: rows with one value always share a
bin, and a value that holds many rows gets a bin of its own. The same bytes,
settings and seed give the same output. After writing, the script reads its own
output file again and checks it.

Exit status: 0 pass, 1 a check failed, 2 refused input. When a check fails before writing, no
fold file is written; when the written file fails its recheck, the report says not to use it.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import random
import re
import sys
from collections import Counter
from pathlib import Path

RECORD_TYPE = "group_folds_report/v2"
DEFAULT_MAX_BYTES = 64 * 1024 * 1024
HARD_MAX_BYTES = 1024 * 1024 * 1024
MAX_CLASS_LABELS = 100
MAX_LISTED_LABELS = 20
DISTINCT_CAP = 5000
LIST_COLUMNS_CAP = 300
NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")
HINTS = {
    "at_least_two_label_strata": "The label has one value or one bin, so there is nothing to balance. "
                                 "Check that --label names the label column.",
    "few_groups": "A label held by fewer groups than folds cannot reach every fold. Use --folds no larger "
                  "than that label's groups count, or add --allow-missing-labels only when the task accepts "
                  "folds without that label.",
    "assignment": "A label held by enough groups was still left out of a fold. Try another --seed.",
    "label_share_gap": "Raise --max-share-gap only when the task allows it, and record that choice.",
    "fold_size_ratio": "One large group can make fold sizes uneven. Raise --max-size-ratio only when the task "
                       "allows it, and record that choice.",
}


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
            self.text = data.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise Refused("input_not_utf8", f"{label}: byte {error.start}") from None
        self.label = label
        self.blank_lines = 0
        csv.field_size_limit(max(limit, 131072))
        self._reader = csv.reader(io.StringIO(self.text, newline=""), strict=True)
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


def numeric_bins(labels: list[str], bins: int) -> tuple[list[str], list[list]]:
    """Cut a numeric label into at most `bins` strata; return each row's stratum and each stratum's [low, high, rows].

    With at most `bins` distinct values, each value is its own stratum. Otherwise the
    sorted distinct values are grouped into strata of about equal row counts. Rows with
    one value always share a stratum, and a value that holds at least one stratum's share
    of the remaining rows closes the open stratum and starts its own, so a label that is
    mostly zero still gives a zero stratum and strata for the other values.
    """
    values = []
    for position, text in enumerate(labels, start=1):
        number = parse_number(text)
        if number is None:
            raise Refused("label_not_numeric", f"data row {position}: {text[:40]!r}; --label-bins needs numbers")
        values.append(number)
    counts = Counter(values)
    distinct = sorted(counts)
    members: list[list[float]] = []
    if len(distinct) <= bins:
        members = [[value] for value in distinct]
    else:
        remaining_rows, remaining_bins = len(values), bins
        current, current_rows = [], 0
        for value in distinct:
            if current and remaining_bins > 1:
                share = remaining_rows / remaining_bins
                if current_rows >= share or counts[value] >= share:
                    members.append(current)
                    remaining_rows -= current_rows
                    remaining_bins -= 1
                    current, current_rows = [], 0
            current.append(value)
            current_rows += counts[value]
        members.append(current)
    stratum_of, ranges = {}, []
    for number, group in enumerate(members):
        for value in group:
            stratum_of[value] = f"bin_{number:02d}"
        ranges.append([round(group[0], 6), round(group[-1], 6), sum(counts[value] for value in group)])
    return [stratum_of[value] for value in values], ranges


def assign_folds(group_rows: dict, group_strata: dict, totals: Counter, folds: int, seed: int) -> dict:
    """Give each group one fold: largest groups first, each to the fold whose counts of the group's
    labels are furthest below their targets, measured relative to each target so rare labels count."""
    order = sorted(group_rows)
    random.Random(seed).shuffle(order)
    order.sort(key=lambda group: len(group_rows[group]), reverse=True)
    target = {stratum: totals[stratum] / folds for stratum in totals}
    weight = {stratum: 1.0 / max(target[stratum], 1.0) for stratum in totals}
    fold_counts = [Counter() for _ in range(folds)]
    fold_rows = [0] * folds
    fold_of_group = {}
    for group in order:
        counts = group_strata[group]
        best = None
        for fold in range(folds):
            cost = sum(amount * (fold_counts[fold][stratum] - target[stratum]) * weight[stratum]
                       for stratum, amount in counts.items())
            key = (cost, fold_rows[fold], fold)
            if best is None or key < best:
                best = key
        chosen = best[2]
        fold_of_group[group] = chosen
        fold_counts[chosen].update(counts)
        fold_rows[chosen] += len(group_rows[group])
    return fold_of_group


def fold_summary(keys: list, strata: list, fold_of_row: list, folds: int) -> dict:
    total = len(keys)
    totals = Counter(strata)
    fold_rows = [0] * folds
    fold_groups = [set() for _ in range(folds)]
    fold_counts = [Counter() for _ in range(folds)]
    folds_of_group = {}
    holders = {}
    for key, stratum, fold in zip(keys, strata, fold_of_row):
        fold_rows[fold] += 1
        fold_groups[fold].add(key)
        fold_counts[fold][stratum] += 1
        folds_of_group.setdefault(key, set()).add(fold)
        holders.setdefault(stratum, set()).add(key)
    worst = {"value": 0.0, "fold": None, "label": None, "fold_share": None, "overall_share": None}
    for fold in range(folds):
        if not fold_rows[fold]:
            continue
        for stratum in sorted(totals):
            share = fold_counts[fold][stratum] / fold_rows[fold]
            overall = totals[stratum] / total
            if abs(share - overall) > worst["value"]:
                worst = {"value": round(abs(share - overall), 6), "fold": fold, "label": stratum,
                         "fold_share": round(share, 6), "overall_share": round(overall, 6)}
    shares = None
    if len(totals) <= 10 and folds <= 20:
        shares = [{stratum: round(fold_counts[fold][stratum] / fold_rows[fold], 6) if fold_rows[fold] else None
                   for stratum in sorted(totals)} for fold in range(folds)]
    ratio = round(max(fold_rows) / min(fold_rows), 6) if min(fold_rows) else None
    rarest = min(sorted(totals), key=lambda stratum: totals[stratum])
    missing = []
    for stratum in sorted(totals, key=lambda item: (totals[item], item)):
        absent = [fold for fold in range(folds) if not fold_counts[fold][stratum]]
        if absent:
            missing.append({"label": stratum, "rows": totals[stratum], "groups": len(holders[stratum]),
                            "folds_without": absent[:MAX_LISTED_LABELS]})
    return {"fold_rows": fold_rows, "fold_groups": [len(item) for item in fold_groups],
            "groups_in_two_folds": sum(1 for item in folds_of_group.values() if len(item) > 1),
            "max_label_share_gap": worst, "fold_size_ratio": ratio, "fold_label_shares": shares,
            "rarest_label": {"label": rarest, "rows": totals[rarest], "groups": len(holders[rarest]),
                             "fold_rows": [fold_counts[fold][rarest] for fold in range(folds)]},
            "labels_missing_from_folds": missing}


def fold_file_text(groups: list, fold_of_row: list) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["row", "group", "fold"])
    for position, (group, fold) in enumerate(zip(groups, fold_of_row), start=1):
        writer.writerow([position, group, fold])
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


def check_written_file(path: Path, groups: list, fold_of_row: list, folds: int) -> tuple[bool, str, str]:
    """Read the written fold file again and confirm rows, groups and folds."""
    data = path.read_bytes()
    reader = csv.reader(io.StringIO(data.decode("utf-8"), newline=""))
    if next(reader, None) != ["row", "group", "fold"]:
        return False, "header differs", hashlib.sha256(data).hexdigest()
    folds_of_group = {}
    count = 0
    for count, row in enumerate(reader, start=1):
        if len(row) != 3 or row[0] != str(count) or count > len(groups) or row[1] != groups[count - 1]:
            return False, f"line {count + 1} does not match data row {count}", hashlib.sha256(data).hexdigest()
        if row[2] != str(fold_of_row[count - 1]) or not 0 <= int(row[2]) < folds:
            return False, f"fold on line {count + 1} differs", hashlib.sha256(data).hexdigest()
        folds_of_group.setdefault(row[1].strip(), set()).add(row[2])
    if count != len(groups):
        return False, f"{count} rows written, {len(groups)} expected", hashlib.sha256(data).hexdigest()
    if any(len(item) > 1 for item in folds_of_group.values()):
        return False, "a group appears in two folds", hashlib.sha256(data).hexdigest()
    return True, "", hashlib.sha256(data).hexdigest()


def build_parser() -> Parser:
    parser = Parser(description="Build group-aware stratified folds and check them. Exit 0 pass, 1 check failed, 2 refused.")
    parser.add_argument("--root", default=".", help="folder that every path is relative to (default: current folder)")
    parser.add_argument("--train", required=True, help="training CSV with a header row, relative to --root")
    parser.add_argument("--list-columns", action="store_true",
                        help="print column names, row count, distinct and empty counts, then exit")
    parser.add_argument("--group", help="column whose rows must stay inside one fold")
    parser.add_argument("--label", help="label column whose shares each fold should keep")
    parser.add_argument("--label-bins", type=int, default=0,
                        help="numeric label: at most this many bins of about equal rows, 2 to 100; "
                             "0 (default) treats labels as classes")
    parser.add_argument("--folds", type=int, default=5, help="number of folds K, 2 to 100 (default 5)")
    parser.add_argument("--seed", type=int, default=0, help="seed for the order of equal-sized groups (default 0)")
    parser.add_argument("--max-share-gap", type=float, default=0.05,
                        help="largest allowed difference between a fold's label share and the whole file's share")
    parser.add_argument("--max-size-ratio", type=float, default=1.5,
                        help="largest allowed ratio of the biggest fold's rows to the smallest fold's rows")
    parser.add_argument("--allow-missing-labels", action="store_true",
                        help="accept folds without a class label that fewer groups than folds hold")
    parser.add_argument("--output", help="new fold CSV, relative to --root; it must not exist yet")
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
    for name in ("group", "label", "output"):
        if not getattr(args, name):
            raise Refused("bad_arguments", f"--{name} is required unless --list-columns is given")
    if not 2 <= args.folds <= 100:
        raise Refused("bad_arguments", "--folds must be between 2 and 100")
    if args.label_bins and not 2 <= args.label_bins <= 100:
        raise Refused("bad_arguments", "--label-bins must be 0 or between 2 and 100")
    if not 0 < args.max_share_gap <= 1 or not args.max_size_ratio >= 1:
        raise Refused("bad_arguments", "--max-share-gap must be in (0, 1] and --max-size-ratio at least 1")
    group_index, label_index = table.index(args.group), table.index(args.label)
    output = under_root(root, args.output)
    if output.exists():
        raise Refused("output_exists", f"{args.output} exists; choose a new name")
    groups, keys, labels = [], [], []
    missing_group, missing_label = [], []
    for line, row in table.rows():
        group, label = row[group_index], row[label_index].strip()
        if not group.strip():
            missing_group.append(line)
        if not label:
            missing_label.append(line)
        groups.append(group)
        keys.append(group.strip())
        labels.append(label)
    if not groups:
        raise Refused("input_has_no_rows", args.train)
    if missing_group:
        raise Refused("group_value_missing", f"{len(missing_group)} rows, first on line {missing_group[0]}")
    if missing_label:
        raise Refused("label_value_missing", f"{len(missing_label)} rows, first on line {missing_label[0]}")
    ranges = None
    if args.label_bins:
        strata, ranges = numeric_bins(labels, args.label_bins)
    else:
        strata = labels
        distinct = len(set(strata))
        if distinct > MAX_CLASS_LABELS:
            raise Refused("too_many_label_values",
                          f"{distinct} distinct labels; for a numeric label add --label-bins 10")
    group_rows: dict = {}
    for position, key in enumerate(keys):
        group_rows.setdefault(key, []).append(position)
    if len(group_rows) < args.folds:
        raise Refused("fewer_groups_than_folds", f"{len(group_rows)} groups for {args.folds} folds")
    spaced = sum(1 for group, key in zip(groups, keys) if group != key)
    spellings: dict = {}
    for group, key in zip(groups, keys):
        spellings.setdefault(key, set()).add(group)
    merged = sorted(key for key, found in spellings.items() if len(found) > 1)
    warnings = []
    if merged:
        example = [item[:40] for item in sorted(spellings[merged[0]])[:3]]
        warnings.append(f"group values that differ only by surrounding spaces were treated as one group; "
                        f"groups affected: {len(merged)}, for example {example}")
    group_strata = {key: Counter(strata[position] for position in rows) for key, rows in group_rows.items()}
    totals = Counter(strata)
    fold_of_group = assign_folds(group_rows, group_strata, totals, args.folds, args.seed)
    fold_of_row = [fold_of_group[key] for key in keys]
    summary = fold_summary(keys, strata, fold_of_row, args.folds)
    classes = not args.label_bins
    listed, blocking, allowed, small_bins = [], [], [], 0
    for item in summary["labels_missing_from_folds"]:
        item["must_reach_every_fold"] = item["groups"] >= args.folds or (classes and not args.allow_missing_labels)
        if item["must_reach_every_fold"]:
            blocking.append(item)
        elif classes:
            allowed.append(item)
        else:
            small_bins += 1
            continue
        listed.append(item)
    if allowed:
        first = allowed[0]
        warnings.append(f"{len(allowed)} labels are held by fewer groups than folds and are missing from some folds, "
                        f"for example {first['label'][:40]!r} ({first['groups']} groups, missing from folds "
                        f"{first['folds_without']}); per-fold scores that need such a label are not defined there")
    summary["labels_missing_from_folds"] = listed[:MAX_LISTED_LABELS]
    summary["small_bins_not_in_every_fold"] = None if classes else small_bins
    gap = summary["max_label_share_gap"]["value"]
    ratio = summary["fold_size_ratio"]
    checks = [
        {"name": "every_row_assigned_once", "passed": len(fold_of_row) == len(groups)},
        {"name": "no_group_in_two_folds", "passed": summary["groups_in_two_folds"] == 0,
         "value": summary["groups_in_two_folds"]},
        {"name": "no_empty_fold", "passed": min(summary["fold_rows"]) > 0},
        {"name": "at_least_two_label_strata", "passed": len(totals) >= 2, "value": len(totals)},
        {"name": "each_label_in_every_fold", "passed": not blocking, "value": len(blocking)},
        {"name": "label_share_gap", "passed": gap <= args.max_share_gap + 1e-12, "value": gap,
         "limit": args.max_share_gap},
        {"name": "fold_size_ratio", "passed": ratio is not None and ratio <= args.max_size_ratio + 1e-12,
         "value": ratio, "limit": args.max_size_ratio},
    ]
    for check in checks:
        if not check["passed"]:
            if check["name"] == "each_label_in_every_fold":
                few = any(item["groups"] < args.folds for item in blocking)
                check["hint"] = HINTS["few_groups" if few else "assignment"]
            elif check["name"] in HINTS:
                check["hint"] = HINTS[check["name"]]
    report = {"record_type": RECORD_TYPE, "status": "pass",
              "input": {"path": args.train, "sha256": digest, "rows": len(groups),
                        "blank_lines_skipped": table.blank_lines},
              "settings": {"group": args.group, "label": args.label,
                           "label_mode": "numeric_bins" if args.label_bins else "classes",
                           "label_bins": args.label_bins, "folds": args.folds, "seed": args.seed,
                           "max_share_gap": args.max_share_gap, "max_size_ratio": args.max_size_ratio,
                           "allow_missing_labels": args.allow_missing_labels,
                           "group_values": "compared after removing surrounding spaces"},
              "groups": len(group_rows), "rows_with_spaces_around_group": spaced,
              "largest_group_rows": max(len(rows) for rows in group_rows.values()),
              "label_strata": len(totals), "label_bin_ranges": ranges,
              **summary, "warnings": warnings, "checks": checks, "output": None}
    if not all(check["passed"] for check in checks):
        report["status"] = "check_failed"
        report["note"] = "No fold file was written. Read the hint of each failed check."
        return report, 1
    write_new_file(output, fold_file_text(groups, fold_of_row))
    matches, problem, written_digest = check_written_file(output, groups, fold_of_row, args.folds)
    checks.append({"name": "written_file_matches", "passed": matches, "detail": problem})
    report["output"] = {"path": args.output, "sha256": written_digest, "columns": ["row", "group", "fold"],
                        "row_numbering": "data rows counted from 1 in input order, header excluded"}
    if not matches:
        report["status"] = "check_failed"
        report["note"] = "The written file did not match the assignment. Do not use it."
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
