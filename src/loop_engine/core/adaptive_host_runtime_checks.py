"""Offline public/adaptive integration checks for explicitly bound host work.

The host endpoint and model transport below are deterministic test fixtures.
They exercise the existing Loop, capability, verification, and solve-result
boundaries without installing plugins, starting a model, or contacting a
network. Host observations remain distinct from generated project artifacts.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace


def _fixture(*, passed=True, complete=True, fail_operation=False, fail_verifier=False,
             complete_after=0, mutating=False, fail_on_calls=(), effect_hook=None,
             authorize_hook=None, approved=True, permission_names=()):
    from ..loop.effect_approval import ApprovalDecision, EffectClass, EffectSpec
    from .capability_directory import CapabilityDirectory, CapabilityHandshake, Endpoint
    from .host_runtime import HostOperationBinding, HostRuntimeBinding

    calls, approvals, snapshots = [], [], []
    state = {"revision": 1, "answer": 42}

    def snapshot():
        snapshots.append(state["revision"])
        return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()

    def operation(*, request):
        calls.append(("operation", request))
        if fail_operation or sum(kind == "operation" for kind, _ in calls) in fail_on_calls:
            raise ValueError("fixture operation unavailable")
        return {"answer": state["answer"]}

    def verifier(*, request):
        calls.append(("verifier", request))
        if fail_verifier:
            raise ValueError("fixture verifier unavailable")
        operation_count = sum(kind == "operation" for kind, _ in calls)
        return {"passed": passed,
                "task_complete": complete and operation_count >= complete_after,
                "observations": {"answer": state["answer"]},
                "notes": "Fixture checks the host-owned answer."}

    def effect(request):
        if effect_hook is not None:
            effect_hook(request)
        effect_class = EffectClass.LOCAL_WRITE if mutating else EffectClass.LOCAL_READ
        return EffectSpec(effect_class, "read_fixture_state", request.scope_ref)

    def authorize(request):
        approvals.append(request)
        if authorize_hook is not None:
            authorize_hook(request, state)
        if not approved:
            return ApprovalDecision.reject(request.request_id, "fixture_host_authority",
                                           reason="fixture refusal")
        return ApprovalDecision.approve(request.request_id, "fixture_host_authority")

    directory = CapabilityDirectory()
    for surface, name, callback in (("fixture_ops", "run", operation),
                                    ("fixture_checks", "validate", verifier)):
        directory.register(CapabilityHandshake(
            surface, "static_component", "Read the host-owned fixture answer.", (name,),
            effects=("pure",), max_response_bytes=8192), (Endpoint(name, callback),))
    action = HostOperationBinding("fixture_ops", "run", {"type": "object"},
                                  {"type": "object"}, effect, "fixture.operation/v1",
                                  permission_names=permission_names)
    check = HostOperationBinding("fixture_checks", "validate", {"type": "object"},
                                 {"type": "object"}, effect, "fixture.verifier/v1")
    binding = HostRuntimeBinding(directory, (action,), check, authorize, snapshot,
                                 "fixture:host-owned-answer", share_outputs_with_model=True)
    return SimpleNamespace(binding=binding, action=action, state=state,
                           calls=calls, approvals=approvals, snapshots=snapshots)


def _services(directory, fixture):
    from ..loop.loop_definition import LoopDefinition, LoopStartRequest
    from ..loop.loop_doctrine import baseline_for_practitioner
    from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
    from ..loop.recursive_loop import Loop, LoopConfig, LoopLedger
    from ..loop.runtime_context import LoopRuntimeContext
    from .action_fence import ActionFenceLedger
    from .context_artifacts import (
        ContextArtifactManager,
        ContextArtifactServices,
        ContextArtifactStore,
        ContextArtifactStoreSpec,
    )

    config = LoopConfig(
        framework="custom", custom_steps=("execute",), power="light",
        allowable_modes=("deterministic",), preferred_modes=("deterministic",),
        delegated_modes=("deterministic",), exit_condition="steps_complete")
    definition = LoopDefinition.from_runtime(
        identity=LoopRoleIdentity(LoopRole.PRACTITIONER, "practitioner.solver"),
        contract=baseline_for_practitioner("host integration fixture", output_roles=("result",)),
        config=config, installed_executor_modes=config.allowable_modes, compatibility=True)
    baseline = LoopRuntimeContext.compatibility(
        capabilities=definition.required_capabilities, permissions=definition.permissions,
        executor_modes=definition.installed_executor_modes)
    owner = Loop(LoopStartRequest("host integration fixture", definition,
        LoopRelationship.starting(), fixture.binding.runtime_context(baseline), LoopLedger()))
    services = SimpleNamespace(
        request=SimpleNamespace(task="Return the verified host answer."),
        dependencies=SimpleNamespace(host_runtime=fixture.binding),
        run_id="host-integration-fixture", host_results=[], host_verification_records=[],
        task_results=[], action_fence=ActionFenceLedger(), action_history=[],
        plan_details={}, active_pass_number=1, web_results=[],
        artifacts=ContextArtifactManager(ContextArtifactServices(
            ContextArtifactStore(ContextArtifactStoreSpec(str(Path(directory) / "artifacts"))))),
        diagnostic=lambda *_: None)
    return services, owner


def _report(kind, tests):
    return {"record_type": kind, "tests": tests,
            "passed": sum(item["passed"] for item in tests), "total": len(tests),
            "all_passed": all(item["passed"] for item in tests)}


def host_contract_checks() -> dict:
    """Exercise real host callbacks, exact issued records, and finality gates."""
    from ..loop.kernel import ResultPacket
    from .adaptive_host_verification import require_host_checks
    from .host_runtime import (
        HostOperationRequest,
        invoke_host_operation,
        validate_host_verification,
        verify_host_result,
    )

    tests = []

    def check(name, value):
        tests.append({"test": name, "passed": bool(value), "detail": "offline canonical host Loop fixture"})

    with tempfile.TemporaryDirectory(prefix="loop-host-contract-check-") as directory:
        fixture = _fixture()
        services, owner = _services(directory, fixture)
        result = invoke_host_operation(HostOperationRequest(fixture.action.capability_ref, {}),
                                       services, owner)
        report = verify_host_result(services.request.task, result, services, owner)
        validate_host_verification(report, services.request.task, result, services, owner)
        packet = ResultPacket("host result", result=result)
        record = {"evaluation": {"best_index": 0},
                  "host_checks": [{"result_index": 0, "report": report}]}
        require_host_checks(record, [packet], services, owner, task_complete=True)
        check("host_action_and_verifier_use_distinct_canonical_loops_and_exact_approvals",
              result["ok"] is True and report["status"] == "passed"
              and report["task_complete"] is True and len(fixture.approvals) == 2
              and report["verifier_loop_id"] != owner.loop_id
              and [kind for kind, _ in fixture.calls] == ["operation", "verifier"])
        refused = 0
        for bad in ({}, {"evaluation": {"best_index": 0}, "host_checks": []},
                    {**record, "host_checks": [{"result_index": 0, "report": {
                        **report, "report_digest": "0" * 64}}]},
                    {**record, "evaluation": {"best_index": 1}}):
            try:
                require_host_checks(bad, [packet], services, owner, task_complete=True)
            except ValueError:
                refused += 1
        check("missing_forged_or_unselected_host_verification_cannot_finish", refused == 4)
        fixture.state["revision"] += 1
        try:
            require_host_checks(record, [packet], services, owner, task_complete=True)
            stale_refused = False
        except ValueError:
            stale_refused = True
        check("host_state_drift_invalidates_prior_completion", stale_refused)

    from .adaptive_host_verification import bind_host_request
    from .adaptive_practitioner_records import (
        AdaptivePractitionerDependencies,
        AdaptivePractitionerRequest,
    )
    fixture = _fixture()
    dependencies = AdaptivePractitionerDependencies(host_runtime=fixture.binding)
    original = AdaptivePractitionerRequest("Return the verified host answer.")
    bound = bind_host_request(original, dependencies)
    check("adaptive_host_manifest_is_bound_before_any_model_or_host_operation",
          original.host_runtime_manifest == {}
          and bound.host_runtime_manifest == fixture.binding.summary()
          and not fixture.calls)
    tampered = deepcopy(fixture.binding.summary())
    tampered["binding_digest"] = "0" * 64
    try:
        bind_host_request(AdaptivePractitionerRequest(original.task, host_runtime_manifest=tampered),
                          dependencies)
        manifest_refused = False
    except ValueError:
        manifest_refused = True
    check("a_caller_cannot_rebind_the_host_manifest_to_a_different_identity", manifest_refused)

    for name, settings in (("incomplete", {"complete": False}),
                           ("failed", {"passed": False}),
                           ("unavailable", {"fail_verifier": True})):
        with tempfile.TemporaryDirectory(prefix="loop-host-gate-check-") as directory:
            fixture = _fixture(**settings)
            services, owner = _services(directory, fixture)
            result = invoke_host_operation(HostOperationRequest(fixture.action.capability_ref, {}),
                                           services, owner)
            report = verify_host_result(services.request.task, result, services, owner)
            record = {"evaluation": {"best_index": 0},
                      "host_checks": [{"result_index": 0, "report": report}]}
            try:
                require_host_checks(record, [ResultPacket("host", result=result)],
                                    services, owner, task_complete=True)
                refused = False
            except ValueError:
                refused = True
            check(name + "_host_gate_cannot_authorize_final_success", refused)
            if name == "incomplete":
                require_host_checks(record, [ResultPacket("host", result=result)], services, owner)
                check("verified_observation_may_continue_without_claiming_task_completion",
                      report["status"] == "passed" and report["task_complete"] is False)
    tests.extend(_unknown_effect_checks())
    tests.extend(_argument_boundary_checks())
    tests.extend(_output_share_checks())
    return _report("host_contract_test/v1", tests)


def _output_share_checks():
    from .host_runtime import HostRuntimeBinding

    fixture = _fixture()
    binding = fixture.binding
    tests = []
    for label, fields in (("missing", {}), ("false", {"share_outputs_with_model": False}),
                          ("none", {"share_outputs_with_model": None}),
                          ("zero", {"share_outputs_with_model": 0}),
                          ("one", {"share_outputs_with_model": 1}),
                          ("text", {"share_outputs_with_model": "true"}),
                          ("array", {"share_outputs_with_model": []})):
        try:
            HostRuntimeBinding(binding.directory, binding.operations, binding.verifier,
                               binding.authorize, binding.snapshot, binding.scope_ref, **fields)
            refused = False
        except ValueError:
            refused = True
        tests.append({"test": label + "_host_output_share_grant_refused_before_callbacks",
                      "passed": refused and not fixture.calls and not fixture.approvals
                      and not fixture.snapshots,
                      "detail": "current model-visible adapter requires explicit literal True; no tool-only claim"})
    return tests


def _argument_boundary_checks():
    from .host_runtime import HostOperationRequest, invoke_host_operation

    tests = []
    for label, settings in (
            ("effect_builder_argument_mutation", {"effect_hook": lambda request:
                request.arguments.update({"selection": "changed"})}),
            ("effect_builder_identity_mutation", {"effect_hook": lambda request:
                object.__setattr__(request, "state_ref", "0" * 64)}),
            ("state_drift_during_authorization", {"authorize_hook": lambda request, state:
                state.update({"revision": 2})}),
            ("host_authorization_refusal", {"approved": False})):
        with tempfile.TemporaryDirectory(prefix="loop-host-argument-check-") as directory:
            fixture = _fixture(**settings)
            services, owner = _services(directory, fixture)
            request = HostOperationRequest(fixture.action.capability_ref, {"selection": "original"})
            try:
                invoke_host_operation(request, services, owner)
                refused = False
            except (ValueError, PermissionError):
                refused = True
            tests.append({"test": label + "_refuses_before_host_callback",
                          "passed": refused and not fixture.calls
                          and request.arguments == {"selection": "original"},
                          "detail": "admitted caller arguments preserved, no physical endpoint invocation"})
    with tempfile.TemporaryDirectory(prefix="loop-host-detached-input-") as directory:
        fixture = _fixture()
        services, owner = _services(directory, fixture)
        arguments = {"nested": {"value": 1}}
        request = HostOperationRequest(fixture.action.capability_ref, arguments)
        arguments["nested"]["value"] = 99
        returned_manifest = fixture.binding.summary()
        returned_manifest["operations"][0]["input_schema"]["type"] = "array"
        result = invoke_host_operation(request, services, owner)
        tests.append({"test": "caller_argument_and_manifest_aliases_cannot_rewrite_bound_host_work",
                      "passed": result["ok"] and fixture.calls[0][1].arguments == {"nested": {"value": 1}}
                      and fixture.binding.summary()["operations"][0]["input_schema"]["type"] == "object",
                      "detail": "nested values are detached at public request and summary boundaries"})
    return tests


def _fence_checks():
    from ..loop.kernel import ExecutionPlan, PractitionerState
    from .adaptive_practitioner_capabilities import (
        AdaptiveCapabilityExecutionRequest,
        execute_adaptive_capability,
    )
    from .adaptive_practitioner_supervision import DEFAULT_SUPERVISION_POLICY

    with tempfile.TemporaryDirectory(prefix="loop-host-fence-check-") as directory:
        fixture = _fixture(fail_operation=True)
        services, owner = _services(directory, fixture)

        def execute(arguments):
            return execute_adaptive_capability(AdaptiveCapabilityExecutionRequest(
                PractitionerState(spec=None), ExecutionPlan("use", "run_dag",
                    handle=fixture.action.capability_ref, experiment={"arguments": arguments}), owner),
                services)

        arguments = {"query": "answer"}
        execute(arguments)  # The first attempt records the previously unknown state.
        for _ in range(DEFAULT_SUPERVISION_POLICY.action_fence.identical_failures_before_fence):
            execute(arguments)
        before_calls, before_snapshots = len(fixture.calls), len(fixture.snapshots)
        blocked = execute(arguments)
        same_state_fenced = (bool(blocked.errors) and len(fixture.calls) == before_calls
                             and len(fixture.snapshots) == before_snapshots
                             and services.action_history[-1].get("fenced") is True)
        previous_state = services.host_results[-1]["state_after"]
        fixture.state["revision"] += 1
        execute({"query": "refresh observation"})
        current_state = services.host_results[-1]["state_after"]
        refreshed_count = len(fixture.calls)
        retried = execute(arguments)
        changed_state_open = (current_state != previous_state
                              and len(fixture.calls) == refreshed_count + 1
                              and bool(retried.errors))
    return [{"test": "identical_failed_host_call_is_fenced_without_hidden_snapshot_reads",
             "passed": same_state_fenced, "detail": "fence uses the last recorded host state"},
            {"test": "a_new_recorded_host_state_reopens_the_previous_call_identity",
             "passed": changed_state_open,
             "detail": "a distinct observation precedes retry; failed execution stays failed"}]


def _unknown_effect_checks():
    from .host_runtime import HostOperationRequest, invoke_host_operation

    with tempfile.TemporaryDirectory(prefix="loop-host-unknown-check-") as directory:
        fixture = _fixture(mutating=True, fail_on_calls=(2,))
        services, owner = _services(directory, fixture)
        request = HostOperationRequest(fixture.action.capability_ref, {})
        first = invoke_host_operation(request, services, owner)
        second = invoke_host_operation(request, services, owner)
        try:
            invoke_host_operation(request, services, owner)
            refused = False
        except ValueError:
            refused = True
        distinct = first["invocation_id"] != second["invocation_id"]
        halted = refused and len(fixture.calls) == 2
    return [{"test": "identical_host_arguments_still_name_distinct_physical_attempts",
             "passed": distinct, "detail": "physical occurrence identity is not an idempotency key"},
            {"test": "prior_known_success_cannot_hide_later_unknown_host_effect",
             "passed": halted, "detail": "no third callback before explicit reconciliation"}]


def _projection_checks() -> list[dict]:
    from ..code_nodes.solve_runtime import _product_result
    from .adaptive_practitioner_result import latest_task_result, task_result_succeeded

    result = {
        "record_type": "host_operation_result/v1", "ok": True,
        "capability_ref": "host.fixture.run", "value": {"answer": 42},
        "artifact_refs": ["host-artifact:fixture"],
    }
    project = {"record_type": "generated_project_execution/v1",
               "deterministic_checks_passed": True,
               "workspace_path": "/fixture/project"}
    adaptive = {"host_results": [result], "project_attempts": [],
                "task_results": [result]}
    complete = _product_result(adaptive, True)
    incomplete = _product_result(adaptive, False)
    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": "host observation projection, not execution qualification"})

    check("host_result_projects_without_a_generated_project_disguise",
          complete["result"] == result and complete["workspace"] == ""
          and complete["tool_calls"] == 1
          and complete["artifacts"] == ({"artifact_ref": "host-artifact:fixture", "verified": True},)
          and "manifest" not in complete["result"]
          and "deterministic_checks_passed" not in complete["result"])
    check("incomplete_host_projection_does_not_verify_artifact_references",
          incomplete["result"] == result
          and incomplete["artifacts"][0]["verified"] is False)
    check("latest_task_result_preserves_actual_mixed_execution_order",
          latest_task_result({"task_results": [result, project],
                              "host_results": [result], "project_attempts": [project]}) is project
          and latest_task_result({"task_results": [project, result],
                                  "host_results": [result], "project_attempts": [project]}) is result)
    check("host_operational_success_requires_literal_true",
          task_result_succeeded(result)
          and all(not task_result_succeeded({**result, "ok": value})
                  for value in (False, None, 1, "true")))
    return tests


def _answers(fixture, permissions=None):
    from .adaptive_practitioner_acceptance_checks import (
        _decision,
        _decision_id,
        _orientation,
    )

    ref = fixture.action.capability_ref
    orientation = _orientation(
        task_summary="Use the existing host operation and verify its answer.",
        ultimate_goal="Return the verified host answer.", outputs=["verified host answer"],
        candidate_capabilities=[ref], verification_obligations=["Host answer is verified."],
        proposed_next_action="Invoke the registered host operation.")
    selected_permissions = fixture.action.permission_names if permissions is None else permissions
    decision = _decision("RUN_TOOL", required_capabilities=[ref], permissions=list(selected_permissions),
                         verification="Use the registered independent host verifier.")
    how = {"action_id": _decision_id(decision), "how_mode": "use", "act_mode": "run_dag",
           "capability_ref": ref, "arguments": {}, "steps": ["invoke host"],
           "spawned_tasks": [], "rationale": "Use the bound host operation."}
    verification = {"verdict": "accept", "best_index": 0, "scores": [1.0],
                    "notes": "Host gates are authoritative for this observation.",
                    "remaining_gaps": [], "advisory_findings": [], "new_requirement_proposals": []}
    return tuple(json.dumps(value) for value in (
        orientation, {"actions": [decision]}, how, verification,
        {"route": "stop_success", "reason": "The host confirms completion."}))


def _public_checks():
    from ..code_nodes.solution_model_port import (
        FixtureModelExecutionRequest,
        fixture_model_execution,
    )
    from ..code_nodes.solve_runtime import SolveRequest, solve_task
    from ..templates.intake import TaskIntakeRequest, intake_task

    tests = []
    for label, settings in (("success", {}), ("incomplete", {"complete": False}),
                            ("failed", {"passed": False}), ("unavailable", {"fail_verifier": True}),
                            ("failed_operation", {"fail_operation": True}), ("unbound", {})):
        with tempfile.TemporaryDirectory(prefix="loop-public-host-check-") as directory:
            fixture = _fixture(**settings)
            binding_before = fixture.binding.summary()
            outcome = solve_task(SolveRequest(
                intake_task(TaskIntakeRequest(text="Return the verified host answer.")),
                model_execution=fixture_model_execution(FixtureModelExecutionRequest(
                    answers=_answers(fixture), max_model_calls=5,
                    required_prompt_fragments=((fixture.action.capability_ref,
                        binding_before["binding_digest"]) if label == "success" else ()))),
                runs_dir=directory, host_runtime=fixture.binding if label != "unbound" else None,
                max_passes=1, quiet_model_io=True))
            tests.append({"test": "public_host_" + label + "_has_exact_completion_status",
                          "passed": outcome.solved is (label == "success"),
                          "detail": "public solve_task, canonical gateway fixture, no real model calls"})
            if label == "success":
                tests.extend([
                    {"test": "public_host_success_preserves_its_generic_result_contract",
                     "passed": outcome.result["record_type"] == "host_operation_result/v1"
                     and outcome.result["value"] == {"answer": 42}
                     and "manifest" not in outcome.result and not outcome.workspace,
                     "detail": "no generated source, project manifest, or artificial workspace"},
                    {"test": "public_host_manifest_propagates_without_model_or_callback_mutation",
                     "passed": outcome.verification["host_runtime_manifest"] == binding_before
                     and fixture.binding.summary() == binding_before,
                     "detail": "exact host binding recorded in the public verification projection"},
                    {"test": "public_host_path_uses_expected_semantic_and_physical_operations",
                     "passed": outcome.model_calls == 5
                     and [kind for kind, _ in fixture.calls] == ["operation", "verifier"]
                     and outcome.run_history["chain_intact"],
                     "detail": "five fixture model calls, one action, one verifier, intact Run History"},
                ])
    with tempfile.TemporaryDirectory(prefix="loop-public-host-multipass-") as directory:
        fixture = _fixture(complete_after=2)
        first = list(_answers(fixture))
        first[-1] = json.dumps({"route": "continue", "reason": "One observation is incomplete."})
        outcome = solve_task(SolveRequest(
            intake_task(TaskIntakeRequest(text="Return the verified host answer.")),
            model_execution=fixture_model_execution(FixtureModelExecutionRequest(
                answers=tuple(first) + _answers(fixture), max_model_calls=10)),
            runs_dir=directory, host_runtime=fixture.binding, max_passes=2, quiet_model_io=True))
        reports = outcome.verification.get("host_verification_records", [])
        tests.append({"test": "public_host_intermediate_observation_can_continue_to_complete_task",
                      "passed": outcome.solved and len(reports) == 2
                      and reports[0]["status"] == reports[1]["status"] == "passed"
                      and reports[0]["task_complete"] is False and reports[1]["task_complete"] is True
                      and outcome.model_calls == 10,
                      "detail": "two real adaptive passes; only the second host check authorizes completion"})
    return tests


def _permission_checks():
    from ..code_nodes.solution_model_port import (
        FixtureModelExecutionRequest,
        fixture_model_execution,
    )
    from ..code_nodes.solve_runtime import SolveRequest, solve_task
    from ..templates.intake import TaskIntakeRequest, intake_task
    from .adaptive_host_verification import validate_action_permissions
    from .adaptive_practitioner_acceptance_checks import _decision
    from .adaptive_practitioner_records import (
        AdaptivePractitionerDependencies,
        AdaptivePractitionerRequest,
        AdaptiveRunServices,
        NextActionDecision,
    )
    from .capability_directory import CapabilityHandshake, Endpoint
    from .host_runtime import HostOperationBinding, HostRuntimeBinding

    tests = []

    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": "declared host intent is not core effect authority"})

    def core_flags(request):
        return (request.allow_source_materialization_to_model, request.allow_workspace_writes,
                request.allow_sandbox_commands, request.allow_network_reads,
                request.allow_local_execution)

    with tempfile.TemporaryDirectory(prefix="loop-host-permission-check-") as directory:
        fixture = _fixture(permission_names=("source_read",))
        request = AdaptivePractitionerRequest(
            "Return the verified host answer.", allow_network_reads=False,
            allow_workspace_writes=False, allow_sandbox_commands=False,
            allow_source_materialization_to_model=False, allow_local_execution=False,
            source_kind="repository", source_refs=(directory,),
            host_runtime_manifest=fixture.binding.summary())
        services = AdaptiveRunServices(request, AdaptivePractitionerDependencies(
            host_runtime=fixture.binding), "permission-fixture", Path(directory), None, None)
        descriptors = services.available_capabilities()
        refs = {item["capability_ref"] for item in descriptors}
        check("host_permission_descriptor_does_not_enable_core_capabilities_or_flags",
              fixture.action.capability_ref in refs
              and {"core.source.inspect", "core.generated_project", "core.workspace.read"}.isdisjoint(refs)
              and fixture.binding.permissions_for(fixture.action.capability_ref) == ("source_read",)
              and next(item for item in descriptors if item["capability_ref"] == fixture.action.capability_ref)
              ["required_permissions"] == ["source_read"] and not any(core_flags(request)))

        def decision(selected, permissions):
            return NextActionDecision.from_mapping(_decision(
                "RUN_TOOL", required_capabilities=list(selected), permissions=list(permissions)))

        validate_action_permissions(decision((fixture.action.capability_ref,), ("source_read",)), services)
        check("declared_host_permission_is_admitted_without_exercising_it",
              not fixture.calls and not fixture.approvals and not any(core_flags(request)))
        validate_action_permissions(NextActionDecision.from_mapping(_decision(
            "REQUEST_AUTHORITY", permissions=["new_explicit_scope"], required_capabilities=[])), services)
        check("explicit_authority_request_remains_a_request_without_grant_or_effect",
              not fixture.calls and not fixture.approvals and not any(core_flags(request)))
        for label, selected, permissions in (
                ("undeclared_host", (fixture.action.capability_ref,), ("network_read",)),
                ("core_source", ("core.source.inspect",), ("source_read",)),
                ("core_project", ("core.generated_project",), ("workspace_write", "sandbox_command")),
                ("mixed_host_core", (fixture.action.capability_ref, "core.source.inspect"), ("source_read",)),
                ("empty_selection", (), ("source_read",))):
            try:
                validate_action_permissions(decision(selected, permissions), services)
                refused = False
            except PermissionError:
                refused = True
            check(label + "_selection_cannot_borrow_host_permission", refused)

        try:
            validate_action_permissions(decision((fixture.action.capability_ref,), ("undeclared_scope",)), services)
        except PermissionError as exc:
            detail = str(exc)
        else:
            detail = ""
        check("invalid_permission_feedback_names_exact_selected_scope_without_granting_it",
              'selected host capabilities: ["source_read"]' in detail
              and 'outside this scope: ["undeclared_scope"]' in detail
              and "exact effect approval" in detail and not fixture.calls and not fixture.approvals)

        directory_store = fixture.binding.directory
        directory_store.register(CapabilityHandshake(
            "fixture_extra", "static_component", "Additional host observation.", ("run",),
            effects=("pure",), max_response_bytes=8192),
            (Endpoint("run", lambda **_kwargs: {"extra": True}),))
        extra = HostOperationBinding("fixture_extra", "run", {"type": "object"},
            {"type": "object"}, fixture.action.effect_factory, "fixture.extra/v1",
            permission_names=("network_read",))
        combined = HostRuntimeBinding(directory_store, (fixture.action, extra), fixture.binding.verifier,
            fixture.binding.authorize, fixture.binding.snapshot, fixture.binding.scope_ref,
            share_outputs_with_model=True)
        selected_services = SimpleNamespace(request=request, dependencies=SimpleNamespace(host_runtime=combined))
        validate_action_permissions(decision((fixture.action.capability_ref, extra.capability_ref),
                                             ("source_read", "network_read")), selected_services)
        check("all_host_selection_uses_only_union_of_selected_declared_permissions",
              not any(core_flags(request)) and not fixture.calls)

    for label, approved, permissions in (("declared", True, ("source_read",)),
                                         ("undeclared", True, ("network_read",)),
                                         ("denied", False, ("source_read",))):
        with tempfile.TemporaryDirectory(prefix="loop-public-host-permission-") as directory:
            fixture = _fixture(permission_names=("source_read",), approved=approved)
            request = SolveRequest(
                intake_task(TaskIntakeRequest(text="Return the verified host answer.")),
                model_execution=fixture_model_execution(FixtureModelExecutionRequest(
                    answers=_answers(fixture, permissions=permissions), max_model_calls=5)),
                host_runtime=fixture.binding, runs_dir=directory, max_passes=1,
                quiet_model_io=True, allow_source_materialization_to_model=False,
                allow_workspace_writes=False, allow_sandbox_commands=False,
                allow_network_reads=False, allow_local_execution=False)
            before = core_flags(request)
            outcome = solve_task(request)
            check("public_host_" + label + "_permission_respects_exact_host_authorization",
                  outcome.solved is (label == "declared") and not any(core_flags(request))
                  and core_flags(request) == before
                  and (len(fixture.approvals) == 2 and len(fixture.calls) == 2 if label == "declared"
                       else not fixture.calls and (bool(fixture.approvals) if label == "denied"
                                                  else not fixture.approvals)))

    from unittest.mock import patch
    original_model = AdaptiveRunServices.model
    for approved in (True, False):
        with tempfile.TemporaryDirectory(prefix="loop-host-permission-repair-") as directory:
            fixture = _fixture(permission_names=("source_read",), approved=approved)
            valid = _answers(fixture)
            invalid = _answers(fixture, permissions=("undeclared_scope",))
            correction_contexts = []

            def capture_model(services, request):
                if (request.step_id == "decide_next"
                        and request.state.get("next_action_validation_failure")):
                    correction_contexts.append({
                        "failure": request.state["next_action_validation_failure"],
                        "calls_before_correction": len(fixture.calls),
                        "approvals_before_correction": len(fixture.approvals)})
                return original_model(services, request)

            request = SolveRequest(
                intake_task(TaskIntakeRequest(text="Return the verified host answer.")),
                model_execution=fixture_model_execution(FixtureModelExecutionRequest(
                    answers=(valid[0], invalid[1], *valid[1:]), max_model_calls=6)),
                host_runtime=fixture.binding, runs_dir=directory, max_passes=1,
                quiet_model_io=True, allow_source_materialization_to_model=False,
                allow_workspace_writes=False, allow_sandbox_commands=False,
                allow_network_reads=False, allow_local_execution=False)
            before = core_flags(request)
            with patch.object(AdaptiveRunServices, "model", capture_model):
                outcome = solve_task(request)
            check("public_permission_proposal_repair_precedes_effects_" + str(approved).lower(),
                  len(correction_contexts) == 1
                  and 'selected host capabilities: ["source_read"]' in correction_contexts[0]["failure"]
                  and 'outside this scope: ["undeclared_scope"]' in correction_contexts[0]["failure"]
                  and correction_contexts[0]["calls_before_correction"] == 0
                  and correction_contexts[0]["approvals_before_correction"] == 0
                  and core_flags(request) == before and not any(core_flags(request)))
            if approved:
                check("corrected_permission_proposal_executes_host_and_counts_correction_call",
                      outcome.solved and outcome.model_calls == 6
                      and outcome.model_calls_known_subtotal == 6
                      and outcome.model_call_accounting_complete is True
                      and [kind for kind, _ in fixture.calls] == ["operation", "verifier"]
                      and len(fixture.approvals) == 2 and outcome.run_history["chain_intact"])
            else:
                check("corrected_proposal_cannot_override_an_actual_host_approval_denial",
                      not outcome.solved and not fixture.calls and len(fixture.approvals) == 1)
    return tests


def run_checks() -> dict:
    return _report("adaptive_host_runtime_test/v1", [*_projection_checks(), *_public_checks(),
                                                    *_fence_checks(), *_permission_checks()])
