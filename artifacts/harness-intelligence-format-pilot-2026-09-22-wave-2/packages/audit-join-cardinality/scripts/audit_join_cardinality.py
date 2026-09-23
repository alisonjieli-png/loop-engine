"""Bounded, read-only cardinality audit for a two-table CSV join."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass

from confined_input import ConfinedInputError, open_approved_file

MAX_INPUT_BYTES = 20_000_000
MAX_ROWS = 100_000
MAX_JOINED_ROWS = 1_000_000


class AuditFailure(ValueError):
    """The material is readable but fails a declared table contract."""


@dataclass(frozen=True)
class Table:
    digest: str
    rows: int
    blank_keys: int
    counts: Counter[str]


def _read_table(
    root: str, relative: str, key: str, max_bytes: int, max_rows: int
) -> Table:
    with open_approved_file(root, relative) as handle:
        if os.fstat(handle.fileno()).st_size > max_bytes:
            raise ConfinedInputError("input_exceeds_byte_ceiling")
        raw = handle.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ConfinedInputError("input_exceeds_byte_ceiling")
    digest = hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise AuditFailure("invalid_utf8") from None
    if "\x00" in text:
        raise AuditFailure("nul_byte_in_csv")
    csv.field_size_limit(max_bytes)
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header = next(reader)
    except StopIteration:
        raise AuditFailure("missing_header") from None
    except csv.Error:
        raise AuditFailure("malformed_header") from None
    if (
        not header
        or len(set(header)) != len(header)
        or any(not name for name in header)
    ):
        raise AuditFailure("empty_or_duplicate_header")
    if key not in header:
        raise AuditFailure("selected_key_absent")
    index = header.index(key)
    counts: Counter[str] = Counter()
    rows = 0
    blank_keys = 0
    try:
        for row in reader:
            rows += 1
            if rows > max_rows:
                raise ConfinedInputError("input_exceeds_row_ceiling")
            if len(row) != len(header):
                raise AuditFailure("field_count_mismatch")
            value = row[index]
            if not value.strip():
                blank_keys += 1
            else:
                counts[value] += 1
                if len(counts) > max_rows:
                    raise ConfinedInputError("input_exceeds_distinct_key_ceiling")
    except csv.Error:
        raise AuditFailure("malformed_csv") from None
    return Table(digest, rows, blank_keys, counts)


def audit(args: argparse.Namespace) -> dict[str, object]:
    if not 0 < args.max_bytes <= MAX_INPUT_BYTES:
        raise ConfinedInputError("max_bytes_outside_supported_ceiling")
    if not 0 < args.max_rows <= MAX_ROWS:
        raise ConfinedInputError("max_rows_outside_supported_ceiling")
    if not 0 < args.max_joined_rows <= MAX_JOINED_ROWS:
        raise ConfinedInputError("max_joined_rows_outside_supported_ceiling")
    left = _read_table(
        args.approved_root,
        args.left_relative,
        args.left_key,
        args.max_bytes,
        args.max_rows,
    )
    right = _read_table(
        args.approved_root,
        args.right_relative,
        args.right_key,
        args.max_bytes,
        args.max_rows,
    )
    joined_rows = sum(
        count * right.counts.get(key, 0) for key, count in left.counts.items()
    )
    unmatched_left = sum(
        count for key, count in left.counts.items() if key not in right.counts
    )
    unmatched_right = sum(
        count for key, count in right.counts.items() if key not in left.counts
    )
    left_duplicate_rows = sum(count - 1 for count in left.counts.values())
    right_duplicate_rows = sum(count - 1 for count in right.counts.values())
    failures = []
    if left.blank_keys or right.blank_keys:
        failures.append("blank_join_key")
    if args.expect in ("one-to-one", "one-to-many") and left_duplicate_rows:
        failures.append("left_key_not_unique")
    if args.expect in ("one-to-one", "many-to-one") and right_duplicate_rows:
        failures.append("right_key_not_unique")
    if args.require_left_match and unmatched_left:
        failures.append("unmatched_left_rows")
    if args.require_right_match and unmatched_right:
        failures.append("unmatched_right_rows")
    if joined_rows > args.max_joined_rows:
        failures.append("projected_join_exceeds_ceiling")
    return {
        "schema": "join_cardinality_audit/v1",
        "status": "fail" if failures else "pass",
        "failures": failures,
        "expect": args.expect,
        "left": {
            "sha256": left.digest,
            "rows": left.rows,
            "blank_keys": left.blank_keys,
            "duplicate_key_rows": left_duplicate_rows,
            "unmatched_rows": unmatched_left,
        },
        "right": {
            "sha256": right.digest,
            "rows": right.rows,
            "blank_keys": right.blank_keys,
            "duplicate_key_rows": right_duplicate_rows,
            "unmatched_rows": unmatched_right,
        },
        "projected_join_rows": joined_rows,
        "max_joined_rows": args.max_joined_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-root", required=True)
    parser.add_argument("--left-relative", required=True)
    parser.add_argument("--right-relative", required=True)
    parser.add_argument("--left-key", required=True)
    parser.add_argument("--right-key", required=True)
    parser.add_argument(
        "--expect",
        choices=("one-to-one", "one-to-many", "many-to-one", "many-to-many"),
        default="one-to-one",
    )
    parser.add_argument("--require-left-match", action="store_true")
    parser.add_argument("--require-right-match", action="store_true")
    parser.add_argument("--max-bytes", type=int, default=MAX_INPUT_BYTES)
    parser.add_argument("--max-rows", type=int, default=MAX_ROWS)
    parser.add_argument("--max-joined-rows", type=int, default=MAX_JOINED_ROWS)
    args = parser.parse_args()
    try:
        result = audit(args)
    except (ConfinedInputError, OSError) as error:
        result = {
            "schema": "join_cardinality_audit/v1",
            "status": "refused",
            "reason": str(error),
        }
    except AuditFailure as error:
        result = {
            "schema": "join_cardinality_audit/v1",
            "status": "fail",
            "failures": [str(error)],
        }
    print(json.dumps(result, sort_keys=True))
    return {"pass": 0, "fail": 1, "refused": 2}[str(result["status"])]


if __name__ == "__main__":
    sys.exit(main())
