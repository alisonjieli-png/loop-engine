"""Exact deterministic resolution before adaptive model escalation.

This operational boundary searches only registered resolvers, runs a compatible
resolver inside the canonical Practitioner Loop, verifies its output contract,
and preserves a complete typed trace for hybrid repair.
"""
from __future__ import annotations

import hashlib

from .adaptive_practitioner_records import (
    AdaptiveRunServices, DeterministicAttemptTrace)

def run_deterministic_attempt(
        task: str, services: AdaptiveRunServices,
        owner_loop) -> DeterministicAttemptTrace:
    from ..loop.encapsulate import as_practitioner_loop
    considered = []
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
                outputs=(("result", result),),
                errors=("OUTPUT_CONTRACT_VIOLATION",),
                diagnostics=(
                    "exact resolver returned without verified=true",),
                recommended_escalation="NEEDS_SEMANTIC_ORIENTATION")
        return DeterministicAttemptTrace(
            hashlib.sha256(task.encode()).hexdigest(), task,
            "COMPLETED",
            parsers_attempted=("literal_utf8",),
            exact_values=(("resolver_id", resolver_id),),
            capabilities_considered=tuple(
                item["resolver_id"] for item in considered),
            outputs=(("result", result),),
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
        diagnostics=("no exact contract-compatible resolver",),
        recommended_escalation="NEEDS_SEMANTIC_ORIENTATION")
