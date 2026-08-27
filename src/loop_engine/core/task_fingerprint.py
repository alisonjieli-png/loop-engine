"""Versioned task fingerprints and contract-based compatibility evidence.

Task identity is a typed record. The pipe-delimited pre-v1 representation is
accepted only by ``TaskFingerprint.from_legacy_serialized`` and is never
emitted by current code. Text search remains a projection, not identity or
compatibility authority.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum


TASK_FINGERPRINT_SCHEMA_VERSION = "task_fingerprint/v1"


class TaskFingerprintError(ValueError):
    """A task fingerprint or compatibility record is invalid."""


class ScaleBand(str, Enum):
    """Normalized task scale used for compatibility, never for authority."""

    UNKNOWN = "unknown"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

    @classmethod
    def for_rows(cls, rows: int) -> "ScaleBand":
        if not isinstance(rows, int) or isinstance(rows, bool) or rows < 0:
            raise TaskFingerprintError("rows must be a non-negative integer")
        if rows == 0:
            return cls.UNKNOWN
        if rows < 10_000:
            return cls.SMALL
        if rows < 1_000_000:
            return cls.MEDIUM
        return cls.LARGE


class CompatibilityDimension(str, Enum):
    """Independent facts compared before a reusable candidate may run."""

    PROBLEM = "problem"
    MODALITY = "modality"
    OPERATOR = "operator"
    RESPONSE_TOPOLOGY = "response_topology"
    INPUT_CONTRACT = "input_contract"
    OUTPUT_CONTRACT = "output_contract"
    ENVIRONMENT = "environment"
    OUTPUT_ROLE = "output_role"
    METRIC = "metric"
    SCALE = "scale"
    DOMAIN = "domain"


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaskFingerprintError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise TaskFingerprintError(f"{name} must be a string")
    return value.strip()


def _known(value: str) -> bool:
    return bool(value and value.casefold() not in {"unknown", "any"})


@dataclass(frozen=True)
class TaskFingerprintRequest:
    """Raw typed values used to construct one normalized task fingerprint."""

    problem: str
    output_role: str
    metric: str = ""
    rows: int = 0
    modality: str = "unknown"
    operator: str = ""
    response_topology: str = ""
    input_contract: str = ""
    output_contract: str = ""
    environment_ref: str = ""
    domain: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "problem", _required_text(self.problem, "problem"))
        object.__setattr__(
            self, "output_role", _required_text(self.output_role, "output_role"))
        for name in (
            "metric", "modality", "operator", "response_topology",
            "input_contract", "output_contract", "environment_ref", "domain",
        ):
            object.__setattr__(
                self, name, _optional_text(getattr(self, name), name))
        ScaleBand.for_rows(self.rows)


@dataclass(frozen=True)
class TaskFingerprint:
    """Versioned task identity used for compatibility, search, and evidence."""

    problem: str
    output_role: str
    metric: str = ""
    scale_band: ScaleBand = ScaleBand.UNKNOWN
    modality: str = "unknown"
    operator: str = ""
    response_topology: str = ""
    input_contract: str = ""
    output_contract: str = ""
    environment_ref: str = ""
    domain: str = ""
    schema_version: str = TASK_FINGERPRINT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "problem", _required_text(self.problem, "problem"))
        object.__setattr__(
            self, "output_role", _required_text(self.output_role, "output_role"))
        for name in (
            "metric", "modality", "operator", "response_topology",
            "input_contract", "output_contract", "environment_ref", "domain",
        ):
            object.__setattr__(
                self, name, _optional_text(getattr(self, name), name))
        scale = self.scale_band
        if not isinstance(scale, ScaleBand):
            try:
                scale = ScaleBand(scale)
            except (TypeError, ValueError) as exc:
                raise TaskFingerprintError(
                    "scale_band is not recognized") from exc
            object.__setattr__(self, "scale_band", scale)
        if self.schema_version != TASK_FINGERPRINT_SCHEMA_VERSION:
            raise TaskFingerprintError(
                f"schema_version must be {TASK_FINGERPRINT_SCHEMA_VERSION}")

    @classmethod
    def from_request(cls, request: TaskFingerprintRequest) -> "TaskFingerprint":
        if not isinstance(request, TaskFingerprintRequest):
            raise TaskFingerprintError(
                "TaskFingerprint.from_request needs TaskFingerprintRequest")
        return cls(
            problem=request.problem,
            output_role=request.output_role,
            metric=request.metric,
            scale_band=ScaleBand.for_rows(request.rows),
            modality=request.modality,
            operator=request.operator,
            response_topology=request.response_topology,
            input_contract=request.input_contract,
            output_contract=request.output_contract,
            environment_ref=request.environment_ref,
            domain=request.domain,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "TaskFingerprint":
        if not isinstance(value, Mapping):
            raise TaskFingerprintError("fingerprint record must be a mapping")
        if value.get("schema_version") != TASK_FINGERPRINT_SCHEMA_VERSION:
            raise TaskFingerprintError(
                "fingerprint record needs schema_version task_fingerprint/v1")
        allowed = {
            "schema_version", "problem", "output_role", "metric",
            "scale_band", "modality", "operator", "response_topology",
            "input_contract", "output_contract", "environment_ref", "domain",
        }
        unknown = set(value) - allowed
        if unknown:
            raise TaskFingerprintError(
                f"fingerprint record has unknown fields {sorted(unknown)!r}")
        return cls(**dict(value))

    @classmethod
    def from_legacy_serialized(cls, value: str) -> "TaskFingerprint":
        """Read the exact pre-v1 five-field pipe representation."""
        if not isinstance(value, str):
            raise TaskFingerprintError("legacy fingerprint must be a string")
        parts = value.split("|")
        if len(parts) != 5 or any(not part.strip() for part in parts):
            raise TaskFingerprintError(
                "legacy fingerprint must contain exactly five non-empty fields")
        modality, problem, output_role, metric, scale = parts
        try:
            scale_band = ScaleBand(scale)
        except ValueError as exc:
            raise TaskFingerprintError(
                "legacy fingerprint has an unknown scale band") from exc
        return cls(
            problem=problem,
            output_role=output_role,
            metric="" if metric == "any" else metric,
            scale_band=scale_band,
            modality=modality,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "problem": self.problem,
            "output_role": self.output_role,
            "metric": self.metric,
            "scale_band": self.scale_band.value,
            "modality": self.modality,
            "operator": self.operator,
            "response_topology": self.response_topology,
            "input_contract": self.input_contract,
            "output_contract": self.output_contract,
            "environment_ref": self.environment_ref,
            "domain": self.domain,
        }

    @property
    def digest(self) -> str:
        encoded = json.dumps(
            self.to_dict(), sort_keys=True, separators=(",", ":"),
            ensure_ascii=True).encode("utf-8")
        return "sha256:" + hashlib.sha256(encoded).hexdigest()

    def search_text(self) -> str:
        """Return a search projection, never an identity or parser input."""
        return " ".join(value for value in (
            self.modality, self.problem, self.operator, self.output_role,
            self.metric, self.scale_band.value, self.domain,
        ) if _known(value))


def task_fingerprint(request: TaskFingerprintRequest) -> TaskFingerprint:
    """Construct a normalized fingerprint from one cohesive request object."""
    return TaskFingerprint.from_request(request)


def parse_task_fingerprint(
        value: TaskFingerprint | Mapping[str, object] | str) -> TaskFingerprint:
    """Read a current fingerprint or the exact isolated legacy representation."""
    if isinstance(value, TaskFingerprint):
        return value
    if isinstance(value, Mapping):
        return TaskFingerprint.from_dict(value)
    if isinstance(value, str):
        return TaskFingerprint.from_legacy_serialized(value)
    raise TaskFingerprintError(
        "fingerprint must be TaskFingerprint, mapping, or legacy string")


@dataclass(frozen=True)
class CompatibilityAssessment:
    """Hard, soft, and unknown compatibility dimensions for one candidate."""

    required_digest: str
    candidate_digest: str
    hard_matches: frozenset[CompatibilityDimension] = field(
        default_factory=frozenset)
    hard_failures: frozenset[CompatibilityDimension] = field(
        default_factory=frozenset)
    soft_matches: frozenset[CompatibilityDimension] = field(
        default_factory=frozenset)
    soft_differences: frozenset[CompatibilityDimension] = field(
        default_factory=frozenset)
    unknowns: frozenset[CompatibilityDimension] = field(
        default_factory=frozenset)

    def __post_init__(self) -> None:
        for name in (
            "hard_matches", "hard_failures", "soft_matches",
            "soft_differences", "unknowns",
        ):
            values = frozenset(getattr(self, name))
            if any(not isinstance(value, CompatibilityDimension)
                   for value in values):
                raise TaskFingerprintError(
                    f"{name} must contain CompatibilityDimension values")
            object.__setattr__(self, name, values)
        groups = (
            self.hard_matches, self.hard_failures, self.soft_matches,
            self.soft_differences, self.unknowns,
        )
        if sum(len(values) for values in groups) != len(
                frozenset().union(*groups)):
            raise TaskFingerprintError(
                "one compatibility dimension cannot have competing states")

    @property
    def compatible(self) -> bool:
        return not self.hard_failures

    @property
    def exact(self) -> bool:
        return self.required_digest == self.candidate_digest

    @property
    def required_delta(self) -> tuple[str, ...]:
        dimensions = self.soft_differences | self.unknowns
        return tuple(sorted(item.value for item in dimensions))

    def to_dict(self) -> dict[str, object]:
        def values(items: frozenset[CompatibilityDimension]) -> list[str]:
            return sorted(item.value for item in items)

        return {
            "required_digest": self.required_digest,
            "candidate_digest": self.candidate_digest,
            "compatible": self.compatible,
            "exact": self.exact,
            "hard_matches": values(self.hard_matches),
            "hard_failures": values(self.hard_failures),
            "soft_matches": values(self.soft_matches),
            "soft_differences": values(self.soft_differences),
            "unknowns": values(self.unknowns),
            "required_delta": list(self.required_delta),
        }


def assess_compatibility(
        required: TaskFingerprint,
        candidate: TaskFingerprint) -> CompatibilityAssessment:
    """Compare task contracts without treating textual similarity as proof."""
    if not isinstance(required, TaskFingerprint) \
            or not isinstance(candidate, TaskFingerprint):
        raise TaskFingerprintError(
            "compatibility assessment needs two TaskFingerprint objects")
    hard_fields = (
        (CompatibilityDimension.PROBLEM, required.problem, candidate.problem),
        (CompatibilityDimension.MODALITY, required.modality, candidate.modality),
        (CompatibilityDimension.OPERATOR, required.operator, candidate.operator),
        (CompatibilityDimension.RESPONSE_TOPOLOGY,
         required.response_topology, candidate.response_topology),
        (CompatibilityDimension.INPUT_CONTRACT,
         required.input_contract, candidate.input_contract),
        (CompatibilityDimension.OUTPUT_CONTRACT,
         required.output_contract, candidate.output_contract),
        (CompatibilityDimension.ENVIRONMENT,
         required.environment_ref, candidate.environment_ref),
    )
    soft_fields = (
        (CompatibilityDimension.OUTPUT_ROLE,
         required.output_role, candidate.output_role),
        (CompatibilityDimension.METRIC, required.metric, candidate.metric),
        (CompatibilityDimension.SCALE,
         required.scale_band.value, candidate.scale_band.value),
        (CompatibilityDimension.DOMAIN, required.domain, candidate.domain),
    )
    states: dict[str, set[CompatibilityDimension]] = {
        "hard_matches": set(), "hard_failures": set(),
        "soft_matches": set(), "soft_differences": set(), "unknowns": set(),
    }
    for dimension, required_value, candidate_value in hard_fields:
        if not _known(required_value):
            states["unknowns"].add(dimension)
        elif not _known(candidate_value):
            states["hard_failures"].add(dimension)
        elif required_value.casefold() == candidate_value.casefold():
            states["hard_matches"].add(dimension)
        else:
            states["hard_failures"].add(dimension)
    for dimension, required_value, candidate_value in soft_fields:
        if not _known(required_value) or not _known(candidate_value):
            states["unknowns"].add(dimension)
        elif required_value.casefold() == candidate_value.casefold():
            states["soft_matches"].add(dimension)
        else:
            states["soft_differences"].add(dimension)
    return CompatibilityAssessment(
        required_digest=required.digest,
        candidate_digest=candidate.digest,
        **{name: frozenset(values) for name, values in states.items()},
    )


def self_test() -> dict[str, object]:
    tests: list[dict[str, object]] = []

    def check(name: str, passed: bool) -> None:
        tests.append({"test": name, "passed": bool(passed)})

    required = task_fingerprint(TaskFingerprintRequest(
        problem="classification", output_role="label", metric="accuracy",
        rows=8_000, modality="tabular", operator="predict",
        response_topology="label", input_contract="tabular_dataset/v1",
        output_contract="prediction_labels/v1"))
    round_trip = TaskFingerprint.from_dict(required.to_dict())
    check("typed_fingerprint_round_trip_is_stable",
          round_trip == required and round_trip.digest == required.digest)
    legacy = TaskFingerprint.from_legacy_serialized(
        "tabular|classification|label|accuracy|small")
    check("exact_legacy_fingerprint_reader_migrates",
          legacy.problem == "classification"
          and legacy.scale_band == ScaleBand.SMALL)
    try:
        TaskFingerprint.from_legacy_serialized(
            "tabular|classification|label|accuracy|small|extra")
        check("malformed_legacy_fingerprint_is_refused", False)
    except TaskFingerprintError:
        check("malformed_legacy_fingerprint_is_refused", True)
    regression = task_fingerprint(TaskFingerprintRequest(
        problem="regression", output_role="value", rows=8_000,
        modality="tabular", operator="predict", response_topology="score",
        input_contract="tabular_dataset/v1",
        output_contract="prediction_scores/v1"))
    assessment = assess_compatibility(required, regression)
    check("compatibility_uses_contracts_not_text_similarity",
          not assessment.compatible
          and CompatibilityDimension.PROBLEM in assessment.hard_failures)
    underspecified = TaskFingerprint(
        problem="classification", output_role="label", modality="tabular")
    incomplete = assess_compatibility(required, underspecified)
    check("missing_required_candidate_contract_fails_closed",
          not incomplete.compatible
          and CompatibilityDimension.INPUT_CONTRACT
              in incomplete.hard_failures)
    return {"tests": tests}


__all__ = (
    "CompatibilityAssessment", "CompatibilityDimension", "ScaleBand",
    "TaskFingerprint", "TaskFingerprintError", "TaskFingerprintRequest",
    "assess_compatibility", "parse_task_fingerprint", "task_fingerprint",
)
