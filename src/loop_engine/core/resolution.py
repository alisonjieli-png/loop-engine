"""Parameterized reuse candidates validated through one Loop.

The records in this module are passive. They describe candidate origins, hard
constraints, preferences, rejections, and an explicit semantic selection. They do not
execute capabilities, mutate active assets, create graph authority, or grant
human approval. ``select_resolution_as_loop`` owns the deterministic operation
through the canonical Practitioner ``Loop``.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from enum import Enum

from .task_fingerprint import (
    CompatibilityAssessment,
    CompatibilityDimension,
    TaskFingerprint,
    TaskFingerprintRequest,
    assess_compatibility,
    task_fingerprint,
)


RESOLUTION_SCHEMA_VERSION = "resolution_decision/v2"


class ResolutionError(ValueError):
    """A resolution record or decision violated its typed contract."""


class ResolutionOrigin(str, Enum):
    """How a candidate proposes to satisfy one material work obligation."""

    EXACT_REUSE = "exact_reuse"
    PARAMETERIZED_REUSE = "parameterized_reuse"
    DERIVED_CANDIDATE = "derived_candidate"
    COMPOSITION = "composition"
    ANALOGICAL_GUIDANCE = "analogical_guidance"
    EXTERNAL_DISCOVERY = "external_discovery"
    NOVEL_DESIGN = "novel_design"


class CompatibilityRequirement(str, Enum):
    """Minimum compatibility evidence required by one resolution request."""

    EXACT = "exact"
    HARD_COMPATIBLE = "hard_compatible"


class ResolutionEligibility(str, Enum):
    """Whether a candidate may execute, guide, or only remain under review."""

    EXECUTABLE = "executable"
    CANDIDATE_ONLY = "candidate_only"
    GUIDANCE_ONLY = "guidance_only"
    UNAVAILABLE = "unavailable"


DEFAULT_ORIGIN_ORDER = (
    ResolutionOrigin.EXACT_REUSE,
    ResolutionOrigin.PARAMETERIZED_REUSE,
    ResolutionOrigin.DERIVED_CANDIDATE,
    ResolutionOrigin.COMPOSITION,
    ResolutionOrigin.ANALOGICAL_GUIDANCE,
    ResolutionOrigin.EXTERNAL_DISCOVERY,
    ResolutionOrigin.NOVEL_DESIGN,
)


def _required_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResolutionError(f"{name} must be a non-empty string")
    return value.strip()


def _probability(value: object, name: str) -> float:
    if (not isinstance(value, (int, float)) or isinstance(value, bool)
            or not math.isfinite(float(value))
            or not 0.0 <= float(value) <= 1.0):
        raise ResolutionError(f"{name} must be a finite value in [0, 1]")
    return float(value)


def _optional_non_negative(value: object, name: str) -> float | None:
    if value is None:
        return None
    if (not isinstance(value, (int, float)) or isinstance(value, bool)
            or not math.isfinite(float(value)) or float(value) < 0.0):
        raise ResolutionError(f"{name} must be finite and non-negative")
    return float(value)


@dataclass(frozen=True)
class ResolutionCandidate:
    """One passive capability, procedure, solution, or design-route candidate."""

    candidate_ref: str
    origin: ResolutionOrigin
    fingerprint: TaskFingerprint
    compatibility: CompatibilityAssessment
    eligibility: ResolutionEligibility = ResolutionEligibility.CANDIDATE_ONLY
    source_state: str = "candidate"
    expected_quality: float | None = None
    expected_cost: float | None = None
    expected_latency_seconds: float | None = None
    verification_strength: float = 0.0
    parameter_bindings: tuple[tuple[str, str], ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "candidate_ref", _required_text(
                self.candidate_ref, "candidate_ref"))
        if not isinstance(self.origin, ResolutionOrigin):
            try:
                object.__setattr__(self, "origin", ResolutionOrigin(self.origin))
            except (TypeError, ValueError) as exc:
                raise ResolutionError(
                    "resolution origin is not recognized") from exc
        if not isinstance(self.fingerprint, TaskFingerprint):
            raise ResolutionError("candidate fingerprint must be TaskFingerprint")
        if not isinstance(self.compatibility, CompatibilityAssessment):
            raise ResolutionError(
                "candidate compatibility must be CompatibilityAssessment")
        if self.compatibility.candidate_digest != self.fingerprint.digest:
            raise ResolutionError(
                "compatibility candidate digest does not match fingerprint")
        eligibility = self.eligibility
        if not isinstance(eligibility, ResolutionEligibility):
            try:
                eligibility = ResolutionEligibility(eligibility)
            except (TypeError, ValueError) as exc:
                raise ResolutionError(
                    "resolution eligibility is not recognized") from exc
            object.__setattr__(self, "eligibility", eligibility)
        object.__setattr__(
            self, "source_state", _required_text(
                self.source_state, "source_state"))
        object.__setattr__(self, "expected_quality", (
            None if self.expected_quality is None else
            _probability(self.expected_quality, "expected_quality")))
        object.__setattr__(
            self, "expected_cost",
            _optional_non_negative(self.expected_cost, "expected_cost"))
        object.__setattr__(
            self, "expected_latency_seconds", _optional_non_negative(
                self.expected_latency_seconds, "expected_latency_seconds"))
        object.__setattr__(self, "verification_strength", _probability(
            self.verification_strength, "verification_strength"))
        bindings = tuple(tuple(pair) for pair in self.parameter_bindings)
        if any(len(pair) != 2 or any(
                not isinstance(value, str) or not value.strip()
                for value in pair) for pair in bindings):
            raise ResolutionError(
                "parameter_bindings must contain non-empty name/value pairs")
        names = tuple(pair[0] for pair in bindings)
        if len(names) != len(set(names)):
            raise ResolutionError("parameter binding names cannot repeat")
        object.__setattr__(self, "parameter_bindings", bindings)
        evidence = tuple(self.evidence_refs)
        if any(not isinstance(ref, str) or not ref.strip() for ref in evidence):
            raise ResolutionError("evidence_refs must be non-empty strings")
        object.__setattr__(self, "evidence_refs", evidence)

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_ref": self.candidate_ref,
            "origin": self.origin.value,
            "fingerprint": self.fingerprint.to_dict(),
            "compatibility": self.compatibility.to_dict(),
            "eligibility": self.eligibility.value,
            "source_state": self.source_state,
            "expected_quality": self.expected_quality,
            "expected_cost": self.expected_cost,
            "expected_latency_seconds": self.expected_latency_seconds,
            "verification_strength": self.verification_strength,
            "parameter_bindings": [list(pair)
                                   for pair in self.parameter_bindings],
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class ResolutionRequest:
    """Hard constraints, candidate preferences, and optional model selection."""

    task_fingerprint: TaskFingerprint
    candidates: tuple[ResolutionCandidate, ...]
    allowed_origins: tuple[ResolutionOrigin, ...] = DEFAULT_ORIGIN_ORDER
    preferred_origins: tuple[ResolutionOrigin, ...] = DEFAULT_ORIGIN_ORDER
    compatibility_requirement: CompatibilityRequirement = (
        CompatibilityRequirement.HARD_COMPATIBLE)
    allowed_eligibilities: tuple[ResolutionEligibility, ...] = (
        ResolutionEligibility.EXECUTABLE,)
    maximum_cost: float | None = None
    maximum_latency_seconds: float | None = None
    minimum_quality: float = 0.0
    minimum_verification_strength: float = 0.0
    semantic_selection_ref: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.task_fingerprint, TaskFingerprint):
            raise ResolutionError("resolution request needs a TaskFingerprint")
        candidates = tuple(self.candidates)
        if any(not isinstance(item, ResolutionCandidate)
               for item in candidates):
            raise ResolutionError(
                "resolution candidates must be ResolutionCandidate objects")
        refs = tuple(item.candidate_ref for item in candidates)
        if len(refs) != len(set(refs)):
            raise ResolutionError("resolution candidate references cannot repeat")
        if any(item.compatibility.required_digest
               != self.task_fingerprint.digest for item in candidates):
            raise ResolutionError(
                "all assessments must target the request fingerprint")
        if (self.semantic_selection_ref
                and self.semantic_selection_ref not in refs):
            raise ResolutionError(
                "semantic_selection_ref must name a supplied candidate")
        object.__setattr__(self, "candidates", candidates)
        for name in ("allowed_origins", "preferred_origins"):
            values = tuple(getattr(self, name))
            try:
                values = tuple(
                    item if isinstance(item, ResolutionOrigin)
                    else ResolutionOrigin(item) for item in values)
            except (TypeError, ValueError) as exc:
                raise ResolutionError(
                    f"{name} contains an unknown origin") from exc
            if len(values) != len(set(values)):
                raise ResolutionError(f"{name} cannot repeat origins")
            object.__setattr__(self, name, values)
        requirement = self.compatibility_requirement
        if not isinstance(requirement, CompatibilityRequirement):
            try:
                requirement = CompatibilityRequirement(requirement)
            except (TypeError, ValueError) as exc:
                raise ResolutionError(
                    "compatibility_requirement is not recognized") from exc
            object.__setattr__(self, "compatibility_requirement", requirement)
        eligibilities = tuple(self.allowed_eligibilities)
        try:
            eligibilities = tuple(
                value if isinstance(value, ResolutionEligibility)
                else ResolutionEligibility(value) for value in eligibilities)
        except (TypeError, ValueError) as exc:
            raise ResolutionError(
                "allowed_eligibilities has an unknown value") from exc
        if not eligibilities or len(eligibilities) != len(set(eligibilities)):
            raise ResolutionError(
                "allowed_eligibilities must contain unique values")
        object.__setattr__(self, "allowed_eligibilities", eligibilities)
        object.__setattr__(
            self, "maximum_cost",
            _optional_non_negative(self.maximum_cost, "maximum_cost"))
        object.__setattr__(
            self, "maximum_latency_seconds", _optional_non_negative(
                self.maximum_latency_seconds, "maximum_latency_seconds"))
        object.__setattr__(
            self, "minimum_quality",
            _probability(self.minimum_quality, "minimum_quality"))
        object.__setattr__(
            self, "minimum_verification_strength", _probability(
                self.minimum_verification_strength,
                "minimum_verification_strength"))


@dataclass(frozen=True)
class ResolutionDecision:
    """Typed result of hard filtering plus optional semantic selection."""

    request_fingerprint_digest: str
    selected_candidate_ref: str = ""
    selected_origin: ResolutionOrigin | None = None
    considered_refs: tuple[str, ...] = ()
    eligible_refs: tuple[str, ...] = ()
    rejected: tuple[tuple[str, tuple[str, ...]], ...] = ()
    required_delta: tuple[str, ...] = ()
    rationale: str = ""
    schema_version: str = RESOLUTION_SCHEMA_VERSION
    decision_digest: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "request_fingerprint_digest", _required_text(
                self.request_fingerprint_digest,
                "request_fingerprint_digest"))
        if self.selected_candidate_ref:
            object.__setattr__(
                self, "selected_candidate_ref", _required_text(
                    self.selected_candidate_ref, "selected_candidate_ref"))
        origin = self.selected_origin
        if origin is not None and not isinstance(origin, ResolutionOrigin):
            try:
                origin = ResolutionOrigin(origin)
            except (TypeError, ValueError) as exc:
                raise ResolutionError(
                    "selected_origin is not recognized") from exc
            object.__setattr__(self, "selected_origin", origin)
        if self.schema_version != RESOLUTION_SCHEMA_VERSION:
            raise ResolutionError(
                f"schema_version must be {RESOLUTION_SCHEMA_VERSION}")
        if bool(self.selected_candidate_ref) != bool(self.selected_origin):
            raise ResolutionError(
                "selected candidate and origin must both be present or absent")
        considered = tuple(self.considered_refs)
        if (any(not isinstance(ref, str) or not ref.strip()
                for ref in considered)
                or len(considered) != len(set(considered))):
            raise ResolutionError(
                "considered references must be unique non-empty strings")
        object.__setattr__(self, "considered_refs", considered)
        eligible = tuple(self.eligible_refs)
        if (any(not isinstance(ref, str) or not ref.strip()
                for ref in eligible)
                or len(eligible) != len(set(eligible))
                or not set(eligible) <= set(considered)):
            raise ResolutionError(
                "eligible references must be unique considered candidates")
        object.__setattr__(self, "eligible_refs", eligible)
        rejected = tuple((ref, tuple(reasons)) for ref, reasons in self.rejected)
        if any(
                not isinstance(ref, str) or not ref.strip() or not reasons
                or any(not isinstance(reason, str) or not reason.strip()
                       for reason in reasons)
                for ref, reasons in rejected):
            raise ResolutionError("every rejected candidate needs reasons")
        object.__setattr__(self, "rejected", rejected)
        delta = tuple(self.required_delta)
        if (any(not isinstance(item, str) or not item.strip() for item in delta)
                or len(delta) != len(set(delta))):
            raise ResolutionError(
                "required_delta must contain unique non-empty dimensions")
        object.__setattr__(self, "required_delta", delta)
        object.__setattr__(
            self, "rationale", _required_text(self.rationale, "rationale"))
        computed = "sha256:" + hashlib.sha256(json.dumps(
            self.to_dict(include_digest=False), sort_keys=True,
            separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()
        if self.decision_digest and self.decision_digest != computed:
            raise ResolutionError(
                "decision_digest does not match decision content")
        object.__setattr__(self, "decision_digest", computed)

    @property
    def selected(self) -> bool:
        return bool(self.selected_candidate_ref)

    def to_dict(self, *, include_digest: bool = True) -> dict[str, object]:
        result: dict[str, object] = {
            "schema_version": self.schema_version,
            "request_fingerprint_digest": self.request_fingerprint_digest,
            "selected": self.selected,
            "selected_candidate_ref": self.selected_candidate_ref,
            "selected_origin": (
                self.selected_origin.value if self.selected_origin else ""),
            "considered_refs": list(self.considered_refs),
            "eligible_refs": list(self.eligible_refs),
            "rejected": [
                {"candidate_ref": ref, "reasons": list(reasons)}
                for ref, reasons in self.rejected
            ],
            "required_delta": list(self.required_delta),
            "rationale": self.rationale,
        }
        if include_digest:
            result["decision_digest"] = self.decision_digest
        return result


@dataclass(frozen=True)
class ResolutionRunResult:
    """One ResolutionDecision plus the Practitioner Loop execution evidence."""

    loop_id: str
    model_calls: int
    decision: ResolutionDecision

    def __post_init__(self) -> None:
        _required_text(self.loop_id, "loop_id")
        if not isinstance(self.model_calls, int) or self.model_calls < 0:
            raise ResolutionError("model_calls must be a non-negative integer")
        if not isinstance(self.decision, ResolutionDecision):
            raise ResolutionError("decision must be ResolutionDecision")

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": "resolution_run_result/v1",
            "loop_id": self.loop_id,
            "model_calls": self.model_calls,
            "decision": self.decision.to_dict(),
        }


def _candidate_rejections(
        request: ResolutionRequest,
        candidate: ResolutionCandidate) -> tuple[str, ...]:
    reasons: list[str] = []
    if candidate.origin not in request.allowed_origins:
        reasons.append("origin_not_allowed")
    if candidate.eligibility not in request.allowed_eligibilities:
        reasons.append("eligibility_not_allowed")
    if request.compatibility_requirement == CompatibilityRequirement.EXACT:
        if not candidate.compatibility.exact:
            reasons.append("exact_compatibility_required")
    elif not candidate.compatibility.compatible:
        reasons.extend(
            f"hard_incompatible:{item.value}"
            for item in sorted(
                candidate.compatibility.hard_failures,
                key=lambda item: item.value))
    if request.maximum_cost is not None:
        if candidate.expected_cost is None:
            reasons.append("cost_unknown")
        elif candidate.expected_cost > request.maximum_cost:
            reasons.append("cost_exceeds_limit")
    if request.maximum_latency_seconds is not None:
        if candidate.expected_latency_seconds is None:
            reasons.append("latency_unknown")
        elif candidate.expected_latency_seconds > request.maximum_latency_seconds:
            reasons.append("latency_exceeds_limit")
    if candidate.expected_quality is None and request.minimum_quality > 0.0:
        reasons.append("quality_unknown")
    elif (candidate.expected_quality is not None
          and candidate.expected_quality < request.minimum_quality):
        reasons.append("quality_below_minimum")
    if candidate.verification_strength < request.minimum_verification_strength:
        reasons.append("verification_below_minimum")
    return tuple(reasons)


def select_resolution(request: ResolutionRequest) -> ResolutionDecision:
    """Validate candidates and one optional model-selected candidate."""
    if not isinstance(request, ResolutionRequest):
        raise ResolutionError("select_resolution needs ResolutionRequest")
    rejected: list[tuple[str, tuple[str, ...]]] = []
    eligible: list[ResolutionCandidate] = []
    for candidate in request.candidates:
        reasons = _candidate_rejections(request, candidate)
        if reasons:
            rejected.append((candidate.candidate_ref, reasons))
        else:
            eligible.append(candidate)
    eligible_by_ref = {item.candidate_ref: item for item in eligible}
    selected = (eligible_by_ref.get(request.semantic_selection_ref)
                if request.semantic_selection_ref else None)
    if request.semantic_selection_ref and selected is None:
        raise ResolutionError(
            "the semantic selection did not pass every hard gate")
    return ResolutionDecision(
        request_fingerprint_digest=request.task_fingerprint.digest,
        selected_candidate_ref=(selected.candidate_ref if selected else ""),
        selected_origin=(selected.origin if selected else None),
        considered_refs=tuple(
            candidate.candidate_ref for candidate in request.candidates),
        eligible_refs=tuple(candidate.candidate_ref for candidate in eligible),
        rejected=tuple(rejected),
        required_delta=(selected.compatibility.required_delta
                        if selected else ()),
        rationale=(
            "validated the model-selected candidate against every hard gate"
            if selected else
            "eligible candidates await model-led semantic selection"
            if eligible else "no candidate passed every hard gate"),
    )


def select_resolution_as_loop(request: ResolutionRequest) -> ResolutionRunResult:
    """Run deterministic candidate validation through the canonical Loop."""
    from ..loop.encapsulate import as_practitioner_loop

    result = as_practitioner_loop(
        "validate contract-compatible resolution candidates",
        lambda: select_resolution(request))
    if result["model_calls"] != 0:
        raise ResolutionError(
            "deterministic resolution selection made an unexpected model call")
    return ResolutionRunResult(
        loop_id=result["loop_id"], model_calls=result["model_calls"],
        decision=result["value"])


def self_test() -> dict[str, object]:
    tests: list[dict[str, object]] = []

    def check(name: str, passed: bool) -> None:
        tests.append({"test": name, "passed": bool(passed)})

    required = task_fingerprint(TaskFingerprintRequest(
        problem="classification", output_role="label", metric="accuracy",
        rows=8_000, modality="tabular", operator="predict",
        response_topology="label", input_contract="tabular_dataset/v1",
        output_contract="prediction_labels/v1", domain="retention"))
    adapted = task_fingerprint(TaskFingerprintRequest(
        problem="classification", output_role="renewed", metric="roc_auc",
        rows=50_000, modality="tabular", operator="predict",
        response_topology="label", input_contract="tabular_dataset/v1",
        output_contract="prediction_labels/v1", domain="retention"))
    regression = task_fingerprint(TaskFingerprintRequest(
        problem="regression", output_role="value", rows=8_000,
        modality="tabular", operator="predict", response_topology="score",
        input_contract="tabular_dataset/v1",
        output_contract="prediction_scores/v1"))
    exact = ResolutionCandidate(
        "solution:exact@1", ResolutionOrigin.EXACT_REUSE, required,
        assess_compatibility(required, required),
        eligibility=ResolutionEligibility.EXECUTABLE,
        source_state="registered",
        expected_quality=0.91, expected_cost=0.1,
        expected_latency_seconds=1.0, verification_strength=1.0)
    parameterized = ResolutionCandidate(
        "solution:adapted@1", ResolutionOrigin.PARAMETERIZED_REUSE, adapted,
        assess_compatibility(required, adapted),
        eligibility=ResolutionEligibility.EXECUTABLE,
        source_state="registered",
        expected_quality=0.95, expected_cost=0.05,
        expected_latency_seconds=0.5, verification_strength=0.9,
        parameter_bindings=(("target", "label"),))
    incompatible = ResolutionCandidate(
        "solution:wrong-family@1", ResolutionOrigin.EXACT_REUSE, regression,
        assess_compatibility(required, regression),
        eligibility=ResolutionEligibility.EXECUTABLE,
        source_state="registered",
        expected_quality=0.99, expected_cost=0.01,
        expected_latency_seconds=0.1, verification_strength=1.0)
    request = ResolutionRequest(
        required, (parameterized, incompatible, exact), maximum_cost=1.0,
        maximum_latency_seconds=10.0, minimum_quality=0.8,
        minimum_verification_strength=0.8)
    decision = select_resolution(request)
    check("eligible_reuse_candidates_wait_for_semantic_selection",
          not decision.selected
          and set(decision.eligible_refs)
              == {exact.candidate_ref, parameterized.candidate_ref})
    model_selected = select_resolution(ResolutionRequest(
        required, (parameterized, incompatible, exact), maximum_cost=1.0,
        maximum_latency_seconds=10.0, minimum_quality=0.8,
        minimum_verification_strength=0.8,
        semantic_selection_ref=parameterized.candidate_ref))
    check("explicit_semantic_selection_is_validated_without_local_ranking",
          model_selected.selected_candidate_ref
              == parameterized.candidate_ref)
    rejection_map = dict(decision.rejected)
    check("hard_incompatible_candidate_is_rejected_before_selection",
          any(reason.startswith("hard_incompatible:")
              for reason in rejection_map[incompatible.candidate_ref]))
    try:
        ResolutionDecision(
            request_fingerprint_digest=required.digest,
            selected_candidate_ref=exact.candidate_ref,
            selected_origin=ResolutionOrigin.EXACT_REUSE,
            rationale="tampered decision fixture",
            decision_digest="sha256:" + "0" * 64)
        check("tampered_resolution_decision_digest_is_refused", False)
    except ResolutionError:
        check("tampered_resolution_decision_digest_is_refused", True)
    unreviewed = ResolutionCandidate(
        "solution:unreviewed@1", ResolutionOrigin.DERIVED_CANDIDATE, required,
        assess_compatibility(required, required),
        eligibility=ResolutionEligibility.CANDIDATE_ONLY,
        source_state="candidate",
        verification_strength=1.0)
    abstained = select_resolution(ResolutionRequest(required, (unreviewed,)))
    check("unreviewed_derived_candidate_cannot_become_active_reuse",
          not abstained.selected)
    loop_result = select_resolution_as_loop(request)
    check("candidate_validation_runs_through_loop_with_zero_model_calls",
          loop_result.loop_id.startswith("loop")
          and loop_result.model_calls == 0
          and loop_result.decision.decision_digest.startswith("sha256:"))
    check("human_authority_is_not_a_resolution_origin",
          "human_resolution" not in {item.value for item in ResolutionOrigin})
    return {"tests": tests}


__all__ = (
    "CompatibilityRequirement", "ResolutionCandidate", "ResolutionDecision",
    "ResolutionEligibility", "ResolutionError", "ResolutionOrigin", "ResolutionRequest",
    "ResolutionRunResult", "select_resolution", "select_resolution_as_loop",
)
