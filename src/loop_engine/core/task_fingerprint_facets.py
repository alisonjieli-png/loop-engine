"""Deterministically generated task facet observations for compatibility.

A facet observation is a typed, versioned projection derived from supplied
typed inputs (for example a column schema for a tabular task). It is computed
by a deterministic function, never by a model, and it binds to the digest of
one :class:`TaskFingerprint`.

Facets extend compatibility evidence without changing the emitted
``task_fingerprint/v1`` identity. A facet record references its fingerprint
digest; it never replaces or mutates the fingerprint.

Hierarchy: each facet observation carries a level on one fixed path

    task -> modality -> family -> shape

so a search can widen or narrow from an exact column shape to every task in
the same modality. Facets are evidence for retrieval ranking. They are not
identity, not authority, and never a permission to run a candidate.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

TASK_FACET_SCHEMA_VERSION = "task_fingerprint_facets/v1"


class TaskFacetError(ValueError):
    """A facet observation or its request is invalid."""


class FacetLevel(str, Enum):
    """Fixed levels on one hierarchical path, ordered coarse to fine."""

    TASK = "task"
    MODALITY = "modality"
    FAMILY = "family"
    SHAPE = "shape"

    @classmethod
    def ordered(cls) -> tuple["FacetLevel", ...]:
        return (cls.TASK, cls.MODALITY, cls.FAMILY, cls.SHAPE)


class FacetKind(str, Enum):
    """The kind of deterministic observation a facet record carries."""

    COLUMN_SHAPE = "column_shape"
    TARGET_SHAPE = "target_shape"
    RESOURCE_SHAPE = "resource_shape"
    ENVIRONMENT_SHAPE = "environment_shape"


_COLUMN_ROLES = ("identifier", "numeric", "categorical", "text",
                 "timestamp", "boolean", "ordinal", "geospatial",
                 "image", "audio", "sequence", "embedded_vector", "other")


def _digest_text(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaskFacetError(f"{name} must be a non-empty string")
    return value.strip()


def _positive_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise TaskFacetError(f"{name} must be a positive integer")
    return value


@dataclass(frozen=True)
class ColumnShape:
    """One observed column role in a typed input schema."""

    name: str
    role: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "name", _required_text(self.name, "column name"))
        object.__setattr__(self, "role", _required_text(self.role, "role"))
        if self.role not in _COLUMN_ROLES:
            raise TaskFacetError(
                f"role must be one of {_COLUMN_ROLES}")


@dataclass(frozen=True)
class ColumnShapeRequest:
    """Typed inputs used to compute one deterministic column-shape facet."""

    row_count: int
    columns: tuple[ColumnShape, ...]
    target_column: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "row_count", _positive_int(self.row_count, "row_count"))
        if not isinstance(self.columns, tuple):
            raise TaskFacetError("columns must be a tuple of ColumnShape")
        if not self.columns:
            raise TaskFacetError("columns must contain at least one column")
        names: set[str] = set()
        for column in self.columns:
            if not isinstance(column, ColumnShape):
                raise TaskFacetError("columns must contain ColumnShape values")
            if column.name.casefold() in names:
                raise TaskFacetError(
                    f"duplicate column name {column.name!r}")
            names.add(column.name.casefold())
        target = self.target_column.strip()
        if target and target.casefold() not in names:
            raise TaskFacetError(
                "target_column must name one of the observed columns")
        object.__setattr__(self, "target_column", target)


@dataclass(frozen=True)
class TaskFacetObservation:
    """One deterministic facet observation bound to a task fingerprint."""

    fingerprint_digest: str
    facet_kind: FacetKind
    level: FacetLevel
    modality: str
    family: str
    shape_digest: str
    shape: tuple[tuple[str, str], ...] = ()
    feature_count: int = 0
    row_count: int = 0
    schema_version: str = TASK_FACET_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "fingerprint_digest",
            _required_text(self.fingerprint_digest, "fingerprint_digest"))
        if not isinstance(self.facet_kind, FacetKind):
            try:
                object.__setattr__(
                    self, "facet_kind", FacetKind(self.facet_kind))
            except (TypeError, ValueError) as exc:
                raise TaskFacetError(
                    "facet_kind is not recognized") from exc
        if not isinstance(self.level, FacetLevel):
            try:
                object.__setattr__(self, "level", FacetLevel(self.level))
            except (TypeError, ValueError) as exc:
                raise TaskFacetError("level is not recognized") from exc
        object.__setattr__(self, "modality", _required_text(
            self.modality, "modality"))
        object.__setattr__(self, "family", _required_text(
            self.family, "family"))
        object.__setattr__(
            self, "shape_digest", _required_text(
                self.shape_digest, "shape_digest"))
        shape = tuple((str(name), str(role))
                      for name, role in self.shape)
        object.__setattr__(self, "shape", shape)
        if (not isinstance(self.feature_count, int)
                or isinstance(self.feature_count, bool)
                or self.feature_count < 0):
            raise TaskFacetError("feature_count must be a non-negative int")
        if (not isinstance(self.row_count, int)
                or isinstance(self.row_count, bool)
                or self.row_count < 0):
            raise TaskFacetError("row_count must be a non-negative int")
        if self.schema_version != TASK_FACET_SCHEMA_VERSION:
            raise TaskFacetError(
                f"schema_version must be {TASK_FACET_SCHEMA_VERSION}")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "fingerprint_digest": self.fingerprint_digest,
            "facet_kind": self.facet_kind.value,
            "level": self.level.value,
            "modality": self.modality,
            "family": self.family,
            "shape_digest": self.shape_digest,
            "shape": [list(pair) for pair in self.shape],
            "feature_count": self.feature_count,
            "row_count": self.row_count,
        }

    @property
    def digest(self) -> str:
        """Stable record identity; changes when any typed field changes."""
        return _digest_text(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "TaskFacetObservation":
        if not isinstance(value, Mapping):
            raise TaskFacetError("facet record must be a mapping")
        if value.get("schema_version") != TASK_FACET_SCHEMA_VERSION:
            raise TaskFacetError(
                "facet record needs schema_version task_fingerprint_facets/v1")
        allowed = {
            "schema_version", "fingerprint_digest", "facet_kind", "level",
            "modality", "family", "shape_digest", "shape",
            "feature_count", "row_count",
        }
        unknown = set(value) - allowed
        if unknown:
            raise TaskFacetError(
                f"facet record has unknown fields {sorted(unknown)!r}")
        return cls(**dict(value))

    def search_text(self) -> str:
        """Return a search projection, never identity or authority."""
        parts = [self.modality, self.family]
        parts.extend(f"{name}:{role}" for name, role in self.shape)
        return " ".join(parts)


def _shape_family(shape: Sequence[ColumnShape],
                   target_column: str) -> str:
    """Deterministically derive one family label from a column role mix."""
    roles = [column.role for column in shape]
    role_set = sorted(set(roles))
    supervised = "supervised" if target_column else "unsupervised"
    return f"{supervised}_{'+'.join(role_set)}"


def _normalized_shape(shape: Sequence[ColumnShape]) -> tuple[tuple[str, str], ...]:
    """Order-independent shape projection so column order cannot change identity."""
    return tuple(sorted((column.name.casefold(), column.role)
                        for column in shape))


def column_shape_facet(
        request: ColumnShapeRequest,
        fingerprint_digest: str,
        modality: str) -> TaskFacetObservation:
    """Compute one deterministic column-shape facet observation."""
    if not isinstance(request, ColumnShapeRequest):
        raise TaskFacetError("column_shape_facet needs ColumnShapeRequest")
    fingerprint_digest = _required_text(
        fingerprint_digest, "fingerprint_digest")
    modality = _required_text(modality, "modality")
    normalized = _normalized_shape(request.columns)
    shape_digest = "sha256:" + hashlib.sha256(
        json.dumps(normalized, separators=(",", ":"),
                    ensure_ascii=True).encode("utf-8")).hexdigest()
    feature_count = len(request.columns) - (1 if request.target_column else 0)
    return TaskFacetObservation(
        fingerprint_digest=fingerprint_digest,
        facet_kind=FacetKind.COLUMN_SHAPE,
        level=FacetLevel.SHAPE,
        modality=modality,
        family=_shape_family(request.columns, request.target_column),
        shape_digest=shape_digest,
        shape=normalized,
        feature_count=feature_count,
        row_count=request.row_count,
    )


def facet_hierarchy(
        observation: TaskFacetObservation) -> tuple[TaskFacetObservation, ...]:
    """Expand one observation into its coarse-to-fine hierarchical path.

    The exact shape observation stays last with its exact original
    ``shape_digest`` preserved. Each wider level keeps the same fingerprint
    binding and a deterministic digest of fewer details, so a search can
    widen from one exact shape to every task in the modality without any
    model call.
    """
    shape_path: list[tuple[str, str]] = []
    for name, role in observation.shape:
        shape_path.append((name, role))
    levels: list[TaskFacetObservation] = []
    for level in FacetLevel.ordered():
        if level == FacetLevel.SHAPE:
            levels.append(observation)
            continue
        if level == FacetLevel.TASK or level == FacetLevel.MODALITY:
            detail: tuple[tuple[str, str], ...] = ()
        else:
            detail = tuple(
                (name, role) for name, role in shape_path
                if role != "identifier")
        levels.append(TaskFacetObservation(
            fingerprint_digest=observation.fingerprint_digest,
            facet_kind=observation.facet_kind,
            level=level,
            modality=observation.modality,
            family=observation.family,
            shape_digest=_digest_text(
                {"level": level.value, "modality": observation.modality,
                 "family": observation.family, "shape": [
                     [name, role] for name, role in detail]}),
            shape=detail,
            feature_count=observation.feature_count
            if level == FacetLevel.SHAPE else len(detail),
            row_count=observation.row_count,
        ))
    return tuple(levels)


def facet_overlap(
        required: TaskFacetObservation,
        candidate: TaskFacetObservation) -> dict[str, object]:
    """Typed overlap evidence between two facet observations of one kind."""
    if required.facet_kind != candidate.facet_kind:
        raise TaskFacetError("facet overlap compares one facet kind")
    required_roles = {role for _, role in required.shape}
    candidate_roles = {role for _, role in candidate.shape}
    shared = required_roles & candidate_roles
    missing = required_roles - candidate_roles
    extra = candidate_roles - required_roles
    return {
        "record_type": "task_facet_overlap/v1",
        "required_shape_digest": required.shape_digest,
        "candidate_shape_digest": candidate.shape_digest,
        "same_family": required.family == candidate.family,
        "same_modality": required.modality == candidate.modality,
        "shared_roles": sorted(shared),
        "missing_roles": sorted(missing),
        "extra_roles": sorted(extra),
        "role_overlap_ratio": (
            len(shared) / len(required_roles) if required_roles else 0.0),
        "prior_not_proof": True,
    }


def self_test() -> dict[str, object]:
    tests: list[dict[str, object]] = []

    def check(name: str, passed: bool) -> None:
        tests.append({"test": name, "passed": bool(passed)})

    columns = (
        ColumnShape("customer_id", "identifier"),
        ColumnShape("age", "numeric"),
        ColumnShape("plan", "categorical"),
        ColumnShape("months_active", "numeric"),
        ColumnShape("churned", "boolean"),
    )
    request = ColumnShapeRequest(
        row_count=8_000, columns=columns, target_column="churned")
    fingerprint_digest = "sha256:" + "a" * 64
    facet = column_shape_facet(request, fingerprint_digest, "tabular")

    check("facet_binds_to_fingerprint_digest",
          facet.fingerprint_digest == fingerprint_digest
          and facet.facet_kind == FacetKind.COLUMN_SHAPE
          and facet.level == FacetLevel.SHAPE)
    check("facet_is_deterministic",
          column_shape_facet(request, fingerprint_digest, "tabular")
          == facet)

    reordered = ColumnShapeRequest(
        row_count=8_000, columns=tuple(reversed(columns)),
        target_column="churned")
    check("column_order_cannot_change_shape_identity",
          column_shape_facet(reordered, fingerprint_digest, "tabular")
          == facet)

    try:
        ColumnShapeRequest(row_count=8_000, columns=columns,
                           target_column="not_a_column")
        check("unknown_target_column_is_refused", False)
    except TaskFacetError:
        check("unknown_target_column_is_refused", True)

    hierarchy = facet_hierarchy(facet)
    check("hierarchy_widens_from_shape_to_task",
          [item.level for item in hierarchy] == [
              item.value for item in FacetLevel.ordered()]
          and hierarchy[-1] == facet
          and all(item.fingerprint_digest == fingerprint_digest
                  for item in hierarchy))

    other = ColumnShapeRequest(
        row_count=8_000, columns=(
            ColumnShape("age", "numeric"),
            ColumnShape("plan", "categorical"),
            ColumnShape("label", "boolean")), target_column="label")
    other_facet = column_shape_facet(other, fingerprint_digest, "tabular")
    overlap = facet_overlap(facet, other_facet)
    check("overlap_reports_typed_evidence_not_proof",
          overlap["same_family"] is False
          and overlap["same_modality"] is True
          and "numeric" in overlap["shared_roles"]
          and overlap["missing_roles"] == ["identifier"]
          and overlap["prior_not_proof"] is True)

    round_trip = TaskFacetObservation.from_dict(facet.to_dict())
    check("facet_round_trip_is_stable", round_trip == facet)
    try:
        TaskFacetObservation.from_dict(
            {**facet.to_dict(), "schema_version": "other/v9"})
        check("unknown_facet_schema_is_refused", False)
    except TaskFacetError:
        check("unknown_facet_schema_is_refused", True)

    return {"tests": tests}


__all__ = (
    "TASK_FACET_SCHEMA_VERSION",
    "ColumnShape",
    "ColumnShapeRequest",
    "FacetKind",
    "FacetLevel",
    "TaskFacetError",
    "TaskFacetObservation",
    "column_shape_facet",
    "facet_hierarchy",
    "facet_overlap",
)