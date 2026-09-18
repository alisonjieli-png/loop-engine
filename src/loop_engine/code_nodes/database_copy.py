"""Copy a table with corrections and a dedupe proposal applied, never in place.

The last member of the detection and correction family turns decisions into
data without touching the source. A source is a delimited file or a SQLite
table; a target is a new SQLite table or a new delimited file, refused when
it already exists or when it is the source. Column corrections are the same
typed operations text conformance and field recovery return, and only a
correction in the applied band changes a value: held and escalated values
are copied unchanged and counted, so a reviewer sees exactly what was left
alone. A dedupe proposal drops the merged identities and keeps the
survivors. The copy manifest records the source digest before and after,
the rows in, out, and dropped, and the corrections per column; the source
digest must not change during the copy. The module grants no authority and
never deletes.
"""
from __future__ import annotations

import csv
import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .text_conformance_operations import (
    DEFAULT_APPLY_AT_OR_ABOVE, DEFAULT_ESCALATE_BELOW, OUTCOMES, classify,
)

MANIFEST_RECORD_TYPE = "database_copy_manifest/v1"
SOURCE_KINDS = ("delimited", "sqlite")
_IDENTIFIER_CHARACTERS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")


class DatabaseCopyError(ValueError):
    """A source, target, correction, or proposal is invalid."""


def _identifier(name: str) -> str:
    if not name or any(character not in _IDENTIFIER_CHARACTERS for character in name) or name[0].isdigit():
        raise DatabaseCopyError(f"{name!r} is not a plain table or column name")
    return name


@dataclass(frozen=True)
class TableLocation:
    """A delimited file, or a table inside a SQLite database file."""

    path: str
    table: str = ""
    delimiter: str = ","

    def __post_init__(self):
        if not isinstance(self.path, str) or not self.path.strip():
            raise DatabaseCopyError("a table location needs a path")
        if not isinstance(self.table, str) or not isinstance(self.delimiter, str) or len(self.delimiter) != 1:
            raise DatabaseCopyError("a table location needs text fields and a one-character delimiter")
        if self.table:
            _identifier(self.table)

    @property
    def kind(self) -> str:
        return SOURCE_KINDS[1] if self.table else SOURCE_KINDS[0]

    def same_as(self, other: "TableLocation") -> bool:
        return Path(self.path).resolve() == Path(other.path).resolve() and self.table == other.table

    def to_dict(self) -> dict:
        return {"path": self.path, "table": self.table, "kind": self.kind}


@dataclass(frozen=True)
class ColumnCorrection:
    """One column and the operation that returns a typed correction for a value."""

    column: str
    operation: object
    apply_at_or_above: float = DEFAULT_APPLY_AT_OR_ABOVE
    escalate_below: float = DEFAULT_ESCALATE_BELOW

    def __post_init__(self):
        _identifier(self.column)
        if not callable(self.operation):
            raise DatabaseCopyError("a column correction needs a callable operation")
        for name in ("apply_at_or_above", "escalate_below"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not 0 <= value <= 1:
                raise DatabaseCopyError(f"{name} must be a number from 0 to 1")
        if self.escalate_below > self.apply_at_or_above:
            raise DatabaseCopyError("escalate_below cannot exceed apply_at_or_above")


def _digest_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_rows(location: TableLocation) -> tuple[list[str], list[dict]]:
    """Column names and rows as mappings, from a delimited file or a SQLite table."""
    if location.kind == SOURCE_KINDS[0]:
        with open(location.path, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter=location.delimiter)
            columns = list(reader.fieldnames or [])
            return columns, [dict(row) for row in reader]
    connection = sqlite3.connect(location.path)
    try:
        cursor = connection.execute(f'SELECT * FROM "{location.table}"')
        columns = [item[0] for item in cursor.description]
        return columns, [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        connection.close()


def _write_rows(location: TableLocation, columns, rows) -> None:
    if location.kind == SOURCE_KINDS[0]:
        with open(location.path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, delimiter=location.delimiter)
            writer.writeheader()
            writer.writerows(rows)
        return
    connection = sqlite3.connect(location.path)
    try:
        quoted = ", ".join(f'"{_identifier(column)}"' for column in columns)
        connection.execute(f'CREATE TABLE "{location.table}" ({quoted})')
        connection.executemany(
            f'INSERT INTO "{location.table}" VALUES ({", ".join("?" for _ in columns)})',
            [tuple(row.get(column) for column in columns) for row in rows])
        connection.commit()
    finally:
        connection.close()


def _target_exists(location: TableLocation) -> bool:
    if location.kind == SOURCE_KINDS[0]:
        return Path(location.path).exists()
    if not Path(location.path).exists():
        return False
    connection = sqlite3.connect(location.path)
    try:
        found = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (location.table,)).fetchone()
        return found is not None
    finally:
        connection.close()


def _row_identity(row: dict, identity_column: str, index: int) -> str:
    if identity_column and str(row.get(identity_column, "")).strip():
        return str(row[identity_column])
    return f"row:{index}"


def copy_table(source: TableLocation, target: TableLocation, *, corrections=(),
               proposal=None, identity_column: str = "") -> dict:
    """Copy the source to a new target with applied corrections and dropped merges."""
    if not isinstance(source, TableLocation) or not isinstance(target, TableLocation):
        raise DatabaseCopyError("copy needs typed source and target locations")
    if source.same_as(target):
        raise DatabaseCopyError("the target must not be the source; a copy is never in place")
    if _target_exists(target):
        raise DatabaseCopyError("the target already exists; a copy never overwrites")
    corrections = tuple(corrections)
    if any(not isinstance(item, ColumnCorrection) for item in corrections):
        raise DatabaseCopyError("corrections must be typed ColumnCorrection records")
    if identity_column:
        _identifier(identity_column)
    dropped = set()
    if proposal is not None:
        merges = getattr(proposal, "merges", None)
        if merges is None:
            raise DatabaseCopyError("a proposal must carry its merges")
        for merge in merges:
            dropped.update(merge.get("merged", ()))
    before = _digest_file(source.path)
    columns, rows = read_rows(source)
    missing = [item.column for item in corrections if item.column not in columns]
    if missing:
        raise DatabaseCopyError(f"corrected columns absent from the source: {missing}")
    counts = {item.column: {outcome: 0 for outcome in OUTCOMES} for item in corrections}
    kept, dropped_identities = [], []
    for index, row in enumerate(rows):
        identity = _row_identity(row, identity_column, index)
        if identity in dropped:
            dropped_identities.append(identity)
            continue
        copied = dict(row)
        for item in corrections:
            value = "" if copied.get(item.column) is None else str(copied[item.column])
            result = item.operation(value)
            outcome = classify(result["confidence"], result["changed"],
                               item.apply_at_or_above, item.escalate_below)
            counts[item.column][outcome] += 1
            if outcome == OUTCOMES[0]:
                copied[item.column] = result["output"]
        kept.append(copied)
    _write_rows(target, columns, kept)
    after = _digest_file(source.path)
    if after != before:
        raise DatabaseCopyError("the source changed during the copy; the manifest cannot vouch for it")
    return {"record_type": MANIFEST_RECORD_TYPE, "source": {**source.to_dict(), "digest": before},
            "target": {**target.to_dict(), "digest": _digest_file(target.path)},
            "columns": columns, "rows_in": len(rows), "rows_out": len(kept),
            "rows_dropped": dropped_identities, "corrections": counts, "in_place": False}


def self_test() -> dict:
    """Copies from and to files and tables, applied bands only, drops, refusals, and digests."""
    import tempfile
    from types import SimpleNamespace
    from .field_recovery import recover_email
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refusal(action) -> str:
        """The typed refusal text, empty when the action ran or failed some other way."""
        try:
            action()
        except DatabaseCopyError as exc:
            return str(exc)
        except Exception:  # noqa: BLE001  (a crash is not a typed refusal)
            return ""
        return ""

    def refuses(action):
        return bool(refusal(action))

    with tempfile.TemporaryDirectory(prefix="loop-database-copy-") as folder:
        root = Path(folder)
        source = TableLocation(str(root / "contacts.csv"))
        with open(source.path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["id", "company", "email"])
            writer.writeheader()
            writer.writerows([
                {"id": "a", "company": "Acme", "email": "sales at acme dot example"},
                {"id": "b", "company": "Beta", "email": "maria@gmail.co"},
                {"id": "c", "company": "Gamma", "email": "ops@beta.example; x@beta.example"},
                {"id": "d", "company": "Delta", "email": "hello@gamma.example"},
                {"id": "e", "company": "Acme Inc", "email": "sales@acme.example"}])
        source_digest = _digest_file(source.path)
        proposal = SimpleNamespace(merges=[{"survivor": "a", "merged": ["e"]}])
        target = TableLocation(str(root / "copy.sqlite"), "contacts_clean")
        manifest = copy_table(source, target, corrections=(ColumnCorrection("email", recover_email),),
                              proposal=proposal, identity_column="id")
        columns, rows = read_rows(target)
        by_id = {row["id"]: row for row in rows}
        check("a_copy_applies_only_applied_corrections_and_leaves_held_and_escalated_values_alone",
              columns == ["id", "company", "email"] and by_id["a"]["email"] == "sales@acme.example"
              and by_id["b"]["email"] == "maria@gmail.co"
              and by_id["c"]["email"] == "ops@beta.example; x@beta.example"
              and by_id["d"]["email"] == "hello@gamma.example"
              and manifest["corrections"]["email"][OUTCOMES[0]] == 1
              and manifest["corrections"]["email"][OUTCOMES[1]] == 1
              and manifest["corrections"]["email"][OUTCOMES[2]] == 1
              and manifest["corrections"]["email"][OUTCOMES[3]] == 1)
        check("a_dedupe_proposal_drops_the_merged_identities_and_keeps_the_survivors",
              "e" not in by_id and manifest["rows_dropped"] == ["e"] and manifest["rows_in"] == 5
              and manifest["rows_out"] == 4 and len(rows) == 4)
        check("the_source_is_untouched_and_the_manifest_carries_both_digests",
              _digest_file(source.path) == source_digest
              and manifest["source"]["digest"] == source_digest
              and manifest["target"]["digest"] == _digest_file(target.path)
              and manifest["in_place"] is False and manifest["record_type"] == MANIFEST_RECORD_TYPE)
        check("a_copy_never_overwrites_and_never_targets_its_source",
              "never overwrites" in refusal(lambda: copy_table(source, target))
              and "never in place" in refusal(lambda: copy_table(source, TableLocation(source.path)))
              and refuses(lambda: copy_table(source, TableLocation(str(root / "other.csv")),
                                             corrections=(ColumnCorrection("phone", recover_email),)))
              and refuses(lambda: copy_table(source, TableLocation(str(root / "other.csv")),
                                             proposal=SimpleNamespace()))
              and refuses(lambda: ColumnCorrection("email", "not callable"))
              and refuses(lambda: TableLocation(str(root / "x.sqlite"), "bad name"))
              and refuses(lambda: TableLocation("")))
        back = TableLocation(str(root / "round_trip.csv"))
        round_trip = copy_table(target, back)
        _columns, again = read_rows(back)
        check("a_table_copies_back_to_a_delimited_file_with_the_same_rows",
              round_trip["rows_in"] == 4 and round_trip["rows_out"] == 4
              and [row["id"] for row in again] == ["a", "b", "c", "d"]
              and again[0]["email"] == "sales@acme.example" and round_trip["rows_dropped"] == [])
        unchanged = copy_table(source, TableLocation(str(root / "plain.csv")))
        check("a_copy_without_corrections_or_a_proposal_copies_every_row_unchanged",
              unchanged["rows_in"] == unchanged["rows_out"] == 5 and unchanged["corrections"] == {}
              and read_rows(TableLocation(str(root / "plain.csv")))[1] == read_rows(source)[1])
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "database_copy_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
