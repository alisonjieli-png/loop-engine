"""Immutable records for stage assistance evidence.

These records separate one exact Loop activation from reusable semantic
signatures, retrieved prior candidates, the material actually exposed to a
solver, the solver's decision, and the resulting trial outcome.  They are
passive data.  They do not retrieve intelligence, assign an experiment arm,
execute a Loop, or grant authority.

Occurrence identity has no physical-attempt field, so retries retain the same
occurrence reference and experiment assignment key.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import MISSING, dataclass, fields
from typing import Any

from .stage_evidence_values import StageEvidenceContractError
from .stage_evidence_values import stored_texts as _stored_texts
from .stage_evidence_values import unique_texts as _unique_texts

EVIDENCE_NAMESPACE_SCHEMA_VERSION = "stage_evidence_namespace/v1"
STAGE_OCCURRENCE_SCHEMA_VERSION = "stage_occurrence_identity/v1"
STAGE_RETRIEVAL_CANDIDATE_SCHEMA_VERSION = "stage_retrieval_candidate/v1"
STAGE_RETRIEVAL_SNAPSHOT_SCHEMA_VERSION = "stage_retrieval_snapshot/v1"
STAGE_EXPOSURE_MANIFEST_SCHEMA_VERSION = "stage_exposure_manifest/v1"
STAGE_ASSISTANCE_DECISION_SCHEMA_VERSION = "stage_assistance_decision/v1"
STAGE_TRIAL_OUTCOME_SCHEMA_VERSION = "stage_trial_outcome/v1"
FRESH_CONTEXT_POLICY = "stage_prior_isolation/v1"

ADVISORY = "advisory"
FRESH = "fresh"
STAGE_ASSISTANCE_ARMS = (ADVISORY, FRESH)

USE = "USE"
MODIFY = "MODIFY"
COMBINE = "COMBINE"
IGNORE = "IGNORE"
RETRIEVE_DEEPER = "RETRIEVE_DEEPER"
START_FRESH = "START_FRESH"
SPAWN_CHALLENGER = "SPAWN_CHALLENGER"
STAGE_ASSISTANCE_DISPOSITIONS = (USE, MODIFY, COMBINE, IGNORE,
                                 RETRIEVE_DEEPER, START_FRESH, SPAWN_CHALLENGER)
METRIC_DIRECTIONS = ("maximize", "minimize", "target")
RUN_VALIDITY_STATES = (
    "INFRASTRUCTURE_INVALID", "INFRASTRUCTURE_UNCERTAIN",
    "SEMANTICALLY_ANALYZABLE", "MIXED_OR_MULTI_CAUSAL")

_DIGEST = re.compile(r"^[0-9a-f]{64}$")

def _canonical_json(value: object) -> str:
    """Return the one strict JSON representation used for record digests."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise StageEvidenceContractError(
            "stage evidence must contain only strict JSON values"
        ) from exc

def _content_digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()

def _json_value(value: object) -> object:
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    return value

def _record_dict(record: object) -> dict[str, object]:
    schema_version = record.schema_version  # type: ignore[attr-defined]
    return {"record_type": schema_version,
            **{item.name: _json_value(getattr(record, item.name))
               for item in fields(record)}}

def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StageEvidenceContractError(f"{name} must be a non-empty string")
    if value != value.strip():
        raise StageEvidenceContractError(
            f"{name} must not have leading or trailing whitespace"
        )
    return value

def _optional_text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise StageEvidenceContractError(f"{name} must be a string")
    if value != value.strip():
        raise StageEvidenceContractError(
            f"{name} must not have leading or trailing whitespace"
        )
    return value

def _sha256(value: object, name: str, *, optional: bool = False) -> str:
    if optional and value == "":
        return ""
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise StageEvidenceContractError(
            f"{name} must be a lowercase SHA-256 digest"
        )
    return value

def _optional_bool(value: object, name: str) -> bool | None:
    if value is not None and not isinstance(value, bool):
        raise StageEvidenceContractError(f"{name} must be bool or None")
    return value

def _finite_number(
    value: object,
    name: str,
    *,
    minimum: float | None = None,
) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StageEvidenceContractError(f"{name} must be a number or None")
    if not math.isfinite(float(value)):
        raise StageEvidenceContractError(f"{name} must be finite")
    if minimum is not None and value < minimum:
        raise StageEvidenceContractError(
            f"{name} must be greater than or equal to {minimum:g}"
        )
    return value

def _optional_count(value: object, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise StageEvidenceContractError(
            f"{name} must be a non-negative integer or None"
        )
    return value

def _strict_body(
    value: Mapping[str, object], record_class: type
) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise StageEvidenceContractError("stage evidence record must be a mapping")
    record_fields = {item.name: item for item in fields(record_class)}
    schema_version = record_fields["schema_version"].default
    allowed = set(record_fields) | {"record_type"}
    unknown = set(value) - allowed
    if unknown:
        raise StageEvidenceContractError(
            f"stage evidence record has unknown fields {sorted(unknown)!r}"
        )
    required = {
        name for name, item in record_fields.items()
        if item.default is MISSING and item.default_factory is MISSING
    }
    missing = (required | {"record_type"}) - set(value)
    if missing:
        raise StageEvidenceContractError(
            f"stage evidence record is missing fields {sorted(missing)!r}"
        )
    if value.get("record_type") != schema_version:
        raise StageEvidenceContractError(
            f"stage evidence record needs record_type {schema_version}"
        )
    declared_schema = value.get("schema_version", schema_version)
    if declared_schema != schema_version:
        raise StageEvidenceContractError(
            f"stage evidence record needs schema_version {schema_version}"
        )
    body = dict(value)
    body.pop("record_type")
    body.setdefault("schema_version", schema_version)
    return body

@dataclass(frozen=True)
class EvidenceNamespace:
    """Explicit campaign and deployment scope for stage evidence."""

    campaign_id: str
    deployment_id: str
    tenant_id: str = ""
    workspace_id: str = ""
    schema_version: str = EVIDENCE_NAMESPACE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _required_text(self.campaign_id, "campaign_id")
        _required_text(self.deployment_id, "deployment_id")
        _optional_text(self.tenant_id, "tenant_id")
        _optional_text(self.workspace_id, "workspace_id")
        if self.schema_version != EVIDENCE_NAMESPACE_SCHEMA_VERSION:
            raise StageEvidenceContractError(
                "unsupported EvidenceNamespace schema_version"
            )

    @property
    def namespace_key(self) -> str:
        return "stage-evidence-namespace:sha256:" + _content_digest(
            self.to_dict()
        )

    def to_dict(self) -> dict[str, object]:
        return _record_dict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> EvidenceNamespace:
        body = _strict_body(value, cls)
        return cls(**body)  # type: ignore[arg-type]

@dataclass(frozen=True)
class StageOccurrenceIdentity:
    """One semantic-call occurrence inside an exact Loop activation."""

    namespace: EvidenceNamespace
    run_id: str
    loop_id: str
    activation_id: str
    semantic_call_id: str
    branch_id: str
    graph_version: str
    source_state_revision: int
    source_state_digest: str
    semantic_signature: str
    shape_signature: str
    motif_signatures: tuple[str, ...] = ()
    schema_version: str = STAGE_OCCURRENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.namespace, EvidenceNamespace):
            raise StageEvidenceContractError(
                "namespace must be an EvidenceNamespace"
            )
        for name in (
            "run_id",
            "loop_id",
            "activation_id",
            "semantic_call_id",
            "branch_id",
            "graph_version",
            "semantic_signature",
            "shape_signature",
        ):
            _required_text(getattr(self, name), name)
        if (
            isinstance(self.source_state_revision, bool)
            or not isinstance(self.source_state_revision, int)
            or self.source_state_revision < 0
        ):
            raise StageEvidenceContractError(
                "source_state_revision must be a non-negative integer"
            )
        _sha256(self.source_state_digest, "source_state_digest")
        object.__setattr__(
            self,
            "motif_signatures",
            _unique_texts(self.motif_signatures, "motif_signatures"),
        )
        if self.schema_version != STAGE_OCCURRENCE_SCHEMA_VERSION:
            raise StageEvidenceContractError(
                "unsupported StageOccurrenceIdentity schema_version"
            )

    @property
    def content_digest(self) -> str:
        return _content_digest(self.to_dict())

    @property
    def loop_activation_ref(self) -> str:
        """Identity of the Loop activation, independent of semantic calls."""
        return "loop-activation:sha256:" + _content_digest({
            "namespace_key": self.namespace.namespace_key,
            "run_id": self.run_id,
            "loop_id": self.loop_id,
            "activation_id": self.activation_id,
            "branch_id": self.branch_id,
            "graph_version": self.graph_version,
            "source_state_revision": self.source_state_revision,
            "source_state_digest": self.source_state_digest,
        })

    @property
    def semantic_call_ref(self) -> str:
        """Identity of one logical semantic call inside the activation."""
        return "semantic-call:sha256:" + _content_digest({
            "loop_activation_ref": self.loop_activation_ref,
            "semantic_call_id": self.semantic_call_id,
        })

    @property
    def occurrence_ref(self) -> str:
        """Compatibility spelling for this stage's semantic-call occurrence."""
        return self.semantic_call_ref

    def to_dict(self) -> dict[str, object]:
        return _record_dict(self)

    @classmethod
    def from_dict(
        cls, value: Mapping[str, object]
    ) -> StageOccurrenceIdentity:
        body = _strict_body(value, cls)
        namespace = body.get("namespace")
        if not isinstance(namespace, Mapping):
            raise StageEvidenceContractError("namespace must be a mapping")
        body["namespace"] = EvidenceNamespace.from_dict(namespace)
        body["motif_signatures"] = _stored_texts(
            body.get("motif_signatures"), "motif_signatures")
        return cls(**body)  # type: ignore[arg-type]

@dataclass(frozen=True)
class StageRetrievalCandidate:
    """One prior occurrence returned as advisory retrieval evidence."""

    candidate_ref: str
    source_occurrence_ref: str
    semantic_signature: str
    found_by: str
    evidence_refs: tuple[str, ...] = ()
    material_differences: tuple[str, ...] = ()
    contract_compatible: bool | None = None
    effect_compatible: bool | None = None
    authority_compatible: bool | None = None
    privacy_compatible: bool | None = None
    outcome_refs: tuple[str, ...] = ()
    counterexample_refs: tuple[str, ...] = ()
    prior_not_proof: bool = True
    schema_version: str = STAGE_RETRIEVAL_CANDIDATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "candidate_ref",
            "source_occurrence_ref",
            "semantic_signature",
            "found_by",
        ):
            _required_text(getattr(self, name), name)
        for name in (
            "evidence_refs",
            "material_differences",
            "outcome_refs",
            "counterexample_refs",
        ):
            object.__setattr__(
                self, name, _unique_texts(getattr(self, name), name)
            )
        for name in (
            "contract_compatible",
            "effect_compatible",
            "authority_compatible",
            "privacy_compatible",
        ):
            _optional_bool(getattr(self, name), name)
        if self.prior_not_proof is not True:
            raise StageEvidenceContractError(
                "retrieval candidates must declare prior_not_proof true"
            )
        if self.schema_version != STAGE_RETRIEVAL_CANDIDATE_SCHEMA_VERSION:
            raise StageEvidenceContractError(
                "unsupported StageRetrievalCandidate schema_version"
            )

    def to_dict(self) -> dict[str, object]:
        return _record_dict(self)

    @classmethod
    def from_dict(
        cls, value: Mapping[str, object]
    ) -> StageRetrievalCandidate:
        body = _strict_body(value, cls)
        for name in (
            "evidence_refs",
            "material_differences",
            "outcome_refs",
            "counterexample_refs",
        ):
            body[name] = _stored_texts(body.get(name), name)
        return cls(**body)  # type: ignore[arg-type]

@dataclass(frozen=True)
class StageRetrievalSnapshot:
    """Immutable candidate portfolio retrieved for one occurrence."""

    snapshot_id: str
    occurrence_ref: str
    semantic_signature: str
    candidates: tuple[StageRetrievalCandidate, ...] = ()
    schema_version: str = STAGE_RETRIEVAL_SNAPSHOT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _required_text(self.snapshot_id, "snapshot_id")
        _required_text(self.occurrence_ref, "occurrence_ref")
        _required_text(self.semantic_signature, "semantic_signature")
        if isinstance(self.candidates, (str, bytes)):
            raise StageEvidenceContractError(
                "candidates must contain StageRetrievalCandidate records"
            )
        try:
            candidates = tuple(self.candidates)
        except TypeError as exc:
            raise StageEvidenceContractError(
                "candidates must contain StageRetrievalCandidate records"
            ) from exc
        if any(not isinstance(item, StageRetrievalCandidate)
               for item in candidates):
            raise StageEvidenceContractError(
                "candidates must contain StageRetrievalCandidate records"
            )
        refs = tuple(item.candidate_ref for item in candidates)
        if len(refs) != len(set(refs)):
            raise StageEvidenceContractError(
                "a retrieval snapshot must contain unique candidate refs"
            )
        if any(not item.prior_not_proof for item in candidates):
            raise StageEvidenceContractError(
                "every retrieval candidate must declare prior_not_proof true"
            )
        if any(item.source_occurrence_ref == self.occurrence_ref
               for item in candidates):
            raise StageEvidenceContractError(
                "a retrieval snapshot cannot offer its own occurrence as prior"
            )
        mismatched = tuple(
            item.candidate_ref for item in candidates
            if item.semantic_signature != self.semantic_signature)
        if mismatched:
            raise StageEvidenceContractError(
                "retrieval candidates must match the snapshot semantic "
                f"signature: {mismatched!r}")
        object.__setattr__(self, "candidates", candidates)
        if self.schema_version != STAGE_RETRIEVAL_SNAPSHOT_SCHEMA_VERSION:
            raise StageEvidenceContractError(
                "unsupported StageRetrievalSnapshot schema_version"
            )

    @property
    def content_digest(self) -> str:
        return _content_digest(self.to_dict())

    @property
    def snapshot_ref(self) -> str:
        return "stage-retrieval-snapshot:sha256:" + self.content_digest

    def to_dict(self) -> dict[str, object]:
        return _record_dict(self)

    @classmethod
    def from_dict(
        cls, value: Mapping[str, object]
    ) -> StageRetrievalSnapshot:
        body = _strict_body(value, cls)
        raw_candidates = body.get("candidates") or ()
        if isinstance(raw_candidates, (str, bytes, Mapping)):
            raise StageEvidenceContractError("candidates must be a list")
        try:
            body["candidates"] = tuple(
                StageRetrievalCandidate.from_dict(item)
                for item in raw_candidates  # type: ignore[union-attr]
            )
        except TypeError as exc:
            raise StageEvidenceContractError("candidates must be a list") from exc
        return cls(**body)  # type: ignore[arg-type]

@dataclass(frozen=True)
class StageExposureManifest:
    """Exact prior references retrieved and exposed for one trial arm."""

    manifest_id: str
    occurrence_ref: str
    experiment_ref: str
    assignment_ref: str
    packet_event_ref: str
    packet_digest: str
    fresh_policy_id: str
    arm: str
    retrieval_snapshot_ref: str = ""
    retrieved_prior_refs: tuple[str, ...] = ()
    exposed_prior_refs: tuple[str, ...] = ()
    packet_context_block_ids: tuple[str, ...] = ()
    schema_version: str = STAGE_EXPOSURE_MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "manifest_id", "occurrence_ref", "experiment_ref",
            "assignment_ref", "fresh_policy_id",
        ):
            _required_text(getattr(self, name), name)
        if self.fresh_policy_id != FRESH_CONTEXT_POLICY:
            raise StageEvidenceContractError(
                "exposure manifest needs the stage-prior isolation policy")
        _sha256(self.packet_event_ref, "packet_event_ref")
        _sha256(self.packet_digest, "packet_digest")
        if self.arm not in STAGE_ASSISTANCE_ARMS:
            raise StageEvidenceContractError(
                f"arm must be one of {STAGE_ASSISTANCE_ARMS!r}"
            )
        retrieved = _unique_texts(
            self.retrieved_prior_refs, "retrieved_prior_refs"
        )
        exposed = _unique_texts(self.exposed_prior_refs, "exposed_prior_refs")
        if not set(exposed).issubset(retrieved):
            raise StageEvidenceContractError(
                "exposed_prior_refs must be a subset of retrieved_prior_refs"
            )
        if self.arm == FRESH and (retrieved or exposed):
            raise StageEvidenceContractError(
                "a fresh exposure manifest cannot retrieve or expose prior refs"
            )
        if self.arm == FRESH and self.retrieval_snapshot_ref:
            raise StageEvidenceContractError(
                "a fresh exposure manifest cannot reference a retrieval snapshot"
            )
        if self.arm == ADVISORY and not self.retrieval_snapshot_ref:
            raise StageEvidenceContractError(
                "an advisory exposure manifest needs a retrieval snapshot ref"
            )
        _optional_text(self.retrieval_snapshot_ref, "retrieval_snapshot_ref")
        object.__setattr__(self, "retrieved_prior_refs", retrieved)
        object.__setattr__(self, "exposed_prior_refs", exposed)
        object.__setattr__(
            self, "packet_context_block_ids",
            _unique_texts(self.packet_context_block_ids,
                          "packet_context_block_ids"),
        )
        if self.schema_version != STAGE_EXPOSURE_MANIFEST_SCHEMA_VERSION:
            raise StageEvidenceContractError(
                "unsupported StageExposureManifest schema_version"
            )

    @property
    def content_digest(self) -> str:
        return _content_digest(self.to_dict())

    @property
    def manifest_ref(self) -> str:
        return "stage-exposure-manifest:sha256:" + self.content_digest

    def to_dict(self) -> dict[str, object]:
        return _record_dict(self)

    @classmethod
    def from_dict(
        cls, value: Mapping[str, object]
    ) -> StageExposureManifest:
        body = _strict_body(value, cls)
        for name in (
            "retrieved_prior_refs", "exposed_prior_refs",
            "packet_context_block_ids",
        ):
            body[name] = _stored_texts(body.get(name), name)
        return cls(**body)  # type: ignore[arg-type]

@dataclass(frozen=True)
class StageAssistanceDecision:
    """Solver-owned disposition toward one exact exposure manifest."""

    decision_id: str
    occurrence_ref: str
    exposure_manifest_ref: str
    disposition: str
    selected_prior_refs: tuple[str, ...] = ()
    reason: str = ""
    evidence_refs: tuple[str, ...] = ()
    schema_version: str = STAGE_ASSISTANCE_DECISION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("decision_id", "occurrence_ref", "exposure_manifest_ref"):
            _required_text(getattr(self, name), name)
        if self.disposition not in STAGE_ASSISTANCE_DISPOSITIONS:
            raise StageEvidenceContractError(
                "disposition must be one of "
                f"{STAGE_ASSISTANCE_DISPOSITIONS!r}"
            )
        object.__setattr__(
            self,
            "selected_prior_refs",
            _unique_texts(self.selected_prior_refs, "selected_prior_refs"),
        )
        _required_text(self.reason, "reason")
        object.__setattr__(
            self,
            "evidence_refs",
            _unique_texts(self.evidence_refs, "evidence_refs"),
        )
        if self.schema_version != STAGE_ASSISTANCE_DECISION_SCHEMA_VERSION:
            raise StageEvidenceContractError(
                "unsupported StageAssistanceDecision schema_version"
            )

    @property
    def content_digest(self) -> str:
        return _content_digest(self.to_dict())

    @property
    def decision_ref(self) -> str:
        return "stage-assistance-decision:sha256:" + self.content_digest

    def to_dict(self) -> dict[str, object]:
        return _record_dict(self)

    @classmethod
    def from_dict(
        cls, value: Mapping[str, object]
    ) -> StageAssistanceDecision:
        body = _strict_body(value, cls)
        for name in ("selected_prior_refs", "evidence_refs"):
            body[name] = _stored_texts(body.get(name), name)
        return cls(**body)  # type: ignore[arg-type]

def validate_decision_against_exposure(
    decision: StageAssistanceDecision,
    manifest: StageExposureManifest,
) -> bool:
    """Validate one solver decision against what the solver actually saw."""
    if not isinstance(decision, StageAssistanceDecision):
        raise StageEvidenceContractError(
            "decision must be a StageAssistanceDecision"
        )
    if not isinstance(manifest, StageExposureManifest):
        raise StageEvidenceContractError(
            "manifest must be a StageExposureManifest"
        )
    if decision.occurrence_ref != manifest.occurrence_ref:
        raise StageEvidenceContractError(
            "decision and exposure manifest occurrence refs differ"
        )
    if decision.exposure_manifest_ref != manifest.manifest_ref:
        raise StageEvidenceContractError(
            "decision does not reference the supplied exposure manifest"
        )
    selected = decision.selected_prior_refs
    if not set(selected).issubset(manifest.exposed_prior_refs):
        raise StageEvidenceContractError(
            "selected_prior_refs must be a subset of exposed_prior_refs"
        )
    if decision.disposition in (USE, MODIFY) and len(selected) != 1:
        raise StageEvidenceContractError(
            f"{decision.disposition} requires exactly one selected prior ref"
        )
    if decision.disposition == COMBINE and len(selected) < 2:
        raise StageEvidenceContractError(
            "COMBINE requires at least two selected prior refs"
        )
    if decision.disposition in (
        IGNORE,
        RETRIEVE_DEEPER,
        START_FRESH,
    ) and selected:
        raise StageEvidenceContractError(
            f"{decision.disposition} cannot select prior refs"
        )
    if (manifest.arm == FRESH
            and (decision.disposition != START_FRESH or selected)):
        raise StageEvidenceContractError(
            "a fresh arm permits only START_FRESH with no selected refs"
        )
    return True

@dataclass(frozen=True)
class StageTrialOutcome:
    """Outcome evidence joined to one occurrence, assignment, and decision."""

    outcome_id: str
    occurrence_ref: str
    experiment_ref: str
    trial_ref: str
    assignment_ref: str
    exposure_manifest_ref: str
    decision_ref: str
    verification_ref: str
    arm: str
    evaluator_id: str
    metric_ref: str
    metric_direction: str
    run_validity: str
    verification_passed: bool | None = None
    quality: int | float | None = None
    cost: int | float | None = None
    latency_seconds: int | float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    schema_version: str = STAGE_TRIAL_OUTCOME_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in (
            "outcome_id",
            "occurrence_ref",
            "experiment_ref",
            "trial_ref",
            "assignment_ref",
            "exposure_manifest_ref",
            "decision_ref",
            "evaluator_id",
            "metric_ref",
        ):
            _required_text(getattr(self, name), name)
        _sha256(self.verification_ref, "verification_ref")
        if self.arm not in STAGE_ASSISTANCE_ARMS:
            raise StageEvidenceContractError(
                f"arm must be one of {STAGE_ASSISTANCE_ARMS!r}"
            )
        if self.metric_direction not in METRIC_DIRECTIONS:
            raise StageEvidenceContractError(
                f"metric_direction must be one of {METRIC_DIRECTIONS!r}"
            )
        if self.run_validity not in RUN_VALIDITY_STATES:
            raise StageEvidenceContractError(
                f"run_validity must be one of {RUN_VALIDITY_STATES!r}"
            )
        _optional_bool(self.verification_passed, "verification_passed")
        _finite_number(self.quality, "quality")
        _finite_number(self.cost, "cost", minimum=0.0)
        _finite_number(self.latency_seconds, "latency_seconds", minimum=0.0)
        _optional_count(self.input_tokens, "input_tokens")
        _optional_count(self.output_tokens, "output_tokens")
        if self.schema_version != STAGE_TRIAL_OUTCOME_SCHEMA_VERSION:
            raise StageEvidenceContractError(
                "unsupported StageTrialOutcome schema_version"
            )

    @property
    def content_digest(self) -> str:
        return _content_digest(self.to_dict())

    @property
    def outcome_ref(self) -> str:
        return "stage-trial-outcome:sha256:" + self.content_digest

    def to_dict(self) -> dict[str, object]:
        return _record_dict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> StageTrialOutcome:
        body = _strict_body(value, cls)
        return cls(**body)  # type: ignore[arg-type]

_RECORD_TYPES = {
    EVIDENCE_NAMESPACE_SCHEMA_VERSION: EvidenceNamespace,
    STAGE_OCCURRENCE_SCHEMA_VERSION: StageOccurrenceIdentity,
    STAGE_RETRIEVAL_CANDIDATE_SCHEMA_VERSION: StageRetrievalCandidate,
    STAGE_RETRIEVAL_SNAPSHOT_SCHEMA_VERSION: StageRetrievalSnapshot,
    STAGE_EXPOSURE_MANIFEST_SCHEMA_VERSION: StageExposureManifest,
    STAGE_ASSISTANCE_DECISION_SCHEMA_VERSION: StageAssistanceDecision,
    STAGE_TRIAL_OUTCOME_SCHEMA_VERSION: StageTrialOutcome,
}

def record_from_dict(value: Mapping[str, object]) -> Any:
    """Read one current stage evidence record by exact schema version."""
    if not isinstance(value, Mapping):
        raise StageEvidenceContractError("stage evidence record must be a mapping")
    schema_version = value.get("record_type")
    record_class = _RECORD_TYPES.get(schema_version)
    if record_class is None:
        raise StageEvidenceContractError(
            f"unknown stage evidence record_type {schema_version!r}"
        )
    return record_class.from_dict(value)

def record_ref(record: object) -> str:
    """Return the canonical reference carried or derived by one record."""
    if isinstance(record, EvidenceNamespace):
        return record.namespace_key
    if isinstance(record, StageOccurrenceIdentity):
        return record.occurrence_ref
    if isinstance(record, StageRetrievalCandidate):
        return record.candidate_ref
    if isinstance(record, StageRetrievalSnapshot):
        return record.snapshot_ref
    if isinstance(record, StageExposureManifest):
        return record.manifest_ref
    if isinstance(record, StageAssistanceDecision):
        return record.decision_ref
    if isinstance(record, StageTrialOutcome):
        return record.outcome_ref
    raise StageEvidenceContractError(
        f"unsupported stage evidence record {type(record).__name__}"
    )

__all__ = [
    "ADVISORY", "COMBINE", "FRESH", "FRESH_CONTEXT_POLICY", "IGNORE",
    "METRIC_DIRECTIONS", "MODIFY", "RETRIEVE_DEEPER",
    "RUN_VALIDITY_STATES", "SPAWN_CHALLENGER", "START_FRESH", "USE",
    "EvidenceNamespace", "StageAssistanceDecision",
    "StageEvidenceContractError", "StageExposureManifest",
    "StageOccurrenceIdentity", "StageRetrievalCandidate",
    "StageRetrievalSnapshot", "StageTrialOutcome", "record_from_dict",
    "record_ref",
    "validate_decision_against_exposure"]
