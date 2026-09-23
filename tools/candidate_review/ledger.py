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
    CALL_RECORD, DISPATCH_RECORD, RUN_END_RECORD, RUN_RECORD, VERDICT_RECORD, canonical_bytes, read_record, refuse,
)

RUN_FIELDS = ("run_id", "started_at", "policy_sha256", "call_ceiling", "token_ceiling", "fixture_run", "requests")
RUN_END_FIELDS = ("run_id", "finished_at", "stop_reason", "elapsed_seconds", "calls", "items", "pause_seconds")
DISPATCH_FIELDS = ("run_id", "sequence", "review_key", "installation_id", "identity", "body_sha256",
                   "request_sha256", "dispatched_at")
CALL_FIELDS = ("run_id", "sequence", "review_key", "installation_id", "installation_sha256", "engine_kind", "family",
               "model", "model_version", "engine_version", "route_or_command", "identity", "body_sha256",
               "request_sha256", "prompt_sha256", "started_at", "elapsed_seconds", "outcome", "error_code",
               "decision", "invalid_answer_excerpt", "physical_model_calls", "physical_calls_basis", "usage",
               "reserved_tokens", "charged_tokens", "charge_basis", "retry_after_seconds", "pause_seconds_after")
VERDICT_FIELDS = ("run_id", "sequence", "review_key", "installation_id", "family", "identity", "body_sha256",
                  "request_sha256", "decision", "findings", "reasons")
ROW_FIELDS = {RUN_RECORD: RUN_FIELDS, RUN_END_RECORD: RUN_END_FIELDS, DISPATCH_RECORD: DISPATCH_FIELDS,
              CALL_RECORD: CALL_FIELDS, VERDICT_RECORD: VERDICT_FIELDS}


def read_row(value) -> dict:
    if type(value) is not dict or value.get("record_type") not in ROW_FIELDS:
        refuse("ledger_row_unknown", "a ledger row names no known record type")
    return read_record(value, value["record_type"], ROW_FIELDS[value["record_type"]])


class ReviewLedger:
    """One ledger file. Appends are serialised, flushed and synced before the append returns."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self._rows, self._verdicts, self._dispatched, self._completed = [], {}, {}, set()
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

    def _index(self, row: dict) -> None:
        self._rows.append(row)
        kind = row["record_type"]
        if kind == DISPATCH_RECORD:
            self._dispatched.setdefault(row["review_key"], []).append(row)
        elif kind == CALL_RECORD:
            self._completed.add((row["run_id"], row["sequence"]))
        elif kind == VERDICT_RECORD:
            self._verdicts.setdefault(row["review_key"], row)

    def _append(self, rows) -> None:
        payload = b"".join(canonical_bytes(read_row(row)) + b"\n" for row in rows)
        with self._lock:
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

    def verdicts(self) -> list:
        return [row for row in self._rows if row["record_type"] == VERDICT_RECORD]

    def runs(self) -> list:
        return [row for row in self._rows if row["record_type"] == RUN_RECORD]

    def run_ends(self) -> list:
        return [row for row in self._rows if row["record_type"] == RUN_END_RECORD]
