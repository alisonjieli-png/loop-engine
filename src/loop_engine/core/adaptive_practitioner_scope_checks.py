"""Offline regression evidence for private, recursively governed task scopes.

The public adaptive path uses fixture models and independent host checks.
The checks preserve scope isolation, accounting, and separate task acceptance.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch


def run_checks():
    from ..code_nodes.solution_model_port import (
        FixtureModelExecutionRequest, fixture_model_execution)
    from ..loop.kernel import PractitionerState, ProblemSpec
    from .adaptive_host_runtime_checks import _answers, _fixture
    from .adaptive_practitioner import _model_state, run_adaptive_practitioner
    from .adaptive_practitioner_acceptance_checks import (
        _decision, _decision_id, _orientation)
    from .adaptive_practitioner_records import (
        AdaptivePractitionerDependencies, AdaptivePractitionerRequest,
        AdaptiveRunServices)
    from .adaptive_practitioner_scope import (
        delegated_task_text, fork_services, scoped_history, validate_scope_workspace)
    from .context_artifacts import (
        ContextArtifactManager, ContextArtifactServices, ContextArtifactStore,
        ContextArtifactStoreSpec)
    from .practitioner_context import load_practitioner_context

    tests = []

    def check(name, passed, detail="offline fixture, zero real provider calls"):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    events = [
        {"event": "init", "loop_id": "spawning_service"},
        {"event": "custom", "loop_id": "spawning_service", "custom_kind": "adaptive_context_scope_started"},
        {"event": "init", "loop_id": "spawned_service", "spawned_by_loop_id": "spawning_service"},
        {"event": "custom", "loop_id": "spawned_service", "custom_kind": "adaptive_context_scope_started"},
        {"event": "init", "loop_id": "query", "queried_by_loop_id": "spawned_service"},
        {"event": "init", "loop_id": "item", "retrieved_by_loop_id": "query"},
        {"event": "custom", "loop_id": "item", "body": "private spawned_service material"},
        {"event": "init", "loop_id": "sibling", "spawned_by_loop_id": "spawning_service"},
        {"event": "custom", "loop_id": "sibling", "custom_kind": "adaptive_context_scope_started"},
        {"event": "custom", "loop_id": "spawning_service", "body": "explicit summary"},
    ]
    check("parent_history_excludes_private_spawned_and_sibling_scopes",
          {e["loop_id"] for e in scoped_history(events, "spawning_service")} == {"spawning_service"})
    check("spawned_history_keeps_owned_queries_and_retrievals_without_parent_context",
          {e["loop_id"] for e in scoped_history(events, "spawned_service")} == {"spawned_service", "query", "item"})
    check("unbound_scope_does_not_default_to_shared_history", not scoped_history(events, ""))

    with tempfile.TemporaryDirectory(prefix="loop-scope-fixture-") as directory:
        root = Path(directory)
        session = SimpleNamespace(calls_used=0, accounting_uncertain=False)
        spawning_service = AdaptiveRunServices(
            AdaptivePractitionerRequest(
                "spawning_service task", source_refs=("spawning_service-input.txt",),
                allow_network_reads=False, allow_source_materialization_to_model=False),
            AdaptivePractitionerDependencies(), "scope-test", root / "workspace",
            ContextArtifactManager(ContextArtifactServices(ContextArtifactStore(
                ContextArtifactStoreSpec(str(root / "artifacts"))))),
            load_practitioner_context(), model_session=session,
            context_owner_loop_id="spawning_service")
        spawning_service.project_attempts.append({"parent_private": True})
        spawning_service.plan_details["accepted_incumbent"] = {"parent_result": True}
        spawning_service.orientation_by_version[0] = "spawning_service orientation"
        spawning_service.context_snapshots.append({"parent_private": True})
        spec = ProblemSpec("spawned_service task", constraints=("retain constraint",),
                           success_criteria=("spawned_service-specific acceptance",))
        spawned_service = fork_services(spawning_service, spec)
        spawned_service.project_attempts.append({"spawned_private": True})
        spawned_service.plan_details["accepted_incumbent"] = {"spawned_result": True}
        check("spawned_request_binds_its_own_task_without_ambient_parent_sources",
              spawned_service.request.task == delegated_task_text(spec) and spawned_service.request.source_refs == ()
              and spawned_service.request.feedback == () and spawned_service.request.instruction_provenance is None)
        check("spawned_mutable_acceptance_context_and_artifacts_are_isolated",
              spawning_service.project_attempts == [{"parent_private": True}]
              and spawning_service.plan_details["accepted_incumbent"] == {"parent_result": True}
              and not spawned_service.context_snapshots and not spawned_service.orientation_by_version
              and not spawned_service.task_results and not spawned_service.independent_probe_cache)
        check("spawned_workspaces_are_confined_and_distinct_without_creating_files",
              spawning_service.workspace_base in spawned_service.workspace_base.parents
              and spawned_service.workspace_base != spawning_service.workspace_base
              and not spawned_service.workspace_base.exists())
        check("model_accounting_and_effect_fence_remain_shared_authorities",
              spawned_service.model_session is spawning_service.model_session
              and spawned_service.action_fence is spawning_service.action_fence
              and spawned_service.run_id == spawning_service.run_id)
        check("spawned_does_not_expand_permissions_or_invent_pass_ceiling",
              not spawned_service.request.allow_network_reads
              and not spawned_service.request.allow_source_materialization_to_model
              and spawned_service.request.max_passes is None)
        view = _model_state(PractitionerState(spec), spawned_service)
        check("active_problem_exposes_exact_spawned_constraints_and_acceptance",
              view["active_problem"] == {"objective": "spawned_service task",
                  "constraints": ["retain constraint"],
                  "success_criteria": ["spawned_service-specific acceptance"]})
        spawning_service.workspace_base.mkdir()
        outside = root / "outside"
        outside.mkdir()
        (spawning_service.workspace_base / "spawned").symlink_to(outside, target_is_directory=True)
        refused = 0
        for operation in (lambda: fork_services(spawning_service, spec),
                          lambda: validate_scope_workspace(spawned_service)):
            try:
                operation()
            except ValueError:
                refused += 1
        check("scope_allocation_and_dispatch_refuse_changed_symlink_ancestors",
              refused == 2 and not list(outside.iterdir()))

    for mode, disposition in (("non_deterministic", "incomplete"),
                              ("non_deterministic", "complete"),
                              ("non_deterministic", "cancel"),
                              ("hybrid", "complete"),
                              ("hybrid", "exact_reuse")):
        parent_finishes = disposition in ("complete", "exact_reuse")
        label = mode + "_" + disposition
        with tempfile.TemporaryDirectory(prefix="loop-recursive-host-fixture-") as directory:
            host = _fixture()
            decision = _decision(
                "SPAWN_LOOP", goal="Resolve a separately verified subproblem.",
                required_capabilities=[], permissions=[])
            spawned_task = "Return the verified spawned observation."
            completion = ("Registered exact resolver confirms the observation."
                          if disposition == "exact_reuse" else
                          "Host confirms the spawned observation.")
            plan = {"action_id": _decision_id(decision), "how_mode": "delegate",
                    "act_mode": "spawn_practitioners", "capability_ref": "",
                    "arguments": {}, "steps": ["resolve subproblem"],
                    "spawned_tasks": [{"objective": spawned_task,
                        "constraints": [], "success_criteria": [completion]}],
                    "rationale": "The selected responsibility needs its own verification."}
            host_answers = _answers(host)
            first = tuple(json.dumps(v) for v in (
                _orientation(candidate_capabilities=[host.action.capability_ref]),
                {"actions": [decision]}, plan))
            answers = first + (() if disposition == "exact_reuse" else host_answers) + (host_answers[-2], json.dumps({
                "route": "continue" if parent_finishes else "stop_success",
                "reason": "Inspect the spawned result before completing the spawning task."}))
            if parent_finishes:
                answers += host_answers
            execution = fixture_model_execution(FixtureModelExecutionRequest(
                answers=answers, max_model_calls=len(answers)))
            progress = []
            original_model = AdaptiveRunServices.model
            exact_calls = []
            expected_assignment = delegated_task_text(ProblemSpec(
                spawned_task, success_criteria=(completion,)))

            class ExactFixtureResolver:
                resolver_id = "fixture.exact_observation/v1"

                def supports(self, task):
                    return task == expected_assignment

                def execute(self, task):
                    exact_calls.append(task)
                    return {"verified": True, "value": sum((19, 23))}

            def observed_model(services, request):
                if disposition == "cancel" and services.spawned_results:
                    raise KeyboardInterrupt()
                return original_model(services, request)

            with patch.object(AdaptiveRunServices, "model", observed_model):
                output = run_adaptive_practitioner(
                    AdaptivePractitionerRequest(
                        "Complete the spawning task after evaluating a spawned observation.",
                        mode=mode, runs_dir=directory,
                        max_passes=2 if parent_finishes else 1, quiet_model_io=True),
                    AdaptivePractitionerDependencies(
                        execution, host_runtime=host.binding, progress=progress.append,
                        deterministic_resolvers=((ExactFixtureResolver(),)
                            if disposition == "exact_reuse" else ())))
            summaries = output.get("spawned_results", [])
            check("recursive_spawn_completes_through_canonical_host_and_verifier_" + label,
                  len(summaries) == 1 and summaries[0].get("task_complete") is True
                  and summaries[0]["objective"] == spawned_task,
                  json.dumps({"solved": output.get("solved"), "spawned_tasks": summaries,
                              "failures": output.get("failures")}, default=str)[:2000])
            check("spawned_success_never_substitutes_for_spawning_task_acceptance_" + label,
                  output.get("solved") is parent_finishes
                  and len(output.get("task_results", ())) == int(parent_finishes))
            check("recursive_model_calls_share_one_physical_accounting_total_" + label,
                  output.get("model_calls") == (8 if disposition == "cancel" else len(answers)))
            verifier_tasks = [invocation.arguments.get("task")
                              for kind, invocation in host.calls if kind == "verifier"]
            if disposition == "exact_reuse":
                check("hybrid_spawn_preserves_verified_exact_result_with_zero_model_calls",
                      exact_calls == [expected_assignment] and summaries[0]["model_calls"] == 0
                      and summaries[0]["verification_kind"] == "registered_exact_resolver"
                      and summaries[0]["accepted_result"]["result"] == {"verified": True, "value": 42})
            else:
                check("spawned_verifier_receives_exact_task_" + label, expected_assignment in verifier_tasks,
                      repr(verifier_tasks))
            sequence = [event["progress_sequence"] for event in progress]
            check("recursive_progress_has_one_unique_ordered_sequence_" + label,
                  sequence == list(range(1, len(sequence) + 1))
                  and all(event.get("context_loop_id") for event in progress))
            if disposition == "cancel":
                check("cancellation_preserves_completed_spawned_work",
                      output.get("failure_code") == "CANCELLED" and len(summaries) == 1)
    return {"record_type": "adaptive_scope_checks/v1", "tests": tests,
            "passed": sum(t["passed"] for t in tests), "total": len(tests),
            "all_passed": all(t["passed"] for t in tests)}
