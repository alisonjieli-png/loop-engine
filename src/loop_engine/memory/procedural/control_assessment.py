"""Passive evidence for bounded, controllable procedural reuse.

The records test one exact procedural-memory version at seven behavioral
boundaries. They do not retrieve, execute, route, mutate, or promote anything.
Experiments and later decisions remain work owned by canonical Loops.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from ...loop.loop_definition import LoopDefinitionRef
from ..model.memory_type import MemoryIdentity, MemoryType

PROCEDURAL_PROBE_SCHEMA = "procedural_probe_evidence/v1"
PROCEDURAL_CONTROL_ASSESSMENT_SCHEMA = "procedural_control_assessment/v1"

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


class ProceduralControlError(ValueError):
    """Procedural control evidence is malformed or internally inconsistent."""


class ProceduralProbeKind(str, Enum):
    INITIATION = "initiation"
    TERMINATION = "termination"
    INTERRUPTION = "interruption"
    OUTCOME_DEVALUATION = "outcome_devaluation"
    NEGATIVE_TRANSFER = "negative_transfer"
    FRESH_CONTROL = "fresh_control"
    DELIBERATIVE_FALLBACK = "deliberative_fallback"


class ProceduralProbeVerdict(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"
    INFRASTRUCTURE_INVALID = "infrastructure_invalid"


class ProceduralControlStatus(str, Enum):
    INSUFFICIENT_VALID_EVIDENCE = "insufficient_valid_evidence"
    CANDIDATE_SUPPORT_PENDING_RESOLUTION = "candidate_support_pending_resolution"
    NOT_SUPPORTED_WITHIN_DECLARED_SCOPE = "not_supported_within_declared_scope"
    CONTRADICTED = "contradicted"


REQUIRED_PROBE_KINDS = tuple(ProceduralProbeKind)


def _text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise ProceduralControlError(f"{name} must be text")
    if (
        not value
        or value != value.strip()
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ProceduralControlError(f"{name} must be trimmed, control-free text")
    return value


def _optional_text(value: object, name: str) -> str:
    if value == "":
        return ""
    return _text(value, name)


def _digest(value: object, name: str) -> str:
    result = _text(value, name)
    if not _DIGEST.fullmatch(result):
        raise ProceduralControlError(f"{name} must be a lowercase SHA-256 digest")
    return result


def _texts(
    values: object,
    name: str,
    *,
    required: bool = False,
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, Mapping, set, frozenset)):
        raise ProceduralControlError(f"{name} must be a sequence, not text")
    try:
        result = tuple(_text(item, name) for item in (values or ()))
    except TypeError as exc:
        raise ProceduralControlError(f"{name} must be a sequence") from exc
    if (required and not result) or len(result) != len(set(result)):
        qualifier = " unique and non-empty" if required else " unique"
        raise ProceduralControlError(f"{name} must be{qualifier}")
    return result


def _digests(values: object, name: str, *, required: bool = False) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, Mapping, set, frozenset)):
        raise ProceduralControlError(f"{name} must be a sequence, not text")
    try:
        result = tuple(_digest(item, name) for item in (values or ()))
    except TypeError as exc:
        raise ProceduralControlError(f"{name} must be a sequence") from exc
    if (required and not result) or len(result) != len(set(result)):
        qualifier = " unique and non-empty" if required else " unique"
        raise ProceduralControlError(f"{name} must be{qualifier}")
    return result


def _enum(value: object, enum_type: type[Enum], name: str) -> Enum:
    try:
        return value if isinstance(value, enum_type) else enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ProceduralControlError(f"{name} is not registered") from exc


def _identity_key(identity: MemoryIdentity) -> tuple[str, str, str]:
    return identity.record_id, identity.version, identity.content_digest


def _validate_identity(
    value: object,
    name: str,
    expected_type: MemoryType,
) -> MemoryIdentity:
    if not isinstance(value, MemoryIdentity):
        raise ProceduralControlError(f"{name} must use MemoryIdentity")
    if value.memory_type is not expected_type:
        raise ProceduralControlError(f"{name} must identify {expected_type.value} memory")
    _text(value.record_id, f"{name}.record_id")
    if not _SEMVER.fullmatch(value.version):
        raise ProceduralControlError(f"{name}.version must use semantic versioning")
    _digest(value.content_digest, f"{name}.content_digest")
    return value


def _identities(
    values: object,
    name: str,
    expected_type: MemoryType,
) -> tuple[MemoryIdentity, ...]:
    if isinstance(values, (str, bytes, Mapping, set, frozenset)):
        raise ProceduralControlError(f"{name} must be a sequence, not text")
    try:
        result = tuple(
            _validate_identity(item, name, expected_type) for item in (values or ())
        )
    except TypeError as exc:
        raise ProceduralControlError(f"{name} must be a sequence") from exc
    keys = tuple(_identity_key(item) for item in result)
    if len(keys) != len(set(keys)):
        raise ProceduralControlError(f"{name} cannot contain duplicates")
    return result


def _identity_dict(identity: MemoryIdentity) -> dict[str, str]:
    return {
        "record_id": identity.record_id,
        "version": identity.version,
        "content_digest": identity.content_digest,
        "memory_type": identity.memory_type.value,
    }


def _identity_from_dict(value: object, name: str) -> MemoryIdentity:
    expected = {"record_id", "version", "content_digest", "memory_type"}
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ProceduralControlError(f"{name} has an invalid identity shape")
    try:
        identity = MemoryIdentity(
            record_id=value["record_id"],
            version=value["version"],
            content_digest=value["content_digest"],
            memory_type=MemoryType(value["memory_type"]),
        )
    except (TypeError, ValueError) as exc:
        raise ProceduralControlError(f"{name} is invalid") from exc
    return identity


def _canonical(value: object) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ProceduralControlError("evidence must be strict JSON") from exc


def _content_digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ProceduralProbeEvidence:
    probe_id: str
    probe_kind: ProceduralProbeKind
    task_region_ref: str
    source_state_digest: str
    expected_behavior_ref: str
    occurrence_refs: tuple[str, ...]
    outcome_refs: tuple[str, ...]
    run_history_event_digests: tuple[str, ...]
    evaluator_loop_ref: str
    evaluator_policy_ref: str
    evaluator_policy_digest: str
    verdict: ProceduralProbeVerdict
    evidence_refs: tuple[str, ...]
    infrastructure_valid: bool = True
    invalid_reason: str = ""
    experiment_ref: str = ""
    experiment_digest: str = ""
    control_occurrence_ref: str = ""
    treatment_occurrence_ref: str = ""
    control_outcome_ref: str = ""
    treatment_outcome_ref: str = ""
    contamination_refs: tuple[str, ...] = ()
    record_type: str = PROCEDURAL_PROBE_SCHEMA

    def __post_init__(self) -> None:
        if self.record_type != PROCEDURAL_PROBE_SCHEMA:
            raise ProceduralControlError("procedural probe schema is unsupported")
        for name in (
            "probe_id",
            "task_region_ref",
            "expected_behavior_ref",
            "evaluator_loop_ref",
            "evaluator_policy_ref",
        ):
            _text(getattr(self, name), name)
        _digest(self.source_state_digest, "source_state_digest")
        _digest(self.evaluator_policy_digest, "evaluator_policy_digest")
        object.__setattr__(
            self,
            "probe_kind",
            _enum(self.probe_kind, ProceduralProbeKind, "probe_kind"),
        )
        object.__setattr__(
            self,
            "verdict",
            _enum(self.verdict, ProceduralProbeVerdict, "verdict"),
        )
        if not isinstance(self.infrastructure_valid, bool):
            raise ProceduralControlError("infrastructure_valid must be Boolean")
        for name in ("occurrence_refs", "evidence_refs"):
            object.__setattr__(
                self, name, _texts(getattr(self, name), name, required=True)
            )
        outcomes = _texts(
            self.outcome_refs,
            "outcome_refs",
            required=self.infrastructure_valid,
        )
        if not self.infrastructure_valid and outcomes:
            raise ProceduralControlError("invalid probes cannot carry outcomes")
        object.__setattr__(self, "outcome_refs", outcomes)
        object.__setattr__(
            self,
            "run_history_event_digests",
            _digests(
                self.run_history_event_digests,
                "run_history_event_digests",
                required=True,
            ),
        )
        object.__setattr__(
            self,
            "contamination_refs",
            _texts(self.contamination_refs, "contamination_refs"),
        )
        invalid_reason = _optional_text(self.invalid_reason, "invalid_reason")
        invalid_verdict = (
            self.verdict is ProceduralProbeVerdict.INFRASTRUCTURE_INVALID
        )
        if self.infrastructure_valid == invalid_verdict:
            raise ProceduralControlError("validity and verdict disagree")
        if bool(invalid_reason) != invalid_verdict:
            raise ProceduralControlError("invalid probes need one reason")

        paired = (
            self.experiment_ref,
            self.control_occurrence_ref,
            self.treatment_occurrence_ref,
            self.control_outcome_ref,
            self.treatment_outcome_ref,
        )
        if not all(isinstance(value, str) for value in (*paired, self.experiment_digest)):
            raise ProceduralControlError("optional control fields must be text")
        if self.probe_kind is ProceduralProbeKind.FRESH_CONTROL:
            for name, value in zip(
                ("experiment_ref", "control_occurrence_ref", "treatment_occurrence_ref"),
                paired[:3],
            ):
                _text(value, name)
            _digest(self.experiment_digest, "experiment_digest")
            if self.control_occurrence_ref == self.treatment_occurrence_ref:
                raise ProceduralControlError("fresh occurrences must differ")
            if self.occurrence_refs != (
                self.control_occurrence_ref,
                self.treatment_occurrence_ref,
            ):
                raise ProceduralControlError("fresh occurrence order is invalid")
            if self.infrastructure_valid:
                _text(self.control_outcome_ref, "control_outcome_ref")
                _text(self.treatment_outcome_ref, "treatment_outcome_ref")
                if self.control_outcome_ref == self.treatment_outcome_ref:
                    raise ProceduralControlError("fresh outcomes must differ")
                if self.outcome_refs != (
                    self.control_outcome_ref,
                    self.treatment_outcome_ref,
                ):
                    raise ProceduralControlError("fresh outcome order is invalid")
            elif self.control_outcome_ref or self.treatment_outcome_ref:
                raise ProceduralControlError("invalid fresh control has outcomes")
            if self.contamination_refs and (
                self.infrastructure_valid
                or self.verdict
                is not ProceduralProbeVerdict.INFRASTRUCTURE_INVALID
            ):
                raise ProceduralControlError("contaminated fresh control must be invalid")
        else:
            if any(paired) or self.experiment_digest or self.contamination_refs:
                raise ProceduralControlError("control fields require a fresh-control probe")

    def _body(self) -> dict[str, object]:
        return {
            "record_type": self.record_type,
            "probe_id": self.probe_id,
            "probe_kind": self.probe_kind.value,
            "task_region_ref": self.task_region_ref,
            "source_state_digest": self.source_state_digest,
            "expected_behavior_ref": self.expected_behavior_ref,
            "occurrence_refs": list(self.occurrence_refs),
            "outcome_refs": list(self.outcome_refs),
            "run_history_event_digests": list(self.run_history_event_digests),
            "evaluator_loop_ref": self.evaluator_loop_ref,
            "evaluator_policy_ref": self.evaluator_policy_ref,
            "evaluator_policy_digest": self.evaluator_policy_digest,
            "verdict": self.verdict.value,
            "evidence_refs": list(self.evidence_refs),
            "infrastructure_valid": self.infrastructure_valid,
            "invalid_reason": self.invalid_reason,
            "experiment_ref": self.experiment_ref,
            "experiment_digest": self.experiment_digest,
            "control_occurrence_ref": self.control_occurrence_ref,
            "treatment_occurrence_ref": self.treatment_occurrence_ref,
            "control_outcome_ref": self.control_outcome_ref,
            "treatment_outcome_ref": self.treatment_outcome_ref,
            "contamination_refs": list(self.contamination_refs),
            "grants_authority": False,
        }

    @property
    def content_digest(self) -> str:
        return _content_digest(self._body())

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> ProceduralProbeEvidence:
        expected = {
            "record_type",
            "probe_id",
            "probe_kind",
            "task_region_ref",
            "source_state_digest",
            "expected_behavior_ref",
            "occurrence_refs",
            "outcome_refs",
            "run_history_event_digests",
            "evaluator_loop_ref",
            "evaluator_policy_ref",
            "evaluator_policy_digest",
            "verdict",
            "evidence_refs",
            "infrastructure_valid",
            "invalid_reason",
            "experiment_ref",
            "experiment_digest",
            "control_occurrence_ref",
            "treatment_occurrence_ref",
            "control_outcome_ref",
            "treatment_outcome_ref",
            "contamination_refs",
            "grants_authority",
            "content_digest",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ProceduralControlError("procedural probe has an invalid shape")
        if value["grants_authority"] is not False:
            raise ProceduralControlError("procedural probe cannot grant authority")
        body = dict(value)
        expected_digest = body.pop("content_digest")
        body.pop("grants_authority")
        for name in (
            "occurrence_refs",
            "outcome_refs",
            "run_history_event_digests",
            "evidence_refs",
            "contamination_refs",
        ):
            if isinstance(body[name], (str, bytes, Mapping, set, frozenset)):
                raise ProceduralControlError(f"{name} must be a sequence")
            body[name] = tuple(body[name])
        record = cls(**body)
        if expected_digest != record.content_digest:
            raise ProceduralControlError("procedural probe digest mismatch")
        return record


@dataclass(frozen=True)
class ProceduralControlAssessment:
    assessment_id: str
    version: str
    procedure_identity: MemoryIdentity
    procedure_loop_definition_ref: LoopDefinitionRef
    producer_loop_ref: str
    assessor_loop_refs: tuple[str, ...]
    assessment_policy_ref: str
    assessment_policy_digest: str
    task_region_scope: tuple[str, ...]
    cognitive_phase_scope: tuple[str, ...]
    semantic_signature_scope: tuple[str, ...]
    shape_signature_scope: tuple[str, ...]
    motif_signature_scope: tuple[str, ...]
    segment_signature_scope: tuple[str, ...]
    graph_definition_digests: tuple[str, ...]
    positive_episode_identities: tuple[MemoryIdentity, ...]
    negative_episode_identities: tuple[MemoryIdentity, ...]
    negative_transfer_episode_identities: tuple[MemoryIdentity, ...]
    probes: tuple[ProceduralProbeEvidence, ...]
    deliberative_fallback_ref: LoopDefinitionRef
    evidence_refs: tuple[str, ...]
    limitations: tuple[str, ...] = ()
    confidence: float | None = None
    record_type: str = PROCEDURAL_CONTROL_ASSESSMENT_SCHEMA

    def __post_init__(self) -> None:
        if self.record_type != PROCEDURAL_CONTROL_ASSESSMENT_SCHEMA:
            raise ProceduralControlError("assessment schema is unsupported")
        _text(self.assessment_id, "assessment_id")
        if not _SEMVER.fullmatch(self.version):
            raise ProceduralControlError("version must use semantic versioning")
        _validate_identity(
            self.procedure_identity, "procedure_identity", MemoryType.PROCEDURAL
        )
        if not isinstance(self.procedure_loop_definition_ref, LoopDefinitionRef):
            raise ProceduralControlError("procedure definition ref has the wrong type")
        if not isinstance(self.deliberative_fallback_ref, LoopDefinitionRef):
            raise ProceduralControlError("fallback definition ref has the wrong type")
        if self.deliberative_fallback_ref == self.procedure_loop_definition_ref:
            raise ProceduralControlError("procedure cannot be its own fallback")
        for name in (
            "producer_loop_ref",
            "assessment_policy_ref",
        ):
            _text(getattr(self, name), name)
        _digest(self.assessment_policy_digest, "assessment_policy_digest")
        assessors = _texts(
            self.assessor_loop_refs, "assessor_loop_refs", required=True
        )
        if self.producer_loop_ref.casefold() in {
            item.casefold() for item in assessors
        }:
            raise ProceduralControlError(
                "a procedure producer cannot assess its own control evidence"
            )
        object.__setattr__(self, "assessor_loop_refs", assessors)
        for name in (
            "task_region_scope",
            "cognitive_phase_scope",
            "semantic_signature_scope",
            "shape_signature_scope",
            "motif_signature_scope",
            "segment_signature_scope",
        ):
            object.__setattr__(
                self, name, _texts(getattr(self, name), name, required=True)
            )
        object.__setattr__(
            self,
            "graph_definition_digests",
            _digests(
                self.graph_definition_digests,
                "graph_definition_digests",
                required=True,
            ),
        )
        for name in (
            "positive_episode_identities",
            "negative_episode_identities",
            "negative_transfer_episode_identities",
        ):
            object.__setattr__(
                self,
                name,
                _identities(getattr(self, name), name, MemoryType.EPISODIC),
            )
        positive = {_identity_key(item) for item in self.positive_episode_identities}
        negative = {_identity_key(item) for item in self.negative_episode_identities}
        transfer = {
            _identity_key(item) for item in self.negative_transfer_episode_identities
        }
        if positive & negative:
            raise ProceduralControlError("positive and negative episodes overlap")
        if {
            item.content_digest for item in self.positive_episode_identities
        } & {item.content_digest for item in self.negative_episode_identities}:
            raise ProceduralControlError(
                "one episode content digest cannot be both positive and negative"
            )
        if not transfer <= negative:
            raise ProceduralControlError(
                "negative-transfer episodes must be classified as negative"
            )
        if isinstance(self.probes, (str, bytes, Mapping, set, frozenset)):
            raise ProceduralControlError("probes must be a typed sequence")
        try:
            probes = tuple(self.probes)
        except TypeError as exc:
            raise ProceduralControlError("probes must be a typed sequence") from exc
        if any(not isinstance(item, ProceduralProbeEvidence) for item in probes):
            raise ProceduralControlError(
                "probes must contain ProceduralProbeEvidence"
            )
        if len({item.probe_id for item in probes}) != len(probes):
            raise ProceduralControlError("probe identities cannot repeat")
        for name in (
            "occurrence_refs",
            "outcome_refs",
            "evidence_refs",
            "run_history_event_digests",
        ):
            references = tuple(
                reference for item in probes for reference in getattr(item, name)
            )
            if len(references) != len(set(references)):
                raise ProceduralControlError(
                    f"{name} cannot be reused across behavioral probe kinds"
                )
        if len({item.expected_behavior_ref for item in probes}) != len(probes):
            raise ProceduralControlError(
                "expected behavior references cannot repeat across probes"
            )
        if any(item.evaluator_loop_ref not in assessors for item in probes):
            raise ProceduralControlError(
                "every probe evaluator must be a declared independent assessor"
            )
        if any(item.task_region_ref not in self.task_region_scope for item in probes):
            raise ProceduralControlError(
                "every probe must remain inside the declared task-region scope"
            )
        if any(
            item.evaluator_policy_ref != self.assessment_policy_ref
            or item.evaluator_policy_digest != self.assessment_policy_digest
            for item in probes
        ):
            raise ProceduralControlError(
                "every probe must bind the assessment's exact evaluator policy"
            )
        object.__setattr__(self, "probes", probes)
        object.__setattr__(
            self, "evidence_refs", _texts(self.evidence_refs, "evidence_refs", required=True)
        )
        object.__setattr__(
            self, "limitations", _texts(self.limitations, "limitations")
        )
        if self.confidence is not None:
            if (
                isinstance(self.confidence, bool)
                or not isinstance(self.confidence, (int, float))
                or not math.isfinite(float(self.confidence))
                or not 0.0 <= float(self.confidence) <= 1.0
            ):
                raise ProceduralControlError(
                    "confidence must be finite and between zero and one"
                )
            object.__setattr__(self, "confidence", float(self.confidence))

    @property
    def status(self) -> ProceduralControlStatus:
        valid = tuple(item for item in self.probes if item.infrastructure_valid)
        verdicts = {
            kind: {
                item.verdict
                for item in valid
                if item.probe_kind is kind
            }
            for kind in REQUIRED_PROBE_KINDS
        }
        if any(
            ProceduralProbeVerdict.PASSED in observed
            and ProceduralProbeVerdict.FAILED in observed
            for observed in verdicts.values()
        ):
            return ProceduralControlStatus.CONTRADICTED
        if any(
            ProceduralProbeVerdict.FAILED in observed
            for observed in verdicts.values()
        ):
            return ProceduralControlStatus.NOT_SUPPORTED_WITHIN_DECLARED_SCOPE
        if len(valid) != len(self.probes):
            return ProceduralControlStatus.INSUFFICIENT_VALID_EVIDENCE
        complete = all(
            tuple(item.probe_kind for item in valid).count(kind) == 1
            and observed == {ProceduralProbeVerdict.PASSED}
            for kind, observed in verdicts.items()
        )
        evidence_population = bool(
            self.positive_episode_identities
            and self.negative_episode_identities
            and self.negative_transfer_episode_identities
        )
        if complete and evidence_population:
            return ProceduralControlStatus.CANDIDATE_SUPPORT_PENDING_RESOLUTION
        return ProceduralControlStatus.INSUFFICIENT_VALID_EVIDENCE

    def _body(self) -> dict[str, object]:
        return {
            "record_type": self.record_type,
            "assessment_id": self.assessment_id,
            "version": self.version,
            "procedure_identity": _identity_dict(self.procedure_identity),
            "procedure_loop_definition_ref": (
                self.procedure_loop_definition_ref.to_dict()
            ),
            "producer_loop_ref": self.producer_loop_ref,
            "assessor_loop_refs": list(self.assessor_loop_refs),
            "assessment_policy_ref": self.assessment_policy_ref,
            "assessment_policy_digest": self.assessment_policy_digest,
            "task_region_scope": list(self.task_region_scope),
            "cognitive_phase_scope": list(self.cognitive_phase_scope),
            "semantic_signature_scope": list(self.semantic_signature_scope),
            "shape_signature_scope": list(self.shape_signature_scope),
            "motif_signature_scope": list(self.motif_signature_scope),
            "segment_signature_scope": list(self.segment_signature_scope),
            "graph_definition_digests": list(self.graph_definition_digests),
            "positive_episode_identities": [
                _identity_dict(item) for item in self.positive_episode_identities
            ],
            "negative_episode_identities": [
                _identity_dict(item) for item in self.negative_episode_identities
            ],
            "negative_transfer_episode_identities": [
                _identity_dict(item)
                for item in self.negative_transfer_episode_identities
            ],
            "probes": [item.to_dict() for item in self.probes],
            "deliberative_fallback_ref": self.deliberative_fallback_ref.to_dict(),
            "evidence_refs": list(self.evidence_refs),
            "limitations": list(self.limitations),
            "confidence": self.confidence,
            "status": self.status.value,
            "grants_authority": False,
            "promotion_authorized": False,
            "generalization_claimed": False,
        }

    @property
    def content_digest(self) -> str:
        return _content_digest(self._body())

    def to_dict(self) -> dict[str, object]:
        return {**self._body(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(
        cls, value: Mapping[str, object]
    ) -> ProceduralControlAssessment:
        expected = {
            "record_type",
            "assessment_id",
            "version",
            "procedure_identity",
            "procedure_loop_definition_ref",
            "producer_loop_ref",
            "assessor_loop_refs",
            "assessment_policy_ref",
            "assessment_policy_digest",
            "task_region_scope",
            "cognitive_phase_scope",
            "semantic_signature_scope",
            "shape_signature_scope",
            "motif_signature_scope",
            "segment_signature_scope",
            "graph_definition_digests",
            "positive_episode_identities",
            "negative_episode_identities",
            "negative_transfer_episode_identities",
            "probes",
            "deliberative_fallback_ref",
            "evidence_refs",
            "limitations",
            "confidence",
            "status",
            "grants_authority",
            "promotion_authorized",
            "generalization_claimed",
            "content_digest",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ProceduralControlError(
                "procedural control assessment has an invalid shape"
            )
        for name in (
            "grants_authority",
            "promotion_authorized",
            "generalization_claimed",
        ):
            if value[name] is not False:
                raise ProceduralControlError(f"{name} must remain false")
        body = dict(value)
        expected_digest = body.pop("content_digest")
        asserted_status = body.pop("status")
        for name in (
            "grants_authority",
            "promotion_authorized",
            "generalization_claimed",
        ):
            body.pop(name)
        body["procedure_identity"] = _identity_from_dict(
            body["procedure_identity"], "procedure_identity"
        )
        try:
            body["procedure_loop_definition_ref"] = LoopDefinitionRef.from_dict(
                body["procedure_loop_definition_ref"]
            )
            body["deliberative_fallback_ref"] = LoopDefinitionRef.from_dict(
                body["deliberative_fallback_ref"]
            )
        except (TypeError, ValueError) as exc:
            raise ProceduralControlError(
                "assessment Loop definition reference is invalid"
            ) from exc
        for name in (
            "assessor_loop_refs",
            "task_region_scope",
            "cognitive_phase_scope",
            "semantic_signature_scope",
            "shape_signature_scope",
            "motif_signature_scope",
            "segment_signature_scope",
            "graph_definition_digests",
            "evidence_refs",
            "limitations",
        ):
            if isinstance(body[name], (str, bytes, Mapping, set, frozenset)):
                raise ProceduralControlError(f"{name} must be a sequence")
            body[name] = tuple(body[name])
        for name in (
            "positive_episode_identities",
            "negative_episode_identities",
            "negative_transfer_episode_identities",
        ):
            raw = body[name]
            if isinstance(raw, (str, bytes, Mapping, set, frozenset)):
                raise ProceduralControlError(f"{name} must be a sequence")
            body[name] = tuple(
                _identity_from_dict(item, name) for item in raw
            )
        raw_probes = body["probes"]
        if isinstance(raw_probes, (str, bytes, Mapping, set, frozenset)):
            raise ProceduralControlError("probes must be a sequence")
        body["probes"] = tuple(
            ProceduralProbeEvidence.from_dict(item) for item in raw_probes
        )
        record = cls(**body)
        if asserted_status != record.status.value:
            raise ProceduralControlError(
                "asserted procedural control status contradicts its evidence"
            )
        if expected_digest != record.content_digest:
            raise ProceduralControlError(
                "procedural control assessment digest does not match its content"
            )
        return record


__all__ = (
    "PROCEDURAL_CONTROL_ASSESSMENT_SCHEMA",
    "PROCEDURAL_PROBE_SCHEMA",
    "REQUIRED_PROBE_KINDS",
    "ProceduralControlAssessment",
    "ProceduralControlError",
    "ProceduralControlStatus",
    "ProceduralProbeEvidence",
    "ProceduralProbeKind",
    "ProceduralProbeVerdict",
)
