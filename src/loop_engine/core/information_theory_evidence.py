"""Passive information measurements for state and context experiments.

This module computes evidence from already observed, typed records. It does
not select context, update memory, call a model, change trusted state, promote
a procedure, or create another runtime. A classified Loop owns any experiment
that creates or acts on these measurements.

The estimators are deliberately narrow. Entropy and mutual information are
empirical plug-in estimates over declared discrete classes. Paired state-policy
assessment measures observed decision loss and context size. Neither result is
a universal claim about sufficiency or generalization.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from .information_evidence_contracts import (
    _EPSILON,
    INFORMATION_MEASUREMENT_SPEC_SCHEMA,
    InformationMeasurementSpec,
    InformationTheoryEvidenceError,
    InfrastructureValidityRecord,
    _content_digest,
    _count,
    _digest,
    _number,
    _optional_text,
    _text,
    _texts,
)
from .information_update_evidence import (
    INFORMATION_UPDATE_SCHEMA,
    CategoricalDistribution,
    InformationUpdateEvidence,
)

EMPIRICAL_INFORMATION_SCHEMA = "empirical_predictive_information/v1"
STATE_POLICY_TRIAL_SCHEMA = "paired_state_policy_trial/v1"
STATE_POLICY_ASSESSMENT_SCHEMA = "state_policy_assessment/v1"

DETERMINISTIC_PROJECTION = "deterministic"
STOCHASTIC_PROJECTION = "stochastic"
PROJECTION_MODES = (DETERMINISTIC_PROJECTION, STOCHASTIC_PROJECTION)

SUPPORTED_WITHIN_TOLERANCE = "SUPPORTED_WITHIN_DECLARED_TOLERANCE"
NOT_SUPPORTED_WITHIN_TOLERANCE = "NOT_SUPPORTED_WITHIN_DECLARED_TOLERANCE"
INSUFFICIENT_VALID_EVIDENCE = "INSUFFICIENT_VALID_EVIDENCE"


@dataclass(frozen=True)
class PredictiveStateSample:
    """One discrete outcome joined to history and state representations."""

    sample_id: str
    namespace_ref: str
    privacy_class: str
    task_region_ref: str
    population_ref: str
    population_digest: str
    source_occurrence_ref: str
    projection_policy_ref: str
    projection_policy_digest: str
    projection_mode: str
    history_representation_ref: str
    history_representation_digest: str
    history_class: str
    state_ref: str
    state_digest: str
    state_class: str
    outcome_contract_ref: str
    outcome_contract_digest: str
    outcome_ref: str
    outcome_class: str
    evaluator_ref: str
    evaluator_digest: str
    temporal_order_evidence_ref: str
    temporal_order_evidence_digest: str
    validity_record: InfrastructureValidityRecord
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "sample_id",
            "namespace_ref",
            "privacy_class",
            "task_region_ref",
            "population_ref",
            "source_occurrence_ref",
            "projection_policy_ref",
            "history_representation_ref",
            "history_class",
            "state_ref",
            "state_class",
            "outcome_contract_ref",
            "evaluator_ref",
            "temporal_order_evidence_ref",
        ):
            _text(getattr(self, name), name)
        for name in (
            "population_digest",
            "projection_policy_digest",
            "history_representation_digest",
            "state_digest",
            "outcome_contract_digest",
            "evaluator_digest",
            "temporal_order_evidence_digest",
        ):
            _digest(getattr(self, name), name)
        if self.projection_mode not in PROJECTION_MODES:
            raise InformationTheoryEvidenceError(
                f"projection_mode must be one of {PROJECTION_MODES}"
            )
        _optional_text(self.outcome_ref, "outcome_ref")
        _optional_text(self.outcome_class, "outcome_class")
        if not isinstance(self.validity_record, InfrastructureValidityRecord):
            raise InformationTheoryEvidenceError(
                "validity_record must use InfrastructureValidityRecord"
            )
        if self.validity_record.subject_ref != self.source_occurrence_ref:
            raise InformationTheoryEvidenceError(
                "validity record does not identify the source occurrence"
            )
        if self.validity_record.subject_digest != self.validity_subject_digest:
            raise InformationTheoryEvidenceError(
                "validity record does not bind the sample source material"
            )
        if (
            self.validity_record.evaluator_ref != self.evaluator_ref
            or self.validity_record.evaluator_digest != self.evaluator_digest
        ):
            raise InformationTheoryEvidenceError(
                "validity record does not bind the sample evaluator"
            )
        if self.validity_record.is_valid:
            _text(self.outcome_ref, "outcome_ref")
            _text(self.outcome_class, "outcome_class")
        elif self.outcome_ref or self.outcome_class:
            raise InformationTheoryEvidenceError(
                "infrastructure-invalid samples cannot carry admitted outcomes"
            )
        object.__setattr__(
            self,
            "evidence_refs",
            _texts(self.evidence_refs, "evidence_refs", required=True),
        )

    @property
    def infrastructure_valid(self) -> bool:
        return self.validity_record.is_valid

    @property
    def exclusion_reason(self) -> str:
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
                "source_occurrence_ref": self.source_occurrence_ref,
                "projection_policy_ref": self.projection_policy_ref,
                "projection_policy_digest": self.projection_policy_digest,
                "projection_mode": self.projection_mode,
                "history_representation_ref": self.history_representation_ref,
                "history_representation_digest": self.history_representation_digest,
                "history_class": self.history_class,
                "state_ref": self.state_ref,
                "state_digest": self.state_digest,
                "state_class": self.state_class,
                "outcome_contract_ref": self.outcome_contract_ref,
                "outcome_contract_digest": self.outcome_contract_digest,
                "outcome_ref": self.outcome_ref,
                "outcome_class": self.outcome_class,
                "evaluator_ref": self.evaluator_ref,
                "evaluator_digest": self.evaluator_digest,
                "temporal_order_evidence_ref": self.temporal_order_evidence_ref,
                "temporal_order_evidence_digest": self.temporal_order_evidence_digest,
            }
        )

    @property
    def source_identity_digest(self) -> str:
        return _content_digest(
            {
                "namespace_ref": self.namespace_ref,
                "population_ref": self.population_ref,
                "population_digest": self.population_digest,
                "source_occurrence_ref": self.source_occurrence_ref,
                "history_representation_ref": self.history_representation_ref,
                "history_representation_digest": self.history_representation_digest,
                "outcome_ref": self.outcome_ref,
                "evaluator_ref": self.evaluator_ref,
                "evaluator_digest": self.evaluator_digest,
                "temporal_order_evidence_ref": self.temporal_order_evidence_ref,
                "temporal_order_evidence_digest": self.temporal_order_evidence_digest,
            }
        )

    def identity_dict(self) -> dict[str, object]:
        return {
            "sample_id": self.sample_id,
            "namespace_ref": self.namespace_ref,
            "privacy_class": self.privacy_class,
            "task_region_ref": self.task_region_ref,
            "population_ref": self.population_ref,
            "population_digest": self.population_digest,
            "source_occurrence_ref": self.source_occurrence_ref,
            "projection_policy_ref": self.projection_policy_ref,
            "projection_policy_digest": self.projection_policy_digest,
            "projection_mode": self.projection_mode,
            "history_representation_ref": self.history_representation_ref,
            "history_representation_digest": self.history_representation_digest,
            "history_class": self.history_class,
            "state_ref": self.state_ref,
            "state_digest": self.state_digest,
            "state_class": self.state_class,
            "outcome_contract_ref": self.outcome_contract_ref,
            "outcome_contract_digest": self.outcome_contract_digest,
            "outcome_ref": self.outcome_ref,
            "outcome_class": self.outcome_class,
            "evaluator_ref": self.evaluator_ref,
            "evaluator_digest": self.evaluator_digest,
            "temporal_order_evidence_ref": self.temporal_order_evidence_ref,
            "temporal_order_evidence_digest": self.temporal_order_evidence_digest,
            "validity_record": self.validity_record.to_dict(),
            "evidence_refs": list(self.evidence_refs),
            "source_identity_digest": self.source_identity_digest,
        }


def _entropy_from_counts(counts: Counter[str]) -> float:
    total = sum(counts.values())
    if total < 1:
        raise InformationTheoryEvidenceError("entropy needs observations")
    return -math.fsum(
        (count / total) * math.log2(count / total) for count in counts.values() if count
    )


def _conditional_entropy(
    samples: tuple[PredictiveStateSample, ...],
    class_value: Callable[[PredictiveStateSample], str],
) -> float:
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    for sample in samples:
        grouped[class_value(sample)][sample.outcome_class] += 1
    total = len(samples)
    return math.fsum(
        (sum(counts.values()) / total) * _entropy_from_counts(counts)
        for counts in grouped.values()
    )


@dataclass(frozen=True, init=False)
class EmpiricalPredictiveInformation:
    """Empirical information retained by a declared state representation."""

    measurement_spec_ref: str
    measurement_spec_digest: str
    source_population_ref: str
    source_population_digest: str
    sample_population_digest: str
    task_region_ref: str
    projection_policy_ref: str
    projection_policy_digest: str
    projection_mode: str
    outcome_contract_ref: str
    outcome_contract_digest: str
    evaluator_ref: str
    evaluator_digest: str
    included_sample_refs: tuple[str, ...]
    excluded_sample_refs: tuple[str, ...]
    total_sample_count: int
    sample_count: int
    valid_population_coverage: float
    minimum_valid_population_coverage: float
    history_class_count: int
    state_class_count: int
    outcome_class_count: int
    outcome_entropy_bits: float
    conditional_entropy_outcome_given_history_bits: float
    conditional_entropy_outcome_given_state_bits: float
    mutual_information_history_outcome_bits: float
    mutual_information_state_outcome_bits: float
    residual_predictive_information_bits: float | None
    residual_predictive_information_interpretation_applicable: bool
    state_information_retention: float | None
    data_processing_check_applicable: bool
    data_processing_inequality_holds: bool | None
    record_type: str = EMPIRICAL_INFORMATION_SCHEMA

    def __init__(self) -> None:
        raise TypeError("use estimate_predictive_information to create this result")

    def __post_init__(self) -> None:
        if self.record_type != EMPIRICAL_INFORMATION_SCHEMA:
            raise InformationTheoryEvidenceError(
                "predictive information record type is unsupported"
            )
        for name in (
            "measurement_spec_digest",
            "source_population_digest",
            "sample_population_digest",
            "projection_policy_digest",
        ):
            _digest(getattr(self, name), name)
        for name in (
            "measurement_spec_ref",
            "source_population_ref",
            "task_region_ref",
            "projection_policy_ref",
            "outcome_contract_ref",
            "evaluator_ref",
        ):
            _text(getattr(self, name), name)
        if self.projection_mode not in PROJECTION_MODES:
            raise InformationTheoryEvidenceError(
                "predictive information projection mode is unknown"
            )
        for name in ("outcome_contract_digest", "evaluator_digest"):
            _digest(getattr(self, name), name)
        included = _texts(
            self.included_sample_refs,
            "included_sample_refs",
            required=True,
        )
        excluded = _texts(self.excluded_sample_refs, "excluded_sample_refs")
        if set(included) & set(excluded):
            raise InformationTheoryEvidenceError(
                "included and excluded samples cannot overlap"
            )
        object.__setattr__(self, "included_sample_refs", included)
        object.__setattr__(self, "excluded_sample_refs", excluded)
        for name in (
            "total_sample_count",
            "sample_count",
            "history_class_count",
            "state_class_count",
            "outcome_class_count",
        ):
            _count(getattr(self, name), name, positive=True)
        if self.total_sample_count != len(included) + len(excluded):
            raise InformationTheoryEvidenceError(
                "total_sample_count must equal included plus excluded samples"
            )
        if self.sample_count != len(included):
            raise InformationTheoryEvidenceError(
                "sample_count must equal the included sample count"
            )
        if any(
            getattr(self, name) > self.sample_count
            for name in (
                "history_class_count",
                "state_class_count",
                "outcome_class_count",
            )
        ):
            raise InformationTheoryEvidenceError(
                "class counts cannot exceed the included sample count"
            )
        for name in (
            "outcome_entropy_bits",
            "conditional_entropy_outcome_given_history_bits",
            "conditional_entropy_outcome_given_state_bits",
            "mutual_information_history_outcome_bits",
            "mutual_information_state_outcome_bits",
        ):
            _number(getattr(self, name), name, minimum=0.0)
        if self.residual_predictive_information_bits is not None:
            _number(
                self.residual_predictive_information_bits,
                "residual_predictive_information_bits",
                minimum=0.0,
            )
        for name in (
            "valid_population_coverage",
            "minimum_valid_population_coverage",
        ):
            value = _number(getattr(self, name), name, minimum=0.0)
            if value <= 0.0 or value > 1.0:
                raise InformationTheoryEvidenceError(
                    f"{name} must be above zero and at most one"
                )
        expected_coverage = self.sample_count / self.total_sample_count
        if not math.isclose(
            self.valid_population_coverage,
            expected_coverage,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise InformationTheoryEvidenceError(
                "valid population coverage disagrees with sample counts"
            )
        if (
            self.valid_population_coverage + _EPSILON
            < self.minimum_valid_population_coverage
        ):
            raise InformationTheoryEvidenceError(
                "valid population coverage is below the declared minimum"
            )
        maximum_outcome_entropy = math.log2(self.outcome_class_count)
        if any(
            value > maximum_outcome_entropy + _EPSILON
            for value in (
                self.outcome_entropy_bits,
                self.conditional_entropy_outcome_given_history_bits,
                self.conditional_entropy_outcome_given_state_bits,
                self.mutual_information_history_outcome_bits,
                self.mutual_information_state_outcome_bits,
                *(
                    (self.residual_predictive_information_bits,)
                    if self.residual_predictive_information_bits is not None
                    else ()
                ),
            )
        ):
            raise InformationTheoryEvidenceError(
                "information quantities exceed the declared outcome support"
            )
        if (
            self.mutual_information_history_outcome_bits
            > math.log2(self.history_class_count) + _EPSILON
            or self.mutual_information_state_outcome_bits
            > math.log2(self.state_class_count) + _EPSILON
        ):
            raise InformationTheoryEvidenceError(
                "mutual information exceeds its declared input support"
            )
        if any(
            value > self.outcome_entropy_bits + _EPSILON
            for value in (
                self.conditional_entropy_outcome_given_history_bits,
                self.conditional_entropy_outcome_given_state_bits,
            )
        ):
            raise InformationTheoryEvidenceError(
                "conditional outcome entropy cannot exceed outcome entropy"
            )
        expected_history_information = max(
            0.0,
            self.outcome_entropy_bits
            - self.conditional_entropy_outcome_given_history_bits,
        )
        expected_state_information = max(
            0.0,
            self.outcome_entropy_bits
            - self.conditional_entropy_outcome_given_state_bits,
        )
        expected_residual = (
            max(
                0.0,
                self.conditional_entropy_outcome_given_state_bits
                - self.conditional_entropy_outcome_given_history_bits,
            )
            if self.projection_mode == DETERMINISTIC_PROJECTION
            else None
        )
        for observed, expected in (
            (
                self.mutual_information_history_outcome_bits,
                expected_history_information,
            ),
            (self.mutual_information_state_outcome_bits, expected_state_information),
        ):
            if not math.isclose(observed, expected, rel_tol=0.0, abs_tol=1e-10):
                raise InformationTheoryEvidenceError(
                    "predictive information identities do not reconcile"
                )
        if (
            (expected_residual is None)
            != (self.residual_predictive_information_bits is None)
            or expected_residual is not None
            and not math.isclose(
                self.residual_predictive_information_bits or 0.0,
                expected_residual,
                rel_tol=0.0,
                abs_tol=1e-10,
            )
        ):
            raise InformationTheoryEvidenceError(
                "residual predictive information applicability is inconsistent"
            )
        if self.state_information_retention is not None:
            retention = _number(
                self.state_information_retention,
                "state_information_retention",
                minimum=0.0,
            )
            if retention > 1.0 + _EPSILON:
                raise InformationTheoryEvidenceError(
                    "state information retention cannot exceed one"
                )
        for name in (
            "residual_predictive_information_interpretation_applicable",
            "data_processing_check_applicable",
        ):
            if not isinstance(getattr(self, name), bool):
                raise InformationTheoryEvidenceError(f"{name} must be Boolean")
        if self.data_processing_inequality_holds is not None and not isinstance(
            self.data_processing_inequality_holds, bool
        ):
            raise InformationTheoryEvidenceError(
                "data_processing_inequality_holds must be Boolean or unknown"
            )
        if self.data_processing_check_applicable != (
            self.projection_mode == DETERMINISTIC_PROJECTION
        ):
            raise InformationTheoryEvidenceError(
                "data-processing applicability disagrees with projection mode"
            )
        observed_dpi = (
            self.mutual_information_state_outcome_bits
            <= self.mutual_information_history_outcome_bits + _EPSILON
        )
        if (
            self.data_processing_check_applicable
            and self.data_processing_inequality_holds != observed_dpi
        ):
            raise InformationTheoryEvidenceError(
                "data-processing result disagrees with the information values"
            )
        if (
            self.data_processing_check_applicable
            and not self.data_processing_inequality_holds
        ):
            raise InformationTheoryEvidenceError(
                "a claimed deterministic projection violates data processing"
            )
        if (
            self.residual_predictive_information_interpretation_applicable
            != self.data_processing_check_applicable
        ):
            raise InformationTheoryEvidenceError(
                "residual-information interpretation needs deterministic projection"
            )
        if self.data_processing_check_applicable != (
            self.data_processing_inequality_holds is not None
        ):
            raise InformationTheoryEvidenceError(
                "data-processing result presence is inconsistent"
            )
        expected_retention = (
            self.mutual_information_state_outcome_bits
            / self.mutual_information_history_outcome_bits
            if self.data_processing_check_applicable
            and self.mutual_information_history_outcome_bits > _EPSILON
            else None
        )
        if (
            (expected_retention is None) != (self.state_information_retention is None)
            or expected_retention is not None
            and not math.isclose(
                self.state_information_retention or 0.0,
                expected_retention,
                rel_tol=0.0,
                abs_tol=1e-10,
            )
        ):
            raise InformationTheoryEvidenceError(
                "state information retention is inconsistent"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": self.record_type,
            **{
                name: list(value) if isinstance(value, tuple) else value
                for name, value in self.__dict__.items()
                if name != "record_type"
            },
            "estimator": "empirical_plugin_base2/v1",
            "estimator_bias_warning": ("finite-sample plug-in estimates may be biased"),
            "source_references_resolved_by_this_record": False,
            "estimator_implementation_verified_by_this_record": False,
            "issued_measurement": False,
            "generalization_claimed": False,
            "grants_authority": False,
        }


def estimate_predictive_information(
    samples: Iterable[PredictiveStateSample],
    specification: InformationMeasurementSpec,
) -> EmpiricalPredictiveInformation:
    """Estimate discrete predictive information over valid observed samples."""
    if not isinstance(specification, InformationMeasurementSpec):
        raise InformationTheoryEvidenceError(
            "predictive information needs InformationMeasurementSpec"
        )
    if specification.measure_kind != "predictive_state_information":
        raise InformationTheoryEvidenceError(
            "predictive information needs a predictive-state measurement spec"
        )
    if isinstance(samples, (str, bytes)):
        raise InformationTheoryEvidenceError("samples must be typed records")
    rows = tuple(samples)
    if not rows or any(not isinstance(row, PredictiveStateSample) for row in rows):
        raise InformationTheoryEvidenceError(
            "predictive information needs typed samples"
        )
    if len({row.sample_id for row in rows}) != len(rows):
        raise InformationTheoryEvidenceError("sample identities cannot repeat")
    if len({row.source_occurrence_ref for row in rows}) != len(rows):
        raise InformationTheoryEvidenceError(
            "source occurrence identities cannot repeat"
        )
    if len({row.source_identity_digest for row in rows}) != len(rows):
        raise InformationTheoryEvidenceError(
            "the same physical sample cannot be relabeled and counted twice"
        )
    ordered = tuple(sorted(rows, key=lambda row: row.sample_id))
    sample_population_digest = _content_digest(
        [row.identity_dict() for row in ordered]
    )
    valid = tuple(row for row in rows if row.infrastructure_valid)
    excluded = tuple(row for row in rows if not row.infrastructure_valid)
    if not valid:
        raise InformationTheoryEvidenceError(
            "no infrastructure-valid sample remains for estimation"
        )
    valid_coverage = len(valid) / len(rows)
    if valid_coverage + _EPSILON < specification.minimum_valid_population_coverage:
        raise InformationTheoryEvidenceError(
            "valid sample coverage is below the predeclared minimum"
        )
    shared_fields = (
        "task_region_ref",
        "namespace_ref",
        "privacy_class",
        "population_ref",
        "population_digest",
        "projection_policy_ref",
        "projection_policy_digest",
        "projection_mode",
        "outcome_contract_ref",
        "outcome_contract_digest",
        "evaluator_ref",
        "evaluator_digest",
    )
    for name in shared_fields:
        if len({getattr(row, name) for row in rows}) != 1:
            raise InformationTheoryEvidenceError(f"samples disagree on {name}")
    if (
        specification.namespace_ref != valid[0].namespace_ref
        or specification.privacy_class != valid[0].privacy_class
        or specification.task_region_ref != valid[0].task_region_ref
        or specification.population_ref != valid[0].population_ref
        or specification.population_digest != valid[0].population_digest
        or specification.target_ref != valid[0].outcome_contract_ref
        or specification.target_digest != valid[0].outcome_contract_digest
        or specification.evaluator_ref != valid[0].evaluator_ref
        or specification.evaluator_digest != valid[0].evaluator_digest
    ):
        raise InformationTheoryEvidenceError(
            "measurement specification does not match the sample target or region"
        )
    projection_mode = valid[0].projection_mode
    history_labels: dict[tuple[str, str], str] = {}
    deterministic_states: dict[tuple[str, str], tuple[str, str, str]] = {}
    state_claims: dict[tuple[str, str], str] = {}
    for row in rows:
        history_identity = (
            row.history_representation_ref,
            row.history_representation_digest,
        )
        existing_label = history_labels.setdefault(history_identity, row.history_class)
        if existing_label != row.history_class:
            raise InformationTheoryEvidenceError(
                "one exact history has conflicting class labels"
            )
        if projection_mode == DETERMINISTIC_PROJECTION:
            state_projection = (row.state_ref, row.state_digest, row.state_class)
            existing_projection = deterministic_states.setdefault(
                history_identity, state_projection
            )
            if existing_projection != state_projection:
                raise InformationTheoryEvidenceError(
                    "one exact history has conflicting deterministic states"
                )
        state_identity = (row.state_ref, row.state_digest)
        existing_state = state_claims.setdefault(state_identity, row.state_class)
        if existing_state != row.state_class:
            raise InformationTheoryEvidenceError(
                "one exact state representation has conflicting class labels"
            )
    if projection_mode == DETERMINISTIC_PROJECTION:
        observed_mapping: dict[str, str] = {}
        for row in valid:
            existing = observed_mapping.setdefault(row.history_class, row.state_class)
            if existing != row.state_class:
                raise InformationTheoryEvidenceError(
                    "a deterministic history class mapped to several state classes"
                )
    outcome_entropy = _entropy_from_counts(Counter(row.outcome_class for row in valid))
    history_conditional = _conditional_entropy(valid, lambda row: row.history_class)
    state_conditional = _conditional_entropy(valid, lambda row: row.state_class)
    history_information = max(0.0, outcome_entropy - history_conditional)
    state_information = max(0.0, outcome_entropy - state_conditional)
    residual = (
        max(0.0, state_conditional - history_conditional)
        if projection_mode == DETERMINISTIC_PROJECTION
        else None
    )
    applicable = projection_mode == DETERMINISTIC_PROJECTION
    retention = (
        state_information / history_information
        if applicable and history_information > _EPSILON
        else None
    )
    dpi = state_information <= history_information + _EPSILON if applicable else None
    values = {
            "measurement_spec_ref": specification.measurement_id,
            "measurement_spec_digest": specification.digest,
            "source_population_ref": specification.population_ref,
            "source_population_digest": specification.population_digest,
            "sample_population_digest": sample_population_digest,
            "task_region_ref": valid[0].task_region_ref,
            "projection_policy_ref": valid[0].projection_policy_ref,
            "projection_policy_digest": valid[0].projection_policy_digest,
            "projection_mode": projection_mode,
            "outcome_contract_ref": valid[0].outcome_contract_ref,
            "outcome_contract_digest": valid[0].outcome_contract_digest,
            "evaluator_ref": valid[0].evaluator_ref,
            "evaluator_digest": valid[0].evaluator_digest,
            "included_sample_refs": tuple(sorted(row.sample_id for row in valid)),
            "excluded_sample_refs": tuple(sorted(row.sample_id for row in excluded)),
            "total_sample_count": len(rows),
            "sample_count": len(valid),
            "valid_population_coverage": valid_coverage,
            "minimum_valid_population_coverage": (
                specification.minimum_valid_population_coverage
            ),
            "history_class_count": len({row.history_class for row in valid}),
            "state_class_count": len({row.state_class for row in valid}),
            "outcome_class_count": len({row.outcome_class for row in valid}),
            "outcome_entropy_bits": outcome_entropy,
            "conditional_entropy_outcome_given_history_bits": history_conditional,
            "conditional_entropy_outcome_given_state_bits": state_conditional,
            "mutual_information_history_outcome_bits": history_information,
            "mutual_information_state_outcome_bits": state_information,
            "residual_predictive_information_bits": residual,
            "residual_predictive_information_interpretation_applicable": applicable,
            "state_information_retention": retention,
            "data_processing_check_applicable": applicable,
            "data_processing_inequality_holds": dpi,
    }
    result = object.__new__(EmpiricalPredictiveInformation)
    for name, value in values.items():
        object.__setattr__(result, name, value)
    object.__setattr__(result, "record_type", EMPIRICAL_INFORMATION_SCHEMA)
    result.__post_init__()
    return result


__all__ = (
    "DETERMINISTIC_PROJECTION",
    "EMPIRICAL_INFORMATION_SCHEMA",
    "INFORMATION_MEASUREMENT_SPEC_SCHEMA",
    "INFORMATION_UPDATE_SCHEMA",
    "PROJECTION_MODES",
    "STATE_POLICY_ASSESSMENT_SCHEMA",
    "STATE_POLICY_TRIAL_SCHEMA",
    "STOCHASTIC_PROJECTION",
    "CategoricalDistribution",
    "EmpiricalPredictiveInformation",
    "InformationMeasurementSpec",
    "InformationTheoryEvidenceError",
    "InformationUpdateEvidence",
    "PredictiveStateSample",
    "estimate_predictive_information",
)
