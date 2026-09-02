"""Question-driven Practitioner execution for arbitrary task text.

This module connects the universal Practitioner kernel to passive question
Context Intelligence, generic capability execution, verification, repair, and
Run History. Task-specific interpretation and solution content come from the
active model run, never from source branches in this module.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import time
from dataclasses import replace
from pathlib import Path

from ..loop.kernel import (
    CandidateAction, DecisionSupportPortfolio, ExecutionPlan,
    KernelRunRequest, PractitionerState, ProblemSpec, ResultPacket,
    Situation, run_kernel_passes)
from ..loop.kernel_runtime import current_kernel_owner
from ..loop.loop_role import LoopRelationship, LoopRole, LoopRoleIdentity
from ..loop.recursive_loop import Loop, LoopConfig, LoopLedger
from ..code_nodes.solution_model_port import SolutionModelError
from .adaptive_practitioner_records import (
    ADAPTIVE_PRACTITIONER_RECORD_TYPE,
    NEXT_ACTION_KINDS,
    AdaptivePractitionerDependencies, AdaptivePractitionerError,
    AdaptivePractitionerRequest, AdaptiveRunServices,
    DeterministicAttemptTrace, ModelStepRequest, NextActionDecision,
    TaskOrientationResult)
from .adaptive_practitioner_deterministic import run_deterministic_attempt
from .adaptive_practitioner_capabilities import (
    AdaptiveCapabilityExecutionRequest, build_action_canvas_candidate,
    execute_adaptive_capability)
from .adaptive_practitioner_source import source_inspection_model_view
from .adaptive_practitioner_planning import (
    AdaptivePlanningRequest, build_execution_plan)
from .adaptive_practitioner_orientation import orientation_policy_findings
from .adaptive_practitioner_supervision import (
    supervision_context, validate_progressing_action)
from .adaptive_practitioner_verification import (
    AdaptiveRouteRequest, AdaptiveVerificationRequest,
    route_adaptive_result, safe_result, verify_adaptive_results)
from .adaptive_practitioner_reuse import observe_generated_project_reuse
from .context_artifacts import (
    ContextArtifactManager, ContextArtifactServices, ContextArtifactStore,
    ContextArtifactStoreSpec)
from .practitioner_context import load_practitioner_context
from .run_history import default_runs_dir
from .adaptive_practitioner_result import (
    failed_adaptive_output, finish_deterministic_attempt, loop_details,
    safe_model_usage, save_adaptive_result)
def _copy_workspace_confined(workspace: Path, destination: Path) -> dict:
    """Copy a workspace into Run History without following links out of it.

    Generated code runs as the host user with the workspace mounted
    read-write, so a symlink it creates could point anywhere on the host.
    Symlinks are copied as symlinks, never dereferenced, and any entry whose
    resolved path leaves the workspace is skipped and counted.
    """
    root = workspace.resolve()
    skipped: list[str] = []
    base_ignore = shutil.ignore_patterns(".venv", "__pycache__", "*.pyc")

    def ignore(directory, names):
        ignored = set(base_ignore(directory, names))
        for name in names:
            path = Path(directory) / name
            try:
                inside = path.resolve().is_relative_to(root)
            except (OSError, RuntimeError):
                inside = False
            if not inside:
                ignored.add(name)
                skipped.append(str(path))
        return ignored

    shutil.copytree(workspace, destination, symlinks=True, ignore=ignore)
    return {"symlinks_preserved": True,
            "skipped_outside_workspace": skipped}


def _model_state(state: PractitionerState,
                 services: AdaptiveRunServices) -> dict:
    view = {
        "state_version": state.version,
        "facts": state.facts,
        "artifact_refs": state.artifacts,
        "open_questions": list(state.open_questions),
        "failures": list(state.failures),
        "last_route": state.last_route,
        "web_search_candidates": [{
            "query_digest": item.get("query_digest"),
            "purpose": item.get("purpose"),
            "results": item.get("results"),
            "evidence_state": item.get("evidence_state"),
        } for item in services.web_search_results],
        "web_evidence": [{
            "final_url": item.get("final_url"),
            "media_type": item.get("media_type"),
            "sha256": item.get("sha256"),
            "text": item.get("text"),
            "text_truncated": item.get("text_truncated"),
        } for item in services.web_results],
        "source_inspections": source_inspection_model_view(
            services.source_inspections),
        "generated_file_checkpoints":
            services.generated_file_checkpoint_summaries(),
        "project_attempts": [{
            "manifest_digest": item.get("manifest_digest"),
            "deterministic_checks_passed": item.get(
                "deterministic_checks_passed"),
            "commands": [{
                "purpose": command.get("purpose"),
                "ok": command.get("ok"),
                "exit_code": command.get("exit_code"),
                "stdout": str(command.get("stdout", "")),
                "stderr": str(command.get("stderr", "")),
                "error_code": command.get("error_code"),
            } for command in item.get("commands", ())],
            "artifacts": item.get("artifacts", ()),
        } for item in services.project_attempts],
        "supervision": supervision_context(services, state),
    }
    # Bounding happens once, at the packet boundary in
    # adaptive_practitioner_records, where every step's state converges.
    return view
def _adaptive_impls(services: AdaptiveRunServices) -> dict:
    def orient(state: PractitionerState) -> Situation:
        services.active_pass_number += 1
        services.publish("practitioner.step.started", step="orient",
                         state_version=state.version)
        schema = json.dumps({
                "original_task_ref": "sha256:<digest>",
                "task_summary": "string", "ultimate_goal": "string",
                "immediate_goal": "string", "current_state": "string",
                "desired_state": "string", "inputs": ["string"],
                "outputs": ["string"], "operator_bundle": ["string"],
                "response_contract": "string", "decision_consumer": "string",
                "explicit_constraints": ["string"],
                "inferred_constraints": ["string"], "non_goals": ["string"],
                "knowns": ["string"], "unknowns": ["string"],
                "assumptions": ["string"], "ambiguities": [{
                    "subject": "string",
                    "state": "UNKNOWN|AMBIGUOUS|DELEGATED_CHOICE|DEFAULTABLE_CHOICE|DERIVED_VALUE|RESEARCH_REQUIRED|USER_CLARIFICATION_REQUIRED|AUTHORITY_REQUIRED|BLOCKED",
                    "reason": "string"}],
                "delegated_choices": ["string"], "safe_defaults": ["string"],
                "blocking_questions": ["string"],
                "research_questions": ["string"], "subproblems": ["string"],
                "dependencies": ["string"], "parallel_candidates": ["string"],
                "candidate_profiles": ["string"],
                "candidate_capabilities": ["string"],
                "verification_obligations": ["string"],
                "confidence_profile": {"overall": 0.0},
                "proposed_next_action": "string",
            }, separators=(",", ":"))
        failures = []
        parsed = None
        for attempt in range(1, 3):
            try:
                value = services.model(ModelStepRequest(
                    "orient",
                    ("Orient on the task and return TaskOrientationResult "
                     "version 1." if attempt == 1 else
                     "Repair the internally inconsistent "
                     "TaskOrientationResult."),
                    {**_model_state(state, services),
                     "orientation_validation_failures": failures}, schema))
            except SolutionModelError as exc:
                services.diagnostic("orientation_provider_unavailable", {
                    "attempt": attempt,
                    "error_code": exc.error_code or "model_gateway_failed"})
                raise
            except AdaptivePractitionerError as exc:
                failures.append({
                    "attempt": attempt,
                    "findings": [f"{type(exc).__name__}: {str(exc)[:500]}"],
                    "rejected_orientation": None})
                services.diagnostic("orientation_model_unavailable", {
                    "attempt": attempt, "error_type": type(exc).__name__})
                continue
            value["original_task_ref"] = (
                "sha256:" + hashlib.sha256(
                    services.request.task.encode("utf-8")).hexdigest())
            try:
                candidate = TaskOrientationResult.from_mapping(value)
                findings = orientation_policy_findings(
                    candidate, services.request.interaction_mode)
            except (AdaptivePractitionerError, ValueError) as exc:
                findings = [str(exc)]
                candidate = None
            if candidate is not None and not findings:
                parsed = candidate
                break
            failures.append({
                "attempt": attempt, "findings": findings,
                "rejected_orientation": value})
            services.diagnostic("orientation_invalid", {
                "attempt": attempt, "findings": findings})
        if parsed is None:
            if services.orientation_by_version:
                previous = services.orientation_by_version[
                    max(services.orientation_by_version)]
                parsed = replace(
                    previous,
                    current_state=(
                        "Latest accepted orientation reused after semantic "
                        "resolver failure; typed Practitioner state remains "
                        "authoritative."),
                    proposed_next_action=(
                        "Continue from the latest accepted orientation and "
                        "current typed state."))
                services.diagnostic("orientation_reused", {
                    "source_state_version": max(
                        services.orientation_by_version),
                    "target_state_version": state.version})
            else:
                raise AdaptivePractitionerError(
                    "orientation remained invalid after one model repair")
        services.orientation_by_version[state.version] = parsed
        services.publish("practitioner.step.completed", step="orient",
                         task_summary=parsed.task_summary[:160])
        return Situation(
            summary=parsed.task_summary,
            knowns={"orientation": parsed},
            unknowns=parsed.unknowns,
            signals=(("missing_info",) if parsed.unknowns else ()),
            resources_hint=tuple(item["capability_ref"]
                                 for item in services.available_capabilities()))
    def standardize_task(state: PractitionerState, situation: Situation):
        orientation = situation.knowns["orientation"]
        return {
            "record_type": "work_item_ir/v1",
            "original_input": services.request.task,
            "normalized_interpretation": orientation.task_summary,
            "ultimate_goal": orientation.ultimate_goal,
            "immediate_goal": orientation.immediate_goal,
            "current_state": orientation.current_state,
            "desired_state": orientation.desired_state,
            "inputs": list(orientation.inputs),
            "outputs": list(orientation.outputs),
            "operator_bundle": list(orientation.operator_bundle),
            "response_contract": orientation.response_contract,
            "decision_consumer": orientation.decision_consumer,
            "explicit_constraints": list(orientation.explicit_constraints),
            "inferred_constraints": list(orientation.inferred_constraints),
            "non_goals": list(orientation.non_goals),
            "knowns": list(orientation.knowns),
            "unknowns": list(orientation.unknowns),
            "assumptions": list(orientation.assumptions),
            "ambiguities": [item.to_dict() for item in orientation.ambiguities],
            "delegated_choices": list(orientation.delegated_choices),
            "safe_defaults": list(orientation.safe_defaults),
            "blocking_questions": list(orientation.blocking_questions),
            "research_questions": list(orientation.research_questions),
            "subproblems": list(orientation.subproblems),
            "dependencies": list(orientation.dependencies),
            "parallel_candidates": list(orientation.parallel_candidates),
            "verification_obligations": list(
                orientation.verification_obligations),
            "template_id": "",
            "binding_mode": "model_oriented_open_task",
            "source": "adaptive_practitioner_orientation",
        }

    def reconcile_horizon(state: PractitionerState, situation: Situation):
        orientation = situation.knowns["orientation"]
        return {
            "record_type": "goal_alignment/v1",
            "ultimate_goal": orientation.ultimate_goal,
            "state_version": state.version,
            "completed_artifact_refs": list(state.artifacts),
            "failures": list(state.failures),
            "remaining_success_criteria": list(
                orientation.verification_obligations),
        }

    def assess_prepare(state: PractitionerState,
                       situation: Situation) -> DecisionSupportPortfolio:
        orientation = situation.knowns["orientation"]
        questions = list(services.portfolio.for_step(
            "assess_prepare").questions)
        questions.extend(orientation.blocking_questions)
        questions.extend(orientation.research_questions)
        return DecisionSupportPortfolio(
            sufficiency=("generated_resources" if questions
                         else "sufficient_no_expansion"),
            questions=list(dict.fromkeys(questions)),
            perspectives=[services.portfolio.persona.persona_id],
            generated=[services.portfolio.portfolio_id],
            notes="General questions only; no task-specific template selected.")

    def decide_next(state: PractitionerState,
                    situation: Situation) -> list[CandidateAction]:
        schema = json.dumps({"actions": [{
                "action_kind": "|".join(NEXT_ACTION_KINDS),
                "goal": "string", "reason": "string", "inputs": {},
                "expected_output": "string",
                "required_capabilities": ["registered capability ref"],
                "permissions": [
                    "source_read|network_read|workspace_write|sandbox_command"],
                "budget": {},
                "dependencies": ["string"], "scheduling": "string",
                "verification": "string", "return_destination": "string",
                "confidence": 0.0, "fallback": {},
            }], "selected_action_index": 0}, separators=(",", ":"))
        decisions = None
        selected_index = 0
        failure = ""
        for attempt in (1, 2):
            try:
                value = services.model(ModelStepRequest(
                    "decide_next",
                    ("Return typed NextActionDecision candidates for verified "
                     "progress." if attempt == 1 else
                     "Repair the rejected next-action response without "
                     "changing the task or adding authority."),
                    {**_model_state(state, services),
                     "orientation": situation.knowns["orientation"].to_dict(),
                     "next_action_validation_failure": failure}, schema))
                actions = value.get("actions")
                if not isinstance(actions, list) or not actions:
                    raise AdaptivePractitionerError(
                        "decide_next must return at least one action")
                raw_selected = value.get("selected_action_index")
                if raw_selected is None:
                    if len(actions) != 1:
                        raise AdaptivePractitionerError(
                            "multiple next actions require a model-selected "
                            "action index")
                    raw_selected = 0
                if (not isinstance(raw_selected, int)
                        or isinstance(raw_selected, bool)
                        or not 0 <= raw_selected < len(actions)):
                    raise AdaptivePractitionerError(
                        "selected_action_index is outside the action list")
                parsed = []
                for item in actions:
                    decision = NextActionDecision.from_mapping(item)
                    orientation = situation.knowns["orientation"]
                    if decision.action_kind == "ASK_USER":
                        if not orientation.blocking_questions:
                            raise AdaptivePractitionerError(
                                "ASK_USER requires a material blocking question")
                        if services.request.interaction_mode == "autonomous":
                            decision = replace(
                                decision, action_kind="ABSTAIN",
                                reason=("Autonomous mode cannot pause for the "
                                        "material clarification identified "
                                        "during orientation."))
                    registered = {entry["capability_ref"] for entry in
                                  services.available_capabilities()}
                    unknown = set(decision.required_capabilities) - registered
                    if unknown:
                        raise AdaptivePractitionerError(
                            "NextActionDecision selected unknown capabilities "
                            f"{sorted(unknown)}")
                    granted = {name for name, allowed in (
                        ("source_read",
                         services.request.allow_source_materialization_to_model
                         and bool(services.request.source_refs)),
                        ("network_read", services.request.allow_network_reads),
                        ("workspace_write",
                         services.request.allow_workspace_writes),
                        ("sandbox_command",
                         services.request.allow_sandbox_commands)) if allowed}
                    if (decision.action_kind != "REQUEST_AUTHORITY"
                            and set(decision.permissions) - granted):
                        raise PermissionError(
                            "NextActionDecision requests permission outside "
                            "run authority")
                    validate_progressing_action(decision, services)
                    budget = dict(decision.budget)
                    for key in ("information_gain", "estimated_cost", "risk",
                                "reversibility"):
                        float(budget.get(key, 0.0))
                    parsed.append(decision)
                decisions = parsed
                selected_index = raw_selected
                break
            except SolutionModelError:
                raise
            except (AdaptivePractitionerError, TypeError, ValueError) as exc:
                failure = str(exc)[:500]
                services.diagnostic("next_action_invalid", {
                    "attempt": attempt, "error": failure})
        if decisions is None:
            decisions = [NextActionDecision.from_mapping({
                "action_kind": "REPAIR",
                "goal": "Repair the typed next-action decision.",
                "reason": failure or "The next-action response was invalid.",
                "inputs": {}, "expected_output": "A valid typed decision.",
                "required_capabilities": [], "permissions": [],
                "budget": {"estimated_cost": 0.0, "risk": 0.0,
                           "reversibility": 1.0},
                "dependencies": [], "scheduling": "next pass",
                "verification": "Validate the next decision contract.",
                "return_destination": "current Practitioner",
                "confidence": 0.0, "fallback": {"action_kind": "ABSTAIN"},
            })]
            selected_index = 0
        candidates = []
        canvas_candidates = []
        for decision in decisions:
            decision_id = "action:" + hashlib.sha256(json.dumps(
                decision.to_dict(), sort_keys=True, separators=(",", ":"),
                default=str).encode()).hexdigest()[:20]
            services.action_details[decision_id] = decision
            services.action_history.append({
                "decision_id": decision_id, "state_version": state.version,
                **decision.to_dict()})
            canvas_candidates.append(build_action_canvas_candidate(
                decision_id, decision))
            budget = dict(decision.budget)
            candidates.append(CandidateAction(
                action=decision_id, kind=decision.action_kind,
                rationale=decision.reason,
                expected_value=decision.confidence,
                confidence=decision.confidence,
                information_gain=float(budget.get("information_gain", 0.0)),
                estimated_cost=float(budget.get("estimated_cost", 1.0)),
                risk=float(budget.get("risk", 0.1)),
                reversibility=float(budget.get("reversibility", 1.0)),
                dependencies=decision.dependencies,
                parallelizable=decision.action_kind == "RUN_PARALLEL"))
        services.candidate_canvases.extend(canvas_candidates)
        services.plan_details["current_candidate_canvases"] = canvas_candidates
        selected_action = candidates[selected_index]
        services.plan_details["model_selected_action_id"] = (
            selected_action.action)
        return [selected_action]

    def determine_how(state: PractitionerState, situation: Situation,
                      chosen: CandidateAction) -> ExecutionPlan:
        return build_execution_plan(
            AdaptivePlanningRequest(state, situation, chosen), services)

    def act(state: PractitionerState, plan: ExecutionPlan) -> list[ResultPacket]:
        owner = current_kernel_owner()
        if owner is None:
            raise AdaptivePractitionerError("act has no active owner Loop")
        services.publish("practitioner.step.started", step="act",
                         capability_ref=plan.handle)
        if plan.act_mode == "spawn_practitioners":
            from ..loop.kernel_runtime import run_spawned_kernel
            results = []
            for spec in plan.spawned_loops:
                try:
                    spawned = run_spawned_kernel(
                        spec, _adaptive_impls(services),
                        selected_mode=services.request.mode)
                    results.append(ResultPacket(
                        objective=spec.objective,
                        result=spawned.run,
                        confidence=0.7,
                        lineage=(spawned.loop_id,),
                        errors=(() if spawned.terminal_code == "ACCEPTED"
                                else (spawned.terminal_code,))))
                except Exception as exc:  # noqa: BLE001
                    results.append(ResultPacket(
                        objective=spec.objective,
                        errors=(f"{type(exc).__name__}: {str(exc)[:300]}",),
                        confidence=0.0))
            return results
        if plan.handle in {item["capability_ref"]
                           for item in services.available_capabilities()}:
            return [execute_adaptive_capability(
                AdaptiveCapabilityExecutionRequest(state, plan, owner),
                services)]
        if plan.handle == "core.finish" and services.project_attempts:
            result = services.project_attempts[-1]
            return [ResultPacket(
                objective="return verified project", result=result,
                confidence=(1.0 if result.get("deterministic_checks_passed")
                            else 0.0))]
        if plan.handle in ("core.ask", "core.authority", "core.abstain"):
            decision = next(reversed(services.action_details.values()))
            return [ResultPacket(
                objective=decision.goal,
                errors=(decision.action_kind,), confidence=0.0,
                limitations=(decision.reason,),
                suggested_next=(decision.expected_output,))]
        return [ResultPacket(
            objective=plan.handle or "unresolved action",
            errors=("action cannot execute through a registered capability",),
            confidence=0.0)]

    def verify(state: PractitionerState, plan: ExecutionPlan, results: list):
        return verify_adaptive_results(AdaptiveVerificationRequest(
            state, plan, tuple(results), _model_state(state, services)), services)

    def integrate_commit(state: PractitionerState,
                         record) -> PractitionerState:
        facts = dict(state.facts)
        artifacts = dict(state.artifacts)
        if record.results:
            latest = record.results[record.evaluation.best_index]
            facts["last_result"] = safe_result(latest)
            for ref in latest.artifact_refs:
                artifacts[str(ref)] = str(ref)
        facts["last_verification"] = (
            services.verification_records[-1]
            if services.verification_records else {})
        return state.derive(facts=facts, artifacts=artifacts)

    def route(state: PractitionerState, record) -> tuple:
        return route_adaptive_result(AdaptiveRouteRequest(
            state, record, _model_state(state, services)), services)

    return {
        "orient": orient,
        "standardize_task": standardize_task,
        "reconcile_horizon": reconcile_horizon,
        "assess_prepare": assess_prepare,
        "decide_next": decide_next,
        "how": determine_how,
        "act": act,
        "verify": verify,
        "integrate_commit": integrate_commit,
        "route": route,
    }


def _history_record(owner: Loop, services: AdaptiveRunServices,
                    runs_dir: Path) -> dict:
    """Return a verified saved or in-memory Run History summary."""
    if services.request.persist_run_history:
        from .run_history import verify_saved_run
        return verify_saved_run(str(runs_dir), services.run_id)
    from .run_history import RunHistory
    history = RunHistory.from_ledger(
        owner.ledger.events, run_id=services.run_id)
    head = history.commit()
    verification = history.verify_chain()
    return {
        "run_id": services.run_id, "events": len(history.event_log),
        "head_digest": head, "chain_intact": verification["intact"],
        "broken_at": verification["broken_at"], "path": "",
        "saved": False, "product_outcome_bound": False,
        "product_outcome_digest": "", "terminal_code": "",
    }

def run_adaptive_practitioner(
        request: AdaptivePractitionerRequest,
        dependencies: AdaptivePractitionerDependencies) -> dict:
    """Run the universal question-driven Practitioner to a verified terminal."""
    if not isinstance(request, AdaptivePractitionerRequest):
        raise AdaptivePractitionerError(
            "run_adaptive_practitioner needs AdaptivePractitionerRequest")
    if not isinstance(dependencies, AdaptivePractitionerDependencies):
        raise AdaptivePractitionerError(
            "run_adaptive_practitioner needs AdaptivePractitionerDependencies")
    run_id = "adaptive-" + hashlib.sha256(
        f"{request.task}\0{time.time_ns()}".encode()).hexdigest()[:24]
    runs_dir = Path(default_runs_dir(request.runs_dir))
    runs_dir.mkdir(parents=True, exist_ok=True)
    workspace = (Path(request.workspace_root).expanduser().resolve()
                 if request.workspace_root else
                 runs_dir / f"{run_id}-workspace")
    source_paths = tuple(Path(value).expanduser().resolve()
                         for value in request.source_refs
                         if not value.startswith(("http://", "https://")))
    if any(workspace == path or workspace in path.parents
           or path in workspace.parents
           for path in source_paths):
        raise AdaptivePractitionerError(
            "workspace must not contain an input source")
    artifact_store = ContextArtifactStore(ContextArtifactStoreSpec(
        str(runs_dir / f"{run_id}-artifacts"), namespace="adaptive"))
    portfolio = dependencies.context_portfolio or load_practitioner_context()
    services = AdaptiveRunServices(
        request, dependencies, run_id, workspace,
        ContextArtifactManager(ContextArtifactServices(artifact_store)),
        portfolio)
    ledger = LoopLedger()
    supported_modes = (("deterministic",) if request.mode == "deterministic"
                       else ("deterministic", request.mode))
    config = LoopConfig(
        framework="nine_step", logical_kind="task_semantic",
        replay_guarantee="event_equivalent",
        allowable_modes=supported_modes,
        preferred_modes=(("deterministic",) if request.mode == "deterministic"
                         else (request.mode, "deterministic")),
        delegated_modes=("deterministic", "hybrid", "non_deterministic"),
        power="deep", llm_thinking_power=(
            "" if request.mode == "deterministic" else "medium"),
        max_depth=None,
        loop_condition="steps_remain", exit_condition="steps_complete")
    owner = Loop(
        request.task, config, ledger=ledger,
        identity=LoopRoleIdentity(
            LoopRole.PRACTITIONER, "practitioner.reference_nine_step"),
        relationship=LoopRelationship.starting())
    if request.persist_run_history:
        owner.enable_run_history(run_id, root_dir=str(runs_dir))
    if request.mode == "non_deterministic":
        services.deterministic_attempt = DeterministicAttemptTrace(
            hashlib.sha256(request.task.encode()).hexdigest(), request.task,
            "SKIPPED_LLM_LED",
            diagnostics=(
                "LLM-led mode starts with semantic orientation by policy",))
    else:
        services.deterministic_attempt = run_deterministic_attempt(
            request.task, services, owner)
    if (request.mode == "deterministic"
            or services.deterministic_attempt.status == "COMPLETED"):
        return finish_deterministic_attempt(
            owner, services,
            lambda: _history_record(owner, services, runs_dir))
    if dependencies.model_execution is None:
        return finish_deterministic_attempt(
            owner, services,
            lambda: _history_record(owner, services, runs_dir))
    services.model_session = dependencies.model_execution.start_session()
    try:
        run = run_kernel_passes(KernelRunRequest(
            ProblemSpec(
                request.task, budget_passes=request.max_passes,
                seed_facts={
                    "context_portfolio_id": portfolio.portfolio_id,
                    "context_portfolio_version": portfolio.version,
                    "persona_id": portfolio.persona.persona_id,
                }),
            _adaptive_impls(services), owner_loop=owner,
            max_passes=request.max_passes, selected_mode=request.mode))
    except KeyboardInterrupt:
        if not owner.is_terminal:
            owner.cancel("operator_interrupt")
        return failed_adaptive_output(
            owner, services, "CANCELLED",
            "The operator interrupted the active Practitioner run.",
            lambda: _history_record(owner, services, runs_dir))
    except Exception as exc:  # noqa: BLE001 - preserve a terminal run record
        if not owner.is_terminal:
            owner.cancel("adaptive_practitioner_failed")
        failure_code = (exc.error_code or type(exc).__name__
                        if isinstance(exc, SolutionModelError)
                        else type(exc).__name__)
        return failed_adaptive_output(
            owner, services, failure_code, str(exc),
            lambda: _history_record(owner, services, runs_dir))
    history = _history_record(owner, services, runs_dir)
    final_attempt = services.project_attempts[-1] \
        if services.project_attempts else None
    solved = bool(
        run.get("final_route") == "stop_success" and final_attempt
        and final_attempt.get("deterministic_checks_passed"))
    output = {
        "record_type": ADAPTIVE_PRACTITIONER_RECORD_TYPE,
        "run_id": run_id,
        "status": "VERIFIED_WORKING" if solved else "NOT_YET_PROVEN",
        "solved": solved,
        "original_task": request.task,
        "task_feedback": [item.to_dict() for item in request.feedback],
        "mode": request.mode,
        "context_intelligence": {
            "portfolio_id": portfolio.portfolio_id,
            "version": portfolio.version,
            "persona": portfolio.persona.to_dict(),
            "selected_refs": list(services.selected_intelligence_refs),
        },
        "deterministic_attempt": services.deterministic_attempt.to_dict(),
        "passes": run.get("passes"),
        "final_route": run.get("final_route"),
        "failures": run.get("failures", []),
        "orientations": [item.to_dict()
                         for item in services.orientation_by_version.values()],
        "action_decisions": services.action_history,
        "context_snapshots": services.context_snapshots,
        "candidate_solution_canvases": services.candidate_canvases,
        "selected_solution_canvas": services.plan_details.get(
            "active_canvas", {}),
        "web_search_candidates": services.web_search_results,
        "web_evidence": services.web_results,
        "source_inspections": services.source_inspections,
        "source_roles": services.source_roles,
        "project_attempts": services.project_attempts,
        "verification": services.verification_records,
        "supervision": services.supervision_findings,
        "recovery_directives": services.recovery_directives,
        "generated_file_checkpoints":
            services.generated_file_checkpoint_summaries(),
        "model_calls": services.model_session.calls_used,
        "model_usage": safe_model_usage(services),
        "loop_details": loop_details(ledger.events),
        "run_history": history,
    }
    run_path = Path(history["path"]) if history.get("path") else None
    if workspace.exists() and run_path is not None:
        destination = run_path / "solution-attempts"
        if destination.exists():
            shutil.rmtree(destination)
        copy_record = _copy_workspace_confined(workspace, destination)
        output["solution_attempts_path"] = str(destination)
        output["solution_attempts_copy"] = copy_record
    elif workspace.exists():
        output["solution_attempts_path"] = str(workspace)
    reuse_observation = observe_generated_project_reuse(
        owner, services, history, solved)
    if reuse_observation is not None:
        output["reuse_observation"] = reuse_observation
    save_adaptive_result(history, output)
    return output

def self_test() -> dict:
    """Run focused task-agnostic adaptive Practitioner checks."""
    from .adaptive_practitioner_checks import run_checks
    from .adaptive_practitioner_acceptance_checks import (
        run_checks as run_acceptance_checks)
    focused = run_checks()
    acceptance = run_acceptance_checks()
    tests = [*focused["tests"], *acceptance["tests"]]
    passed = sum(item["passed"] for item in tests)
    return {
        "record_type": "adaptive_practitioner_complete_test/v1",
        "tests": tests, "passed": passed, "total": len(tests),
        "all_passed": passed == len(tests),
    }
