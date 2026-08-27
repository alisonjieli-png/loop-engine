"""Public facade for the bounded Model-Routing Intelligence slice.

Records and deterministic selection live in focused modules below the 800-line
conformance cap. ModelGateway remains the only model invocation boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .model_routing_records import (
    ACTIVE_LIFECYCLES,
    CAPABILITY_STATES,
    DECISION_STATES,
    MODEL_ROUTING_PORTFOLIO,
    MODEL_ROUTING_PORTFOLIO_ID,
    MODEL_ROUTING_SCHEMA_VERSION,
    RISK_LEVELS,
    ROLES,
    RUN_MODES,
    THINKING_POWER,
    ModelCapabilityRecord,
    ModelOutcomeEvidence,
    ModelRouteAvailabilitySnapshot,
    ModelRoutingError,
    ModelRoutingLearningCandidate,
    ModelRoutingPortfolioDefinition,
    ModelSelectionRequest,
    ModelSuitabilityRecord,
)
from .model_routing_selector import (
    HardConstraintResult,
    ModelRouteBootstrapSelector,
    ModelRouteCatalog,
    ModelRoutingEvidence,
    ModelSelectionDecision,
    ModelSelectorConfig,
    RejectedRoute,
    RouteCandidateAssessment,
)


@dataclass(frozen=True)
class ModelSelectionLoopContext:
    """Passive run context for one governed route-selection operation."""

    as_of: str | None = None
    parent: object | None = field(default=None, repr=False, compare=False)
    ledger: object | None = field(default=None, repr=False, compare=False)


def select_model_as_loop(
    selector: ModelRouteBootstrapSelector,
    request: ModelSelectionRequest,
    context: ModelSelectionLoopContext | None = None,
) -> dict:
    """Execute deterministic model selection as one governed Loop."""
    from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
    from ..loop.recursive_loop import Loop, LoopConfig, LoopLedger, StepOutcome

    selected_context = context or ModelSelectionLoopContext()
    parent = selected_context.parent
    selected_ledger = (parent.ledger if parent is not None
                       else selected_context.ledger or LoopLedger())
    config = LoopConfig(
        framework="custom", custom_steps=("select",), power="light",
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",),
        exit_condition="accepted_success")
    identity = LoopRoleIdentity(
        LoopRole.PRACTITIONER, "practitioner.code_execution")
    relationship = (LoopRelationship.spawned_by(parent.loop_id)
                    if parent is not None else LoopRelationship.starting())
    loop = (parent.spawn("select one model route", config, identity=identity,
                         relationship=relationship)
            if parent is not None else Loop(
                "select one model route", config, ledger=selected_ledger,
                identity=identity, relationship=relationship))
    selected_ledger.record(
        loop_id=loop.loop_id, event="model.selection.requested",
        request_id=request.request_id,
        portfolio_id=MODEL_ROUTING_PORTFOLIO_ID)
    holder = {}

    def handler(active, step, run_context):
        holder["decision"] = selector.select(
            request, as_of=selected_context.as_of or "")
        return StepOutcome(output="selection:complete", mode="deterministic",
                           confidence=1.0)

    loop.run(handler=handler, max_steps=2)
    decision = holder["decision"]
    for rejected in decision.rejected_routes:
        selected_ledger.record(
            loop_id=loop.loop_id, event="model.route.rejected",
            route_id=rejected.route_id, provider_id=rejected.provider_id,
            reasons=list(rejected.reasons))
    if decision.no_model_required:
        selected_ledger.record(
            loop_id=loop.loop_id, event="model.no_model_required",
            decision_id=decision.decision_id)
    elif decision.selected_route:
        selected_ledger.record(
            loop_id=loop.loop_id, event="model.route.selected",
            decision_id=decision.decision_id,
            route_id=decision.selected_route,
            provider_id=decision.selected_provider,
            model=decision.selected_model)
    selected_ledger.record(
        loop_id=loop.loop_id, event="model.selection.completed",
        decision_id=decision.decision_id, status=decision.status,
        decision_digest=decision.decision_digest,
        provider_calls_made=decision.provider_calls_made)
    return {"loop_id": loop.loop_id, "decision": decision,
            "decision_record": decision.to_dict()}


def self_test() -> dict:
    """Run the offline contract suite without contacting a provider."""
    from .model_routing_intelligence_checks import run_contract_checks
    return run_contract_checks()


__all__ = (
    "ACTIVE_LIFECYCLES",
    "CAPABILITY_STATES",
    "DECISION_STATES",
    "MODEL_ROUTING_PORTFOLIO",
    "MODEL_ROUTING_PORTFOLIO_ID",
    "MODEL_ROUTING_SCHEMA_VERSION",
    "RISK_LEVELS",
    "ROLES",
    "RUN_MODES",
    "THINKING_POWER",
    "HardConstraintResult",
    "ModelCapabilityRecord",
    "ModelOutcomeEvidence",
    "ModelRouteAvailabilitySnapshot",
    "ModelRouteBootstrapSelector",
    "ModelRouteCatalog",
    "ModelRoutingError",
    "ModelRoutingEvidence",
    "ModelRoutingLearningCandidate",
    "ModelRoutingPortfolioDefinition",
    "ModelSelectionDecision",
    "ModelSelectionLoopContext",
    "ModelSelectionRequest",
    "ModelSelectorConfig",
    "ModelSuitabilityRecord",
    "RejectedRoute",
    "RouteCandidateAssessment",
    "select_model_as_loop",
    "self_test",
)
