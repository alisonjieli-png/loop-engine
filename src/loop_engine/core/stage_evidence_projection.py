"""SQLite projection of stage evidence carried by canonical Run History.

The database in this module is deliberately not an authority.  Its rows are a
query-efficient projection of immutable, hash-chained ``RunHistory`` events.
Deleting the database loses an index, not evidence: replaying the same source
histories rebuilds the same rows.

Only events whose detail contains ``custom_kind`` equal to
``stage_evidence_projection_source`` are projected.  A record cannot be written
directly, which keeps the source event, its digest, and its history head attached
to every row.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .stage_assistance_experiment import (
    STAGE_EXPERIMENT_ASSIGNMENT_SCHEMA_VERSION,
    STAGE_PACKET_EVENT_KIND,
    PairedStageAssistanceTrial,
    StageAssistanceExperimentSpec,
    StageExperimentAssignment,
)
from .stage_evidence_records import (
    ADVISORY,
    FRESH,
    FRESH_CONTEXT_POLICY,
    STAGE_ASSISTANCE_DECISION_SCHEMA_VERSION,
    STAGE_EXPOSURE_MANIFEST_SCHEMA_VERSION,
    STAGE_OCCURRENCE_SCHEMA_VERSION,
    STAGE_RETRIEVAL_SNAPSHOT_SCHEMA_VERSION,
    EvidenceNamespace,
    StageAssistanceDecision,
    StageExposureManifest,
    StageOccurrenceIdentity,
    StageRetrievalCandidate,
    StageRetrievalSnapshot,
    StageTrialOutcome,
    record_from_dict,
    record_ref,
    validate_decision_against_exposure,
)
from .stage_evidence_temporal import (
    occurrence_source_error,
    rebuild_temporal_error,
)

PROJECTION_SCHEMA_VERSION = 1
PROJECTION_AUTHORITY = "rebuildable_projection"
PROJECTION_EVENT_KIND = "stage_evidence_projection_source"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS stage_evidence_records (
    namespace_key TEXT NOT NULL,
    record_ref TEXT NOT NULL,
    record_type TEXT NOT NULL,
    content_digest TEXT NOT NULL,
    occurrence_ref TEXT NOT NULL,
    semantic_signature TEXT NOT NULL,
    source_run_id TEXT NOT NULL,
    source_sequence INTEGER NOT NULL,
    source_event_digest TEXT NOT NULL,
    source_history_head_digest TEXT NOT NULL,
    payload TEXT NOT NULL,
    PRIMARY KEY (namespace_key, record_ref),
    UNIQUE (namespace_key, source_event_digest)
);
CREATE INDEX IF NOT EXISTS stage_evidence_by_occurrence
    ON stage_evidence_records(namespace_key, occurrence_ref);
CREATE INDEX IF NOT EXISTS stage_evidence_by_signature
    ON stage_evidence_records(namespace_key, semantic_signature);
CREATE INDEX IF NOT EXISTS stage_evidence_by_type
    ON stage_evidence_records(namespace_key, record_type);
"""


class StageEvidenceProjectionError(ValueError):
    """Run History evidence cannot be projected without changing its meaning."""


def _canonical(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _record_from_payload(value: dict):
    """Read either a core evidence record or an experiment-owned record."""
    try:
        return record_from_dict(value)
    except ValueError as evidence_error:
        from .stage_assistance_experiment import experiment_record_from_dict
        try:
            return experiment_record_from_dict(value)
        except ValueError:
            raise evidence_error


def _record_reference(record) -> str:
    reference = getattr(record, "record_ref", "")
    if callable(reference):
        reference = reference()
    return str(reference or record_ref(record))


def _is_sha256(value: object) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(character in "0123456789abcdef"
                                   for character in text)


@dataclass(frozen=True)
class ProjectionWriteResult:
    """Observable result of projecting one record or one failed batch."""

    record_ref: str
    stored: bool
    replayed: bool
    degraded: bool
    error: str = ""
    source_event_digest: str = ""

    def __post_init__(self) -> None:
        if self.stored and self.replayed:
            raise StageEvidenceProjectionError(
                "a projection write cannot be both stored and replayed")
        if self.degraded and not self.error:
            raise StageEvidenceProjectionError(
                "a degraded projection result must name the error")
        if not self.degraded and self.error:
            raise StageEvidenceProjectionError(
                "a healthy projection result cannot carry an error")

    def to_dict(self) -> dict:
        return {
            "record_type": "stage_evidence_projection_write/v1",
            "record_ref": self.record_ref,
            "stored": self.stored,
            "replayed": self.replayed,
            "degraded": self.degraded,
            "error": self.error,
            "source_event_digest": self.source_event_digest,
            "authority": PROJECTION_AUTHORITY,
        }


def projection_event_detail(record) -> dict:
    """Return the exact custom-event detail used as projection source input."""
    payload = record.to_dict()
    return {
        "custom_kind": PROJECTION_EVENT_KIND,
        "stage_evidence_record": payload,
        "stage_evidence_record_ref": _record_reference(record),
        "stage_evidence_content_digest": getattr(
            record, "content_digest", _digest(payload)),
        "projection_authority": PROJECTION_AUTHORITY,
    }


class SQLiteStageEvidenceProjection:
    """Idempotent SQLite/WAL index rebuilt only from valid Run History.

    The adapter never grants lifecycle, execution, retrieval, or model
    authority.  Query results repeat that fact so a caller cannot mistake a
    fast lookup for an admitted intelligence record.
    """

    def __init__(self, database_path: str) -> None:
        if not isinstance(database_path, str) or not database_path.strip():
            raise StageEvidenceProjectionError(
                "stage evidence projection needs an explicit database path")
        if database_path.strip() == ":memory:":
            raise StageEvidenceProjectionError(
                "a WAL durability projection requires a file-backed database")
        path = Path(database_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.database_path = str(path)
        self._connection = sqlite3.connect(self.database_path, timeout=5.0)
        self._connection.execute("PRAGMA busy_timeout=5000")
        self._connection.execute("PRAGMA foreign_keys=ON")
        mode = str(self._connection.execute(
            "PRAGMA journal_mode=WAL").fetchone()[0]).lower()
        if mode != "wal":
            self._connection.close()
            raise StageEvidenceProjectionError(
                f"SQLite refused WAL mode and returned {mode!r}")
        self._connection.execute("PRAGMA synchronous=FULL")
        current = int(self._connection.execute(
            "PRAGMA user_version").fetchone()[0])
        if current not in (0, PROJECTION_SCHEMA_VERSION):
            self._connection.close()
            raise StageEvidenceProjectionError(
                f"unsupported stage projection schema {current}")
        self._connection.executescript(_SCHEMA)
        if current == 0:
            self._connection.execute(
                f"PRAGMA user_version={PROJECTION_SCHEMA_VERSION}")
        self._connection.commit()
        self._journal_mode = mode
        self._write_failures = 0
        self._last_error = ""
        self._last_known_count = self._count()
        self._closed = False

    @staticmethod
    def _validate_history(history) -> tuple:
        from .run_history import RunHistory

        if not isinstance(history, RunHistory):
            raise StageEvidenceProjectionError(
                "projection input must be canonical RunHistory")
        if not bool(getattr(history, "_committed", False)):
            raise StageEvidenceProjectionError(
                "only committed Run History may feed a durable projection")
        verified = history.verify_chain()
        if not verified.get("intact"):
            raise StageEvidenceProjectionError(
                "Run History digest chain is not intact")
        head = (history.event_log[-1].event_digest
                if history.event_log else "")
        if head and not _is_sha256(head):
            raise StageEvidenceProjectionError(
                "Run History head is not a SHA-256 digest")
        return tuple(history.event_log), head

    @staticmethod
    def _matching_records(history) -> tuple:
        events, head = SQLiteStageEvidenceProjection._validate_history(history)
        rows = []
        for event in events:
            detail = event.detail if isinstance(event.detail, dict) else {}
            if detail.get("custom_kind") != PROJECTION_EVENT_KIND:
                continue
            raw = detail.get("stage_evidence_record")
            if not isinstance(raw, dict):
                raise StageEvidenceProjectionError(
                    "stage evidence Run History event needs one record mapping")
            if event.run_id != history.run_id:
                raise StageEvidenceProjectionError(
                    "stage evidence event run does not match its history")
            if not event.loop_id or not any(
                    candidate.event_type == "loop_init"
                    and candidate.loop_id == event.loop_id
                    for candidate in events):
                raise StageEvidenceProjectionError(
                    "stage evidence events need an actual owning Loop init")
            if not _is_sha256(event.event_digest):
                raise StageEvidenceProjectionError(
                    "stage evidence source event lacks a SHA-256 digest")
            record = _record_from_payload(raw)
            declared_ref = str(detail.get("stage_evidence_record_ref") or "")
            declared_digest = str(
                detail.get("stage_evidence_content_digest") or "")
            if not declared_ref or declared_ref != _record_reference(record):
                raise StageEvidenceProjectionError(
                    "Run History stage record reference does not match payload")
            actual_digest = str(getattr(record, "content_digest", _digest(raw)))
            if not declared_digest or declared_digest != actual_digest:
                raise StageEvidenceProjectionError(
                    "Run History stage record digest does not match payload")
            if detail.get("projection_authority") != PROJECTION_AUTHORITY:
                raise StageEvidenceProjectionError(
                    "stage evidence source event has no projection authority")
            rows.append((record, event, head, events))
        return tuple(rows)

    @staticmethod
    def _record_occurrence_ref(record) -> str:
        if isinstance(record, StageOccurrenceIdentity):
            return record.occurrence_ref
        return str(getattr(record, "occurrence_ref", "")
                   or getattr(record, "source_occurrence_ref", "") or "")

    @staticmethod
    def _event_by_digest(events, digest: str):
        return next((item for item in events
                     if item.event_digest == digest), None)

    @staticmethod
    def _event_detail(event) -> dict:
        return event.detail if event is not None and isinstance(
            event.detail, dict) else {}

    def _record_signature(self, record, namespace: EvidenceNamespace) -> str:
        direct = str(getattr(record, "semantic_signature", "") or "")
        if direct:
            return direct
        occurrence = self._record_occurrence_ref(record)
        if not occurrence:
            return ""
        row = self._connection.execute(
            "SELECT semantic_signature FROM stage_evidence_records "
            "WHERE namespace_key = ? AND record_ref = ? AND record_type = ?",
            (namespace.namespace_key, occurrence,
             STAGE_OCCURRENCE_SCHEMA_VERSION)).fetchone()
        return str(row[0]) if row else ""

    def _require_namespace_and_occurrence(
            self, record, namespace: EvidenceNamespace, event, events) -> None:
        if isinstance(record, EvidenceNamespace):
            if record != namespace:
                raise StageEvidenceProjectionError(
                    "evidence namespace record does not match projection scope")
            return
        if isinstance(record, StageAssistanceExperimentSpec):
            return
        if isinstance(record, StageOccurrenceIdentity):
            if record.namespace != namespace:
                raise StageEvidenceProjectionError(
                    "stage occurrence namespace does not match projection scope")
            temporal_error = occurrence_source_error(record, event, events)
            if temporal_error:
                raise StageEvidenceProjectionError(temporal_error)
            return
        if isinstance(record, PairedStageAssistanceTrial):
            spec = self._load_record(
                namespace, record.experiment_ref,
                "stage_assistance_experiment/v1")
            if spec.experiment_ref != record.experiment_ref:
                raise StageEvidenceProjectionError(
                    "paired trial experiment definition is unavailable")
            for occurrence in record.occurrences:
                if occurrence.namespace != namespace:
                    raise StageEvidenceProjectionError(
                        "paired trial crosses evidence namespaces")
                stored = self._load_record(
                    namespace, occurrence.occurrence_ref,
                    STAGE_OCCURRENCE_SCHEMA_VERSION)
                if stored != occurrence:
                    raise StageEvidenceProjectionError(
                        "paired trial embeds a changed occurrence record")
            return
        occurrence = self._record_occurrence_ref(record)
        if not occurrence:
            raise StageEvidenceProjectionError(
                "a projected stage record must reference an exact occurrence")
        occurrence_source = self._connection.execute(
            "SELECT source_run_id, source_sequence FROM stage_evidence_records "
            "WHERE namespace_key = ? AND record_ref = ? AND record_type = ?",
            (namespace.namespace_key, occurrence,
             STAGE_OCCURRENCE_SCHEMA_VERSION)).fetchone()
        if occurrence_source is None:
            raise StageEvidenceProjectionError(
                f"stage record references unavailable occurrence {occurrence!r}")
        if (occurrence_source[0] == event.run_id
                and int(occurrence_source[1]) >= int(event.sequence_number)):
            raise StageEvidenceProjectionError(
                "referenced occurrence evidence must precede the dependent event")
        if isinstance(record, StageExperimentAssignment):
            self._require_assignment(record, namespace)
        if isinstance(record, StageRetrievalCandidate):
            self._require_source_occurrence(
                namespace, record.source_occurrence_ref,
                semantic_signature=record.semantic_signature,
                history_event=event)
        if isinstance(record, StageRetrievalSnapshot):
            for candidate in record.candidates:
                self._require_source_occurrence(
                    namespace, candidate.source_occurrence_ref,
                    semantic_signature=candidate.semantic_signature,
                    history_event=event)
        if isinstance(record, StageExposureManifest):
            self._require_matching_assignment(record, namespace, event, events)
        if isinstance(record, StageAssistanceDecision):
            manifest = self._load_record(
                namespace, record.exposure_manifest_ref,
                STAGE_EXPOSURE_MANIFEST_SCHEMA_VERSION)
            try:
                validate_decision_against_exposure(record, manifest)
            except ValueError as exc:
                raise StageEvidenceProjectionError(str(exc)) from exc
        if isinstance(record, StageTrialOutcome):
            self._require_outcome_links(record, namespace, event, events)

    def _require_assignment(self, assignment: StageExperimentAssignment,
                            namespace: EvidenceNamespace) -> None:
        spec = self._load_record(
            namespace, assignment.experiment_ref,
            "stage_assistance_experiment/v1")
        trial = self._load_record(
            namespace, assignment.trial_ref,
            "paired_stage_assistance_trial/v1")
        occurrence = self._load_record(
            namespace, assignment.occurrence_ref,
            STAGE_OCCURRENCE_SCHEMA_VERSION)
        trial_occurrences = {item.occurrence_ref for item in trial.occurrences}
        if (trial.experiment_ref != spec.experiment_ref
                or assignment.experiment_ref != spec.experiment_ref
                or assignment.campaign_seed != spec.campaign_seed
                or assignment.occurrence_ref not in trial_occurrences
                or assignment.semantic_signature != trial.semantic_signature
                or assignment.semantic_signature
                != occurrence.semantic_signature):
            raise StageEvidenceProjectionError(
                "assignment conflicts with its experiment, trial, or occurrence")
        rows = self._connection.execute(
            "SELECT record_ref, payload FROM stage_evidence_records "
            "WHERE namespace_key = ? AND record_type = ?",
            (namespace.namespace_key,
             STAGE_EXPERIMENT_ASSIGNMENT_SCHEMA_VERSION)).fetchall()
        for record_reference, payload in rows:
            prior = _record_from_payload(json.loads(payload))
            if (prior.trial_ref == assignment.trial_ref
                    and prior.occurrence_ref == assignment.occurrence_ref
                    and record_reference != assignment.assignment_ref):
                raise StageEvidenceProjectionError(
                    "one trial occurrence cannot receive more than one arm")

    def _trial_assignments(self, namespace: EvidenceNamespace,
                           trial_ref: str) -> tuple:
        rows = self._connection.execute(
            "SELECT payload FROM stage_evidence_records "
            "WHERE namespace_key = ? AND record_type = ?",
            (namespace.namespace_key,
             STAGE_EXPERIMENT_ASSIGNMENT_SCHEMA_VERSION)).fetchall()
        return tuple(item for item in (
            _record_from_payload(json.loads(payload)) for (payload,) in rows)
            if item.trial_ref == trial_ref)

    def _require_source_occurrence(
            self, namespace: EvidenceNamespace, occurrence_ref: str, *,
            semantic_signature: str, history_event) -> None:
        source = self._connection.execute(
            "SELECT payload, source_run_id, source_sequence "
            "FROM stage_evidence_records "
            "WHERE namespace_key = ? AND record_ref = ? AND record_type = ?",
            (namespace.namespace_key, occurrence_ref,
             STAGE_OCCURRENCE_SCHEMA_VERSION)).fetchone()
        if source is None:
            raise StageEvidenceProjectionError(
                "retrieval candidate source occurrence is unavailable")
        occurrence = _record_from_payload(json.loads(source[0]))
        if occurrence.semantic_signature != semantic_signature:
            raise StageEvidenceProjectionError(
                "retrieval candidate signature differs from its source occurrence")
        if (source[1] == history_event.run_id
                and int(source[2]) >= int(history_event.sequence_number)):
            raise StageEvidenceProjectionError(
                "retrieval source evidence must precede the retrieval event")

    def _load_record(self, namespace: EvidenceNamespace, reference: str,
                     expected_type: str):
        row = self._connection.execute(
            "SELECT payload FROM stage_evidence_records "
            "WHERE namespace_key = ? AND record_ref = ? AND record_type = ?",
            (namespace.namespace_key, reference, expected_type)).fetchone()
        if row is None:
            raise StageEvidenceProjectionError(
                f"required {expected_type} reference {reference!r} is unavailable")
        return _record_from_payload(json.loads(row[0]))

    def _require_matching_assignment(
            self, manifest: StageExposureManifest,
            namespace: EvidenceNamespace, event, events) -> None:
        assignment = self._load_record(
            namespace, manifest.assignment_ref,
            STAGE_EXPERIMENT_ASSIGNMENT_SCHEMA_VERSION)
        if (assignment.occurrence_ref != manifest.occurrence_ref
                or assignment.experiment_ref != manifest.experiment_ref
                or assignment.arm != manifest.arm):
            raise StageEvidenceProjectionError(
                "exposure manifest conflicts with its exact assignment")
        trial = self._load_record(
            namespace, assignment.trial_ref,
            "paired_stage_assistance_trial/v1")
        assignments = self._trial_assignments(namespace, assignment.trial_ref)
        if (len(assignments) != 2
                or {item.arm for item in assignments} != {ADVISORY, FRESH}
                or {item.occurrence_ref for item in assignments}
                != {item.occurrence_ref for item in trial.occurrences}):
            raise StageEvidenceProjectionError(
                "paired trial needs exactly one persisted assignment per arm")
        if manifest.arm == FRESH:
            if (manifest.retrieval_snapshot_ref
                    or manifest.retrieved_prior_refs
                    or manifest.exposed_prior_refs):
                raise StageEvidenceProjectionError(
                    "fresh manifest contains prior-stage material")
        else:
            snapshot = self._load_record(
                namespace, manifest.retrieval_snapshot_ref,
                STAGE_RETRIEVAL_SNAPSHOT_SCHEMA_VERSION)
            if (snapshot.occurrence_ref != manifest.occurrence_ref
                    or snapshot.semantic_signature
                    != assignment.semantic_signature
                    or tuple(item.candidate_ref for item in snapshot.candidates)
                    != manifest.retrieved_prior_refs):
                raise StageEvidenceProjectionError(
                    "manifest conflicts with its retrieval snapshot")
            exposed = set(manifest.exposed_prior_refs)
            for candidate in snapshot.candidates:
                if candidate.candidate_ref in exposed and not all(
                        value is True for value in (
                            candidate.contract_compatible,
                            candidate.effect_compatible,
                            candidate.authority_compatible,
                            candidate.privacy_compatible)):
                    raise StageEvidenceProjectionError(
                        "exposed prior lacks proven hard compatibility")
        packet_event = self._event_by_digest(events, manifest.packet_event_ref)
        detail = self._event_detail(packet_event)
        occurrence = self._load_record(
            namespace, manifest.occurrence_ref,
            STAGE_OCCURRENCE_SCHEMA_VERSION)
        expected = {
            "custom_kind": STAGE_PACKET_EVENT_KIND,
            "packet_digest": manifest.packet_digest,
            "assignment_ref": manifest.assignment_ref,
            "retrieval_snapshot_ref": manifest.retrieval_snapshot_ref,
            "stage_prior_refs": list(manifest.exposed_prior_refs),
            "context_block_ids": list(manifest.packet_context_block_ids),
            "fresh_policy_id": FRESH_CONTEXT_POLICY,
        }
        if (packet_event is None or packet_event.event_type != "custom"
                or packet_event.loop_id != occurrence.loop_id
                or any(detail.get(key) != value
                       for key, value in expected.items())
                or packet_event.sequence_number >= event.sequence_number):
            raise StageEvidenceProjectionError(
                "manifest is not backed by the exact prior packet event")

    def _require_outcome_links(
            self, outcome: StageTrialOutcome,
            namespace: EvidenceNamespace, event, events) -> None:
        assignment = self._load_record(
            namespace, outcome.assignment_ref,
            STAGE_EXPERIMENT_ASSIGNMENT_SCHEMA_VERSION)
        manifest = self._load_record(
            namespace, outcome.exposure_manifest_ref,
            STAGE_EXPOSURE_MANIFEST_SCHEMA_VERSION)
        decision = self._load_record(
            namespace, outcome.decision_ref,
            STAGE_ASSISTANCE_DECISION_SCHEMA_VERSION)
        trial = self._load_record(
            namespace, outcome.trial_ref,
            "paired_stage_assistance_trial/v1")
        spec = self._load_record(
            namespace, outcome.experiment_ref,
            "stage_assistance_experiment/v1")
        occurrences = {
            assignment.occurrence_ref,
            manifest.occurrence_ref,
            decision.occurrence_ref,
            outcome.occurrence_ref,
        }
        if len(occurrences) != 1:
            raise StageEvidenceProjectionError(
                "trial outcome links records from different occurrences")
        if (assignment.experiment_ref != manifest.experiment_ref
                or assignment.experiment_ref != spec.experiment_ref
                or assignment.trial_ref != trial.trial_ref
                or assignment.trial_ref != outcome.trial_ref
                or assignment.experiment_ref != outcome.experiment_ref
                or assignment.arm != manifest.arm
                or assignment.arm != outcome.arm
                or manifest.assignment_ref != assignment.assignment_ref
                or decision.exposure_manifest_ref != manifest.manifest_ref):
            raise StageEvidenceProjectionError(
                "trial outcome links disagree about assignment or exposure")
        verification = self._event_by_digest(events, outcome.verification_ref)
        detail = self._event_detail(verification)
        expected = {
            "verification_contract_ref": spec.verification_contract_ref,
            "metric_ref": outcome.metric_ref,
            "metric_direction": outcome.metric_direction,
            "run_validity": outcome.run_validity,
            "verification_passed": outcome.verification_passed,
            "quality": outcome.quality,
            "cost": outcome.cost,
            "latency_seconds": outcome.latency_seconds,
            "input_tokens": outcome.input_tokens,
            "output_tokens": outcome.output_tokens,
        }
        if (verification is None or verification.event_type != "evaluation"
                or verification.loop_id != outcome.evaluator_id
                or any(detail.get(key) != value
                       for key, value in expected.items())
                or verification.sequence_number >= event.sequence_number):
            raise StageEvidenceProjectionError(
                "trial outcome has no matching evaluation event")

    def _insert(self, record, event, head: str, events,
                namespace: EvidenceNamespace) -> ProjectionWriteResult:
        self._require_namespace_and_occurrence(
            record, namespace, event, events)
        payload_value = record.to_dict()
        payload = _canonical(payload_value)
        reference = _record_reference(record)
        content_digest = str(getattr(record, "content_digest", _digest(
            payload_value)))
        record_type = str(payload_value.get("record_type")
                          or payload_value.get("schema_version") or "")
        occurrence = self._record_occurrence_ref(record)
        signature = self._record_signature(record, namespace)
        existing = self._connection.execute(
            "SELECT content_digest, payload, source_run_id, source_sequence, "
            "source_event_digest, source_history_head_digest "
            "FROM stage_evidence_records WHERE namespace_key = ? "
            "AND record_ref = ?",
            (namespace.namespace_key, reference)).fetchone()
        binding = (content_digest, payload, event.run_id,
                   int(event.sequence_number), event.event_digest, head)
        if existing is not None:
            if tuple(existing) != binding:
                raise StageEvidenceProjectionError(
                    f"record reference {reference!r} was rebound to changed "
                    "content or a different Run History event")
            return ProjectionWriteResult(
                reference, False, True, False,
                source_event_digest=event.event_digest)
        self._connection.execute(
            "INSERT INTO stage_evidence_records VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (namespace.namespace_key, reference, record_type, content_digest,
             occurrence, signature, event.run_id, int(event.sequence_number),
             event.event_digest, head, payload))
        return ProjectionWriteResult(
            reference, True, False, False,
            source_event_digest=event.event_digest)

    def _ingest_rows(self, rows: tuple,
                     namespace: EvidenceNamespace) -> tuple:
        results = []
        for record, event, head, events in rows:
            results.append(self._insert(
                record, event, head, events, namespace))
        return tuple(results)

    def ingest_run_history(self, history,
                           namespace: EvidenceNamespace) -> tuple:
        """Project one committed intact history in one atomic transaction."""
        if not isinstance(namespace, EvidenceNamespace):
            raise StageEvidenceProjectionError(
                "ingest requires an EvidenceNamespace")
        rows = self._matching_records(history)
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            results = self._ingest_rows(rows, namespace)
            self._connection.commit()
            self._last_known_count = self._count()
            return results
        except Exception:
            self._connection.rollback()
            raise

    def safe_ingest_run_history(self, history,
                                namespace: EvidenceNamespace) -> tuple:
        """Keep instrumentation failure non-fatal and return a visible result."""
        try:
            return self.ingest_run_history(history, namespace)
        except Exception as exc:  # noqa: BLE001 - this is the safety boundary
            self._write_failures += 1
            self._last_error = f"{type(exc).__name__}: {exc}"[:300]
            return (ProjectionWriteResult(
                "", False, False, True, self._last_error),)

    def rebuild(self, histories, namespace: EvidenceNamespace) -> tuple:
        """Atomically replace one namespace projection from canonical histories."""
        if not isinstance(namespace, EvidenceNamespace):
            raise StageEvidenceProjectionError(
                "rebuild requires an EvidenceNamespace")
        all_rows = []
        positioned_rows = []
        for history_index, history in enumerate(tuple(histories)):
            rows = self._matching_records(history)
            all_rows.extend(rows)
            positioned_rows.extend(
                (row, (history_index, int(row[1].sequence_number)))
                for row in rows)
        temporal_error = rebuild_temporal_error(positioned_rows)
        if temporal_error:
            raise StageEvidenceProjectionError(temporal_error)
        ranks = {
            "stage_assistance_experiment/v1": 0,
            STAGE_OCCURRENCE_SCHEMA_VERSION: 1,
            "paired_stage_assistance_trial/v1": 2,
            STAGE_EXPERIMENT_ASSIGNMENT_SCHEMA_VERSION: 3,
            STAGE_RETRIEVAL_SNAPSHOT_SCHEMA_VERSION: 4,
            STAGE_EXPOSURE_MANIFEST_SCHEMA_VERSION: 5,
            STAGE_ASSISTANCE_DECISION_SCHEMA_VERSION: 6,
            "stage_trial_outcome/v1": 7,
        }
        all_rows.sort(key=lambda row: (
            ranks.get(row[0].to_dict().get("record_type"), 4),
            row[1].run_id, row[1].sequence_number))
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            self._connection.execute(
                "DELETE FROM stage_evidence_records WHERE namespace_key = ?",
                (namespace.namespace_key,))
            results = self._ingest_rows(tuple(all_rows), namespace)
            self._connection.commit()
            self._last_known_count = self._count()
            return results
        except Exception:
            self._connection.rollback()
            raise

    def query(self, namespace: EvidenceNamespace, *, occurrence_ref: str = "",
              semantic_signature: str = "", record_type: str = "") -> dict:
        """Read an explicitly scoped projection without granting authority."""
        if not isinstance(namespace, EvidenceNamespace):
            raise StageEvidenceProjectionError(
                "query requires an EvidenceNamespace")
        clauses = ["namespace_key = ?"]
        parameters: list[object] = [namespace.namespace_key]
        for column, value in (
                ("occurrence_ref", occurrence_ref),
                ("semantic_signature", semantic_signature),
                ("record_type", record_type)):
            if value:
                clauses.append(f"{column} = ?")
                parameters.append(value)
        rows = self._connection.execute(
            "SELECT payload, source_run_id, source_sequence, "
            "source_event_digest, source_history_head_digest "
            "FROM stage_evidence_records WHERE " + " AND ".join(clauses)
            + " ORDER BY source_run_id, source_sequence, record_ref",
            tuple(parameters)).fetchall()
        records = []
        for payload, run_id, sequence, event_digest, head_digest in rows:
            records.append({
                "record": json.loads(payload),
                "source": {
                    "run_id": run_id,
                    "sequence_number": sequence,
                    "event_digest": event_digest,
                    "history_head_digest": head_digest,
                },
                "authority": PROJECTION_AUTHORITY,
                "prior_not_proof": True,
            })
        return {
            "record_type": "stage_evidence_projection_query/v1",
            "namespace": namespace.to_dict(),
            "authority": PROJECTION_AUTHORITY,
            "authoritative": False,
            "filters": {
                "occurrence_ref": occurrence_ref,
                "semantic_signature": semantic_signature,
                "record_type": record_type,
            },
            "records": records,
        }

    def _count(self) -> int:
        return int(self._connection.execute(
            "SELECT COUNT(*) FROM stage_evidence_records").fetchone()[0])

    def health(self) -> dict:
        """Report storage failure separately from an honestly empty projection."""
        error = self._last_error
        healthy = not self._closed
        count = self._last_known_count
        if not self._closed:
            try:
                count = self._count()
                self._last_known_count = count
            except sqlite3.Error as exc:
                healthy = False
                error = f"{type(exc).__name__}: {exc}"[:300]
        degraded = bool(self._write_failures or not healthy)
        return {
            "record_type": "stage_evidence_projection_health/v1",
            "healthy": healthy and not self._write_failures,
            "degraded": degraded,
            "write_failures": self._write_failures,
            "last_error": error,
            "record_count": count,
            "journal_mode": self._journal_mode,
            "schema_version": PROJECTION_SCHEMA_VERSION,
            "authority": PROJECTION_AUTHORITY,
            "authoritative": False,
            "rebuild_required": degraded,
        }

    def close(self) -> None:
        if not self._closed:
            self._connection.close()
            self._closed = True


__all__ = (
    "PROJECTION_AUTHORITY",
    "PROJECTION_EVENT_KIND",
    "PROJECTION_SCHEMA_VERSION",
    "ProjectionWriteResult",
    "SQLiteStageEvidenceProjection",
    "StageEvidenceProjectionError",
    "projection_event_detail",
)
