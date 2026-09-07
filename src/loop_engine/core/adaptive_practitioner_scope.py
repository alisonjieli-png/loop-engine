"""Private per-Practitioner state within one canonical Loop Run History.

These helpers prepare passive service state and project existing events. They
do not create another runtime, event store, approval service, or task executor.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path


def begin_scope(services, owner) -> None:
    """Bind one model context to its exact owning Practitioner Loop."""
    if services.context_owner_loop_id:
        return
    services.context_owner_loop_id = owner.loop_id
    owner.ledger.record(
        loop_id=owner.loop_id, event="custom",
        custom_kind="adaptive_context_scope_started",
        record_type="adaptive_context_scope/v1",
        task_digest=hashlib.sha256(services.request.task.encode()).hexdigest(),
        spawning_context_loop_id=services.spawning_context_loop_id,
        spawning_history_visible=False)


def scoped_history(events, scope_loop_id: str) -> tuple[dict, ...]:
    """Select this scope's events, excluding other Practitioner contexts.

    Classified implementation Loops stay visible to their owning scope.
    Spawned Practitioner context bodies stay private in both directions;
    their explicitly returned summaries are supplied through task state.
    """
    if not scope_loop_id:
        return ()
    parents = {}
    scopes = set()
    for event in events:
        loop_id = event.get("loop_id", "")
        if event.get("custom_kind") == "adaptive_context_scope_started":
            scopes.add(loop_id)
        if event.get("event") in ("init", "spawn"):
            spawning_service = next((event.get(key) for key in (
                "spawned_by_loop_id", "queried_by_loop_id",
                "retrieved_by_loop_id", "spawning_loop_id") if event.get(key)), "")
            if spawning_service:
                parents[loop_id] = spawning_service

    def visible(loop_id):
        visited = set()
        while loop_id and loop_id not in visited:
            if loop_id == scope_loop_id:
                return True
            if loop_id in scopes:
                return False
            visited.add(loop_id)
            loop_id = parents.get(loop_id, "")
        return False

    return tuple(event for event in events if visible(event.get("loop_id", "")))


def delegated_task_text(spec, *, assignment=None, inputs=()) -> str:
    """Expose the complete admitted assignment to models and host verifiers."""
    value = {
        "record_type": "delegated_problem/v1",
        "objective": spec.objective,
        "constraints": list(spec.constraints),
        "success_criteria": list(spec.success_criteria),
    }
    if assignment is not None:
        value.update(task_id=assignment.task_id,
                     output_contract=assignment.output_contract.to_dict()
                     if assignment.output_contract else None,
                     dependency_inputs=[item.to_dict() for item in inputs])
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def fork_services(spawning_service, spec):
    """Isolate task, context, workspace, and acceptance; retain shared authority."""
    from .adaptive_practitioner_records import (
        AdaptiveRunServices, StageAssistanceRuntimeBinding)

    if spawning_service.request.stage_assistance.mode != "shadow":
        raise ValueError("Spawned work in a paired experiment requires exact per-Loop assignments")
    workspace = spawning_service.workspace_base / "spawned" / str(len(spawning_service.spawned_results) + 1)
    request = replace(
        spawning_service.request, task=delegated_task_text(spec), max_passes=spec.budget_passes,
        source_kind="text", source_refs=(), feedback=(),
        workspace_root=str(workspace), instruction_provenance=None,
        prior_region_evidence={}, stage_assistance=StageAssistanceRuntimeBinding())
    spawned_service = AdaptiveRunServices(
        request, spawning_service.dependencies, spawning_service.run_id, workspace,
        spawning_service.artifacts, deepcopy(spawning_service.portfolio),
        model_session=spawning_service.model_session,
        action_fence=spawning_service.action_fence,
        route_health=spawning_service.route_health,
        route_health_ledger=spawning_service.route_health_ledger,
        progress_sequence_source=spawning_service.progress_sequence_source,
        started_monotonic=spawning_service.started_monotonic,
        spawning_context_loop_id=spawning_service.context_owner_loop_id,
        workspace_scope_root=(spawning_service.workspace_scope_root
                              or spawning_service.workspace_base.resolve()))
    validate_scope_workspace(spawned_service)
    return spawned_service


def validate_scope_workspace(services, target: Path | None = None) -> None:
    """Refuse changed path resolution before a scoped workspace effect."""
    anchor = getattr(services, "workspace_scope_root", None)
    if anchor is None:
        return
    scope = Path(services.workspace_base)
    workspace = scope if target is None else Path(target)
    try:
        resolved = workspace.resolve()
        valid = (resolved == workspace and Path(anchor) in resolved.parents
                 and (workspace == scope or scope in workspace.parents))
    except (OSError, RuntimeError):
        valid = False
    if not valid:
        raise ValueError("spawned workspace no longer resolves inside its granted scope")


def spawned_summary(spawned, spawned_service, *, spec, calls_before: int) -> dict:
    """Return exact accepted material without inheriting spawning_service completion."""
    from .adaptive_practitioner_result import (
        has_bound_accepted_incumbent, latest_task_result, task_result_succeeded)

    result = latest_task_result(spawned_service)
    verified = bool(
        spawned.run.get("final_route") == "stop_success" and result
        and task_result_succeeded(result)
        and has_bound_accepted_incumbent(spawned.run, result))
    incumbent = spawned.run.get("facts", {}).get("accepted_incumbent", {})
    accepted = spawned.run.get("facts", {}).get("last_result") if verified else None
    verification_digest = incumbent.get("verification_record_digest") if verified else None
    verification_kind = "adaptive_verification" if verified else "unverified"
    trace = spawned_service.deterministic_attempt
    if (trace is not None and trace.status == "COMPLETED"
            and trace.literal_input == spawned_service.request.task
            and spawned.run.get("solved") is True
            and spawned.run.get("deterministic_attempt") == trace.to_dict()
            and spawned.run.get("result") == dict(trace.outputs).get("result")
            and spawned.terminal_code == "ACCEPTED"):
        verified = True
        accepted = {"objective": spec.objective,
                    "result": deepcopy(spawned.run["result"])}
        verification_digest = summary_digest(trace.to_dict())
        verification_kind = "registered_exact_resolver"
    session = spawned_service.model_session
    calls = None if getattr(session, "accounting_uncertain", False) else (
        session.calls_used - calls_before)
    return {
        "record_type": "spawned_practitioner_result/v1",
        "loop_id": spawned.loop_id,
        "definition_id": spawned.definition_id,
        "definition_version": spawned.definition_version,
        "definition_digest": spawned.definition_digest,
        "spawned_by_loop_id": spawned.relationship.spawned_by_loop_id,
        "objective": spec.objective,
        "terminal_code": spawned.terminal_code,
        "final_route": spawned.run.get("final_route"),
        "task_complete": verified,
        "completes_spawning_task": False,
        "accepted_result": deepcopy(accepted),
        "verification_record_digest": verification_digest,
        "verification_kind": verification_kind,
        "workspace": str(spawned_service.workspace_base),
        "model_calls": calls,
        "nested_results": deepcopy(spawned_service.spawned_results),
        "failure_count": len(spawned.run.get("failures", ())),
    }


def summary_digest(summary) -> str:
    return hashlib.sha256(json.dumps(
        summary, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def prepare_exact_result(services, owner):
    """Honor the existing hybrid exact-resolver path within the spawned Loop."""
    from ..loop.kernel_runtime import SpawnedKernelRun
    from .adaptive_practitioner_deterministic import run_deterministic_attempt
    from .adaptive_practitioner_result import finish_deterministic_attempt

    begin_scope(services, owner)
    if services.request.mode == "non_deterministic":
        return None
    services.deterministic_attempt = run_deterministic_attempt(
        services.request.task, services, owner)
    if services.deterministic_attempt.status != "COMPLETED":
        return None
    output = finish_deterministic_attempt(owner, services, lambda: {
        "run_id": services.run_id, "path": "", "separate_run": False,
        "authority": "shared_canonical_run_history"})
    return SpawnedKernelRun(
        owner.loop_id, owner.definition_ref.definition_id,
        owner.definition_ref.version, owner.definition_ref.content_digest,
        owner.relationship, owner.result().terminal_code, output)


def run_spawned_tasks(state, plan, services, implementations):
    """Execute admitted serial work through the existing canonical kernel."""
    from ..loop.kernel import ResultPacket
    from ..loop.kernel_runtime import current_kernel_owner, run_spawned_kernel
    from .run_history import default_runs_dir
    from .run_stages import close_stages
    from .adaptive_practitioner_bindings import (
        ASSIGNMENT_KEY, DependencyBindingError, SpawnedDependencyFrame,
        assignment_for, compile_assignments)

    owner = current_kernel_owner()
    if owner is None:
        raise ValueError("spawned work requires an active owning Loop")
    specs = tuple(replace(deepcopy(spec), constraints=tuple(dict.fromkeys(
        (*state.spec.constraints, *spec.constraints)))) for spec in plan.spawned_loops)
    order, plan_digest = compile_assignments(specs, state.spec.objective)
    frame = (SpawnedDependencyFrame(owner, services.run_id, plan_digest,
             {assignment_for(spec).task_id: assignment_for(spec) for spec in specs})
             if plan_digest else None)
    if frame is not None:
        owner.ledger.record(loop_id=owner.loop_id, event="custom",
            custom_kind="adaptive_dependency_plan_admitted", plan_digest=plan_digest,
            task_order=[assignment_for(specs[index]).task_id for index in order])
    results = []
    for index in order:
        assignment = assignment_for(specs[index])
        # Reserved metadata has been admitted and consumed by the controller.
        # It is not a free-form seed that can become trusted task facts.
        spec = replace(specs[index], seed_facts={
            key: value for key, value in specs[index].seed_facts.items()
            if key != ASSIGNMENT_KEY})
        spawned_service = None
        try:
            spawned_service = fork_services(services, spec)
            calls_before = services.model_session.calls_used

            def prepare(active):
                if frame is not None:
                    bound, delegation, _resolver = frame.resolve(
                        assignment, active, request=spawned_service.request, spec=spec)
                    spawned_service.request = replace(spawned_service.request,
                        task=delegated_task_text(spec, assignment=assignment, inputs=bound))
                    spawned_service.plan_details["dependency_inputs"] = [item.to_dict() for item in bound]
                    active.ledger.record(loop_id=active.loop_id, event="custom",
                        custom_kind="adaptive_dependency_inputs_bound", plan_digest=plan_digest,
                        task_id=assignment.task_id, input_roles=list(delegation.contract.input_roles),
                        value_refs=[item.reference.to_dict() for item in bound],
                        schema_digests=[item.schema_digest for item in bound],
                        deliveries=[item.delivery for item in bound],
                        value_bytes=[item.value_bytes for item in bound],
                        maximum_value_bytes=frame.policy.maximum_value_bytes)
                return prepare_exact_result(spawned_service, active)

            spawned = run_spawned_kernel(
                spec, implementations(spawned_service), selected_mode=services.request.mode,
                prepare=prepare)
            summary = spawned_summary(spawned, spawned_service, spec=spec, calls_before=calls_before)
            if frame is not None:
                summary.update(task_id=assignment.task_id, dependency_plan_digest=plan_digest)
                try:
                    frame.register(assignment, summary)
                except DependencyBindingError as exc:
                    summary.update(task_complete=False, accepted_result=None,
                                   binding_disposition=exc.disposition.value,
                                   verification_kind="output_contract_rejected")
                    frame.register(assignment, summary)
                    owner.ledger.record(loop_id=owner.loop_id, event="custom",
                        custom_kind="adaptive_dependency_output_rejected",
                        task_id=assignment.task_id, spawned_loop_id=spawned.loop_id,
                        disposition=exc.disposition.value)
            services.spawned_results.append(summary)
            owner.ledger.record(
                loop_id=owner.loop_id, event="custom",
                custom_kind="adaptive_spawned_result_returned",
                spawned_loop_id=spawned.loop_id,
                result_digest=summary_digest(summary),
                spawned_task_complete=summary["task_complete"],
                completes_spawning_task=False)
            results.append(ResultPacket(
                objective=spec.objective, result=deepcopy(summary),
                confidence=1.0 if summary["task_complete"] else 0.0,
                lineage=(spawned.loop_id,),
                errors=(() if summary["task_complete"]
                        else ("SPAWNED_TASK_UNVERIFIED",))))
        except (Exception, KeyboardInterrupt) as exc:
            services.spawned_results.append({
                "record_type": "spawned_practitioner_result/v1",
                "objective": spec.objective, "task_complete": False,
                "completes_spawning_task": False,
                "error_type": type(exc).__name__,
                **({"task_id": assignment.task_id, "dependency_plan_digest": plan_digest}
                   if assignment is not None else {}),
                **({"binding_disposition": exc.disposition.value} if isinstance(exc, DependencyBindingError) else {}),
                "workspace": str(spawned_service.workspace_base) if spawned_service else ""})
            if isinstance(exc, KeyboardInterrupt):
                raise
            results.append(ResultPacket(
                objective=spec.objective,
                errors=(f"{type(exc).__name__}: {str(exc)[:300]}",), confidence=0.0))
        finally:
            if spawned_service is not None:
                close_stages(spawned_service, default_runs_dir(services.request.runs_dir), helped=None)
    return results


def self_test():
    from .adaptive_practitioner_scope_checks import run_checks
    return run_checks()
