"""Compile one adaptive Practitioner capability action into a Solution graph.

The model selects a registered capability through ``NextActionDecision`` and
``ExecutionPlan``. This module creates a candidate Solution Canvas, validates
its authoritative ``LoopGraphDefinition``, executes it through Solution Loops,
and returns a typed result. It contains no task or domain routing.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from ..code_nodes.solution_canvas import SolutionLoopSpec, SolutionSpec
from ..code_nodes.solution_compiler import (
    compile_solution, render_canvas, run_compiled)
from ..code_nodes.solution_model_port import SolutionModelError
from ..loop.kernel import ExecutionPlan, PractitionerState, ResultPacket
from ..loop.encapsulate import as_practitioner_loop
from .adaptive_practitioner_records import (
    AdaptivePractitionerError, AdaptiveRunServices, NextActionDecision)
from .generated_project import (
    sandbox_image,
    GeneratedProjectAuthority, GeneratedProjectError, GeneratedProjectExecutionContext, GeneratedProjectExecutionRequest,
    validate_generated_project_input_use)
from .web_fetch import WebFetchAuthority, WebFetchContext, WebFetchRequest
from .web_search import (
    WebSearchAuthority, WebSearchContext, WebSearchRequest)
from .adaptive_practitioner_orientation_capabilities import (
    environment_describe_operation, intelligence_search_operation)
from .workspace_read import workspace_read_operation
from .adaptive_practitioner_source import (
    source_inspection_operation, source_profile_operation)
from .adaptive_practitioner_project import (
    project_inputs, project_manifest)
from .adaptive_practitioner_supervision import DEFAULT_SUPERVISION_POLICY
from .source_role_orientation import orient_source_roles
from .action_fence import ActionFenceLedger
from .capability_rejection import (CapabilityRejection,
                                   rejection_from_exception)


@dataclass(frozen=True)
class AdaptiveCapabilityExecutionRequest:
    """Current state, selected plan, and owning Practitioner Loop."""

    state: PractitionerState
    plan: ExecutionPlan
    owner_loop: object

    def __post_init__(self) -> None:
        if not isinstance(self.state, PractitionerState):
            raise AdaptivePractitionerError(
                "capability execution needs PractitionerState")
        if not isinstance(self.plan, ExecutionPlan):
            raise AdaptivePractitionerError(
                "capability execution needs ExecutionPlan")
        if (self.owner_loop is None
                or not getattr(self.owner_loop, "loop_id", "")
                or getattr(self.owner_loop, "ledger", None) is None):
            raise AdaptivePractitionerError(
                "capability execution needs an active owner Loop")


def build_action_canvas_candidate(
        decision_id: str, decision: NextActionDecision) -> dict:
    """Project one capability-bearing action into a passive candidate graph."""
    if not isinstance(decision, NextActionDecision):
        raise AdaptivePractitionerError(
            "candidate canvas needs NextActionDecision")
    if not decision.required_capabilities:
        return {
            "record_type": "solution_canvas_candidate/v1",
            "candidate_id": f"canvas:{decision_id}",
            "action_kind": decision.action_kind,
            "selected": False,
            "graph": None,
            "validation": {"valid": True, "violations": []},
            "note": "control action requires no executable capability graph",
        }
    capability_ref = decision.required_capabilities[0]
    spec = SolutionSpec(
        f"adaptive.candidate.{decision_id.replace(':', '_')}",
        permitted_loop_modes=("deterministic",),
        loops=(SolutionLoopSpec(
            "candidate_action", capability_ref,
            input_role="next_action_decision/v1",
            output_role="capability_result/v1",
            params={"action_kind": decision.action_kind,
                    "verification": decision.verification}),))
    return {
        "record_type": "solution_canvas_candidate/v1",
        "candidate_id": f"canvas:{decision_id}",
        "action_kind": decision.action_kind,
        "selected": False,
        "graph": spec.graph.to_dict(),
        "validation": spec.validate(),
    }


def _web_operation(arguments, services, owner):
    maximum_bytes = arguments.get("maximum_bytes")
    return services.dependencies.web_fetcher(
        WebFetchRequest(
            str(arguments.get("url") or ""),
            str(arguments.get("purpose") or ""),
            maximum_bytes=(None if maximum_bytes is None
                           else int(maximum_bytes))),
        WebFetchAuthority(
            services.run_id, services.request.allow_network_reads),
        WebFetchContext(owner, services.artifacts))


def _search_operation(arguments, services, owner):
    maximum_results = arguments.get("maximum_results")
    return services.dependencies.web_searcher(
        WebSearchRequest(
            str(arguments.get("query") or ""),
            str(arguments.get("purpose") or ""),
            maximum_results=(None if maximum_results is None
                             else int(maximum_results))),
        WebSearchAuthority(
            services.run_id, services.request.allow_network_reads),
        WebSearchContext(owner))


def _execute_project_attempt(manifest, input_artifacts, input_validation,
                             services, owner):
    """Keep every started attempt, including partial failures and cancellation.

    Allocate before the executor can create a workspace. This is run-local
    serial allocation, not a concurrent or cross-process workspace allocator.
    """
    attempt = len(services.project_attempts) + 1
    workspace = services.workspace_base / f"attempt-{attempt}"
    execution_request = GeneratedProjectExecutionRequest(
        manifest, str(workspace), GeneratedProjectAuthority(
            services.run_id,
            services.request.allow_workspace_writes,
            services.request.allow_sandbox_commands,
            services.request.allow_network_reads,
            allow_local_execution=services.request.allow_local_execution),
        sandbox_image(), input_artifacts=input_artifacts)
    context = GeneratedProjectExecutionContext(owner)
    record = {
        "record_type": "generated_project_execution/v1",
        "attempt_number": attempt, "execution_status": "STARTED",
        "manifest_digest": manifest.digest, "manifest": manifest.to_dict(),
        "workspace_path": str(workspace),
        "input_use_validation": input_validation,
        "deterministic_checks_passed": False,
        "commands": [], "artifacts": [], "effects_complete": False,
    }
    services.project_attempts.append(record)
    try:
        result = dict(services.dependencies.project_executor(execution_request, context))
        completed = result.get("deterministic_checks_passed") is True
        if not completed:
            result["artifacts"] = [
                {**item, "verified": False} for item in result.get("artifacts", ())]
        # The executor supplies evidence; the runtime owns attempt identity.
        result.update({key: record[key] for key in (
            "record_type", "attempt_number", "manifest_digest", "manifest",
            "workspace_path", "input_use_validation")})
        result.update(execution_status="COMPLETED" if completed else "FAILED",
                      deterministic_checks_passed=completed, effects_complete=True)
        record.update(result)
        return record
    except BaseException as exc:
        rejection = rejection_from_exception(
            "core.generated_project", exc,
            pass_number=services.active_pass_number)
        record.update(
            execution_status="FAILED", deterministic_checks_passed=False,
            error_type=type(exc).__name__, error=rejection.message,
            cancelled=isinstance(exc, (KeyboardInterrupt, SystemExit)),
            effects_complete=False, artifacts=[], commands=[])
        raise


def execute_adaptive_capability(
        request: AdaptiveCapabilityExecutionRequest,
        services: AdaptiveRunServices) -> ResultPacket:
    """Compile, validate, and execute one selected generic capability."""
    plan = request.plan
    owner = request.owner_loop
    arguments = dict(plan.experiment.get("arguments") or {})
    manifest = None
    fence_policy = DEFAULT_SUPERVISION_POLICY.action_fence
    if services.action_fence.is_fenced(plan.handle, arguments, fence_policy):
        refusal = services.action_fence.refusal(
            plan.handle, arguments, fence_policy,
            pass_number=services.active_pass_number)
        services.action_history.append({
            "capability_ref": plan.handle, "fenced": True,
            "refusal": refusal.to_dict(),
        })
        return ResultPacket(
            objective=plan.handle,
            errors=(refusal.message,),
            confidence=0.0,
            limitations=(
                "The runtime refused to repeat an identical failed call; "
                + refusal.repair_hint,),
        )
    if plan.handle == "core.source.inspect":
        operation = lambda _value, _params: source_inspection_operation(
            arguments, services)
        input_value = arguments
        input_role = "next_action_decision/v1"
        output_role = "source_inspection_result/v1"
    elif plan.handle == "core.web.search":
        operation = lambda _value, _params: _search_operation(
            arguments, services, owner)
        input_value = arguments
        input_role = "next_action_decision/v1"
        output_role = "web_search_result/v1"
    elif plan.handle == "core.web.get":
        operation = lambda _value, _params: _web_operation(
            arguments, services, owner)
        input_value = arguments
        input_role = "next_action_decision/v1"
        output_role = "web_fetch_result/v1"
    elif plan.handle == "core.workspace.read":
        operation = lambda _value, _params: workspace_read_operation(
            arguments, services)
        input_value = arguments
        input_role = "next_action_decision/v1"
        output_role = "workspace_read_result/v1"
    elif plan.handle == "core.source.profile":
        operation = lambda _value, _params: source_profile_operation(
            arguments, services)
        input_value = arguments
        input_role = "next_action_decision/v1"
        output_role = "source_profile_result/v1"
    elif plan.handle == "core.environment.describe":
        operation = lambda _value, _params: environment_describe_operation(
            services)
        input_value = arguments
        input_role = "next_action_decision/v1"
        output_role = "environment_description/v1"
    elif plan.handle == "core.intelligence.search":
        operation = lambda _value, _params: intelligence_search_operation(
            arguments, services, owner)
        input_value = arguments
        input_role = "next_action_decision/v1"
        output_role = "intelligence_search_result/v1"
    elif plan.handle == "core.generated_project":
        if services.web_search_results and not services.web_results:
            return ResultPacket(
                objective="resolve selected public source",
                errors=(
                    "web search produced candidates, but no selected source "
                    "has been fetched and verified",),
                confidence=0.0,
                limitations=(
                    "Search candidates are not evidence. Fetch a selected "
                    "source before constructing a source-dependent project.",))
        # These refusals used to return without telling the fence, so the
        # fence view stated "recent_failures: []" while a live run refused
        # the same construction on twenty consecutive passes. A refusal the
        # runtime does not remember is a refusal the model cannot learn from.
        def refuse_project(objective: str, exc: BaseException,
                           limitation: str,
                           fence_arguments: dict) -> ResultPacket:
            rejection = rejection_from_exception(
                plan.handle, exc, pass_number=services.active_pass_number)
            services.action_fence.note_failure(
                plan.handle, fence_arguments, error=rejection.message,
                rejection=rejection.to_dict(),
                pass_number=services.active_pass_number)
            services.diagnostic("generated_project_refused", {
                "objective": objective, "error": rejection.message[:500]})
            return ResultPacket(
                objective=objective,
                result={"rejection": rejection.to_dict()},
                errors=(rejection.message,),
                confidence=0.0,
                limitations=(limitation,))

        # A construction that never reached a manifest is remembered under
        # its stage, not under the capability, because the model repairs it
        # by changing run state rather than by changing this call.
        prepare_arguments = {**arguments, "construction_stage": "prepare"}
        try:
            input_artifacts = project_inputs(services)
            manifest = project_manifest(
                request.state, plan, services, input_artifacts)
        except (AdaptivePractitionerError, GeneratedProjectError,
                SolutionModelError, PermissionError) as exc:
            return refuse_project(
                "prepare and construct a valid executable project", exc,
                "The project could not be prepared from the current run "
                "state. Select the required local sources through "
                "core.source.inspect first; no workspace or command "
                "effect was performed.", prepare_arguments)
        services.action_fence.note_success(plan.handle, prepare_arguments)
        # An attempt is identified by its manifest, not by the empty argument
        # set every generated-project call shares. A corrected project is a
        # different action and stays admissible; the identical one cannot
        # behave differently and is refused before it costs anything.
        attempt_arguments = {**arguments, "manifest_digest": manifest.digest}
        if services.action_fence.is_fenced(
                plan.handle, attempt_arguments, fence_policy):
            refusal = services.action_fence.refusal(
                plan.handle, attempt_arguments, fence_policy,
                pass_number=services.active_pass_number)
            return ResultPacket(
                objective="execute a generated project",
                result={"rejection": refusal.to_dict()},
                errors=(refusal.message,),
                confidence=0.0,
                limitations=(
                    "This exact project already failed and cannot behave "
                    "differently; change the files or the commands. "
                    + refusal.repair_hint,))
        try:
            input_validation = as_practitioner_loop(
                "validate generated project input use",
                lambda: validate_generated_project_input_use(
                    manifest, input_artifacts), parent=owner)["value"]
        except Exception as exc:
            return refuse_project(
                "validate generated project input use", exc,
                "The generated project ignored supplied inputs or violated "
                "offline execution policy; no effect was performed.",
                attempt_arguments)
        def operation(_value, _params):
            return _execute_project_attempt(
                manifest, input_artifacts, input_validation, services, owner)
        input_value = manifest.to_dict()
        input_role = "generated_project_manifest/v1"
        output_role = "generated_project_execution/v1"
    else:
        return ResultPacket(
            objective=plan.handle or "unresolved action",
            errors=("action has no registered capability executor",),
            confidence=0.0)

    identity = hashlib.sha256(json.dumps(
        {"handle": plan.handle, "steps": list(plan.steps),
         "arguments": arguments}, sort_keys=True, default=str,
        separators=(",", ":")).encode()).hexdigest()[:20]
    spec = SolutionSpec(
        f"adaptive.action.{identity}",
        permitted_loop_modes=("deterministic",),
        loops=(SolutionLoopSpec(
            "execute_selected_capability", plan.handle,
            mode="deterministic", params={
                "instruction": plan.rationale,
                "plan_digest": identity,
            }, input_role=input_role, output_role=output_role),))
    registry = {plan.handle: operation}
    compiled = compile_solution(spec, registry)
    if compiled["plan"] is None:
        return ResultPacket(
            objective=plan.handle,
            errors=("Solution graph validation failed: "
                    + "; ".join(compiled["violations"]),),
            confidence=0.0)
    canvas = render_canvas(compiled["plan"])
    trace = []
    try:
        output = run_compiled(
            compiled["plan"], registry, input_value,
            trace=trace, ledger=owner.ledger, parent=owner)
    except Exception as exc:
        # Every refused call is described by the runtime in its own typed
        # vocabulary, not left as prose for the model to re-diagnose. The
        # admitted values and the repair travel back on the packet the model
        # reads next, and the fence remembers the identity.
        rejection = rejection_from_exception(
            plan.handle, exc, pass_number=services.active_pass_number)
        services.action_fence.note_failure(
            plan.handle, arguments,
            error=rejection.message,
            rejection=rejection.to_dict(),
            pass_number=services.active_pass_number)
        admitted = rejection.admitted_values
        limitations = (rejection.repair_hint,) if rejection.repair_hint else ()
        if admitted:
            limitations = limitations + (
                f"admitted values for {rejection.capability_ref}: "
                f"{list(admitted)}"
                + ("" if len(admitted) == rejection.admitted_values_total
                   else f" (first {len(admitted)} of "
                        f"{rejection.admitted_values_total})"),)
        return ResultPacket(
            objective=plan.handle,
            result={"rejection": rejection.to_dict()},
            # The rejection already names the deepest cause; repeating the
            # wrapper here would put the uninformative sentence back in front
            # of the model beside the informative one.
            errors=(rejection.message,),
            confidence=0.0,
            limitations=limitations,
            lineage=(compiled["digest"],))
    services.action_fence.note_success(plan.handle, arguments)
    if manifest is not None:
        # Executing is not passing. A project that ran and failed its own
        # checks has told the run everything an identical rerun would, so the
        # identical manifest is remembered as failed and a changed one is not.
        if output.get("deterministic_checks_passed"):
            services.action_fence.note_success(
                plan.handle, {**arguments,
                              "manifest_digest": manifest.digest})
        else:
            services.action_fence.note_failure(
                plan.handle,
                {**arguments, "manifest_digest": manifest.digest},
                error="the project executed and its deterministic checks "
                      "did not pass",
                pass_number=services.active_pass_number)
    services.plan_details["active_canvas"] = {
        "candidate_id": f"canvas:{identity}",
        "selected": True,
        "graph_digest": compiled["digest"],
        "loop_graph": compiled["plan"],
        "mermaid": canvas["mermaid"],
        "runtime_trace": trace,
    }
    if plan.handle == "core.source.inspect":
        services.source_inspections.append(output)
        services.selected_intelligence_refs.extend(
            f"source:{item['digest']}" for item in output["selected"]
            if f"source:{item['digest']}"
            not in services.selected_intelligence_refs)
        # What each supplied file *is* is a reading, not a rule this runtime
        # could hold, so one model call states it and the answer is saved.
        # It runs once per distinct manifest, here, because this is the first
        # moment the run holds bytes to read it from.
        orient_source_roles(services)
        return ResultPacket(
            objective=(str(arguments.get("query") or "")
                       or "inspect supplied source"),
            result=output,
            evidence_refs=tuple(
                f"source:{item['digest']}" for item in output["selected"]),
            confidence=1.0,
            lineage=(compiled["digest"],))
    if plan.handle == "core.workspace.read":
        read = output.get("read") or {}
        return ResultPacket(
            objective=(f"read {read['path']} from this run's workspace"
                       if read else "list what this run has produced"),
            result=output,
            confidence=1.0,
            lineage=(compiled["digest"],),
            limitations=(
                "This is what the file says now, which is evidence about "
                "the run's own output and about nothing else.",)
            + (("The file was longer than the measured evidence allowance; "
                "ask for a later first_line to continue reading.",)
               if read.get("truncated") else ()))
    if plan.handle == "core.source.profile":
        return ResultPacket(
            objective="profile supplied source structure",
            result=output,
            confidence=1.0,
            lineage=(compiled["digest"],),
            limitations=(
                "A structural profile is discovery evidence; it never "
                "selects a source or grants authority.",))
    if plan.handle == "core.environment.describe":
        return ResultPacket(
            objective="describe the runtime environment",
            result=output,
            confidence=1.0,
            lineage=(compiled["digest"],),
            limitations=(
                "The environment description is effect-free discovery; "
                "provider names appear without secrets or availability "
                "proof.",))
    if plan.handle == "core.intelligence.search":
        return ResultPacket(
            objective=str(arguments.get("query") or "intelligence search"),
            result=output,
            confidence=1.0,
            lineage=(compiled["digest"],),
            limitations=(
                "Intelligence references are advisory candidates; they "
                "never become active without the existing admission and "
                "promotion paths.",))
    if plan.handle == "core.web.search":
        services.web_search_results.append(output)
        return ResultPacket(
            objective=str(arguments.get("purpose") or "public web search"),
            result=output,
            confidence=1.0,
            lineage=(compiled["digest"],),
            limitations=(
                "Search candidates are not evidence until a URL is fetched.",))
    if plan.handle == "core.web.get":
        services.web_results.append(output)
        services.selected_intelligence_refs.append(
            f"artifact:{output['sha256']}")
        return ResultPacket(
            objective=str(arguments.get("purpose") or "public web research"),
            result=output,
            evidence_refs=(f"artifact:{output['sha256']}",),
            artifact_refs=(output["artifact_ref"]["object_key"],),
            confidence=1.0,
            lineage=(compiled["digest"],))
    output["context_evidence_count"] = len(services.web_results)
    errors = (() if output.get("deterministic_checks_passed") else (
        "generated project deterministic checks failed",))
    return ResultPacket(
        objective=(manifest.summary if manifest is not None else plan.handle),
        result=output,
        artifact_refs=tuple(item["path"] for item in output.get("artifacts", ())
                            if item.get("verified")),
        confidence=(1.0 if not errors else 0.0), errors=errors,
        lineage=(compiled["digest"], manifest.digest if manifest else ""))


def self_test() -> dict:
    """Static contract check; execution is covered by the adaptive suite."""
    source = Path(__file__).read_text(encoding="utf-8").split(
        "def self_test()", 1)[0].lower()
    task_words = ("openml", "iris", "boosted-tree", "target_column=", "kaggle")
    passed = not any(word in source for word in task_words)
    fence_policy = DEFAULT_SUPERVISION_POLICY.action_fence
    fence = ActionFenceLedger()
    repeated_call = {"paths": ["/never/admitted"], "include_contents": False}
    unadmitted = CapabilityRejection(
        "core.source.inspect", "argument_not_admitted",
        "source inspection requested unknown paths ['/never/admitted']",
        rejected_arguments=(("paths", ("/never/admitted",)),),
        admitted_values=("a.csv", "b.csv"), admitted_values_total=2,
        repair_hint="omit paths to receive the manifest").to_dict()
    for attempt in range(fence_policy.identical_failures_before_fence):
        fence.note_failure("core.source.inspect", repeated_call,
                           error="unknown paths", rejection=unadmitted,
                           pass_number=attempt + 1)
    repeat_refused = fence.is_fenced(
        "core.source.inspect", repeated_call, fence_policy)
    manifest_call_open = not fence.is_fenced(
        "core.source.inspect", {"include_contents": False}, fence_policy)
    refusal = fence.refusal("core.source.inspect", repeated_call,
                            fence_policy, pass_number=9)
    fence_passed = (
        repeat_refused and manifest_call_open
        and refusal.reason_code == "repeated_identical_failure"
        and "a.csv" in refusal.repair_hint)
    tests = [{
        "test": "capability_graph_compiler_has_no_example_route",
        "passed": passed,
        "detail": "one generic Solution graph path",
    }, {
        "test": "an_identical_failed_call_is_refused_while_a_new_one_is_not",
        "passed": fence_passed,
        "detail": (f"fenced after "
                   f"{fence_policy.identical_failures_before_fence} identical "
                   "failures; a different argument set stays admissible"),
    }]
    tests.extend(_project_attempt_checks())
    return {
        "record_type": "adaptive_capability_compilation_test/v1",
        "tests": tests,
        "passed": sum(item["passed"] for item in tests),
        "total": len(tests), "all_passed": all(
            item["passed"] for item in tests),
    }


def _project_attempt_checks() -> list[dict]:
    """Offline physical-executor fixture through the real capability graph."""
    import tempfile
    from types import SimpleNamespace
    from unittest.mock import patch

    from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
    from ..loop.recursive_loop import Loop, LoopConfig
    from .adaptive_practitioner_records import AdaptivePractitionerDependencies
    from .generated_project import (
        GeneratedProjectInputArtifact,
        GeneratedProjectManifest,
    )

    tests = []

    def check(name, value):
        tests.append({"test": name, "passed": bool(value),
                      "detail": "offline executor fixture; no model or container calls"})

    manifest = GeneratedProjectManifest.from_mapping({
        "record_type": "generated_project_manifest/v1", "project_id": "attempt_fixture",
        "summary": "Read the input and verify authored code.",
        "files": [{"path": "main.py", "content": "open('inputs/source.txt').read()\n"}],
        "commands": [{"argv": ["python", "main.py"], "purpose": "Verify code.",
                      "command_kind": "verify", "expected_exit_codes": [0]}],
        "expected_artifacts": []})
    inputs = (GeneratedProjectInputArtifact("inputs/source.txt", b"admitted fixture"),)
    owner = Loop("attempt lifecycle fixture", LoopConfig(
        framework="custom", custom_steps=("execute",), power="light",
        allowable_modes=("deterministic",), preferred_modes=("deterministic",),
        delegated_modes=("deterministic",), logical_kind="execution",
        replay_guarantee="event_equivalent", exit_condition="steps_complete"),
        identity=LoopRoleIdentity(LoopRole.PRACTITIONER, "practitioner.solver"),
        relationship=LoopRelationship.starting())
    request = AdaptiveCapabilityExecutionRequest(
        PractitionerState(spec=None), ExecutionPlan("use", "run_dag",
            handle="core.generated_project"), owner)
    with tempfile.TemporaryDirectory(prefix="loop-engine-attempt-check-") as directory:
        physical_paths, observed_started = [], []
        outcome = ["raise"]

        def executor(execution, _context):
            path = Path(execution.workspace_root)
            physical_paths.append(path)
            record = services.project_attempts[-1]
            observed_started.append(record["execution_status"] == "STARTED"
                and not record["deterministic_checks_passed"]
                and not record["artifacts"] and not path.exists())
            path.mkdir()
            (path / "inputs").mkdir()
            (path / inputs[0].path).write_bytes(inputs[0].content)
            (path / "partial.py").write_text("partial = True\n", encoding="utf-8")
            if outcome[0] == "raise":
                raise GeneratedProjectError("fixture failure after input copy")
            if outcome[0] == "cancel":
                raise KeyboardInterrupt("fixture cancellation after input copy")
            return {"deterministic_checks_passed": outcome[0] == "pass",
                    "commands": [], "artifacts": [{"path": "main.py", "verified": True}]}

        services = AdaptiveRunServices(
            request=SimpleNamespace(allow_workspace_writes=True,
                allow_sandbox_commands=True, allow_network_reads=False,
                allow_local_execution=False, context_budget=None),
            dependencies=AdaptivePractitionerDependencies(project_executor=executor),
            run_id="attempt-fixture", workspace_base=Path(directory),
            artifacts=None, portfolio=None)
        services.plan_details["accepted_incumbent"] = {"reference": "prior unchanged"}
        with patch(__name__ + ".project_inputs", return_value=inputs), \
                patch(__name__ + ".project_manifest", return_value=manifest):
            first = execute_adaptive_capability(request, services)
            failed = services.project_attempts[0]
            check("partial_executor_failure_keeps_exact_failed_attempt",
                  first.errors and len(services.project_attempts) == 1
                  and failed["execution_status"] == "FAILED"
                  and not failed["deterministic_checks_passed"]
                  and not failed["artifacts"] and not failed["effects_complete"]
                  and failed["manifest_digest"] == manifest.digest
                  and failed["manifest"] == manifest.to_dict()
                  and "fixture failure" in failed["error"])
            partial = workspace_read_operation({"path": "attempt-1/partial.py"}, services)
            check("production_workspace_base_reads_partial_failed_attempt",
                  not hasattr(services, "workspace")
                  and partial["read"]["lines"] == [{"line": 1, "text": "partial = True"}])
            outcome[0] = "pass"
            second = execute_adaptive_capability(request, services)
            check("retry_after_partial_copy_allocates_fresh_attempt_without_double_append",
                  not second.errors and len(services.project_attempts) == 2
                  and [path.name for path in physical_paths] == ["attempt-1", "attempt-2"]
                  and services.project_attempts[1]["execution_status"] == "COMPLETED"
                  and services.project_attempts[0] is failed)
            outcome[0] = "cancel"
            cancelled = False
            try:
                execute_adaptive_capability(request, services)
            except KeyboardInterrupt:
                cancelled = True
            cancellation = services.project_attempts[-1]
            check("cancellation_finalizes_failure_and_propagates_without_verified_artifacts",
                  cancelled and len(services.project_attempts) == 3
                  and cancellation["execution_status"] == "FAILED"
                  and cancellation["cancelled"] and not cancellation["effects_complete"]
                  and not cancellation["deterministic_checks_passed"]
                  and not cancellation["artifacts"])
            outcome[0] = "fail_checks"
            fourth = execute_adaptive_capability(request, services)
            check("failed_checks_cannot_mark_source_artifacts_verified",
                  fourth.errors and not fourth.artifact_refs
                  and services.project_attempts[-1]["execution_status"] == "FAILED"
                  and not services.project_attempts[-1]["artifacts"][0]["verified"])
            check("every_physical_attempt_is_recorded_before_its_first_effect",
                  len(observed_started) == 4 and all(observed_started)
                  and physical_paths[-1].name == "attempt-4")
            check("failed_and_cancelled_attempts_do_not_replace_accepted_incumbent",
                  services.plan_details["accepted_incumbent"] == {"reference": "prior unchanged"}
                  and inputs[0].content == b"admitted fixture"
                  and (physical_paths[0] / inputs[0].path).read_bytes() == inputs[0].content)
    return tests
