"""The step executor slot's envelope: one step, selected, recorded, bound and dispatched once per attempt.

Owns StepExecutionHost (what a host binds for the slot: the slot record, its
slot configuration, the installed engines, their qualifications, the grants
the owning Loop gives an engine's own mechanics and the run's services),
execute_step (the caller's one entry: build the selection request from the
step, select inside a deterministic Loop, dispatch, assess the attempt and
fall back only as the slot and the policy allow) and run_step_attempt (one
physical attempt in one Spawned Loop: the recorded decision is required, the
bound engine is revalidated, the engine is invoked exactly once, the result is
checked against the edge, and ``delegated`` is computed here and never read
from the engine). Belongs to the step execution component (roadmap S-6.31);
the registered boundary is "delegated step execution".
Does not own: an engine's work, selection rules (core.engines.selection), a
model call (the owning Loop's broker) or acceptance. Completion is never
acceptance, and no fallback ever replenishes consumed authority.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import time
from types import MappingProxyType

from ..configuration_capabilities import digest
from ..engines.decision_records import ConsumedAuthority, PolicySource, SelectionScope
from ..engines.fallback import EngineAttemptOutcome, assess_engine_attempt, fallback_request
from ..engines.host_records import EngineSlotConfiguration
from ..engines.records import EngineRecordError, identifier
from ..engines.selection import (
    EngineCandidate, EngineSelectionRequest, SelectionAuthority, require_prior_decision, revalidate_binding,
    select_engine_as_loop)
from ..engines.slots import EngineSlot
from ..external_harness_contract import STEP_EDGE, STEP_EXECUTOR_SLOT
from .engines import StepRequirementScreen, project_descriptor
from .records import (
    DELEGATING_ISOLATIONS, FAILED, REFUSED, UNAVAILABLE, ExecutorIdentity, StepRunRequest, StepRunResult,
    StepServices)

#: The grants an owning Loop gives an engine's own mechanics, never the step's work.
MECHANICS_EFFECTS = ("spawns_process",)
DELEGATION_GROUP = "delegation"
ATTEMPT_COMPONENT = "engine_attempt"


@dataclass(frozen=True)
class StepExecutionHost:
    """What one host binds for the step executor slot; it grants nothing a step did not."""

    slot: EngineSlot
    configuration: EngineSlotConfiguration
    engines: object
    qualifications: object
    services: StepServices
    mechanics_grants: tuple = MECHANICS_EFFECTS
    scope_key: str = "default"

    def __post_init__(self):
        if not isinstance(self.slot, EngineSlot) or self.slot.slot_id != STEP_EXECUTOR_SLOT:
            raise EngineRecordError("invalid_field", "a step host binds the step executor slot")
        if not isinstance(self.configuration, EngineSlotConfiguration) or not isinstance(self.services,
                                                                                         StepServices):
            raise EngineRecordError("invalid_field", "a step host carries its slot configuration and services")
        identifier(self.scope_key, "scope_key")
        object.__setattr__(self, "engines", MappingProxyType(dict(self.engines)))
        object.__setattr__(self, "qualifications", MappingProxyType(dict(self.qualifications or {})))
        object.__setattr__(self, "mechanics_grants", tuple(self.mechanics_grants))

    def candidates(self, as_of: datetime) -> tuple:
        """Every installed engine the host holds, projected now from its own declaration."""
        found = []
        for installation in self.configuration.installed:
            engine = self.engines.get(installation.installation_id)
            if engine is None:
                continue
            qualification = self.qualifications.get(installation.installation_id)
            descriptor = project_descriptor(engine, installation, as_of=as_of, qualification=qualification)
            found.append(EngineCandidate(installation, descriptor, qualification))
        return tuple(found)


@dataclass(frozen=True)
class StepExecution:
    """The one result the caller receives, with every decision and attempt behind it."""

    result: StepRunResult
    decisions: tuple
    attempts: tuple
    assessments: tuple


def step_scope(request: StepRunRequest) -> SelectionScope:
    """The exact step a decision is made for; the owning Loop is recorded, not fingerprinted."""
    output = digest({"contract": request.output_contract_ref,
                     "ports": [item.to_dict() for item in request.output_ports]})
    return SelectionScope(STEP_EDGE, request.owning_profile_ref, request.owning_loop_ref,
                          request.evaluation_contract_ref, {},
                          {"output_contract": output, "owning_definition": request.definition_digest})


def selection_request(request: StepRunRequest, host: StepExecutionHost, *, as_of: datetime,
                      policy_source: PolicySource) -> EngineSelectionRequest:
    """The shared selector's request for one step, built only from typed fields."""
    requirements, slot = request.requirements, host.slot
    delegating = slot.engine_kind_groups.get(DELEGATION_GROUP, ())
    kinds = requirements.allowed_engine_kinds or (delegating if requirements.delegation_required else ())
    isolations = requirements.allowed_isolations or (DELEGATING_ISOLATIONS if requirements.delegation_required
                                                     else ())
    authority = SelectionAuthority(
        granted_effects=tuple(dict.fromkeys(request.granted_effects + host.mechanics_grants)),
        allowed_isolations=isolations, required_preemptive_limits=requirements.required_limits,
        allowed_engine_kinds=tuple(kinds))
    return EngineSelectionRequest(
        slot=slot, configuration=host.configuration, scope_key=host.scope_key, scope=step_scope(request),
        candidates=host.candidates(as_of), authority=authority, edge_contract=STEP_EDGE, as_of=as_of,
        policy_source=policy_source, requirement_screen=StepRequirementScreen(request, as_of))


def delegated(slot: EngineSlot, candidate: EngineCandidate, result: StepRunResult) -> bool:
    """True only when a delegating kind ran as a separately confined, identified process
    whose model calls were all counted by the broker; the engine's own claim is never read."""
    identities = dict(result.native_identities)
    descriptor = candidate.descriptor
    return (descriptor.engine_kind in slot.engine_kind_groups.get(DELEGATION_GROUP, ())
            and descriptor.isolation in DELEGATING_ISOLATIONS
            and _is_digest(identities.get("process_identity")) and _is_digest(identities.get("sandbox_profile_digest"))
            and result.accounting.model_calls is not None)


def _is_digest(value) -> bool:
    return type(value) is str and len(value) == 64 and all(item in "0123456789abcdef" for item in value)


def _attempt_config(mode: str):
    from ...loop.recursive_loop import LoopConfig
    return LoopConfig(framework="custom", custom_steps=("dispatch",), allowable_modes=(mode,),
                      preferred_modes=(mode,), delegated_modes=tuple(dict.fromkeys(("deterministic", mode))),
                      exit_condition="steps_complete")


def run_step_attempt(engine, candidate: EngineCandidate, request: StepRunRequest, decision, *, parent,
                     services: StepServices, slot: EngineSlot) -> StepRunResult:
    """One physical attempt in one Spawned Loop of the owning Loop; never a retry inside."""
    from ...loop.loop_profile_catalog import LoopProfileRef
    from ...loop.loop_profile_ontology import get_profile
    from ...loop.loop_role import LoopRoleIdentity
    from ...loop.recursive_loop import StepOutcome
    require_prior_decision(parent.ledger, decision.content_digest)
    if revalidate_binding(decision, candidate):
        return _unavailable(request, FAILED, "engine_changed_after_selection", "engine_changed_after_selection")
    profile_id, _, version = request.owning_profile_ref.partition("@")
    profile = get_profile(LoopProfileRef(profile_id, version))
    attempt = parent.spawn(f"attempt step {request.step_name} on {decision.selected.engine_ref}",
                           _attempt_config(request.mode),
                           identity=LoopRoleIdentity(profile.family, profile.profile_id, profile.version))
    holder, started = {}, time.monotonic()

    def handler(active, step, context):
        # One Loop invocation owns one physical engine invocation: a retry here could repeat
        # effects while keeping only the last attempt's accounting.
        try:
            holder["result"] = engine.run_step(request, replace(services, attempt_loop=active))
        except Exception as exc:
            holder["result"] = _unavailable(request, FAILED, "engine_reported_failure",
                                            "engine_exception_" + type(exc).__name__.lower()[:40])
        result = holder["result"]
        return StepOutcome(output="dispatch:" + result.status, mode=request.mode,
                           confidence=1.0 if result.status == "completed" else 0.0,
                           failed=result.status != "completed",
                           model_calls=result.accounting.model_calls or 0)

    attempt.run(handler=handler, max_steps=1)
    result = holder.get("result") or _unavailable(request, FAILED, "engine_reported_failure", "no_engine_result")
    measured = round(time.monotonic() - started, 6)
    if not isinstance(result, StepRunResult) or result.request_digest != request.digest:
        result = _unavailable(request, FAILED, "output_validation_failed", "result_for_another_request")
    executor = ExecutorIdentity(decision.selected.engine_ref, decision.selected.descriptor_digest,
                                candidate.installation.installation_digest,
                                _text_digest(dict(result.native_identities).get("process_identity")),
                                _text_digest(dict(result.native_identities).get("sandbox_profile_digest")),
                                delegated(slot, candidate, result))
    result = replace(result, executor=executor, engine_reported_seconds=result.engine_reported_seconds,
                     measured_seconds=measured)
    parent.ledger.record(loop_id=parent.loop_id, event="state.committed", component=ATTEMPT_COMPONENT,
                         slot_id=slot.slot_id, attempt_loop_id=attempt.loop_id,
                         decision_digest=decision.content_digest, engine_ref=executor.engine_ref,
                         status=result.status, failure_kind=result.failure_kind, measured_seconds=measured,
                         model_calls=result.accounting.model_calls, delegated=executor.delegated,
                         request_digest=request.digest, result_digest=digest(result.to_dict()))
    return result


def _text_digest(value) -> str:
    return value if _is_digest(value) else ""


def _unavailable(request, status, kind, code) -> StepRunResult:
    from .records import StepAccounting
    return StepRunResult(request.request_id, request.digest, status, kind, code, (), (), (), "none",
                         StepAccounting(0, 0, 0, 0.0), (), {}, None, (), None, None)


def _outcome(decision, result: StepRunResult, consumed: ConsumedAuthority, attempt_ref: str) -> EngineAttemptOutcome:
    calls = result.accounting.model_calls
    total = ConsumedAuthority(
        None if calls is None or consumed.model_calls is None else consumed.model_calls + calls,
        None if result.accounting.input_tokens is None or consumed.input_tokens is None
        else consumed.input_tokens + result.accounting.input_tokens,
        None if result.accounting.output_tokens is None or consumed.output_tokens is None
        else consumed.output_tokens + result.accounting.output_tokens,
        None if consumed.elapsed_seconds is None else consumed.elapsed_seconds + (result.measured_seconds or 0.0),
        "unknown", None)
    return EngineAttemptOutcome(decision.selected.installation_id, decision.selected.engine_ref,
                                result.failure_kind, result.status not in (REFUSED, UNAVAILABLE), result.effects,
                                calls is None, total, attempt_ref)


def execute_step(request: StepRunRequest, host: StepExecutionHost, *, parent,
                 as_of: "datetime | None" = None) -> StepExecution:
    """Run one step on whichever engine the host's configuration selects; the caller never names one."""
    if not isinstance(request, StepRunRequest) or not isinstance(host, StepExecutionHost):
        raise EngineRecordError("invalid_field", "a step and its host are typed")
    moment = as_of or datetime.now(timezone.utc)
    source = PolicySource("declared", ({"source_kind": "deployment_configuration",
                                        "source_ref": f"host#engines.{STEP_EXECUTOR_SLOT}", "source_version": "1",
                                        "precedence_rank": 6, "requested_state": "PROVIDED",
                                        "disposition": "SELECTED",
                                        "reason": "the host declares the step executor slot"},))
    selection = selection_request(request, host, as_of=moment, policy_source=source)
    decisions, attempts, assessments = [], [], []
    while True:
        decision = select_engine_as_loop(selection, parent=parent)
        decisions.append(decision)
        if decision.selected is None:
            result = _unavailable(request, UNAVAILABLE, "engine_unavailable", decision.status)
            break
        installation_id = decision.selected.installation_id
        current = next((item for item in host.candidates(moment)
                        if item.installation.installation_id == installation_id), None)
        result = run_step_attempt(host.engines[installation_id], current, request, decision, parent=parent,
                                  services=host.services, slot=host.slot)
        attempts.append(result)
        outcome = _outcome(decision, result, selection.consumed, parent.loop_id)
        assessment = assess_engine_attempt(host.slot, selection.policy, decision, outcome)
        assessments.append(assessment)
        if assessment.action != "fallback":
            break
        selection = fallback_request(selection, outcome, expected_effect="the next declared engine runs the step",
                                     fixed_settings=("model_access",))
    return StepExecution(result, tuple(decisions), tuple(attempts), tuple(assessments))


def self_test():
    """Run the step execution checks, which cover the envelope."""
    from .engines_checks import self_test as run_engine_checks
    return run_engine_checks()
