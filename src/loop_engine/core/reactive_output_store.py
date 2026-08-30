"""Durable append-only serving for reactive Loop outputs.

The store persists candidate metadata, independent evaluations, and immutable
portfolio snapshots.  Candidate payload bodies remain behind ``LoopValueRef``
and the storage-neutral information resolver.  Reading a portfolio never
reactivates its producer.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from ..loop.reactive_contracts import CandidateVerdict
from ..loop.reactive_outputs import (
    CandidateEvaluation, CandidateOutput, OutputPortfolioSnapshot, OutputQuery,
    PortfolioEntry)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS reactive_candidates (
    candidate_id TEXT PRIMARY KEY,
    series_id TEXT NOT NULL,
    topic_ref TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    record_digest TEXT NOT NULL,
    body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reactive_evaluations (
    evaluation_id TEXT PRIMARY KEY,
    candidate_ref TEXT NOT NULL,
    evaluated_at TEXT NOT NULL,
    record_digest TEXT NOT NULL,
    body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reactive_portfolios (
    series_id TEXT NOT NULL,
    topic_ref TEXT NOT NULL,
    view TEXT NOT NULL,
    portfolio_version INTEGER NOT NULL,
    generated_at TEXT NOT NULL,
    record_digest TEXT NOT NULL,
    body TEXT NOT NULL,
    PRIMARY KEY (series_id, topic_ref, view, portfolio_version)
);
CREATE INDEX IF NOT EXISTS reactive_candidate_topic
ON reactive_candidates(series_id, topic_ref, generated_at);
CREATE INDEX IF NOT EXISTS reactive_evaluation_candidate
ON reactive_evaluations(candidate_ref, evaluated_at);
"""


class ReactiveOutputStoreError(RuntimeError):
    """A durable candidate, evaluation, or portfolio invariant failed."""


def _canonical(value: dict) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False)


def _digest(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class OutputQueryResult:
    """One read-only portfolio projection and its selected record metadata."""

    query: OutputQuery
    snapshot: OutputPortfolioSnapshot
    entries: tuple[PortfolioEntry, ...]
    candidates: tuple[CandidateOutput, ...]
    evaluations: tuple[CandidateEvaluation, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.query, OutputQuery):
            raise ReactiveOutputStoreError("query result needs OutputQuery")
        if not isinstance(self.snapshot, OutputPortfolioSnapshot):
            raise ReactiveOutputStoreError(
                "query result needs OutputPortfolioSnapshot")
        candidate_ids = {item.candidate_id for item in self.candidates}
        evaluation_ids = {item.evaluation_id for item in self.evaluations}
        if any(item.candidate_ref not in candidate_ids
               or (item.evaluation_ref
                   and item.evaluation_ref not in evaluation_ids)
               for item in self.entries):
            raise ReactiveOutputStoreError(
                "query result metadata does not cover selected entries")


class SQLiteReactiveOutputStore:
    """SQLite WAL store for immutable reactive output records."""

    def __init__(self, database_path: str, observations=None) -> None:
        from .runtime_observer import RuntimeObservationServices
        if not isinstance(database_path, str) or not database_path.strip():
            raise ReactiveOutputStoreError(
                "reactive output store requires an explicit path")
        path = Path(database_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.database_path = str(path)
        self._connection = sqlite3.connect(self.database_path, timeout=5.0)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.executescript(_SCHEMA)
        self._connection.commit()
        self._observations = observations or RuntimeObservationServices()

    def append_candidate(self, candidate: CandidateOutput) -> None:
        """Append one immutable candidate or accept an identical replay."""
        if not isinstance(candidate, CandidateOutput):
            raise ReactiveOutputStoreError(
                "append_candidate requires CandidateOutput")
        body = _canonical(candidate.to_dict())
        digest = _digest(body)
        existing = self._connection.execute(
            "SELECT record_digest, body FROM reactive_candidates "
            "WHERE candidate_id = ?", (candidate.candidate_id,)).fetchone()
        if existing is not None:
            if tuple(existing) != (digest, body):
                raise ReactiveOutputStoreError(
                    "candidate identity cannot be reused for changed content")
            return
        self._connection.execute(
            "INSERT INTO reactive_candidates VALUES (?, ?, ?, ?, ?, ?)",
            (candidate.candidate_id, candidate.series_id, candidate.topic_ref,
             candidate.generated_at, digest, body))
        self._connection.commit()
        from .runtime_observer import RuntimeObservation
        self._observations.emit(RuntimeObservation(
            "reactive_candidate_stored", {
                "series_id": candidate.series_id,
                "candidate_id": candidate.candidate_id,
                "producer_loop_id": candidate.producer_loop_id,
                "payload_digest": candidate.payload_ref.content_digest,
                "status": "stored",
            }, loop_id=candidate.producer_loop_id))

    def append_evaluation(self, evaluation: CandidateEvaluation) -> None:
        """Append one evaluation after checking candidate and verifier identity."""
        if not isinstance(evaluation, CandidateEvaluation):
            raise ReactiveOutputStoreError(
                "append_evaluation requires CandidateEvaluation")
        candidate = self.get_candidate(evaluation.candidate_ref)
        if candidate is None:
            raise ReactiveOutputStoreError(
                "evaluation references an unknown candidate")
        if (evaluation.verdict is CandidateVerdict.VERIFIED
                and set(evaluation.evaluator_loop_refs)
                == {candidate.producer_loop_id}):
            raise ReactiveOutputStoreError(
                "a candidate producer cannot be its sole verifier")
        body = _canonical(evaluation.to_dict())
        digest = _digest(body)
        existing = self._connection.execute(
            "SELECT record_digest, body FROM reactive_evaluations "
            "WHERE evaluation_id = ?",
            (evaluation.evaluation_id,)).fetchone()
        if existing is not None:
            if tuple(existing) != (digest, body):
                raise ReactiveOutputStoreError(
                    "evaluation identity cannot be reused for changed content")
            return
        self._connection.execute(
            "INSERT INTO reactive_evaluations VALUES (?, ?, ?, ?, ?)",
            (evaluation.evaluation_id, evaluation.candidate_ref,
             evaluation.evaluated_at, digest, body))
        self._connection.commit()
        from .runtime_observer import RuntimeObservation
        self._observations.emit(RuntimeObservation(
            "reactive_evaluation_stored", {
                "evaluation_id": evaluation.evaluation_id,
                "candidate_id": evaluation.candidate_ref,
                "verifier_count": len(evaluation.evaluator_loop_refs),
                "verdict": evaluation.verdict.value, "status": "stored",
            }, loop_id=evaluation.evaluator_loop_refs[0]))

    def append_portfolio(self, snapshot: OutputPortfolioSnapshot) -> None:
        """Append one contiguous portfolio version or accept an exact replay."""
        if not isinstance(snapshot, OutputPortfolioSnapshot):
            raise ReactiveOutputStoreError(
                "append_portfolio requires OutputPortfolioSnapshot")
        self._validate_snapshot_refs(snapshot)
        body = _canonical(snapshot.to_dict())
        digest = _digest(body)
        key = (snapshot.series_id, snapshot.topic_ref, snapshot.view.value,
               snapshot.portfolio_version)
        existing = self._connection.execute(
            "SELECT record_digest, body FROM reactive_portfolios "
            "WHERE series_id = ? AND topic_ref = ? AND view = ? "
            "AND portfolio_version = ?", key).fetchone()
        if existing is not None:
            if tuple(existing) != (digest, body):
                raise ReactiveOutputStoreError(
                    "portfolio version cannot be rewritten")
            return
        previous = self._connection.execute(
            "SELECT MAX(portfolio_version) FROM reactive_portfolios "
            "WHERE series_id = ? AND topic_ref = ? AND view = ?",
            key[:3]).fetchone()[0]
        expected = 1 if previous is None else int(previous) + 1
        if snapshot.portfolio_version != expected:
            raise ReactiveOutputStoreError(
                f"portfolio version must be contiguous; expected {expected}")
        self._connection.execute(
            "INSERT INTO reactive_portfolios VALUES (?, ?, ?, ?, ?, ?, ?)",
            (*key, snapshot.generated_at, digest, body))
        self._connection.commit()
        from .runtime_observer import RuntimeObservation
        self._observations.emit(RuntimeObservation(
            "reactive_portfolio_stored", {
                "series_id": snapshot.series_id,
                "topic_ref": snapshot.topic_ref,
                "portfolio_version": snapshot.portfolio_version,
                "view": snapshot.view.value,
                "candidate_count": len(snapshot.entries),
                "status": "stored",
            }))

    def get_candidate(self, candidate_id: str) -> CandidateOutput | None:
        row = self._connection.execute(
            "SELECT record_digest, body FROM reactive_candidates "
            "WHERE candidate_id = ?", (candidate_id,)).fetchone()
        if row is None:
            return None
        body = self._verified_body(row, "candidate")
        return CandidateOutput.from_dict(json.loads(body))

    def get_evaluation(
            self, evaluation_id: str) -> CandidateEvaluation | None:
        row = self._connection.execute(
            "SELECT record_digest, body FROM reactive_evaluations "
            "WHERE evaluation_id = ?", (evaluation_id,)).fetchone()
        if row is None:
            return None
        body = self._verified_body(row, "evaluation")
        return CandidateEvaluation.from_dict(json.loads(body))

    def query(self, query: OutputQuery) -> OutputQueryResult:
        """Read current or historical output metadata without running a Loop."""
        if not isinstance(query, OutputQuery):
            raise ReactiveOutputStoreError("query requires OutputQuery")
        version = query.as_of_portfolio_version
        if version is None:
            row = self._connection.execute(
                "SELECT record_digest, body FROM reactive_portfolios "
                "WHERE series_id = ? AND topic_ref = ? AND view = ? "
                "ORDER BY portfolio_version DESC LIMIT 1",
                (query.series_id, query.topic_ref, query.view.value)).fetchone()
        else:
            row = self._connection.execute(
                "SELECT record_digest, body FROM reactive_portfolios "
                "WHERE series_id = ? AND topic_ref = ? AND view = ? "
                "AND portfolio_version = ?",
                (query.series_id, query.topic_ref, query.view.value,
                 version)).fetchone()
        if row is None:
            raise ReactiveOutputStoreError(
                "requested output portfolio is unavailable")
        body = self._verified_body(row, "portfolio")
        snapshot = OutputPortfolioSnapshot.from_dict(json.loads(body))
        entries = tuple(
            item for item in snapshot.entries
            if item.derived_score >= query.minimum_derived_score
        )[:query.maximum_results]
        candidates = tuple(
            self._require_candidate(item.candidate_ref) for item in entries)
        evaluations = tuple(
            self._require_evaluation(item.evaluation_ref) for item in entries
            if item.evaluation_ref)
        return OutputQueryResult(
            query, snapshot, entries, candidates, evaluations)

    def portfolio_history(
            self, query: OutputQuery) -> tuple[OutputPortfolioSnapshot, ...]:
        """Return every verified stored snapshot for one exact view."""
        if not isinstance(query, OutputQuery):
            raise ReactiveOutputStoreError(
                "portfolio_history requires OutputQuery")
        rows = self._connection.execute(
            "SELECT record_digest, body FROM reactive_portfolios "
            "WHERE series_id = ? AND topic_ref = ? AND view = ? "
            "ORDER BY portfolio_version",
            (query.series_id, query.topic_ref, query.view.value)).fetchall()
        return tuple(OutputPortfolioSnapshot.from_dict(json.loads(
            self._verified_body(row, "portfolio"))) for row in rows)

    def _validate_snapshot_refs(
            self, snapshot: OutputPortfolioSnapshot) -> None:
        candidates = {
            item.candidate_ref: self.get_candidate(item.candidate_ref)
            for item in snapshot.entries}
        evaluations = {
            item.evaluation_ref: self.get_evaluation(item.evaluation_ref)
            for item in snapshot.entries if item.evaluation_ref}
        if any(value is None for value in candidates.values()) \
                or any(value is None for value in evaluations.values()):
            raise ReactiveOutputStoreError(
                "portfolio references unavailable candidate or evaluation")
        for entry in snapshot.entries:
            evaluation = (evaluations[entry.evaluation_ref]
                          if entry.evaluation_ref else None)
            if (evaluation is not None
                    and evaluation.candidate_ref != entry.candidate_ref):
                raise ReactiveOutputStoreError(
                    "portfolio evaluation belongs to another candidate")

    @staticmethod
    def _verified_body(row, label: str) -> str:
        digest, body = row
        if _digest(body) != digest:
            raise ReactiveOutputStoreError(
                f"stored {label} failed digest verification")
        return body

    def _require_candidate(self, candidate_id: str) -> CandidateOutput:
        candidate = self.get_candidate(candidate_id)
        if candidate is None:
            raise ReactiveOutputStoreError(
                "portfolio candidate disappeared")
        return candidate

    def _require_evaluation(self, evaluation_id: str) -> CandidateEvaluation:
        evaluation = self.get_evaluation(evaluation_id)
        if evaluation is None:
            raise ReactiveOutputStoreError(
                "portfolio evaluation disappeared")
        return evaluation

    def close(self) -> None:
        self._connection.close()


__all__ = (
    "OutputQueryResult", "ReactiveOutputStoreError",
    "SQLiteReactiveOutputStore",
)
