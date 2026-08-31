"""Observe, dispatch, assess, and parameterize reusable capability work.

This module owns the online-to-offline harvest boundary. Every semantic action
runs through the canonical Loop runtime. Records remain passive, and candidate
creation still delegates lifecycle authority to ``CapabilityAuthority``.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from ..loop.atomic_primitives import LoopValue, LoopValueCreateRequest
from ..loop.loop_role import LoopRole
from .code_intelligence_assets import CodeAssetSpec
from .reusable_capability_flywheel import (
    CandidateRegistrationRequest,
    CandidateRegistrationResult,
    CapabilityAuthority,
    ReusableCapabilityError,
    _CREATE_RECOMMENDATIONS,
    _assessment_record,
    _put_immutable,
    _run_operation,
)
from .reusable_capability_records import (
    CapabilityGeneralizationRecord,
    HarvestDispatch,
    ReuseAssessment,
    ReuseHarvestPolicy,
    ReuseOpportunityObserved,
    content_digest,
)


@dataclass(frozen=True)
class GeneralizedCapabilityCandidate:
    """One proposed candidate plus explicit parameterization evidence."""

    spec: CodeAssetSpec
    parameter_names: tuple[str, ...]
    preserved_invariants: tuple[str, ...]
    removed_assumptions: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.spec, CodeAssetSpec):
            raise ReusableCapabilityError(
                "generalized candidate requires a CodeAssetSpec")
        for name in (
                "parameter_names", "preserved_invariants",
                "removed_assumptions", "evidence_refs"):
            values = tuple(getattr(self, name))
            if (len(values) != len(set(values))
                    or any(not isinstance(item, str) or not item.strip()
                           for item in values)):
                raise ReusableCapabilityError(
                    f"{name} must contain unique non-empty strings")
            object.__setattr__(self, name, values)
        if not self.preserved_invariants or not self.evidence_refs:
            raise ReusableCapabilityError(
                "generalized candidate needs invariants and evidence")


@dataclass(frozen=True)
class ReuseHarvestServices:
    """Injected semantic boundaries for assessment and generalization."""

    assessor: Callable[[ReuseOpportunityObserved], ReuseAssessment]
    generalizer: Callable[
        [ReuseOpportunityObserved, ReuseAssessment],
        GeneralizedCapabilityCandidate]
    assessment_mode: str = "non_deterministic"
    generalization_mode: str = "non_deterministic"

    def __post_init__(self) -> None:
        if not callable(self.assessor) or not callable(self.generalizer):
            raise ReusableCapabilityError(
                "reuse harvest services require callable semantic boundaries")
        for name in ("assessment_mode", "generalization_mode"):
            if getattr(self, name) not in (
                    "deterministic", "non_deterministic"):
                raise ReusableCapabilityError(
                    f"{name} must be deterministic or non_deterministic")


@dataclass(frozen=True)
class ReuseHarvestRequest:
    opportunity: ReuseOpportunityObserved
    policy: ReuseHarvestPolicy
    services: ReuseHarvestServices
    source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (not isinstance(self.opportunity, ReuseOpportunityObserved)
                or not isinstance(self.policy, ReuseHarvestPolicy)
                or not isinstance(self.services, ReuseHarvestServices)):
            raise ReusableCapabilityError(
                "reuse harvest request has an invalid contract")
        if self.opportunity.dispatch is not self.policy.dispatch:
            raise ReusableCapabilityError(
                "reuse opportunity and harvest policy dispatch differ")
        refs = tuple(self.source_refs)
        if (len(refs) != len(set(refs))
                or any(not isinstance(item, str) or not item.strip()
                       for item in refs)):
            raise ReusableCapabilityError(
                "reuse harvest source references must be unique")
        object.__setattr__(self, "source_refs", refs)


@dataclass(frozen=True)
class ReuseHarvestResult:
    outcome: str
    assessment: ReuseAssessment
    generalization: CapabilityGeneralizationRecord | None
    registration: CandidateRegistrationResult | None
    producer_loop_id: str
    assessment_loop_id: str
    model_calls: int


def _run_harvest_stage(
        objective: str, operation: Callable[[], object], mode: str, *,
        ledger=None, parent=None) -> dict:
    if mode == "deterministic":
        return _run_operation(
            objective, operation, LoopRole.PRACTITIONER,
            "practitioner.self_improvement", "spawned_by",
            ledger=ledger, parent=parent)
    from ..loop.encapsulate import as_model_loop
    result = as_model_loop(
        objective, operation, ledger=ledger, parent=parent)
    if not result.get("ok"):
        raise ReusableCapabilityError(
            f"{objective} failed inside Loop {result['loop_id']}")
    return {
        "value": result["value"], "loop_id": result["loop_id"],
        "model_calls": 1,
    }


def harvest_reuse_opportunity_as_loop(
        authority: CapabilityAuthority,
        request: ReuseHarvestRequest, *, ledger=None, parent=None
        ) -> ReuseHarvestResult:
    """Assess and parameterize one opportunity through reusable Loop stages.

    This is the single harvest implementation for reactive and inline calls.
    It may create a candidate, but it never qualifies or promotes one.
    """
    if (not isinstance(authority, CapabilityAuthority)
            or not isinstance(request, ReuseHarvestRequest)):
        raise ReusableCapabilityError(
            "reuse harvesting requires typed authority and request")
    if not request.policy.enabled:
        raise ReusableCapabilityError("reuse harvesting is disabled by policy")
    if request.opportunity.artifact_kind not in set(
            request.policy.allowed_artifact_kinds):
        raise ReusableCapabilityError(
            "reuse opportunity artifact kind is outside harvest policy")

    assessed = _run_harvest_stage(
        f"assess reuse opportunity {request.opportunity.event_id}",
        lambda: request.services.assessor(request.opportunity),
        request.services.assessment_mode, ledger=ledger, parent=parent)
    assessment = assessed["value"]
    if (not isinstance(assessment, ReuseAssessment)
            or assessment.opportunity_id != request.opportunity.event_id):
        raise ReusableCapabilityError(
            "reuse assessor returned a different or invalid assessment")

    if (assessment.recommendation not in _CREATE_RECOMMENDATIONS
            or assessment.blocking_reasons):
        recorded = _run_operation(
            f"record reuse assessment {assessment.assessment_id}",
            lambda: _put_immutable(
                authority.store, _assessment_record(assessment)),
            LoopRole.PRACTITIONER, "practitioner.self_improvement",
            "spawned_by", ledger=ledger, parent=parent)
        return ReuseHarvestResult(
            "evidence_only", assessment, None, None, "",
            assessed["loop_id"],
            assessed["model_calls"] + recorded["model_calls"])

    generalized = _run_harvest_stage(
        f"generalize reuse opportunity {request.opportunity.event_id}",
        lambda: request.services.generalizer(
            request.opportunity, assessment),
        request.services.generalization_mode, ledger=ledger, parent=parent)
    candidate = generalized["value"]
    if not isinstance(candidate, GeneralizedCapabilityCandidate):
        raise ReusableCapabilityError(
            "reuse generalizer returned an invalid candidate")
    identity = content_digest({
        "opportunity_id": request.opportunity.event_id,
        "candidate_digest": candidate.spec.body_ref.digest,
        "producer_loop_id": generalized["loop_id"],
    })[:24]
    generalization = CapabilityGeneralizationRecord(
        "generalization." + identity,
        request.opportunity.event_id,
        request.opportunity.artifact_ref,
        request.opportunity.artifact_digest,
        candidate.spec.body_ref.uri,
        candidate.spec.body_ref.digest,
        generalized["loop_id"],
        candidate.parameter_names,
        candidate.preserved_invariants,
        candidate.removed_assumptions,
        candidate.evidence_refs)
    refs = tuple(dict.fromkeys((
        request.opportunity.execution_record_ref,
        f"reuse_assessment.{assessment.assessment_id}",
        *request.source_refs,
        *candidate.evidence_refs,
    )))
    registration = authority.register_candidate_as_loop(
        CandidateRegistrationRequest(
            request.opportunity, assessment, candidate.spec,
            generalized["loop_id"], refs, generalization),
        ledger=ledger, parent=parent)
    return ReuseHarvestResult(
        registration.outcome, assessment, generalization, registration,
        generalized["loop_id"], assessed["loop_id"],
        assessed["model_calls"] + generalized["model_calls"]
        + registration.model_calls)


@dataclass(frozen=True)
class ReuseObservationRequest:
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
    observed_at: str
    accepted: bool
    verified: bool
    dispatch: HarvestDispatch = HarvestDispatch.ASYNC

    def __post_init__(self) -> None:
        if any(not isinstance(value, bool)
               for value in (self.accepted, self.verified)):
            raise ReusableCapabilityError(
                "reuse observation acceptance fields must be booleans")
        if not isinstance(self.dispatch, HarvestDispatch):
            raise ReusableCapabilityError(
                "reuse observation dispatch is invalid")


@dataclass(frozen=True)
class ReuseObservationPort:
    """Typed optional sink used by a completed Practitioner run."""

    handler: Callable[[ReuseObservationRequest], ReuseOpportunityObserved]
    dispatch: HarvestDispatch = HarvestDispatch.ASYNC

    def __post_init__(self) -> None:
        if not callable(self.handler) or not isinstance(
                self.dispatch, HarvestDispatch):
            raise ReusableCapabilityError(
                "reuse observation port requires handler and dispatch policy")

    def submit(
            self, request: ReuseObservationRequest
            ) -> ReuseOpportunityObserved:
        if request.dispatch is not self.dispatch:
            raise ReusableCapabilityError(
                "reuse observation request and port dispatch differ")
        observed = self.handler(request)
        if (not isinstance(observed, ReuseOpportunityObserved)
                or observed.source_run_id != request.source_run_id
                or observed.source_loop_id != request.source_loop_id
                or observed.artifact_digest != request.artifact_digest):
            raise ReusableCapabilityError(
                "reuse observation port returned a different opportunity")
        return observed


def observe_reuse_opportunity_as_loop(
        request: ReuseObservationRequest, *, ledger=None, parent=None
        ) -> ReuseOpportunityObserved:
    """Observe only accepted verified work and return a reference-only event."""
    if not isinstance(request, ReuseObservationRequest):
        raise ReusableCapabilityError(
            "reuse observation requires its typed request")

    def observe() -> ReuseOpportunityObserved:
        if not request.accepted or not request.verified:
            raise ReusableCapabilityError(
                "unaccepted or unverified work cannot enter reuse harvesting")
        key = content_digest({
            "source_run_id": request.source_run_id,
            "result_ref": request.accepted_result_ref,
            "artifact_digest": request.artifact_digest,
            "observer_policy": "reuse-observer/v1",
        })
        return ReuseOpportunityObserved(
            "reuse." + key[:24], request.correlation_id,
            request.source_run_id, request.source_loop_id,
            request.source_loop_profile_ref,
            request.source_loop_definition_ref,
            request.accepted_result_ref, request.execution_record_ref,
            request.artifact_ref, request.artifact_digest,
            request.artifact_kind, request.operation_family,
            request.dispatch, "dedup." + key[:24], request.observed_at)

    run = _run_operation(
        "observe accepted work for possible reuse", observe,
        LoopRole.PRACTITIONER, "practitioner.self_improvement",
        "spawned_by", ledger=ledger, parent=parent)
    return run["value"]


@dataclass(frozen=True)
class ReuseDispatchResult:
    opportunity: ReuseOpportunityObserved
    input_ref: object
    activation_id: str
    created: bool
    loop_id: str


def dispatch_reuse_opportunity_as_loop(
        opportunity: ReuseOpportunityObserved,
        scheduler,
        information_resolver,
        series_id: str,
        *, ledger=None, parent=None) -> ReuseDispatchResult:
    """Publish an exact event value and admit it through reactive scheduling."""
    from ..loop.reactive_activation import TriggerEnvelope
    from ..loop.reactive_contracts import TriggerKind
    from .information_access import (
        InformationDurability, InformationPublicationRequest,
        InformationScope, InlineInformationAdapter)

    def dispatch() -> ReuseDispatchResult:
        if opportunity.dispatch is not HarvestDispatch.ASYNC:
            raise ReusableCapabilityError(
                "reactive dispatch requires an async opportunity")
        if not getattr(information_resolver, "_adapters", {}).get(
                InlineInformationAdapter.adapter_id):
            information_resolver.register(InlineInformationAdapter())
        value = LoopValue.create(
            opportunity.to_dict(), LoopValueCreateRequest(
                "reuse_opportunity_observed/v1", "reuse_opportunity",
                opportunity.source_loop_id,
                opportunity.source_loop_definition_ref,
                (opportunity.execution_record_ref,)))
        information_resolver.publish(InformationPublicationRequest(
            value, InlineInformationAdapter.adapter_id,
            InformationDurability.RUN, InformationScope.RUN_SHARED,
            run_id=opportunity.source_run_id))
        trigger = TriggerEnvelope(
            "trigger." + opportunity.event_id,
            series_id, TriggerKind.PUSH_EVENT,
            "artifact." + opportunity.artifact_digest[:24], value.to_ref(),
            opportunity.source_loop_id, opportunity.observed_at,
            opportunity.observed_at, opportunity.idempotency_key, 1.0,
            correlation_id=opportunity.correlation_id,
            causation_id=opportunity.event_id)
        admitted = scheduler.admit(trigger)
        return ReuseDispatchResult(
            opportunity, value.to_ref(),
            admitted.activation.activation_id, admitted.created, "")

    run = _run_operation(
        f"dispatch reuse opportunity {opportunity.event_id}", dispatch,
        LoopRole.PRACTITIONER, "practitioner.self_improvement",
        "spawned_by", ledger=ledger, parent=parent)
    return replace(run["value"], loop_id=run["loop_id"])


__all__ = (
    "GeneralizedCapabilityCandidate", "ReuseDispatchResult",
    "ReuseHarvestRequest", "ReuseHarvestResult", "ReuseHarvestServices",
    "ReuseObservationPort", "ReuseObservationRequest",
    "dispatch_reuse_opportunity_as_loop",
    "harvest_reuse_opportunity_as_loop",
    "observe_reuse_opportunity_as_loop",
)
