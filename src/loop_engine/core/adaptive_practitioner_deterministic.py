"""Exact deterministic resolution before adaptive model escalation.

This operational boundary searches only registered resolvers, runs a compatible
resolver inside the canonical Practitioner Loop, verifies its output contract,
and preserves a complete typed trace for hybrid repair.
"""
from __future__ import annotations

import hashlib

from .adaptive_practitioner_records import ATTEMPT_COMPLETED
from .adaptive_practitioner_records import (
    AdaptiveRunServices, DeterministicAttemptTrace)

#: The implementation the run falls to when no exact resolver completes: a
#: service model behind the gateway, chosen by the route the run declares.
SERVICE_MODEL_IMPLEMENTATION = "service_model:gateway"


def implementation_decision_output(considered: list, chosen_id: str, *,
                                   run_id: str) -> tuple[str, dict]:
    """The model-versus-not decision this attempt made, as an output pair.

    Every considered resolver is a deterministic candidate, available only
    when it supported the task; the service model is always a candidate.
    The chosen implementation is the resolver that completed, or the model.
    """
    from .implementation_choice import CANDIDATE_KINDS, ImplementationCandidate, ImplementationDecision
    candidates = [ImplementationCandidate(str(item["resolver_id"]), CANDIDATE_KINDS[0],
                                          available=bool(item.get("supported")))
                  for item in considered]
    candidates.append(ImplementationCandidate(SERVICE_MODEL_IMPLEMENTATION, CANDIDATE_KINDS[2], True))
    supported = [item["resolver_id"] for item in considered if item.get("supported")]
    if chosen_id == SERVICE_MODEL_IMPLEMENTATION:
        reason = (f"no exact resolver completed a verified result ({len(supported)} supported the task); "
                  "the service model is the next implementation")
    else:
        reason = f"exact resolver {chosen_id} completed a verified result before any model call"
    decision = ImplementationDecision(f"task.{run_id}", tuple(candidates), chosen_id, reason,
                                      evidence_refs=(f"deterministic_attempt:{run_id}",))
    return ("implementation_decision", decision.to_dict())


def run_deterministic_attempt(
        task: str, services: AdaptiveRunServices,
        owner_loop) -> DeterministicAttemptTrace:
    from ..loop.encapsulate import as_practitioner_loop
    considered = []
    run_id = str(getattr(services, "run_id", "") or "run")
    for resolver in services.dependencies.deterministic_resolvers:
        resolver_id = str(getattr(resolver, "resolver_id", "unnamed"))
        try:
            def run_exact():
                supported_value = bool(resolver.supports(task))
                return {
                    "supported": supported_value,
                    "result": (resolver.execute(task)
                               if supported_value else None),
                }
            attempt = as_practitioner_loop(
                f"try exact deterministic resolver {resolver_id}",
                run_exact, parent=owner_loop)
            supported = bool(attempt["value"]["supported"])
        except Exception as exc:
            cause = exc.__cause__ or exc
            considered.append({
                "resolver_id": resolver_id, "supported": False,
                "failure": type(cause).__name__})
            return DeterministicAttemptTrace(
                hashlib.sha256(task.encode()).hexdigest(), task,
                "DETERMINISTIC_EXECUTION_FAILED",
                parsers_attempted=("literal_utf8",),
                templates_considered=(),
                exact_values=(("resolver_id", resolver_id),),
                capabilities_considered=tuple(
                    item["resolver_id"] for item in considered),
                rejected_matches=tuple(
                    item["resolver_id"] for item in considered
                    if not item.get("supported")),
                unresolved_requirements=("verified_result",),
                errors=(type(cause).__name__,),
                diagnostics=("exact resolver raised inside its Loop",),
                recommended_escalation="NEEDS_SEMANTIC_ORIENTATION")
        considered.append({
            "resolver_id": resolver_id, "supported": supported,
            "loop_id": attempt["loop_id"]})
        if not supported:
            continue
        result = attempt["value"]["result"]
        if not isinstance(result, dict) or result.get("verified") is not True:
            return DeterministicAttemptTrace(
                hashlib.sha256(task.encode()).hexdigest(), task,
                "DETERMINISTIC_VERIFICATION_FAILED",
                parsers_attempted=("literal_utf8",),
                exact_values=(("resolver_id", resolver_id),),
                capabilities_considered=tuple(
                    item["resolver_id"] for item in considered),
                unresolved_requirements=("verified_result",),
                outputs=(("result", result),
                         implementation_decision_output(
                             considered, SERVICE_MODEL_IMPLEMENTATION, run_id=run_id)),
                errors=("OUTPUT_CONTRACT_VIOLATION",),
                diagnostics=(
                    "exact resolver returned without verified=true",),
                recommended_escalation="NEEDS_SEMANTIC_ORIENTATION")
        return DeterministicAttemptTrace(
            hashlib.sha256(task.encode()).hexdigest(), task,
            ATTEMPT_COMPLETED,
            parsers_attempted=("literal_utf8",),
            exact_values=(("resolver_id", resolver_id),),
            capabilities_considered=tuple(
                item["resolver_id"] for item in considered),
            outputs=(("result", result),
                     implementation_decision_output(considered, resolver_id, run_id=run_id)),
            decisions=(f"selected exact resolver {resolver_id}",
                       f"executed in {attempt['loop_id']}"))
    return DeterministicAttemptTrace(
        hashlib.sha256(task.encode()).hexdigest(), task,
        "NO_VERIFIED_CAPABILITY",
        parsers_attempted=("literal_utf8",),
        templates_considered=(),
        exact_values=(("original_task_preserved", True),),
        capabilities_considered=tuple(
            item["resolver_id"] for item in considered),
        rejected_matches=tuple(
            item["resolver_id"] for item in considered),
        unresolved_requirements=("semantic_orientation", "verified_result"),
        outputs=(implementation_decision_output(
            considered, SERVICE_MODEL_IMPLEMENTATION, run_id=run_id),),
        diagnostics=("no exact contract-compatible resolver",),
        recommended_escalation="NEEDS_SEMANTIC_ORIENTATION")
