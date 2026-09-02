"""Passive contracts for the Reusable Capability Flywheel.

These records describe needs, opportunities, policies, matches, plans, and
results. They do not search, execute, qualify, promote, or schedule work.
Those operations remain owned by canonical Loops in
``reusable_capability_flywheel``.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Mapping


_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")

REUSE_ASSESSMENT_DIMENSIONS = (
    "observed_correctness",
    "recurrence_likelihood",
    "expected_use_volume",
    "transfer_breadth",
    "parameterization_clarity",
    "contract_clarity",
    "determinism_potential",
    "testability",
    "catalog_gap",
    "cost_savings",
    "quality_uplift",
    "dependency_stability",
    "effect_safety",
    "security_privacy",
    "build_difficulty",
    "qualification_difficulty",
    "maintenance_burden",
    "evidence_diversity",
)


class ReusableCapabilityContractError(ValueError):
    """A flywheel record does not satisfy its public contract."""


class ReuseRecommendation(str, Enum):
    DISCARD = "discard"
    STORE_AS_EXAMPLE_ONLY = "store_as_example_only"
    OBSERVE_AND_CLUSTER = "observe_and_cluster"
    CREATE_NEW_CAPABILITY_CANDIDATE = "create_new_capability_candidate"
    CREATE_NEW_VERSION_CANDIDATE = "create_new_version_candidate"
    CREATE_ADAPTER_CANDIDATE = "create_adapter_candidate"
    MERGE_INTO_EXISTING_CANDIDATE = "merge_into_existing_candidate"
    CREATE_COMPOSITE_CANDIDATE = "create_composite_candidate"
    REQUIRE_MORE_EVIDENCE = "require_more_evidence"
    REQUIRE_HUMAN_REVIEW = "require_human_review"
    QUARANTINE = "quarantine"


class HarvestDispatch(str, Enum):
    ASYNC = "async"
    INLINE = "inline"


class ResolutionDisposition(str, Enum):
    EXECUTE_EXACT = "execute_exact"
    REQUIRE_SELECTION = "require_selection"
    REQUEST_HYBRID_ASSISTANCE = "request_hybrid_assistance"
    ESCALATE_TO_NOVEL_BUILD = "escalate_to_novel_build"
    ABSTAIN = "abstain"


class HybridAssistanceStage(str, Enum):
    NEED_NORMALIZATION = "need_normalization"
    QUERY_EXPANSION = "query_expansion"
    CANDIDATE_RERANKING = "candidate_reranking"
    PARAMETER_BINDING = "parameter_binding"
    INPUT_ADAPTER_SYNTHESIS = "input_adapter_synthesis"
    OUTPUT_ADAPTER_SYNTHESIS = "output_adapter_synthesis"
    CAPABILITY_COMPOSITION = "capability_composition"
    FAILURE_DIAGNOSIS = "failure_diagnosis"
    BOUNDED_REPAIR = "bounded_repair"


def canonical_json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        default=str)


def content_digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _identifier(label: str, value: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ReusableCapabilityContractError(f"{label} is invalid")
    return value


def _digest(label: str, value: str) -> str:
    if (not isinstance(value, str) or len(value) != 64
            or any(character not in "0123456789abcdef"
                   for character in value)):
        raise ReusableCapabilityContractError(
            f"{label} must be a lowercase SHA-256 digest")
    return value


def _names(label: str, values) -> tuple[str, ...]:
    result = tuple(values or ())
    if (any(not isinstance(item, str) or not item.strip() for item in result)
            or len(result) != len(set(result))):
        raise ReusableCapabilityContractError(
            f"{label} must contain unique non-empty strings")
    return result


def _pairs(label: str, values) -> tuple[tuple[str, str], ...]:
    if isinstance(values, Mapping):
        values = tuple(sorted((str(key), str(value))
                              for key, value in values.items()))
    result = tuple(values or ())
    if (any(not isinstance(item, tuple) or len(item) != 2
            or any(not isinstance(part, str) or not part.strip()
                   for part in item) for item in result)
            or len({item[0] for item in result}) != len(result)):
        raise ReusableCapabilityContractError(
            f"{label} must contain unique non-empty string keys and values")
    return tuple(sorted(result))


@dataclass(frozen=True)
class CapabilityNeed:
    """Typed subtask need used for retrieval, not the raw user request."""

    need_id: str
    originating_run_id: str
    originating_loop_profile_ref: str
    goal: str
    operation_family: str
    semantic_summary: str
    input_contract_ref: str
    input_contract_digest: str
    output_contract_ref: str
    output_contract_digest: str
    allowed_effects: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    prohibited_capabilities: tuple[str, ...] = ()
    environment_constraints: tuple[tuple[str, str], ...] = ()
    dependency_constraints: tuple[tuple[str, str], ...] = ()
    privacy_scope: str = "run_private"
    tenant_scope: str = ""
    search_terms: tuple[str, ...] = ()
    schema_version: str = "capability_need/v1"

    def __post_init__(self) -> None:
        if self.schema_version != "capability_need/v1":
            raise ReusableCapabilityContractError(
                "unsupported CapabilityNeed schema")
        for label, value in (
                ("need_id", self.need_id),
                ("originating_run_id", self.originating_run_id)):
            _identifier(label, value)
        for label, value in (
                ("originating_loop_profile_ref",
                 self.originating_loop_profile_ref),
                ("goal", self.goal),
                ("operation_family", self.operation_family),
                ("semantic_summary", self.semantic_summary),
                ("input_contract_ref", self.input_contract_ref),
                ("output_contract_ref", self.output_contract_ref),
                ("privacy_scope", self.privacy_scope)):
            if not isinstance(value, str) or not value.strip():
                raise ReusableCapabilityContractError(f"{label} is required")
        _digest("input_contract_digest", self.input_contract_digest)
        _digest("output_contract_digest", self.output_contract_digest)
        for label in (
                "allowed_effects", "required_capabilities",
                "prohibited_capabilities", "search_terms"):
            object.__setattr__(self, label, _names(label, getattr(self, label)))
        if set(self.required_capabilities) & set(self.prohibited_capabilities):
            raise ReusableCapabilityContractError(
                "a capability cannot be both required and prohibited")
        for label in ("environment_constraints", "dependency_constraints"):
            object.__setattr__(
                self, label, _pairs(label, getattr(self, label)))

    @property
    def normalized_digest(self) -> str:
        """Digest reusable semantics without retry or provenance identity."""
        return content_digest({
            "schema_version": self.schema_version,
            "goal": self.goal,
            "operation_family": self.operation_family,
            "semantic_summary": self.semantic_summary,
            "input_contract_ref": self.input_contract_ref,
            "input_contract_digest": self.input_contract_digest,
            "output_contract_ref": self.output_contract_ref,
            "output_contract_digest": self.output_contract_digest,
            "allowed_effects": list(self.allowed_effects),
            "required_capabilities": list(self.required_capabilities),
            "prohibited_capabilities": list(self.prohibited_capabilities),
            "environment_constraints": dict(self.environment_constraints),
            "dependency_constraints": dict(self.dependency_constraints),
            "privacy_scope": self.privacy_scope,
            "tenant_scope": self.tenant_scope,
            "search_terms": list(self.search_terms),
        })

    @property
    def record_digest(self) -> str:
        """Digest the full record, including its run provenance."""
        return content_digest(self.to_dict())

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "need_id": self.need_id,
            "originating_run_id": self.originating_run_id,
            "originating_loop_profile_ref": self.originating_loop_profile_ref,
            "goal": self.goal,
            "operation_family": self.operation_family,
            "semantic_summary": self.semantic_summary,
            "input_contract_ref": self.input_contract_ref,
            "input_contract_digest": self.input_contract_digest,
            "output_contract_ref": self.output_contract_ref,
            "output_contract_digest": self.output_contract_digest,
            "allowed_effects": list(self.allowed_effects),
            "required_capabilities": list(self.required_capabilities),
            "prohibited_capabilities": list(self.prohibited_capabilities),
            "environment_constraints": dict(self.environment_constraints),
            "dependency_constraints": dict(self.dependency_constraints),
            "privacy_scope": self.privacy_scope,
            "tenant_scope": self.tenant_scope,
            "search_terms": list(self.search_terms),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "CapabilityNeed":
        body = dict(value)
        for name in (
                "allowed_effects", "required_capabilities",
                "prohibited_capabilities", "search_terms"):
            body[name] = tuple(body.get(name) or ())
        for name in ("environment_constraints", "dependency_constraints"):
            body[name] = _pairs(name, body.get(name) or {})
        return cls(**body)


@dataclass(frozen=True)
class ReuseOpportunityObserved:
    """Lightweight post-verification observation suitable for a queue."""

    event_id: str
    correlation_id: str
    source_run_id: str
    source_loop_id: str
    source_loop_profile_ref: str
    source_loop_definition_ref: str
    accepted_result_ref: str
    execution_record_ref: str
    artifact_ref: str
    artifact_digest: str
    artifact_kind: str
    operation_family: str
    dispatch: HarvestDispatch
    idempotency_key: str
    observed_at: str
    schema_version: str = "reuse_opportunity_observed/v1"

    def __post_init__(self) -> None:
        if self.schema_version != "reuse_opportunity_observed/v1":
            raise ReusableCapabilityContractError(
                "unsupported reuse opportunity schema")
        for label in ("event_id", "correlation_id", "source_run_id",
                      "source_loop_id", "idempotency_key"):
            _identifier(label, getattr(self, label))
        for label in (
                "source_loop_profile_ref", "source_loop_definition_ref",
                "accepted_result_ref",
                "execution_record_ref", "artifact_ref", "artifact_kind",
                "operation_family", "observed_at"):
            value = getattr(self, label)
            if not isinstance(value, str) or not value.strip():
                raise ReusableCapabilityContractError(f"{label} is required")
        _digest("artifact_digest", self.artifact_digest)
        if not isinstance(self.dispatch, HarvestDispatch):
            raise ReusableCapabilityContractError(
                "reuse dispatch must use HarvestDispatch")

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "correlation_id": self.correlation_id,
            "source_run_id": self.source_run_id,
            "source_loop_id": self.source_loop_id,
            "source_loop_profile_ref": self.source_loop_profile_ref,
            "source_loop_definition_ref": self.source_loop_definition_ref,
            "accepted_result_ref": self.accepted_result_ref,
            "execution_record_ref": self.execution_record_ref,
            "artifact_ref": self.artifact_ref,
            "artifact_digest": self.artifact_digest,
            "artifact_kind": self.artifact_kind,
            "operation_family": self.operation_family,
            "dispatch": self.dispatch.value,
            "idempotency_key": self.idempotency_key,
            "observed_at": self.observed_at,
        }

    @property
    def digest(self) -> str:
        return content_digest(self.to_dict())

    @classmethod
    def from_dict(
            cls, value: Mapping[str, object]) -> "ReuseOpportunityObserved":
        body = dict(value)
        try:
            body["dispatch"] = HarvestDispatch(body.get("dispatch"))
        except (TypeError, ValueError) as exc:
            raise ReusableCapabilityContractError(
                "reuse opportunity dispatch is invalid") from exc
        return cls(**body)


@dataclass(frozen=True)
class ReuseAssessment:
    """Advisory model judgement plus structured evidence and disposition."""

    assessment_id: str
    opportunity_id: str
    assessor_loop_id: str
    source_success_verified: bool
    dimensions: tuple[tuple[str, float], ...]
    summary_score_1_to_10: float
    confidence: float
    recommendation: ReuseRecommendation
    rationale: str
    evidence_refs: tuple[str, ...]
    expected_value: float | None = None
    blocking_reasons: tuple[str, ...] = ()
    schema_version: str = "reuse_assessment/v1"

    def __post_init__(self) -> None:
        if self.schema_version != "reuse_assessment/v1":
            raise ReusableCapabilityContractError(
                "unsupported ReuseAssessment schema")
        for label in ("assessment_id", "opportunity_id", "assessor_loop_id"):
            _identifier(label, getattr(self, label))
        if not isinstance(self.source_success_verified, bool):
            raise ReusableCapabilityContractError(
                "source_success_verified must be boolean evidence")
        dimensions = tuple(self.dimensions)
        if (not dimensions or any(
                not isinstance(item, tuple) or len(item) != 2
                or not isinstance(item[0], str) or not item[0].strip()
                or not isinstance(item[1], (int, float))
                or isinstance(item[1], bool)
                or not 0.0 <= float(item[1]) <= 10.0
                for item in dimensions)
                or len({item[0] for item in dimensions}) != len(dimensions)):
            raise ReusableCapabilityContractError(
                "assessment dimensions must be unique zero-to-ten scores")
        object.__setattr__(self, "dimensions", tuple(
            (name, float(score)) for name, score in dimensions))
        if {name for name, _score in dimensions} != set(
                REUSE_ASSESSMENT_DIMENSIONS):
            raise ReusableCapabilityContractError(
                "reuse assessment must cover every registered dimension")
        if (not isinstance(self.summary_score_1_to_10, (int, float))
                or isinstance(self.summary_score_1_to_10, bool)
                or not 1.0 <= float(self.summary_score_1_to_10) <= 10.0):
            raise ReusableCapabilityContractError(
                "reuse summary score must be from one through ten")
        if (not isinstance(self.confidence, (int, float))
                or isinstance(self.confidence, bool)
                or not 0.0 <= float(self.confidence) <= 1.0):
            raise ReusableCapabilityContractError(
                "reuse assessment confidence must be zero through one")
        if not isinstance(self.recommendation, ReuseRecommendation):
            raise ReusableCapabilityContractError(
                "reuse recommendation is not registered")
        if not self.rationale.strip():
            raise ReusableCapabilityContractError(
                "reuse assessment needs a rationale")
        evidence_refs = _names("evidence_refs", self.evidence_refs)
        if self.source_success_verified and not evidence_refs:
            raise ReusableCapabilityContractError(
                "verified source assessment requires evidence references")
        object.__setattr__(self, "evidence_refs", evidence_refs)
        object.__setattr__(
            self, "blocking_reasons",
            _names("blocking_reasons", self.blocking_reasons))

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "assessment_id": self.assessment_id,
            "opportunity_id": self.opportunity_id,
            "assessor_loop_id": self.assessor_loop_id,
            "source_success_verified": self.source_success_verified,
            "dimensions": dict(self.dimensions),
            "summary_score_1_to_10": self.summary_score_1_to_10,
            "confidence": self.confidence,
            "recommendation": self.recommendation.value,
            "rationale": self.rationale,
            "evidence_refs": list(self.evidence_refs),
            "expected_value": self.expected_value,
            "blocking_reasons": list(self.blocking_reasons),
        }

    @property
    def digest(self) -> str:
        return content_digest(self.to_dict())

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "ReuseAssessment":
        body = dict(value)
        dimensions = body.get("dimensions")
        dimension_map = {
            str(name): float(score)
            for name, score in dict(dimensions or {}).items()}
        body["dimensions"] = tuple(
            (name, dimension_map[name])
            for name in REUSE_ASSESSMENT_DIMENSIONS
            if name in dimension_map)
        for name in ("evidence_refs", "blocking_reasons"):
            body[name] = tuple(body.get(name) or ())
        try:
            body["recommendation"] = ReuseRecommendation(
                body.get("recommendation"))
        except (TypeError, ValueError) as exc:
            raise ReusableCapabilityContractError(
                "reuse recommendation is invalid") from exc
        return cls(**body)


@dataclass(frozen=True)
class CapabilityGeneralizationRecord:
    """Lineage from one observed artifact to one parameterized candidate."""

    generalization_id: str
    opportunity_id: str
    source_artifact_ref: str
    source_artifact_digest: str
    candidate_artifact_ref: str
    candidate_artifact_digest: str
    producer_loop_id: str
    parameter_names: tuple[str, ...]
    preserved_invariants: tuple[str, ...]
    removed_assumptions: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    schema_version: str = "capability_generalization/v1"

    def __post_init__(self) -> None:
        if self.schema_version != "capability_generalization/v1":
            raise ReusableCapabilityContractError(
                "unsupported capability generalization schema")
        for label in (
                "generalization_id", "opportunity_id", "producer_loop_id"):
            _identifier(label, getattr(self, label))
        for label in ("source_artifact_ref", "candidate_artifact_ref"):
            if not isinstance(getattr(self, label), str) or not getattr(
                    self, label).strip():
                raise ReusableCapabilityContractError(f"{label} is required")
        _digest("source_artifact_digest", self.source_artifact_digest)
        _digest("candidate_artifact_digest", self.candidate_artifact_digest)
        for label in (
                "parameter_names", "preserved_invariants",
                "removed_assumptions", "evidence_refs"):
            object.__setattr__(self, label, _names(label, getattr(self, label)))
        if not self.preserved_invariants or not self.evidence_refs:
            raise ReusableCapabilityContractError(
                "generalization needs invariants and evidence")

    @property
    def digest(self) -> str:
        return content_digest(self.to_dict())

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "generalization_id": self.generalization_id,
            "opportunity_id": self.opportunity_id,
            "source_artifact_ref": self.source_artifact_ref,
            "source_artifact_digest": self.source_artifact_digest,
            "candidate_artifact_ref": self.candidate_artifact_ref,
            "candidate_artifact_digest": self.candidate_artifact_digest,
            "producer_loop_id": self.producer_loop_id,
            "parameter_names": list(self.parameter_names),
            "preserved_invariants": list(self.preserved_invariants),
            "removed_assumptions": list(self.removed_assumptions),
            "evidence_refs": list(self.evidence_refs),
        }

    @classmethod
    def from_dict(
            cls, value: Mapping[str, object]
            ) -> "CapabilityGeneralizationRecord":
        body = dict(value)
        for name in (
                "parameter_names", "preserved_invariants",
                "removed_assumptions", "evidence_refs"):
            body[name] = tuple(body.get(name) or ())
        return cls(**body)


@dataclass(frozen=True)
class ReuseHarvestPolicy:
    """Dispatch and trust policy with no built-in score threshold."""

    policy_id: str
    version: str
    dispatch: HarvestDispatch = HarvestDispatch.ASYNC
    enabled: bool = True
    require_verified_source: bool = True
    require_independent_qualifier: bool = True
    automatic_promotion: bool = False
    allowed_artifact_kinds: tuple[str, ...] = (
        "python_function", "python_module", "python_project", "query",
        "adapter", "composition", "semantic_procedure",
        "cached_procedure", "verifier", "context_policy", "test_fixture")

    def __post_init__(self) -> None:
        _identifier("policy_id", self.policy_id)
        if not _SEMVER.fullmatch(self.version):
            raise ReusableCapabilityContractError(
                "harvest policy version must use semantic versioning")
        if not isinstance(self.dispatch, HarvestDispatch):
            raise ReusableCapabilityContractError(
                "harvest policy dispatch is invalid")
        if any(not isinstance(value, bool) for value in (
                self.enabled,
                self.require_verified_source,
                self.require_independent_qualifier,
                self.automatic_promotion)):
            raise ReusableCapabilityContractError(
                "harvest policy flags must be booleans")
        if self.automatic_promotion:
            raise ReusableCapabilityContractError(
                "harvesting cannot grant itself automatic promotion")
        object.__setattr__(
            self, "allowed_artifact_kinds",
            _names("allowed_artifact_kinds", self.allowed_artifact_kinds))


@dataclass(frozen=True)
class HybridAssistanceProfile:
    """Named bounded stages under the single canonical hybrid mode."""

    profile_id: str
    version: str
    stages: tuple[HybridAssistanceStage, ...]
    maximum_model_calls: int | None = None
    maximum_repair_attempts: int | None = None
    candidate_limit_before_model: int | None = None

    def __post_init__(self) -> None:
        _identifier("profile_id", self.profile_id)
        if not _SEMVER.fullmatch(self.version):
            raise ReusableCapabilityContractError(
                "hybrid profile version must use semantic versioning")
        stages = tuple(self.stages)
        if (not stages or any(not isinstance(stage, HybridAssistanceStage)
                              for stage in stages)
                or len(stages) != len(set(stages))):
            raise ReusableCapabilityContractError(
                "hybrid assistance stages must be unique and typed")
        object.__setattr__(self, "stages", stages)
        for label in (
                "maximum_model_calls", "maximum_repair_attempts",
                "candidate_limit_before_model"):
            value = getattr(self, label)
            if (value is not None and (
                    not isinstance(value, int) or isinstance(value, bool)
                    or value < 0)):
                raise ReusableCapabilityContractError(
                    f"{label} must be a non-negative integer when supplied")


@dataclass(frozen=True)
class CapabilityCandidateMatch:
    capability_ref: str
    artifact_digest: str
    eligible: bool
    rejection_reasons: tuple[str, ...]
    exact_contract_match: bool
    operation_family_match: bool
    adapter_required: bool
    feature_evidence: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        if not self.capability_ref.strip():
            raise ReusableCapabilityContractError(
                "candidate match requires a capability reference")
        _digest("artifact_digest", self.artifact_digest)
        if any(not isinstance(value, bool) for value in (
                self.eligible, self.exact_contract_match,
                self.operation_family_match, self.adapter_required)):
            raise ReusableCapabilityContractError(
                "candidate match flags must be booleans")
        object.__setattr__(
            self, "rejection_reasons",
            _names("rejection_reasons", self.rejection_reasons))
        if self.eligible and self.rejection_reasons:
            raise ReusableCapabilityContractError(
                "eligible candidate cannot carry rejection reasons")


@dataclass(frozen=True)
class CapabilityResolutionPlan:
    plan_id: str
    need_id: str
    disposition: ResolutionDisposition
    execution_mode: str
    selected_capability_ref: str = ""
    selected_artifact_digest: str = ""
    assistance_profile_ref: str = ""
    model_call_budget: int | None = None
    selection_evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _identifier("plan_id", self.plan_id)
        _identifier("need_id", self.need_id)
        if not isinstance(self.disposition, ResolutionDisposition):
            raise ReusableCapabilityContractError(
                "resolution disposition is invalid")
        if self.execution_mode not in (
                "deterministic", "hybrid", "non_deterministic"):
            raise ReusableCapabilityContractError(
                "resolution plan uses an unknown canonical mode")
        if self.selected_artifact_digest:
            _digest("selected_artifact_digest",
                    self.selected_artifact_digest)
        if (self.disposition is ResolutionDisposition.EXECUTE_EXACT
                and (not self.selected_capability_ref
                     or not self.selected_artifact_digest)):
            raise ReusableCapabilityContractError(
                "exact execution requires capability and artifact identity")
        if (self.model_call_budget is not None
                and (not isinstance(self.model_call_budget, int)
                     or isinstance(self.model_call_budget, bool)
                     or self.model_call_budget < 0)):
            raise ReusableCapabilityContractError(
                "model call budget must be non-negative when supplied")
        object.__setattr__(
            self, "selection_evidence_refs",
            _names("selection_evidence_refs",
                   self.selection_evidence_refs))


@dataclass(frozen=True)
class CapabilityInvocationRecord:
    invocation_id: str
    run_id: str
    need_id: str
    resolution_plan_id: str
    exact_capability_ref: str
    exact_artifact_digest: str
    exact_dependency_digest: str
    verifier_id: str
    mode_used: str
    assistance_profile_ref: str
    model_call_count: int
    input_digest: str
    output_digest: str
    execution_status: str
    verification_status: str
    accepted: bool
    failure_class: str = ""
    record_type: str = "capability_invocation_record/v1"

    def __post_init__(self) -> None:
        if self.record_type != "capability_invocation_record/v1":
            raise ReusableCapabilityContractError(
                "unsupported invocation record schema")
        for label in (
                "invocation_id", "run_id", "need_id",
                "resolution_plan_id"):
            _identifier(label, getattr(self, label))
        _identifier("verifier_id", self.verifier_id)
        for label in (
                "exact_artifact_digest", "exact_dependency_digest",
                "input_digest"):
            _digest(label, getattr(self, label))
        if self.output_digest:
            _digest("output_digest", self.output_digest)
        if self.mode_used not in (
                "deterministic", "hybrid", "non_deterministic"):
            raise ReusableCapabilityContractError(
                "invocation record mode is invalid")
        if (not isinstance(self.model_call_count, int)
                or isinstance(self.model_call_count, bool)
                or self.model_call_count < 0):
            raise ReusableCapabilityContractError(
                "model call count must be non-negative")
        if self.accepted and (
                self.execution_status != "completed"
                or self.verification_status != "verified"
                or not self.output_digest):
            raise ReusableCapabilityContractError(
                "accepted invocation requires completed verified output")

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def from_dict(
            cls, value: Mapping[str, object]) -> "CapabilityInvocationRecord":
        return cls(**dict(value))


__all__ = (
    "REUSE_ASSESSMENT_DIMENSIONS",
    "CapabilityCandidateMatch",
    "CapabilityGeneralizationRecord",
    "CapabilityInvocationRecord",
    "CapabilityNeed",
    "CapabilityResolutionPlan",
    "HarvestDispatch",
    "HybridAssistanceProfile",
    "HybridAssistanceStage",
    "ResolutionDisposition",
    "ReusableCapabilityContractError",
    "ReuseAssessment",
    "ReuseHarvestPolicy",
    "ReuseOpportunityObserved",
    "ReuseRecommendation",
    "canonical_json",
    "content_digest",
)
