"""The review ledger: an append-only record of runs, dispatches, calls and verdicts, and the resumable cursor.

Every call is written twice. A dispatch row is written and flushed to disk
before the engine is asked; a call row, and the verdict when there is one, is
written when the engine answers. A later run reads the ledger first:

- a verdict already given for the same review key (the same installation and
  the same request, so the same bytes, provenance, criteria and instructions)
  is reused and no call is made;
- a dispatch with no call row is an interrupted call whose outcome is unknown.
  It is reported and never repeated automatically, so a stopped run never
  reviews the same bytes twice with the same reviewer;
- a completed call that produced no verdict (a failure) may be tried again in a
  later run, because it produced nothing to reuse.

A batch call asks one reviewer about several candidates in one request. Its
dispatch row names every candidate's review key before the engine is asked,
and its call row holds the call's usage once, with one member row per candidate
naming that candidate's outcome. Each verdict row names the batch call it came
from and must agree with its member row, so a verdict is reused only for the
exact candidate, installation and member prompt it answered.

A call is named by its run identity and its sequence number within the run, so
each run identity appears once in a ledger. A new run under an identity the
ledger already holds is refused, and so is a ledger file that holds one
identity twice: a reused identity would give a new call the name of an earlier
dispatch that never completed, that dispatch would read as completed, and a
later run would ask the same reviewer about the same bytes again.

Rows are strict ``name/vN`` records. A row of an unknown type, with an unknown
or missing field, or a line that is not JSON refuses the whole ledger: an
unknown commit is never read as a success.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import threading

from .records import (
    BATCH_CALL_RECORD, BATCH_DISPATCH_RECORD, CALL_RECORD, DISPATCH_RECORD, RUN_END_RECORD, RUN_RECORD, SHA256,
    VERDICT_RECORD, canonical_bytes, read_part, read_record, refuse,
)

RUN_FIELDS = ("run_id", "started_at", "policy_sha256", "call_ceiling", "token_ceiling", "fixture_run", "requests")
RUN_END_FIELDS = ("run_id", "finished_at", "stop_reason", "elapsed_seconds", "calls", "items", "pause_seconds")
DISPATCH_FIELDS = ("run_id", "sequence", "review_key", "installation_id", "identity", "body_sha256",
                   "request_sha256", "request_record_type", "dispatched_at")
CALL_FIELDS = ("run_id", "sequence", "review_key", "installation_id", "installation_sha256", "engine_kind", "family",
               "model", "model_version", "engine_version", "route_or_command", "identity", "body_sha256",
               "request_sha256", "prompt_sha256", "started_at", "elapsed_seconds", "outcome", "error_code",
               "decision", "invalid_answer_excerpt", "physical_model_calls", "physical_calls_basis", "usage",
               "reserved_tokens", "charged_tokens", "charge_basis", "retry_after_seconds", "pause_seconds_after",
               "reported_model", "request_record_type")
VERDICT_FIELDS = ("run_id", "sequence", "review_key", "installation_id", "family", "identity", "body_sha256",
                  "request_sha256", "decision", "findings", "reasons", "reported_model", "request_record_type")
BATCH_MEMBER_FIELDS = ("position", "review_key", "identity", "body_sha256", "request_sha256",
                       "request_record_type", "member_prompt_sha256")
BATCH_CALL_MEMBER_FIELDS = BATCH_MEMBER_FIELDS + ("outcome", "error_code", "decision")
BATCH_DISPATCH_FIELDS = ("run_id", "sequence", "batch_key", "installation_id", "members", "dispatched_at")
BATCH_CALL_FIELDS = ("run_id", "sequence", "batch_key", "installation_id", "installation_sha256", "engine_kind",
                     "family", "model", "reported_model", "model_version", "engine_version", "route_or_command",
                     "prompt_sha256", "started_at", "elapsed_seconds", "outcome", "error_code",
                     "invalid_answer_excerpt", "physical_model_calls", "physical_calls_basis", "usage",
                     "reserved_tokens", "charged_tokens", "charge_basis", "retry_after_seconds",
                     "pause_seconds_after", "members")
ROW_FIELDS = {RUN_RECORD: RUN_FIELDS, RUN_END_RECORD: RUN_END_FIELDS, DISPATCH_RECORD: DISPATCH_FIELDS,
              CALL_RECORD: CALL_FIELDS, VERDICT_RECORD: VERDICT_FIELDS, BATCH_DISPATCH_RECORD: BATCH_DISPATCH_FIELDS,
              BATCH_CALL_RECORD: BATCH_CALL_FIELDS}
REVIEW_SUBJECTS = ("candidate_review_request/v1", "candidate_native_package_review_request/v1",
                   "candidate_imported_package_review_request/v1")
#: What one candidate of a batch call came to: a verdict, an answer that was not a valid verdict for it, or
#: nothing because the call itself failed.
MEMBER_OUTCOMES = ("verdict", "invalid_response", "not_answered")
MAXIMUM_BATCH_MEMBERS = 12


def _members(row) -> list:
    """The member rows of a batch dispatch or call, each exact, in position order, each key once."""
    fields = BATCH_CALL_MEMBER_FIELDS if row["record_type"] == BATCH_CALL_RECORD else BATCH_MEMBER_FIELDS
    members = row["members"]
    if type(members) is not list or not 1 <= len(members) <= MAXIMUM_BATCH_MEMBERS:
        refuse("batch_members_invalid", "a batch names from 1 to 12 candidates")
    parts = [read_part(member, "batch member", fields) for member in members]
    if [part["position"] for part in parts] != list(range(len(parts))) or \
            len({part["review_key"] for part in parts}) != len(parts):
        refuse("batch_members_invalid", "batch members are in position order and each has its own review key")
    for part in parts:
        if part["request_record_type"] not in REVIEW_SUBJECTS:
            refuse("review_subject_unsupported", "the ledger row names an unsupported review subject version")
        if type(part["member_prompt_sha256"]) is not str or not SHA256.fullmatch(part["member_prompt_sha256"]):
            refuse("batch_members_invalid", "each batch member names its member prompt digest")
        if fields is BATCH_CALL_MEMBER_FIELDS and part["outcome"] not in MEMBER_OUTCOMES:
            refuse("batch_members_invalid", f"a batch member outcome is one of {list(MEMBER_OUTCOMES)}")
    return parts


def read_row(value) -> dict:
    if type(value) is not dict or value.get("record_type") not in ROW_FIELDS:
        refuse("ledger_row_unknown", "a ledger row names no known record type")
    row = read_record(value, value["record_type"], ROW_FIELDS[value["record_type"]])
    if row["record_type"] in (DISPATCH_RECORD, CALL_RECORD, VERDICT_RECORD) and \
            row["request_record_type"] not in REVIEW_SUBJECTS:
        refuse("review_subject_unsupported", "the ledger row names an unsupported review subject version")
    if row["record_type"] in (CALL_RECORD, VERDICT_RECORD, BATCH_CALL_RECORD) and type(row["reported_model"]) is not str:
        refuse("reported_model_invalid", "reported model is text; empty text means unknown")
    if row["record_type"] == CALL_RECORD and row["outcome"] == "verdict" and row["reported_model"] != row["model"]:
        refuse("reviewer_identity_unverified", "a verdict requires the exact reported reviewer model")
    if row["record_type"] in (BATCH_DISPATCH_RECORD, BATCH_CALL_RECORD):
        members = _members(row)
        if row["record_type"] == BATCH_CALL_RECORD and any(member["outcome"] == "verdict" for member in members) \
                and row["reported_model"] != row["model"]:
            refuse("reviewer_identity_unverified", "a verdict requires the exact reported reviewer model")
    return row


#: What a verdict row must repeat from the call row that produced it, and from its member row in a batch.
CALL_FIELDS_A_VERDICT_REPEATS = ("installation_id", "family", "reported_model")
MEMBER_FIELDS_A_VERDICT_REPEATS = ("review_key", "identity", "body_sha256", "request_sha256", "request_record_type",
                                   "decision")


def verdict_matches_call(row: dict, call: "dict | None") -> bool:
    """Whether a verdict row is exactly the verdict its recorded, verified call produced."""
    if call is None or not row["reported_model"]:
        return False
    if call["record_type"] == BATCH_CALL_RECORD:
        member = next((part for part in call["members"] if part["review_key"] == row["review_key"]), None)
        return (member is not None and member["outcome"] == "verdict"
                and all(row[name] == member[name] for name in MEMBER_FIELDS_A_VERDICT_REPEATS)
                and all(row[name] == call[name] for name in CALL_FIELDS_A_VERDICT_REPEATS))
    return call["outcome"] == "verdict" and all(row[name] == call[name] for name in (
        "review_key", "installation_id", "family", "identity", "body_sha256", "request_sha256",
        "request_record_type", "reported_model", "decision"))


class ReviewLedger:
    """One ledger file. Appends are serialised, flushed and synced before the append returns."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self._rows, self._verdicts, self._dispatched, self._completed = [], {}, {}, set()
        self._run_ids = set()
        self._call_rows = {}
        if self.path.is_symlink():
            refuse("ledger_unsafe", "the ledger path is a link")
        if self.path.exists():
            data = self.path.read_bytes()
            if data and not data.endswith(b"\n"):
                refuse("ledger_truncated", "the last ledger line was not completed; inspect the ledger before resuming")
            for number, line in enumerate(data.decode("utf-8").splitlines(), 1):
                try:
                    value = json.loads(line)
                except ValueError:
                    refuse("ledger_row_unreadable", f"line {number} of the ledger is not JSON")
                self._index(read_row(value))

    def _run_identity_is_new(self, row: dict) -> None:
        """Refuse a run row whose identity the ledger already holds. A mutant control removes this guard."""
        if row["record_type"] == RUN_RECORD and row["run_id"] in self._run_ids:
            refuse("run_identity_repeated", f"the ledger already holds a run named {row['run_id']!r}; "
                                            "a new run needs a new identity")

    def _index(self, row: dict) -> None:
        self._run_identity_is_new(row)
        self._rows.append(row)
        kind = row["record_type"]
        if kind == RUN_RECORD:
            self._run_ids.add(row["run_id"])
        elif kind == DISPATCH_RECORD:
            self._dispatched.setdefault(row["review_key"], []).append(row)
        elif kind == BATCH_DISPATCH_RECORD:
            for member in row["members"]:
                self._dispatched.setdefault(member["review_key"], []).append(row)
        elif kind in (CALL_RECORD, BATCH_CALL_RECORD):
            self._completed.add((row["run_id"], row["sequence"]))
            self._call_rows[(row["run_id"], row["sequence"])] = row
        elif kind == VERDICT_RECORD:
            call = self._call_rows.get((row["run_id"], row["sequence"]))
            if not verdict_matches_call(row, call):
                refuse("verdict_without_verified_call", "a reusable verdict needs its exact verified model call")
            self._verdicts.setdefault(row["review_key"], row)

    def _append(self, rows) -> None:
        payload = b"".join(canonical_bytes(read_row(row)) + b"\n" for row in rows)
        with self._lock:
            for row in rows:
                self._run_identity_is_new(row)
            descriptor = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
                                 0o600)
            try:
                os.write(descriptor, payload)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            for row in rows:
                self._index(row)

    def start_run(self, row: dict) -> None:
        self._append([row])

    def end_run(self, row: dict) -> None:
        self._append([row])

    def dispatch(self, row: dict) -> None:
        self._append([row])

    def complete(self, call_row: dict, verdict_row: "dict | None" = None) -> None:
        self._append([call_row] + ([verdict_row] if verdict_row is not None else []))

    def complete_batch(self, call_row: dict, verdict_rows) -> None:
        """One batch call row and the verdict row of every member that gave one, written together."""
        self._append([call_row] + list(verdict_rows))

    def verdict(self, review_key: str) -> "dict | None":
        return self._verdicts.get(review_key)

    def interrupted(self, review_key: str) -> bool:
        """A dispatch for this key that never received its call row."""
        return any((row["run_id"], row["sequence"]) not in self._completed
                   for row in self._dispatched.get(review_key, ()))

    def dispatches(self) -> list:
        return [row for row in self._rows if row["record_type"] == DISPATCH_RECORD]

    def interrupted_dispatches(self) -> list:
        """Every dispatch that never received its call row: a call whose outcome and usage are unknown."""
        return [row for row in self.dispatches() if (row["run_id"], row["sequence"]) not in self._completed]

    def calls(self) -> list:
        return [row for row in self._rows if row["record_type"] == CALL_RECORD]

    def batch_calls(self) -> list:
        return [row for row in self._rows if row["record_type"] == BATCH_CALL_RECORD]

    def interrupted_batch_dispatches(self) -> list:
        """Every batch dispatch that never received its call row."""
        return [row for row in self._rows if row["record_type"] == BATCH_DISPATCH_RECORD
                and (row["run_id"], row["sequence"]) not in self._completed]

    def verdicts(self) -> list:
        return [row for row in self._rows if row["record_type"] == VERDICT_RECORD]

    def runs(self) -> list:
        return [row for row in self._rows if row["record_type"] == RUN_RECORD]

    def run_ends(self) -> list:
        return [row for row in self._rows if row["record_type"] == RUN_END_RECORD]
