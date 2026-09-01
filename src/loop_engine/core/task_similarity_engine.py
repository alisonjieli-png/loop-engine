"""Containerized task similarity finding engine.

Task fingerprints identify one task. This engine finds prior work that looks
like the current task without making similarity a source of authority. It is
core infrastructure: one typed facade, layered resolution, parameterized
policy, and pluggable candidate sources, so the matching logic can improve
without changes at call sites.

Architecture: the engine is a passive component consumed by Loops. Its one
operational boundary (``task similarity resolution``) crosses through a
deterministic component Loop. Candidates and facets remain evidence with
``prior_not_proof``; similarity ranking never authorizes execution, never
promotes a candidate, and never replaces contract compatibility.

Layers, tried in one fixed order inside one engine call:

    1. exact fingerprint digest
    2. contract compatibility (hard dimensions must pass)
    3. exact facet shape digest
    4. facet family overlap
    5. facet modality overlap

Each layer produces typed evidence. The engine records which layer produced
each result so an improvement to one layer cannot silently change the meaning
of another.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from .resolution import (
    CompatibilityRequirement,
    ResolutionCandidate,
    ResolutionOrigin,
)
from .solution_library import SolutionLibrary
from .task_fingerprint import (
    CompatibilityAssessment,
    TaskFingerprint,
    assess_compatibility,
)
from .task_fingerprint_facets import (
    FacetLevel,
    TaskFacetObservation,
    facet_overlap,
)

TASK_SIMILARITY_SCHEMA_VERSION = "task_similarity/v1"


class TaskSimilarityError(ValueError):
    """A similarity request, policy, or result is invalid."""


class SimilarityLayer(str, Enum):
    """The fixed resolution layers inside one engine call."""

    EXACT_FINGERPRINT = "exact_fingerprint"
    CONTRACT_COMPATIBLE = "contract_compatible"
    FACET_SHAPE = "facet_shape"
    FACET_FAMILY = "facet_family"
    FACET_MODALITY = "facet_modality"


LAYER_ORDER = (
    SimilarityLayer.EXACT_FINGERPRINT,
    SimilarityLayer.CONTRACT_COMPATIBLE,
    SimilarityLayer.FACET_SHAPE,
    SimilarityLayer.FACET_FAMILY,
    SimilarityLayer.FACET_MODALITY,
)


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaskSimilarityError(f"{name} must be a non-empty string")
    return value.strip()


def _digest_payload(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TaskSimilarityRequest:
    """Typed input for one similarity search."""

    fingerprint: TaskFingerprint
    facets: tuple[TaskFacetObservation, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.fingerprint, TaskFingerprint):
            raise TaskSimilarityError(
                "fingerprint must be a TaskFingerprint")
        facets = tuple(self.facets)
        for item in facets:
            if not isinstance(item, TaskFacetObservation):
                raise TaskSimilarityError(
                    "facets must contain TaskFacetObservation values")
        object.__setattr__(self, "facets", facets)


@dataclass(frozen=True)
class SimilarityPolicy:
    """Parameterized matching behavior; never a permission.

    ``widen_levels`` declares which facet layers may run. Lowering it narrows
    matching to stricter evidence. ``min_role_overlap`` floors family and
    modality layer results. ``top_n`` bounds one result page and follows the
    repository rule against implicit work ceilings: it defaults to unbounded
    (``None``) and an owner must set an explicit limit.
    """

    top_n: "int | None" = None
    min_role_overlap: float = 0.5
    widen_levels: tuple[SimilarityLayer, ...] = LAYER_ORDER

    def __post_init__(self) -> None:
        if self.top_n is not None and (
                not isinstance(self.top_n, int)
                or isinstance(self.top_n, bool) or self.top_n < 1):
            raise TaskSimilarityError(
                "top_n must be None (unbounded) or a positive integer")
        if (not isinstance(self.min_role_overlap, (int, float))
                or isinstance(self.min_role_overlap, bool)
                or not 0.0 <= self.min_role_overlap <= 1.0):
            raise TaskSimilarityError(
                "min_role_overlap must be between 0.0 and 1.0")
        levels = tuple(self.widen_levels)
        if not levels:
            raise TaskSimilarityError("widen_levels cannot be empty")
        unknown = {level.value for level in levels} - {
            layer.value for layer in LAYER_ORDER}
        if unknown:
            raise TaskSimilarityError(
                f"widen_levels has unknown layers {sorted(unknown)!r}")
        ordered = tuple(
            layer for layer in LAYER_ORDER
            if layer in {level for level in levels})
        object.__setattr__(self, "widen_levels", ordered)


@runtime_checkable
class SimilarityCandidateSource(Protocol):
    """How the engine draws prior candidates; adapters stay replaceable."""

    def find_candidates(
            self, fingerprint: TaskFingerprint) -> tuple[ResolutionCandidate, ...]:
        ...


@dataclass(frozen=True)
class LibraryCandidateSource:
    """Draw candidates from a SolutionLibrary behind one typed port."""

    library: SolutionLibrary

    def find_candidates(
            self, fingerprint: TaskFingerprint) -> tuple[ResolutionCandidate, ...]:
        return self.library.find_candidates(fingerprint)


@dataclass(frozen=True)
class FacetCandidateSource:
    """Prior facet observations to compare; a store, not an authority."""

    observations: tuple[TaskFacetObservation, ...] = ()

    def __post_init__(self) -> None:
        items = tuple(self.observations)
        for item in items:
            if not isinstance(item, TaskFacetObservation):
                raise TaskSimilarityError(
                    "facet source must hold TaskFacetObservation values")
        object.__setattr__(self, "observations", items)


@dataclass(frozen=True)
class SimilarityHit:
    """One typed similarity result with the layer that produced it."""

    candidate_ref: str
    layer: SimilarityLayer
    origin: ResolutionOrigin
    compatibility: CompatibilityAssessment
    role_overlap: float | None = None
    shared_roles: tuple[str, ...] = ()
    missing_roles: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": "similarity_hit/v1",
            "candidate_ref": self.candidate_ref,
            "layer": self.layer.value,
            "origin": self.origin.value,
            "compatible": self.compatibility.compatible,
            "exact": self.compatibility.exact,
            "role_overlap": self.role_overlap,
            "shared_roles": list(self.shared_roles),
            "missing_roles": list(self.missing_roles),
            "evidence_refs": list(self.evidence_refs),
            "prior_not_proof": True,
        }


@dataclass(frozen=True)
class TaskSimilarityResult:
    """The full typed result of one similarity search."""

    request_digest: str
    layers_run: tuple[SimilarityLayer, ...]
    hits: tuple[SimilarityHit, ...]
    schema_version: str = TASK_SIMILARITY_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "request_digest": self.request_digest,
            "layers_run": [layer.value for layer in self.layers_run],
            "hits": [hit.to_dict() for hit in self.hits],
            "prior_not_proof": True,
        }


@dataclass
class SimilarityEngine:
    """One parameterized facade over layered similarity finding.

    The engine is passive infrastructure. A Loop owns each boundary crossing;
    the engine never spawns, executes, or authorizes anything.
    """

    candidate_source: SimilarityCandidateSource
    facet_source: FacetCandidateSource = field(
        default_factory=FacetCandidateSource)
    policy: SimilarityPolicy = field(default_factory=SimilarityPolicy)

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_source, SimilarityCandidateSource) \
                and not hasattr(self.candidate_source, "find_candidates"):
            raise TaskSimilarityError(
                "candidate_source must expose find_candidates")
        if not isinstance(self.facet_source, FacetCandidateSource):
            raise TaskSimilarityError(
                "facet_source must be a FacetCandidateSource")

    def find_similar(
            self, request: TaskSimilarityRequest) -> TaskSimilarityResult:
        """Run the fixed layer order and return one typed result."""
        if not isinstance(request, TaskSimilarityRequest):
            raise TaskSimilarityError(
                "find_similar needs a TaskSimilarityRequest")
        request_digest = _digest_payload(
            {"fingerprint": request.fingerprint.digest,
             "facets": [item.to_dict() for item in request.facets]})
        layers_run: list[SimilarityLayer] = []
        hits: list[SimilarityHit] = []
        seen: set[str] = set()

        candidates = tuple(
            self.candidate_source.find_candidates(request.fingerprint))
        contract_compatible = [
            item for item in candidates if item.compatibility.compatible]

        for layer in self.policy.widen_levels:
            layers_run.append(layer)
            produced = self._run_layer(
                layer, request, contract_compatible)
            for hit in produced:
                if hit.candidate_ref in seen:
                    continue
                seen.add(hit.candidate_ref)
                hits.append(hit)
            if (self.policy.top_n is not None
                    and len(hits) >= self.policy.top_n):
                break

        bounded = (tuple(hits[:self.policy.top_n])
                   if self.policy.top_n is not None else tuple(hits))
        return TaskSimilarityResult(
            request_digest=request_digest,
            layers_run=tuple(layers_run),
            hits=bounded,
        )

    def _run_layer(
            self,
            layer: SimilarityLayer,
            request: TaskSimilarityRequest,
            candidates: Sequence[ResolutionCandidate],
    ) -> tuple[SimilarityHit, ...]:
        """Produce the hits of exactly one layer; never cross layers."""
        if layer == SimilarityLayer.EXACT_FINGERPRINT:
            return tuple(
                SimilarityHit(
                    candidate_ref=item.candidate_ref,
                    layer=layer,
                    origin=item.origin,
                    compatibility=item.compatibility,
                    evidence_refs=item.evidence_refs,
                )
                for item in candidates if item.compatibility.exact)
        if layer == SimilarityLayer.CONTRACT_COMPATIBLE:
            return tuple(
                SimilarityHit(
                    candidate_ref=item.candidate_ref,
                    layer=layer,
                    origin=item.origin,
                    compatibility=item.compatibility,
                    evidence_refs=item.evidence_refs,
                )
                for item in candidates if not item.compatibility.exact)
        if layer in (SimilarityLayer.FACET_SHAPE, SimilarityLayer.FACET_FAMILY,
                     SimilarityLayer.FACET_MODALITY):
            return self._run_facet_layer(layer, request, candidates)
        raise TaskSimilarityError(f"unhandled layer {layer!r}")

    def _run_facet_layer(
            self,
            layer: SimilarityLayer,
            request: TaskSimilarityRequest,
            candidates: Sequence[ResolutionCandidate],
    ) -> tuple[SimilarityHit, ...]:
        """Compare facet observations at the layer's exactness level."""
        prior_by_digest: dict[str, TaskFacetObservation] = {}
        for observation in self.facet_source.observations:
            prior_by_digest.setdefault(
                observation.fingerprint_digest, observation)
        hits: list[SimilarityHit] = []
        for candidate in candidates:
            candidate_fingerprint_digest = candidate.fingerprint.digest
            prior = prior_by_digest.get(candidate_fingerprint_digest)
            if prior is None:
                continue
            for required_facet in request.facets:
                if required_facet.facet_kind != prior.facet_kind:
                    continue
                overlap = facet_overlap(required_facet, prior)
                ratio = float(overlap["role_overlap_ratio"])
                same_shape = bool(
                    required_facet.shape_digest == prior.shape_digest)
                family_ok = bool(overlap["same_family"])
                modality_ok = bool(overlap["same_modality"])
                if layer == SimilarityLayer.FACET_SHAPE and not same_shape:
                    continue
                if layer == SimilarityLayer.FACET_FAMILY:
                    if not family_ok or ratio < self.policy.min_role_overlap:
                        continue
                if layer == SimilarityLayer.FACET_MODALITY and not modality_ok:
                    continue
                hits.append(SimilarityHit(
                    candidate_ref=candidate.candidate_ref,
                    layer=layer,
                    origin=ResolutionOrigin.PARAMETERIZED_REUSE,
                    compatibility=candidate.compatibility,
                    role_overlap=ratio,
                    shared_roles=tuple(overlap["shared_roles"]),
                    missing_roles=tuple(overlap["missing_roles"]),
                    evidence_refs=(
                        f"facet:{required_facet.shape_digest}",
                        f"facet:{prior.shape_digest}"),
                ))
        return tuple(hits)


def find_similar_as_loop(
        engine: SimilarityEngine,
        request: TaskSimilarityRequest,
        *, parent=None, ledger=None) -> TaskSimilarityResult:
    """Cross the task similarity boundary through one component Loop."""
    from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
    from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome

    if not isinstance(engine, SimilarityEngine):
        raise TaskSimilarityError(
            "find_similar_as_loop needs a SimilarityEngine")
    if not isinstance(request, TaskSimilarityRequest):
        raise TaskSimilarityError(
            "find_similar_as_loop needs a TaskSimilarityRequest")
    config = LoopConfig(
        framework="custom", custom_steps=("resolve_similar",), power="light",
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",),
        logical_kind="execution", replay_guarantee="event_equivalent",
        exit_condition="steps_complete")
    identity = LoopRoleIdentity(LoopRole.INTELLIGENCE, "intelligence.search")
    relationship = (
        LoopRelationship.spawned_by(parent.loop_id) if parent is not None
        else LoopRelationship.starting())
    loop = (parent.spawn(
        "resolve similar prior tasks", config, identity=identity,
        relationship=relationship) if parent is not None else Loop(
            "resolve similar prior tasks", config, ledger=ledger,
            identity=identity, relationship=relationship))
    holder: dict[str, TaskSimilarityResult] = {}

    def handler(active, _step, _context):
        holder["value"] = engine.find_similar(request)
        record = holder["value"].to_dict()
        active.ledger.record(
            loop_id=active.loop_id, event="custom",
            custom_kind="task_similarity_resolution",
            similarity=record)
        return StepOutcome(
            "similarity:resolved", "deterministic", 1.0,
            failed=False)

    run = loop.run(handler=handler, max_steps=2)
    value = holder.get("value")
    if not isinstance(value, TaskSimilarityResult):
        raise TaskSimilarityError(
            "task similarity resolution returned the wrong type")
    return value


def self_test() -> dict[str, object]:
    tests: list[dict[str, object]] = []

    def check(name: str, passed: bool) -> None:
        tests.append({"test": name, "passed": bool(passed)})

    from .resolution import (
        ResolutionRequest, select_resolution_as_loop)
    from .store_serve import SolverStore
    from .solution_library import SolutionAsset, SolutionLibrary
    from .task_fingerprint import (
        ScaleBand, TaskFingerprint, task_fingerprint, TaskFingerprintRequest)
    from .task_fingerprint_facets import (
        ColumnShape, ColumnShapeRequest, column_shape_facet)

    fingerprint = task_fingerprint(TaskFingerprintRequest(
        problem="classification", output_role="churned", metric="accuracy",
        rows=8_000, modality="tabular", operator="predict",
        response_topology="label", input_contract="tabular_dataset/v1",
        output_contract="prediction_labels/v1"))

    related = TaskFingerprint(
        problem="classification", output_role="renewed",
        modality="tabular", operator="predict",
        response_topology="label", input_contract="tabular_dataset/v1",
        output_contract="prediction_labels/v1",
        scale_band=ScaleBand.SMALL)

    store = SolverStore()
    library = SolutionLibrary(store)
    library.add(SolutionAsset(
        "churn_lightgbm", "solution.tabular_churn", fingerprint,
        maturity="registered",
        runtime={"quality": 0.9, "cost": 0.1, "wall_seconds": 3.0}))
    library.add(SolutionAsset(
        "renewal_lightgbm", "solution.tabular_renewal", related,
        maturity="validated",
        runtime={"quality": 0.8, "cost": 0.05, "wall_seconds": 1.0}))

    columns = (
        ColumnShape("customer_id", "identifier"),
        ColumnShape("age", "numeric"),
        ColumnShape("plan", "categorical"),
        ColumnShape("churned", "boolean"),
    )
    shape_request = ColumnShapeRequest(
        row_count=8_000, columns=columns, target_column="churned")
    current_facet = column_shape_facet(
        shape_request, fingerprint.digest, "tabular")
    prior_facet = column_shape_facet(
        ColumnShapeRequest(
            row_count=8_000, columns=(
                ColumnShape("account_id", "identifier"),
                ColumnShape("tenure", "numeric"),
                ColumnShape("plan", "categorical"),
                ColumnShape("renewed", "boolean")),
            target_column="renewed"),
        related.digest, "tabular")

    engine = SimilarityEngine(
        candidate_source=LibraryCandidateSource(library=library),
        facet_source=FacetCandidateSource(
            observations=(prior_facet,)),
        policy=SimilarityPolicy(top_n=10))

    request = TaskSimilarityRequest(
        fingerprint=fingerprint, facets=(current_facet,))
    result = engine.find_similar(request)
    check("exact_layer_finds_the_registered_asset",
          any(hit.layer == SimilarityLayer.EXACT_FINGERPRINT
              and hit.candidate_ref == "solasset.churn_lightgbm"
              for hit in result.hits))
    check("contract_layer_finds_the_related_asset",
          any(hit.layer == SimilarityLayer.CONTRACT_COMPATIBLE
              and hit.candidate_ref == "solasset.renewal_lightgbm"
              for hit in result.hits))
    facet_engine = SimilarityEngine(
        candidate_source=LibraryCandidateSource(library=library),
        facet_source=FacetCandidateSource(observations=(prior_facet,)),
        policy=SimilarityPolicy(
            widen_levels=(SimilarityLayer.FACET_SHAPE,
                          SimilarityLayer.FACET_FAMILY,
                          SimilarityLayer.FACET_MODALITY)))
    facet_result = facet_engine.find_similar(request)
    check("facet_family_layer_reports_role_evidence",
          any(hit.layer == SimilarityLayer.FACET_FAMILY
              and hit.role_overlap is not None
              and hit.role_overlap >= 0.5
              and hit.candidate_ref == "solasset.renewal_lightgbm"
              for hit in facet_result.hits))
    check("layers_run_in_fixed_order",
          result.layers_run == tuple(
              layer for layer in LAYER_ORDER
              if layer in result.layers_run)
          and result.layers_run[0] == SimilarityLayer.EXACT_FINGERPRINT)
    check("every_hit_stays_prior_not_proof",
          all(hit.to_dict()["prior_not_proof"] is True
              for hit in result.hits))
    narrow_engine = SimilarityEngine(
        candidate_source=LibraryCandidateSource(library=library),
        policy=SimilarityPolicy(
            widen_levels=(SimilarityLayer.EXACT_FINGERPRINT,)))
    narrow_result = narrow_engine.find_similar(
        TaskSimilarityRequest(fingerprint=fingerprint))
    check("narrow_policy_blocks_widening",
          narrow_result.layers_run
          == (SimilarityLayer.EXACT_FINGERPRINT,))

    try:
        SimilarityPolicy(top_n=0)
        check("invalid_policy_is_refused", False)
    except TaskSimilarityError:
        check("invalid_policy_is_refused", True)

    looped = find_similar_as_loop(engine, request)
    check("boundary_crosses_through_a_component_loop",
          looped.hits == result.hits
          and looped.request_digest == result.request_digest)

    return {"tests": tests}


__all__ = (
    "FacetCandidateSource", "LibraryCandidateSource", "LAYER_ORDER",
    "SimilarityCandidateSource", "SimilarityEngine", "SimilarityHit",
    "SimilarityLayer", "SimilarityPolicy", "TaskSimilarityError",
    "TaskSimilarityRequest", "TaskSimilarityResult",
    "TASK_SIMILARITY_SCHEMA_VERSION", "find_similar_as_loop",
)