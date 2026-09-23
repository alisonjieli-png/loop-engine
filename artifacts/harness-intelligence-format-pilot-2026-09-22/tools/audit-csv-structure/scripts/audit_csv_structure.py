"""Read-only structural audit of a UTF-8 comma or tab delimited table."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os

from confined_input import ConfinedInputError, open_approved_file

DEFAULT_MAX_BYTES = 20_000_000
MAX_EXAMPLES = 20
HEADER_MODES = {"present", "absent"}


class AuditInputError(ValueError):
    """The requested source cannot be safely audited under this contract."""


def audit(
    approved_root: str,
    input_relative: str,
    delimiter: str = ",",
    max_bytes: int = DEFAULT_MAX_BYTES,
    header_mode: str = "absent",
) -> dict:
    if len(delimiter) != 1 or delimiter in {"\n", "\r", '"'}:
        raise AuditInputError("delimiter_must_be_one_non_quote_character")
    if not 1 <= max_bytes <= DEFAULT_MAX_BYTES:
        raise AuditInputError("max_bytes_outside_supported_range")
    if header_mode not in HEADER_MODES:
        raise AuditInputError("header_mode_must_be_present_or_absent")
    with open_approved_file(approved_root, input_relative) as handle:
        before = os.fstat(handle.fileno())
        body = handle.read(max_bytes + 1)
        after = os.fstat(handle.fileno())
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    ):
        raise AuditInputError("input_changed_during_read")
    if len(body) > max_bytes:
        raise AuditInputError("input_exceeds_max_bytes")

    examples: list[dict] = []
    issue_count = 0

    def issue(kind: str, record: int, physical_line: int) -> None:
        nonlocal issue_count
        issue_count += 1
        if len(examples) < MAX_EXAMPLES:
            examples.append(
                {"kind": kind, "record": record, "physical_line": physical_line}
            )

    header: list[str] = []
    data_rows = 0
    column_count: int | None = None
    prior_limit = csv.field_size_limit()
    csv.field_size_limit(max_bytes)
    try:
        with io.StringIO(body.decode("utf-8-sig"), newline="") as handle:
            reader = csv.reader(handle, delimiter=delimiter, strict=True)
            try:
                for record, row in enumerate(reader, start=1):
                    if record == 1:
                        column_count = len(row)
                        if header_mode == "present":
                            header = row
                            if not header:
                                issue("empty_header", record, reader.line_num)
                            normalized = [name.strip().casefold() for name in header]
                            if any(not name for name in normalized):
                                issue("blank_header_name", record, reader.line_num)
                            if len(set(normalized)) != len(normalized):
                                issue("duplicate_header_name", record, reader.line_num)
                        else:
                            data_rows += 1
                    else:
                        data_rows += 1
                        if len(row) != column_count:
                            issue("row_width_mismatch", record, reader.line_num)
                    if any("\x00" in field for field in row):
                        issue("nul_character", record, reader.line_num)
            except csv.Error:
                issue("malformed_csv", data_rows + 2, reader.line_num)
    finally:
        csv.field_size_limit(prior_limit)
    if column_count is None and issue_count == 0:
        issue("missing_header" if header_mode == "present" else "empty_input", 0, 0)
    return {
        "record_type": "csv_structure_audit/v1",
        "status": "pass" if issue_count == 0 else "fail",
        "input_sha256": hashlib.sha256(body).hexdigest(),
        "header_mode": header_mode,
        "header": header,
        "column_count": column_count or 0,
        "data_rows": data_rows,
        "issue_count": issue_count,
        "issue_examples": examples,
        "examples_truncated": issue_count > len(examples),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-root", required=True)
    parser.add_argument("--input-relative", required=True)
    parser.add_argument("--header-mode", choices=sorted(HEADER_MODES), default="absent")
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    args = parser.parse_args(argv)
    try:
        report = audit(
            args.approved_root,
            args.input_relative,
            args.delimiter,
            args.max_bytes,
            args.header_mode,
        )
    except (AuditInputError, ConfinedInputError, OSError, UnicodeError) as error:
        report = {
            "record_type": "csv_structure_audit/v1",
            "status": "refused",
            "reason": str(error)
            if isinstance(error, (AuditInputError, ConfinedInputError))
            else "input_unreadable",
        }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return {"pass": 0, "fail": 1, "refused": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
