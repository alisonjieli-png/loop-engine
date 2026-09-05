"""Shared contracts and validation for passive information evidence.

These values define measurement provenance and strict scalar validation. They
perform no estimation, execution, storage, retrieval, or policy selection.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass

INFORMATION_MEASUREMENT_SPEC_SCHEMA = "information_measurement_spec/v1"
INFRASTRUCTURE_VALIDITY_RECORD_SCHEMA = "infrastructure_validity_record/v1"
INFORMATION_MEASURE_KINDS = (
    "paired_state_compression_distortion",
    "predictive_state_information",
)
INFRASTRUCTURE_INVALID_REASONS = (
    "artifact_integrity_invalid",
    "evaluator_invalid",
    "execution_not_observed",
    "provider_transport_invalid",
    "source_state_mismatch",
)
EMPIRICAL_PLUGIN_ESTIMATOR_CONTRACT_DIGEST = (
    "626fffa9126d01f4fccad8b8758b4c37e7d85b4e29191a560c69531ab4b6ef81"
)
PAIRED_COMPRESSION_DISTORTION_ESTIMATOR_CONTRACT_DIGEST = (
    "0dc5d6f95a0fc76723ec6bf3520e6c9d511a4a91c0b0569c5f06fba7d72679d7"
)
_HEX = frozenset("0123456789abcdef")
_EPSILON = 1e-12
_MAX_EXACT_INTEGER = 2**63 - 1


class InformationTheoryEvidenceError(ValueError):
    """A measurement input or passive result is malformed."""


@dataclass(frozen=True)
class InfrastructureValidityRecord:
    """Typed validity decision bound to one exact measurement subject."""

    record_id: str
    subject_ref: str
    subject_digest: str
    evaluator_ref: str
    evaluator_digest: str
    status: str
    reason_code: str
    evidence_refs: tuple[str, ...]
    record_type: str = INFRASTRUCTURE_VALIDITY_RECORD_SCHEMA

    def __post_init__(self) -> None:
        if self.record_type != INFRASTRUCTURE_VALIDITY_RECORD_SCHEMA:
            raise InformationTheoryEvidenceError(
                "infrastructure validity record schema is unsupported"
            )
        for name in ("record_id", "subject_ref", "evaluator_ref", "status"):
            _text(getattr(self, name), name)
        for name in ("subject_digest", "evaluator_digest"):
            _digest(getattr(self, name), name)
        if self.status not in ("valid", "invalid"):
            raise InformationTheoryEvidenceError(
                "infrastructure validity status must be valid or invalid"
            )
        _optional_text(self.reason_code, "reason_code")
        if self.status == "valid" and self.reason_code:
            raise InformationTheoryEvidenceError(
                "a valid infrastructure record cannot have an invalid reason"
            )
        if self.status == "invalid":
            _text(self.reason_code, "reason_code")
            if self.reason_code not in INFRASTRUCTURE_INVALID_REASONS:
                raise InformationTheoryEvidenceError(
                    "invalid infrastructure reason is not registered"
                )
        object.__setattr__(
            self,
            "evidence_refs",
            _texts(self.evidence_refs, "evidence_refs", required=True),
        )

    @property
    def is_valid(self) -> bool:
        return self.status == "valid"

    @property
    def digest(self) -> str:
        return _content_digest(self.to_dict())

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": self.record_type,
            **{
                name: list(value) if isinstance(value, tuple) else value
                for name, value in self.__dict__.items()
                if name != "record_type"
            },
            "grants_authority": False,
        }


@dataclass(frozen=True)
class InformationMeasurementSpec:
    """Declared variables, population, estimator, and validity design."""

    measurement_id: str
    measure_kind: str
    random_variable_refs: tuple[str, ...]
    target_ref: str
    target_digest: str
    target_horizon: str
    conditioning_refs: tuple[str, ...]
    namespace_ref: str
    privacy_class: str
    task_region_ref: str
    population_ref: str
    population_digest: str
    evaluator_ref: str
    evaluator_digest: str
    exclusion_policy_ref: str
    exclusion_policy_digest: str
    minimum_valid_population_coverage: float
    selection_rule_ref: str
    selection_rule_digest: str
    probability_model_ref: str
    probability_model_digest: str
    estimator_ref: str
    estimator_contract_digest: str
    holdout_design_ref: str
    holdout_design_digest: str
    bias_correction: str
    confidence_interval_method: str
    reference_manifest_ref: str
    reference_manifest_digest: str
    evidence_refs: tuple[str, ...]
    log_base: float | None = 2.0
    units: str = "bits"
    record_type: str = INFORMATION_MEASUREMENT_SPEC_SCHEMA

    def __post_init__(self) -> None:
        if self.record_type != INFORMATION_MEASUREMENT_SPEC_SCHEMA:
            raise InformationTheoryEvidenceError(
                "information measurement specification is unsupported"
            )
        for name in (
            "measurement_id",
            "measure_kind",
            "target_ref",
            "target_horizon",
            "namespace_ref",
            "privacy_class",
            "task_region_ref",
            "population_ref",
            "evaluator_ref",
            "exclusion_policy_ref",
            "selection_rule_ref",
            "probability_model_ref",
            "estimator_ref",
            "holdout_design_ref",
            "bias_correction",
            "confidence_interval_method",
            "reference_manifest_ref",
            "units",
        ):
            _text(getattr(self, name), name)
        for name in (
            "target_digest",
            "population_digest",
            "evaluator_digest",
            "exclusion_policy_digest",
            "selection_rule_digest",
            "probability_model_digest",
            "estimator_contract_digest",
            "holdout_design_digest",
            "reference_manifest_digest",
        ):
            _digest(getattr(self, name), name)
        for name in (
            "random_variable_refs",
            "conditioning_refs",
            "evidence_refs",
        ):
            object.__setattr__(
                self,
                name,
                _texts(getattr(self, name), name, required=True),
            )
        if self.measure_kind not in INFORMATION_MEASURE_KINDS:
            raise InformationTheoryEvidenceError(
                "information measure kind is not implemented"
            )
        if self.bias_correction != "none":
            raise InformationTheoryEvidenceError(
                "the current plug-in estimator implements no bias correction"
            )
        if self.confidence_interval_method != "not_estimated":
            raise InformationTheoryEvidenceError(
                "the current estimator does not compute confidence intervals"
            )
        if self.measure_kind == "predictive_state_information":
            if (
                self.estimator_ref != "empirical_plugin_base2/v1"
                or self.estimator_contract_digest
                != EMPIRICAL_PLUGIN_ESTIMATOR_CONTRACT_DIGEST
                or self.log_base != 2.0
                or self.units != "bits"
            ):
                raise InformationTheoryEvidenceError(
                    "predictive information needs its base-two estimator contract"
                )
        elif (
            self.estimator_ref != "paired_empirical_compression_distortion/v1"
            or self.estimator_contract_digest
            != PAIRED_COMPRESSION_DISTORTION_ESTIMATOR_CONTRACT_DIGEST
            or self.log_base is not None
            or self.units != "bytes_and_declared_loss"
        ):
            raise InformationTheoryEvidenceError(
                "paired assessment needs its byte-and-loss estimator contract"
            )
        coverage = _number(
            self.minimum_valid_population_coverage,
            "minimum_valid_population_coverage",
            minimum=0.0,
        )
        if coverage <= 0.0 or coverage > 1.0:
            raise InformationTheoryEvidenceError(
                "minimum valid population coverage must be above zero and at most one"
            )
        object.__setattr__(self, "minimum_valid_population_coverage", coverage)

    @property
    def digest(self) -> str:
        return _content_digest(self.to_dict())

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": self.record_type,
            **{
                name: list(value) if isinstance(value, tuple) else value
                for name, value in self.__dict__.items()
                if name != "record_type"
            },
            "external_references_resolved_by_this_record": False,
            "grants_authority": False,
        }


def _text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise InformationTheoryEvidenceError(f"{name} must be text")
    result = value.strip()
    if (
        not result
        or result != value
        or "\n" in result
        or "\r" in result
        or any(ord(character) < 32 or ord(character) == 127 for character in result)
    ):
        raise InformationTheoryEvidenceError(
            f"{name} must be non-empty, trimmed, control-free text"
        )
    return result


def _digest(value: object, name: str) -> str:
    result = _text(value, name)
    if len(result) != 64 or any(character not in _HEX for character in result):
        raise InformationTheoryEvidenceError(
            f"{name} must be a lowercase SHA-256 digest"
        )
    return result


def _optional_text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise InformationTheoryEvidenceError(f"{name} must be text")
    if value and _text(value, name) != value:
        raise InformationTheoryEvidenceError(f"{name} is invalid")
    return value


def _texts(values: object, name: str, *, required: bool = False) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, Mapping)):
        raise InformationTheoryEvidenceError(f"{name} must be a sequence")
    try:
        result = tuple(_text(item, name) for item in (values or ()))
    except TypeError as exc:
        raise InformationTheoryEvidenceError(f"{name} must be a sequence") from exc
    if (required and not result) or len(result) != len(set(result)):
        raise InformationTheoryEvidenceError(
            f"{name} must contain unique text and cannot be empty here"
        )
    return result


def _number(
    value: object,
    name: str,
    *,
    minimum: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InformationTheoryEvidenceError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result) or (minimum is not None and result < minimum):
        raise InformationTheoryEvidenceError(f"{name} is outside its finite range")
    return result


def _optional_number(
    value: object,
    name: str,
    *,
    minimum: float = 0.0,
) -> float | None:
    return None if value is None else _number(value, name, minimum=minimum)


def _count(value: object, name: str, *, positive: bool = False) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < (1 if positive else 0)
        or value > _MAX_EXACT_INTEGER
    ):
        qualifier = "positive" if positive else "non-negative"
        raise InformationTheoryEvidenceError(
            f"{name} must be a bounded {qualifier} integer"
        )
    return value


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
        raise InformationTheoryEvidenceError(
            "information evidence must be strict JSON"
        ) from exc


def _content_digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


__all__ = (
    "EMPIRICAL_PLUGIN_ESTIMATOR_CONTRACT_DIGEST",
    "INFORMATION_MEASUREMENT_SPEC_SCHEMA",
    "INFORMATION_MEASURE_KINDS",
    "INFRASTRUCTURE_INVALID_REASONS",
    "INFRASTRUCTURE_VALIDITY_RECORD_SCHEMA",
    "PAIRED_COMPRESSION_DISTORTION_ESTIMATOR_CONTRACT_DIGEST",
    "InformationMeasurementSpec",
    "InformationTheoryEvidenceError",
    "InfrastructureValidityRecord",
)
