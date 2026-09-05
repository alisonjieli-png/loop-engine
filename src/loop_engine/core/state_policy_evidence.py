"""Passive paired compression and distortion evidence for state policies.
It compares observed records and never selects, executes, or promotes a policy.
Experiments and later decisions remain work owned by classified Loops."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from .information_evidence_contracts import (
    _EPSILON,
    InformationMeasurementSpec,
    InformationTheoryEvidenceError,
    InfrastructureValidityRecord,
    _content_digest,
    _count,
    _digest,
    _number,
    _optional_number,
    _optional_text,
    _text,
    _texts,
)
from .information_theory_evidence import (
    INSUFFICIENT_VALID_EVIDENCE,
    NOT_SUPPORTED_WITHIN_TOLERANCE,
    STATE_POLICY_ASSESSMENT_SCHEMA,
    STATE_POLICY_TRIAL_SCHEMA,
    SUPPORTED_WITHIN_TOLERANCE,
)


@dataclass(frozen=True)
class PairedStatePolicyTrial:
    trial_id: str
    namespace_ref: str
    privacy_class: str
    task_region_ref: str
    population_ref: str
    population_digest: str
    pair_source_ref: str
    source_state_digest: str
    full_history_policy_ref: str
    state_policy_ref: str
    model_profile_ref: str
    model_profile_digest: str
    evaluator_ref: str
    evaluator_digest: str
    outcome_contract_ref: str
    outcome_contract_digest: str
    control_occurrence_ref: str
    treatment_occurrence_ref: str
    control_outcome_ref: str
    treatment_outcome_ref: str
    control_context_bytes: int
    treatment_context_bytes: int
    control_loss: float
    treatment_loss: float
    control_false_acceptance: bool
    treatment_false_acceptance: bool
    validity_record: InfrastructureValidityRecord
    evidence_refs: tuple[str, ...]
    control_cost_usd: float | None = None
    treatment_cost_usd: float | None = None
    control_latency_seconds: float | None = None
    treatment_latency_seconds: float | None = None
    record_type: str = STATE_POLICY_TRIAL_SCHEMA

    def __post_init__(self) -> None:
        if self.record_type != STATE_POLICY_TRIAL_SCHEMA:
            raise InformationTheoryEvidenceError("state policy trial type is unsupported")
        for name in (
            "trial_id",
            "namespace_ref",
            "privacy_class",
            "task_region_ref",
            "population_ref",
            "pair_source_ref",
            "full_history_policy_ref",
            "state_policy_ref",
            "model_profile_ref",
            "evaluator_ref",
            "outcome_contract_ref",
            "control_occurrence_ref",
            "treatment_occurrence_ref",
        ):
            _text(getattr(self, name), name)
        for name in (
            "population_digest",
            "source_state_digest",
            "model_profile_digest",
            "evaluator_digest",
            "outcome_contract_digest",
        ):
            _digest(getattr(self, name), name)
        if self.control_occurrence_ref == self.treatment_occurrence_ref:
            raise InformationTheoryEvidenceError("paired arms need independent occurrences")
        _optional_text(self.control_outcome_ref, "control_outcome_ref")
        _optional_text(self.treatment_outcome_ref, "treatment_outcome_ref")
        for name in ("control_context_bytes", "treatment_context_bytes"):
            _count(getattr(self, name), name, positive=True)
        for name in ("control_loss", "treatment_loss"):
            _number(getattr(self, name), name, minimum=0.0)
        for name in (
            "control_false_acceptance",
            "treatment_false_acceptance",
        ):
            if not isinstance(getattr(self, name), bool):
                raise InformationTheoryEvidenceError(f"{name} must be Boolean")
        for name in (
            "control_cost_usd",
            "treatment_cost_usd",
            "control_latency_seconds",
            "treatment_latency_seconds",
        ):
            _optional_number(getattr(self, name), name)
        if not isinstance(self.validity_record, InfrastructureValidityRecord):
            raise InformationTheoryEvidenceError("validity_record has the wrong type")
        if self.validity_record.subject_ref != self.pair_source_ref:
            raise InformationTheoryEvidenceError("validity record names another source")
        if self.validity_record.subject_digest != self.validity_subject_digest:
            raise InformationTheoryEvidenceError("validity record binds other material")
        if (
            self.validity_record.evaluator_ref != self.evaluator_ref
            or self.validity_record.evaluator_digest != self.evaluator_digest
        ):
            raise InformationTheoryEvidenceError("validity record binds another evaluator")
        if self.validity_record.is_valid:
            _text(self.control_outcome_ref, "control_outcome_ref")
            _text(self.treatment_outcome_ref, "treatment_outcome_ref")
            if self.control_outcome_ref == self.treatment_outcome_ref:
                raise InformationTheoryEvidenceError("paired outcomes must be distinct")
        elif self.control_outcome_ref or self.treatment_outcome_ref:
            raise InformationTheoryEvidenceError("invalid trials cannot carry outcomes")
        if not self.validity_record.is_valid and (
            self.control_loss != 0.0
            or self.treatment_loss != 0.0
            or self.control_false_acceptance
            or self.treatment_false_acceptance
        ):
            raise InformationTheoryEvidenceError("invalid trials cannot carry semantic loss")
        object.__setattr__(
            self,
            "evidence_refs",
            _texts(self.evidence_refs, "evidence_refs", required=True),
        )

    @property
    def infrastructure_valid(self) -> bool:
        return self.validity_record.is_valid

    @property
    def invalid_reason(self) -> str:
        return self.validity_record.reason_code

    @property
    def validity_subject_digest(self) -> str:
        return _content_digest(
            {
                "namespace_ref": self.namespace_ref,
                "privacy_class": self.privacy_class,
                "task_region_ref": self.task_region_ref,
                "population_ref": self.population_ref,
                "population_digest": self.population_digest,
                "pair_source_ref": self.pair_source_ref,
                "source_state_digest": self.source_state_digest,
                "full_history_policy_ref": self.full_history_policy_ref,
                "state_policy_ref": self.state_policy_ref,
                "model_profile_ref": self.model_profile_ref,
                "model_profile_digest": self.model_profile_digest,
                "evaluator_ref": self.evaluator_ref,
                "evaluator_digest": self.evaluator_digest,
                "outcome_contract_ref": self.outcome_contract_ref,
                "outcome_contract_digest": self.outcome_contract_digest,
                "control_occurrence_ref": self.control_occurrence_ref,
                "treatment_occurrence_ref": self.treatment_occurrence_ref,
                "control_outcome_ref": self.control_outcome_ref,
                "treatment_outcome_ref": self.treatment_outcome_ref,
                "control_context_bytes": self.control_context_bytes,
                "treatment_context_bytes": self.treatment_context_bytes,
                "control_loss": self.control_loss,
                "treatment_loss": self.treatment_loss,
                "control_false_acceptance": self.control_false_acceptance,
                "treatment_false_acceptance": self.treatment_false_acceptance,
                "control_cost_usd": self.control_cost_usd,
                "treatment_cost_usd": self.treatment_cost_usd,
                "control_latency_seconds": self.control_latency_seconds,
                "treatment_latency_seconds": self.treatment_latency_seconds,
            }
        )

    @property
    def context_compression_ratio(self) -> float:
        return self.control_context_bytes / self.treatment_context_bytes

    @property
    def excess_loss(self) -> float:
        return self.treatment_loss - self.control_loss

    def identity_dict(self) -> dict[str, object]:
        return {
            name: (
                value.to_dict()
                if isinstance(value, InfrastructureValidityRecord)
                else list(value)
                if isinstance(value, tuple)
                else value
            )
            for name, value in self.__dict__.items()
            if name != "record_type"
        }

    @property
    def comparison_identity_digest(self) -> str:
        """Identity of the paired evidence, excluding its replaceable label."""
        return _content_digest(
            {
                "namespace_ref": self.namespace_ref,
                "population_ref": self.population_ref,
                "population_digest": self.population_digest,
                "pair_source_ref": self.pair_source_ref,
                "source_state_digest": self.source_state_digest,
                "full_history_policy_ref": self.full_history_policy_ref,
                "state_policy_ref": self.state_policy_ref,
                "model_profile_ref": self.model_profile_ref,
                "model_profile_digest": self.model_profile_digest,
                "evaluator_ref": self.evaluator_ref,
                "evaluator_digest": self.evaluator_digest,
                "outcome_contract_ref": self.outcome_contract_ref,
                "outcome_contract_digest": self.outcome_contract_digest,
                "control_occurrence_ref": self.control_occurrence_ref,
                "treatment_occurrence_ref": self.treatment_occurrence_ref,
            }
        )


@dataclass(frozen=True)
class StatePolicyTolerance:
    policy_id: str
    version: str
    minimum_valid_pairs: int
    maximum_mean_excess_loss: float
    maximum_treatment_loss: float
    maximum_false_acceptance_delta: float
    maximum_treatment_false_acceptance_rate: float
    minimum_aggregate_compression_ratio: float

    def __post_init__(self) -> None:
        _text(self.policy_id, "policy_id")
        _text(self.version, "version")
        _count(self.minimum_valid_pairs, "minimum_valid_pairs", positive=True)
        for name in (
            "maximum_mean_excess_loss",
            "maximum_treatment_loss",
            "maximum_false_acceptance_delta",
            "maximum_treatment_false_acceptance_rate",
            "minimum_aggregate_compression_ratio",
        ):
            object.__setattr__(
                self,
                name,
                _number(getattr(self, name), name, minimum=0.0),
            )
        if (
            self.maximum_false_acceptance_delta > 1.0
            or self.maximum_treatment_false_acceptance_rate > 1.0
        ):
            raise InformationTheoryEvidenceError("false-acceptance limits exceed one")

    @property
    def digest(self) -> str:
        return _content_digest(self.to_dict())

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": "state_policy_tolerance/v1",
            **self.__dict__,
        }


@dataclass(frozen=True, init=False)
class StatePolicyAssessment:
    assessment_id: str
    measurement_spec_ref: str
    measurement_spec_digest: str
    population_ref: str
    population_digest: str
    namespace_ref: str
    privacy_class: str
    task_region_ref: str
    full_history_policy_ref: str
    state_policy_ref: str
    model_profile_ref: str
    model_profile_digest: str
    evaluator_ref: str
    evaluator_digest: str
    outcome_contract_ref: str
    outcome_contract_digest: str
    tolerance_policy_ref: str
    tolerance_policy_id: str
    tolerance_policy_version: str
    tolerance_policy_digest: str
    source_trial_population_digest: str
    total_pairs: int
    minimum_valid_pairs: int
    minimum_valid_population_coverage: float
    maximum_mean_excess_loss: float
    maximum_treatment_loss: float
    maximum_false_acceptance_delta: float
    maximum_treatment_false_acceptance_rate: float
    minimum_aggregate_compression_ratio: float
    included_trial_refs: tuple[str, ...]
    excluded_trial_refs: tuple[str, ...]
    valid_pairs: int
    valid_population_coverage: float
    mean_control_context_bytes: float
    mean_treatment_context_bytes: float
    aggregate_context_compression_ratio: float | None
    mean_excess_loss: float
    maximum_observed_treatment_loss: float
    false_acceptance_delta: float
    treatment_false_acceptance_rate: float
    mean_cost_delta_usd: float | None
    mean_latency_delta_seconds: float | None
    economics_complete: bool
    latency_complete: bool
    economic_claim_supported: bool
    status: str
    record_type: str = STATE_POLICY_ASSESSMENT_SCHEMA

    def __init__(self) -> None:
        raise TypeError("use assess_state_policy to create this result")

    def __post_init__(self) -> None:
        if self.record_type != STATE_POLICY_ASSESSMENT_SCHEMA:
            raise InformationTheoryEvidenceError("assessment type is unsupported")
        for name in (
            "assessment_id",
            "measurement_spec_ref",
            "population_ref",
            "namespace_ref",
            "privacy_class",
            "task_region_ref",
            "full_history_policy_ref",
            "state_policy_ref",
            "model_profile_ref",
            "evaluator_ref",
            "outcome_contract_ref",
            "tolerance_policy_ref",
            "tolerance_policy_id",
            "tolerance_policy_version",
        ):
            _text(getattr(self, name), name)
        for name in (
            "measurement_spec_digest",
            "population_digest",
            "model_profile_digest",
            "evaluator_digest",
            "outcome_contract_digest",
            "tolerance_policy_digest",
            "source_trial_population_digest",
        ):
            _digest(getattr(self, name), name)
        included = _texts(self.included_trial_refs, "included_trial_refs")
        excluded = _texts(self.excluded_trial_refs, "excluded_trial_refs")
        if set(included) & set(excluded):
            raise InformationTheoryEvidenceError("trial populations overlap")
        object.__setattr__(self, "included_trial_refs", included)
        object.__setattr__(self, "excluded_trial_refs", excluded)
        _count(self.total_pairs, "total_pairs", positive=True)
        _count(self.valid_pairs, "valid_pairs")
        _count(self.minimum_valid_pairs, "minimum_valid_pairs", positive=True)
        if self.total_pairs != len(included) + len(excluded):
            raise InformationTheoryEvidenceError("total pair count is inconsistent")
        if self.valid_pairs != len(included):
            raise InformationTheoryEvidenceError("valid pair count is inconsistent")
        for name in (
            "mean_control_context_bytes",
            "mean_treatment_context_bytes",
        ):
            _number(getattr(self, name), name, minimum=0.0)
        if self.aggregate_context_compression_ratio is not None:
            _number(
                self.aggregate_context_compression_ratio,
                "aggregate_context_compression_ratio",
                minimum=0.0,
            )
        _number(self.mean_excess_loss, "mean_excess_loss")
        _number(
            self.maximum_observed_treatment_loss,
            "maximum_observed_treatment_loss",
            minimum=0.0,
        )
        false_delta = _number(self.false_acceptance_delta, "false_acceptance_delta")
        if not -1.0 <= false_delta <= 1.0:
            raise InformationTheoryEvidenceError(
                "false_acceptance_delta must be between minus one and one"
            )
        for name in ("mean_cost_delta_usd", "mean_latency_delta_seconds"):
            if getattr(self, name) is not None:
                _number(getattr(self, name), name)
        treatment_false_rate = _number(
            self.treatment_false_acceptance_rate,
            "treatment_false_acceptance_rate",
            minimum=0.0,
        )
        if treatment_false_rate > 1.0:
            raise InformationTheoryEvidenceError("false-acceptance rate exceeds one")
        for name in (
            "economics_complete",
            "latency_complete",
            "economic_claim_supported",
        ):
            if not isinstance(getattr(self, name), bool):
                raise InformationTheoryEvidenceError(f"{name} must be Boolean")
        if self.economics_complete != (self.mean_cost_delta_usd is not None):
            raise InformationTheoryEvidenceError("cost completeness is inconsistent")
        if self.latency_complete != (self.mean_latency_delta_seconds is not None):
            raise InformationTheoryEvidenceError("latency completeness is inconsistent")
        if self.economic_claim_supported:
            raise InformationTheoryEvidenceError("economic claims are not supported here")
        if self.status not in (
            SUPPORTED_WITHIN_TOLERANCE,
            NOT_SUPPORTED_WITHIN_TOLERANCE,
            INSUFFICIENT_VALID_EVIDENCE,
        ):
            raise InformationTheoryEvidenceError("assessment status is unknown")
        for name in (
            "maximum_mean_excess_loss",
            "maximum_treatment_loss",
            "maximum_false_acceptance_delta",
            "maximum_treatment_false_acceptance_rate",
            "minimum_aggregate_compression_ratio",
        ):
            _number(getattr(self, name), name, minimum=0.0)
        if (
            self.maximum_false_acceptance_delta > 1.0
            or self.maximum_treatment_false_acceptance_rate > 1.0
        ):
            raise InformationTheoryEvidenceError("false-acceptance limits exceed one")
        valid_coverage = _number(
            self.valid_population_coverage,
            "valid_population_coverage",
            minimum=0.0,
        )
        minimum_coverage = _number(
            self.minimum_valid_population_coverage,
            "minimum_valid_population_coverage",
            minimum=0.0,
        )
        if valid_coverage > 1.0 or minimum_coverage <= 0.0 or minimum_coverage > 1.0:
            raise InformationTheoryEvidenceError("valid coverage is outside its range")
        expected_coverage = self.valid_pairs / self.total_pairs
        if not math.isclose(
            self.valid_population_coverage,
            expected_coverage,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise InformationTheoryEvidenceError("valid pair coverage is inconsistent")
        if self.tolerance_policy_ref != (
            f"{self.tolerance_policy_id}@{self.tolerance_policy_version}"
        ):
            raise InformationTheoryEvidenceError("tolerance identity is inconsistent")
        embedded_tolerance = StatePolicyTolerance(
            policy_id=self.tolerance_policy_id,
            version=self.tolerance_policy_version,
            minimum_valid_pairs=self.minimum_valid_pairs,
            maximum_mean_excess_loss=self.maximum_mean_excess_loss,
            maximum_treatment_loss=self.maximum_treatment_loss,
            maximum_false_acceptance_delta=self.maximum_false_acceptance_delta,
            maximum_treatment_false_acceptance_rate=(
                self.maximum_treatment_false_acceptance_rate
            ),
            minimum_aggregate_compression_ratio=(
                self.minimum_aggregate_compression_ratio
            ),
        )
        if embedded_tolerance.digest != self.tolerance_policy_digest:
            raise InformationTheoryEvidenceError("tolerance digest is inconsistent")
        expected_compression = (
            self.mean_control_context_bytes / self.mean_treatment_context_bytes
            if self.valid_pairs
            else None
        )
        if (
            (expected_compression is None)
            != (self.aggregate_context_compression_ratio is None)
            or expected_compression is not None
            and not math.isclose(
                self.aggregate_context_compression_ratio or 0.0,
                expected_compression,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            raise InformationTheoryEvidenceError("compression ratio is inconsistent")
        enough = (
            self.valid_pairs >= self.minimum_valid_pairs
            and self.valid_population_coverage + _EPSILON
            >= self.minimum_valid_population_coverage
        )
        within = (
            enough
            and self.mean_excess_loss <= self.maximum_mean_excess_loss + _EPSILON
            and self.maximum_observed_treatment_loss
            <= self.maximum_treatment_loss + _EPSILON
            and self.false_acceptance_delta
            <= self.maximum_false_acceptance_delta + _EPSILON
            and self.treatment_false_acceptance_rate
            <= self.maximum_treatment_false_acceptance_rate + _EPSILON
            and self.aggregate_context_compression_ratio is not None
            and self.aggregate_context_compression_ratio + _EPSILON
            >= self.minimum_aggregate_compression_ratio
        )
        expected_status = (
            SUPPORTED_WITHIN_TOLERANCE
            if within
            else NOT_SUPPORTED_WITHIN_TOLERANCE
            if enough
            else INSUFFICIENT_VALID_EVIDENCE
        )
        if self.status != expected_status:
            raise InformationTheoryEvidenceError("status disagrees with tolerance")

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": self.record_type,
            **{
                name: list(value) if isinstance(value, tuple) else value
                for name, value in self.__dict__.items()
                if name != "record_type"
            },
            "measurement_only": True,
            "rate_distortion_function_estimated": False,
            "source_references_resolved_by_this_record": False,
            "issued_assessment": False,
            "generalization_claimed": False,
            "promotion_authorized": False,
        }


def _mean_known(
    rows: tuple[PairedStatePolicyTrial, ...],
    left: str,
    right: str,
) -> float | None:
    differences = []
    for row in rows:
        first = getattr(row, left)
        second = getattr(row, right)
        if first is None or second is None:
            return None
        differences.append(second - first)
    return math.fsum(differences) / len(differences)


def assess_state_policy(
    trials: Iterable[PairedStatePolicyTrial],
    tolerance: StatePolicyTolerance,
    measurement_spec: InformationMeasurementSpec,
    *,
    assessment_id: str,
) -> StatePolicyAssessment:
    """Assess one state policy against one full-history policy."""
    if not isinstance(tolerance, StatePolicyTolerance):
        raise InformationTheoryEvidenceError("assessment needs StatePolicyTolerance")
    if not isinstance(measurement_spec, InformationMeasurementSpec):
        raise InformationTheoryEvidenceError(
            "assessment needs InformationMeasurementSpec"
        )
    if measurement_spec.measure_kind != "paired_state_compression_distortion":
        raise InformationTheoryEvidenceError(
            "state-policy assessment needs a paired compression-distortion spec"
        )
    _text(assessment_id, "assessment_id")
    if isinstance(trials, (str, bytes)):
        raise InformationTheoryEvidenceError("trials must be typed records")
    rows = tuple(trials)
    if not rows or any(not isinstance(row, PairedStatePolicyTrial) for row in rows):
        raise InformationTheoryEvidenceError(
            "state policy assessment needs typed trials"
        )
    if len({row.trial_id for row in rows}) != len(rows):
        raise InformationTheoryEvidenceError("trial identities cannot repeat")
    if len({row.pair_source_ref for row in rows}) != len(rows):
        raise InformationTheoryEvidenceError("paired source identities cannot repeat")
    if len({row.comparison_identity_digest for row in rows}) != len(rows):
        raise InformationTheoryEvidenceError(
            "the same paired comparison cannot be relabeled as another trial"
        )
    occurrence_refs = tuple(
        reference
        for row in rows
        for reference in (row.control_occurrence_ref, row.treatment_occurrence_ref)
    )
    if len(occurrence_refs) != len(set(occurrence_refs)):
        raise InformationTheoryEvidenceError(
            "an occurrence cannot contribute to more than one paired arm"
        )
    source_trial_population_digest = _content_digest(
        [
            row.identity_dict()
            for row in sorted(rows, key=lambda candidate: candidate.trial_id)
        ]
    )
    valid = tuple(row for row in rows if row.infrastructure_valid)
    excluded = tuple(row for row in rows if not row.infrastructure_valid)
    outcome_refs = tuple(
        reference
        for row in valid
        for reference in (row.control_outcome_ref, row.treatment_outcome_ref)
    )
    if len(outcome_refs) != len(set(outcome_refs)):
        raise InformationTheoryEvidenceError(
            "an admitted outcome cannot contribute to more than one paired arm"
        )
    compared_fields = (
        "population_ref",
        "population_digest",
        "namespace_ref",
        "privacy_class",
        "task_region_ref",
        "full_history_policy_ref",
        "state_policy_ref",
        "model_profile_ref",
        "model_profile_digest",
        "evaluator_ref",
        "evaluator_digest",
        "outcome_contract_ref",
        "outcome_contract_digest",
    )
    source = rows
    for name in compared_fields:
        if len({getattr(row, name) for row in source}) != 1:
            raise InformationTheoryEvidenceError(f"trials disagree on {name}")
    if (
        measurement_spec.namespace_ref != source[0].namespace_ref
        or measurement_spec.privacy_class != source[0].privacy_class
        or measurement_spec.population_ref != source[0].population_ref
        or measurement_spec.population_digest != source[0].population_digest
        or measurement_spec.task_region_ref != source[0].task_region_ref
        or measurement_spec.target_ref != source[0].outcome_contract_ref
        or measurement_spec.target_digest != source[0].outcome_contract_digest
        or measurement_spec.evaluator_ref != source[0].evaluator_ref
        or measurement_spec.evaluator_digest != source[0].evaluator_digest
    ):
        raise InformationTheoryEvidenceError(
            "measurement specification does not match the paired trial population"
        )
    pair_count = len(valid)
    valid_coverage = pair_count / len(rows)
    if pair_count:
        control_bytes = (
            math.fsum(row.control_context_bytes for row in valid) / pair_count
        )
        treatment_bytes = (
            math.fsum(row.treatment_context_bytes for row in valid) / pair_count
        )
        compression = control_bytes / treatment_bytes
        excess_loss = math.fsum(row.excess_loss for row in valid) / pair_count
        maximum_treatment_loss = max(row.treatment_loss for row in valid)
        false_delta = (
            sum(row.treatment_false_acceptance for row in valid)
            - sum(row.control_false_acceptance for row in valid)
        ) / pair_count
        treatment_false_rate = (
            sum(row.treatment_false_acceptance for row in valid) / pair_count
        )
    else:
        control_bytes = treatment_bytes = 0.0
        compression = None
        excess_loss = maximum_treatment_loss = 0.0
        false_delta = treatment_false_rate = 0.0
    enough = (
        pair_count >= tolerance.minimum_valid_pairs
        and valid_coverage + _EPSILON
        >= measurement_spec.minimum_valid_population_coverage
    )
    within = (
        enough
        and excess_loss <= tolerance.maximum_mean_excess_loss + _EPSILON
        and maximum_treatment_loss <= tolerance.maximum_treatment_loss + _EPSILON
        and false_delta <= tolerance.maximum_false_acceptance_delta + _EPSILON
        and treatment_false_rate
        <= tolerance.maximum_treatment_false_acceptance_rate + _EPSILON
        and compression is not None
        and compression + _EPSILON >= tolerance.minimum_aggregate_compression_ratio
    )
    status = (
        SUPPORTED_WITHIN_TOLERANCE
        if within
        else NOT_SUPPORTED_WITHIN_TOLERANCE
        if enough
        else INSUFFICIENT_VALID_EVIDENCE
    )
    values = {
            "assessment_id": assessment_id,
            "measurement_spec_ref": measurement_spec.measurement_id,
            "measurement_spec_digest": measurement_spec.digest,
            "population_ref": source[0].population_ref,
            "population_digest": source[0].population_digest,
            "namespace_ref": source[0].namespace_ref,
            "privacy_class": source[0].privacy_class,
            "task_region_ref": source[0].task_region_ref,
            "full_history_policy_ref": source[0].full_history_policy_ref,
            "state_policy_ref": source[0].state_policy_ref,
            "model_profile_ref": source[0].model_profile_ref,
            "model_profile_digest": source[0].model_profile_digest,
            "evaluator_ref": source[0].evaluator_ref,
            "evaluator_digest": source[0].evaluator_digest,
            "outcome_contract_ref": source[0].outcome_contract_ref,
            "outcome_contract_digest": source[0].outcome_contract_digest,
            "tolerance_policy_ref": f"{tolerance.policy_id}@{tolerance.version}",
            "tolerance_policy_id": tolerance.policy_id,
            "tolerance_policy_version": tolerance.version,
            "tolerance_policy_digest": tolerance.digest,
            "source_trial_population_digest": source_trial_population_digest,
            "total_pairs": len(rows),
            "minimum_valid_pairs": tolerance.minimum_valid_pairs,
            "minimum_valid_population_coverage": (
                measurement_spec.minimum_valid_population_coverage
            ),
            "maximum_mean_excess_loss": tolerance.maximum_mean_excess_loss,
            "maximum_treatment_loss": tolerance.maximum_treatment_loss,
            "maximum_false_acceptance_delta": (
                tolerance.maximum_false_acceptance_delta
            ),
            "maximum_treatment_false_acceptance_rate": (
                tolerance.maximum_treatment_false_acceptance_rate
            ),
            "minimum_aggregate_compression_ratio": (
                tolerance.minimum_aggregate_compression_ratio
            ),
            "included_trial_refs": tuple(sorted(row.trial_id for row in valid)),
            "excluded_trial_refs": tuple(sorted(row.trial_id for row in excluded)),
            "valid_pairs": pair_count,
            "valid_population_coverage": valid_coverage,
            "mean_control_context_bytes": control_bytes,
            "mean_treatment_context_bytes": treatment_bytes,
            "aggregate_context_compression_ratio": compression,
            "mean_excess_loss": excess_loss,
            "maximum_observed_treatment_loss": maximum_treatment_loss,
            "false_acceptance_delta": false_delta,
            "treatment_false_acceptance_rate": treatment_false_rate,
            "mean_cost_delta_usd": (
                _mean_known(valid, "control_cost_usd", "treatment_cost_usd")
                if valid
                else None
            ),
            "mean_latency_delta_seconds": (
                _mean_known(
                    valid, "control_latency_seconds", "treatment_latency_seconds"
                )
                if valid
                else None
            ),
            "economics_complete": bool(valid)
            and all(
                row.control_cost_usd is not None
                and row.treatment_cost_usd is not None
                for row in valid
            ),
            "latency_complete": bool(valid)
            and all(
                row.control_latency_seconds is not None
                and row.treatment_latency_seconds is not None
                for row in valid
            ),
            "economic_claim_supported": False,
            "status": status,
    }
    result = object.__new__(StatePolicyAssessment)
    for name, value in values.items():
        object.__setattr__(result, name, value)
    object.__setattr__(result, "record_type", STATE_POLICY_ASSESSMENT_SCHEMA)
    result.__post_init__()
    return result


__all__ = (
    "INSUFFICIENT_VALID_EVIDENCE",
    "NOT_SUPPORTED_WITHIN_TOLERANCE",
    "STATE_POLICY_ASSESSMENT_SCHEMA",
    "STATE_POLICY_TRIAL_SCHEMA",
    "SUPPORTED_WITHIN_TOLERANCE",
    "PairedStatePolicyTrial",
    "StatePolicyAssessment",
    "StatePolicyTolerance",
    "assess_state_policy",
)
