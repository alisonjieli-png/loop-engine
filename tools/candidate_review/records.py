"""Record names, the one strict reader and the digest rules every review record shares.

Every record here is written ``name/vN``. A reader refuses another version, an
unknown field and a missing field before anything is built from the record,
so a newer or older writer can never be reinterpreted. Digests are SHA-256 of
canonical JSON (sorted keys, no spaces, UTF-8), so the same content always
produces the same digest.
"""
from __future__ import annotations

import hashlib
import json
import re

CRITERIA_RECORD = "candidate_review_criteria/v2"
PANEL_RECORD = "candidate_review_panel/v1"
POLICY_RECORD = "candidate_review_panel_policy/v1"
INSTALLATION_RECORD = "candidate_reviewer_installation/v1"
PRODUCER_RECORD = "candidate_producer_declaration/v1"
REQUEST_RECORD = "candidate_review_request/v1"
VERDICT_RECORD = "candidate_review_verdict/v2"
PRECHECK_RECORD = "candidate_precheck_result/v1"
DISPATCH_RECORD = "candidate_review_dispatch/v2"
CALL_RECORD = "candidate_review_call/v2"
#: One call that asked one reviewer about several candidates, and the dispatch written before it.
BATCH_DISPATCH_RECORD = "candidate_review_batch_dispatch/v1"
BATCH_CALL_RECORD = "candidate_review_batch_call/v1"
RUN_RECORD = "candidate_review_run/v2"
RUN_END_RECORD = "candidate_review_run_end/v2"
PANEL_REVIEW_RECORD = "starter_catalogue_panel_review/v3"

SHA256 = re.compile(r"[0-9a-f]{64}")
IDENTIFIER = re.compile(r"[a-z][a-z0-9_.-]{0,95}")


class CandidateReviewError(ValueError):
    """A stable refusal code and an operator message that never holds an item body or a secret."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def refuse(code: str, message: str):
    raise CandidateReviewError(code, message)


def read_record(value, record_type: str, fields) -> dict:
    """Return ``value`` only when its type, version and field set are exactly the declared ones."""
    if type(value) is not dict:
        refuse("record_not_a_mapping", f"{record_type} must be a JSON object")
    found = value.get("record_type")
    if found != record_type:
        same_name = type(found) is str and found.rpartition("/")[0] == record_type.rpartition("/")[0]
        refuse("unsupported_record_version" if same_name else "unknown_record_type",
               f"expected {record_type}, found {found!r}")
    return read_part(value, record_type, tuple(fields) + ("record_type",))


def read_part(value, name: str, fields) -> dict:
    """The same exact field rule for a part nested inside a record."""
    if type(value) is not dict:
        refuse("record_not_a_mapping", f"{name} must be a JSON object")
    expected = set(fields)
    unknown = sorted(str(key) for key in set(value) - expected)
    if unknown:
        refuse("unknown_record_fields", f"{name} carries unknown fields {unknown}")
    missing = sorted(expected - set(value))
    if missing:
        refuse("missing_record_fields", f"{name} lacks {missing}")
    return value


def canonical_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_whitespace(text: str) -> str:
    """Every run of whitespace as one space, for the declared ``whitespace_canonical`` match mode."""
    return " ".join(text.split())


def text_field(value, name: str, *, limit: int = 4096, empty: bool = False) -> str:
    if type(value) is not str or len(value) > limit or (not empty and not value.strip()):
        refuse("invalid_text", f"{name} must be text of at most {limit} characters")
    return value


def identifier(value, name: str) -> str:
    if type(value) is not str or IDENTIFIER.fullmatch(value) is None:
        refuse("invalid_identifier", f"{name} must match {IDENTIFIER.pattern}")
    return value


def positive_integer(value, name: str) -> int:
    if type(value) is not int or value < 1:
        refuse("invalid_policy", f"{name} must be a positive integer")
    return value


def positive_number(value, name: str) -> float:
    if type(value) not in (int, float) or not value > 0 or value != value or value == float("inf"):
        refuse("invalid_policy", f"{name} must be a positive finite number")
    return float(value)


def boolean(value, name: str) -> bool:
    if type(value) is not bool:
        refuse("invalid_policy", f"{name} must be true or false")
    return value
