"""Read-only audit of JSON Lines event identities and payload consistency."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from decimal import Decimal, InvalidOperation

from confined_input import ConfinedInputError, open_approved_file

DEFAULT_MAX_BYTES = 20_000_000
DEFAULT_MAX_RECORDS = 100_000
MAX_EXAMPLES = 20


class AuditInputError(ValueError):
    """The requested source cannot be safely audited under this contract."""


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("non_finite_json_number")


def _canonical(value: object) -> list:
    """Retain exact parsed numeric values and type boundaries in the digest."""
    if isinstance(value, dict):
        pairs = []
        for key in sorted(value):
            key.encode("utf-8")
            pairs.append([key, _canonical(value[key])])
        return ["object", pairs]
    if isinstance(value, list):
        return ["array", [_canonical(item) for item in value]]
    if isinstance(value, str):
        value.encode("utf-8")
        return ["string", value]
    if isinstance(value, bool):
        return ["boolean", value]
    if value is None:
        return ["null"]
    if isinstance(value, int):
        return ["integer", str(value)]
    if isinstance(value, Decimal):
        return ["decimal", str(value)]
    raise ValueError("unsupported_json_value")


def audit(
    approved_root: str,
    input_relative: str,
    id_field: str,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_records: int = DEFAULT_MAX_RECORDS,
) -> dict:
    if not id_field:
        raise AuditInputError("id_field_must_be_one_top_level_key")
    if (
        not 1 <= max_bytes <= DEFAULT_MAX_BYTES
        or not 1 <= max_records <= DEFAULT_MAX_RECORDS
    ):
        raise AuditInputError("resource_limits_outside_supported_range")
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
    decoded = body.decode("utf-8-sig")
    # Stop after the first record beyond the limit. An unrestricted split can
    # allocate millions of list entries even when the byte limit is bounded.
    lines = decoded.split("\n", max_records) if decoded else []
    if lines and lines[-1] == "":
        lines.pop()
    if len(lines) > max_records:
        raise AuditInputError("input_exceeds_max_records")

    examples: list[dict] = []
    counts = {
        "valid_events": 0,
        "identical_repeats": 0,
        "conflicting_repeats": 0,
        "invalid_records": 0,
    }
    seen: dict[str, tuple[str, int]] = {}

    def problem(kind: str, line: int, first_line: int | None = None) -> None:
        counts["invalid_records" if first_line is None else "conflicting_repeats"] += 1
        if len(examples) < MAX_EXAMPLES:
            example = {"kind": kind, "line": line}
            if first_line is not None:
                example["first_line"] = first_line
            examples.append(example)

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.removesuffix("\r")
        if not line.strip():
            problem("blank_line", line_number)
            continue
        try:
            event = json.loads(
                line,
                object_pairs_hook=_unique_pairs,
                parse_constant=_reject_constant,
                parse_float=Decimal,
            )
        except (json.JSONDecodeError, ValueError, InvalidOperation, RecursionError):
            problem("invalid_json_or_duplicate_key", line_number)
            continue
        if not isinstance(event, dict):
            problem("event_must_be_object", line_number)
            continue
        identity = event.get(id_field)
        if (
            isinstance(identity, bool)
            or not isinstance(identity, (str, int))
            or isinstance(identity, str)
            and not identity
        ):
            problem("missing_or_invalid_identity", line_number)
            continue
        try:
            key = json.dumps(
                _canonical(identity), ensure_ascii=False, separators=(",", ":")
            )
            canonical = json.dumps(
                _canonical(event), ensure_ascii=False, separators=(",", ":")
            )
        except (ValueError, UnicodeError, RecursionError):
            problem("invalid_json_value", line_number)
            continue
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        counts["valid_events"] += 1
        if key in seen:
            prior_digest, first_line = seen[key]
            if digest == prior_digest:
                counts["identical_repeats"] += 1
            else:
                problem("conflicting_identity_payload", line_number, first_line)
        else:
            seen[key] = (digest, line_number)
    if not lines:
        problem("empty_input", 0)
    failure_count = counts["conflicting_repeats"] + counts["invalid_records"]
    return {
        "record_type": "jsonl_identity_audit/v1",
        "status": "pass" if failure_count == 0 else "fail",
        "input_sha256": hashlib.sha256(body).hexdigest(),
        "id_field": id_field,
        "line_count": len(lines),
        "distinct_identities": len(seen),
        "counts": counts,
        "issue_examples": examples,
        "examples_truncated": failure_count > len(examples),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-root", required=True)
    parser.add_argument("--input-relative", required=True)
    parser.add_argument("--id-field", required=True)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--max-records", type=int, default=DEFAULT_MAX_RECORDS)
    args = parser.parse_args(argv)
    try:
        report = audit(
            args.approved_root,
            args.input_relative,
            args.id_field,
            args.max_bytes,
            args.max_records,
        )
    except (AuditInputError, ConfinedInputError, OSError, UnicodeError) as error:
        report = {
            "record_type": "jsonl_identity_audit/v1",
            "status": "refused",
            "reason": str(error)
            if isinstance(error, (AuditInputError, ConfinedInputError))
            else "input_unreadable",
        }
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return {"pass": 0, "fail": 1, "refused": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
