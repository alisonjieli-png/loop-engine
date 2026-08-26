"""Full four-task non-deterministic Loop Engine DS-1000 smoke campaign."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from loop_engine.code_nodes.loop_report import report_from_run
from loop_engine.code_nodes.run_playback import playback, render_run_report
from loop_engine.loop.loop_templates import TEMPLATE_LIBRARY, config_from_template
from loop_engine.loop.recursive_loop import Loop, LoopConfig, StepOutcome
from loop_engine.core import ollama_client
from loop_engine.core.run_history import (
    RunHistory,
    as_ledger_events,
)
from loop_engine.core.model_gateway import (
    ModelGateway,
    ModelGatewayConfig,
    ModelGatewayRequest,
    builtin_provider_specs,
)
from loop_engine.core.model_routes import ModelRoute

from code_intelligence import (
    CanvasExecution,
    CodeCandidate,
    SolverTask,
    compile_and_run_canvas,
    load_evaluator_context,
    load_solver_task,
    safe_extract_code,
    upstream_passed,
    verify_pinned_source,
)
from canonical_portfolio import (
    SpawnedLoopIntelligenceGateError,
    prepare_spawned_loop_intelligence,
)
from intelligence import (
    IntelligenceSelection,
    USER_RECORD_ID,
    build_layer_records,
    failure_history_record,
    planned_portfolio_ids,
    retrieve_predecision_intelligence,
)
from prepare import SOURCE_DIR, population
from runtime import RuntimeImage, verify_sandbox
from self_test import (
    PREFLIGHT_PATH,
    PreflightGateError,
    load_preflight,
    run_preflight,
    save_preflight,
)


BENCHMARK_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BENCHMARK_DIR / "results"
MODEL = "deepseek-v4-flash:0731"
PROVIDER = "ollama_cloud"
ROUTE_NAME = "benchmark.ds1000.deepseek-v4-flash-0731"
MAXIMUM_OUTPUT_TOKENS = 65536
MAXIMUM_CALLS_PER_TASK = 4
MAXIMUM_CALLS_POPULATION = 15
MAXIMUM_REPAIRS_POPULATION = 3
EXCLUDED_DIAGNOSTIC_PHYSICAL_CALLS = 1
PACKET_PHYSICAL_CALL_CEILING = 16
EXCLUDED_DIAGNOSTIC_CAMPAIGN = "ds1000-full-v1-20260825T145820Z"


SYSTEM_PROMPT = (
    "You are one bounded model-led code candidate Loop inside a full Loop "
    "Engine Practitioner. Solve only the supplied DS-1000 public prompt. "
    "Return only the Python completion body. Do not return Markdown, prose, "
    "tests, package installation commands, or a main program. You have not "
    "been given evaluator tests or a reference solution."
)


class CampaignGateError(RuntimeError):
    """A frozen campaign gate or physical call ceiling was violated."""


@dataclass
class CallBudget:
    maximum_population: int = MAXIMUM_CALLS_POPULATION
    maximum_per_task: int = MAXIMUM_CALLS_PER_TASK
    physical_population: int = 0
    physical_by_task: dict[int, int] = field(default_factory=dict)
    semantic_requests_by_task: dict[int, int] = field(default_factory=dict)
    repair_requests: int = 0
    attempts: list[dict] = field(default_factory=list)

    def authorize_request(self, problem_id: int, role: str) -> None:
        semantic = self.semantic_requests_by_task.get(problem_id, 0)
        if semantic >= self.maximum_per_task:
            raise CampaignGateError(
                f"problem {problem_id} reached its four-request ceiling")
        if self.physical_population >= self.maximum_population:
            raise CampaignGateError("population physical call ceiling reached")
        if self.physical_by_task.get(problem_id, 0) >= self.maximum_per_task:
            raise CampaignGateError(
                f"problem {problem_id} reached its physical call ceiling")
        if role == "repair":
            if self.repair_requests >= MAXIMUM_REPAIRS_POPULATION:
                raise CampaignGateError(
                    "the packet has allocated all three repair calls")
            self.repair_requests += 1
        self.semantic_requests_by_task[problem_id] = semantic + 1

    def repair_available(self, problem_id: int) -> bool:
        return (
            self.repair_requests < MAXIMUM_REPAIRS_POPULATION
            and self.semantic_requests_by_task.get(problem_id, 0)
            < self.maximum_per_task
            and self.physical_by_task.get(problem_id, 0)
            < self.maximum_per_task
            and self.physical_population < self.maximum_population
        )

    def record_result(self, problem_id: int, role: str, result) -> int:
        physical = [attempt for attempt in result.attempts if attempt.loop_id]
        if len(physical) > 1:
            raise CampaignGateError(
                f"one {role} request made {len(physical)} physical calls")
        count = len(physical)
        self.physical_population += count
        self.physical_by_task[problem_id] = (
            self.physical_by_task.get(problem_id, 0) + count)
        if self.physical_population > self.maximum_population \
                or self.physical_by_task[problem_id] > self.maximum_per_task:
            raise CampaignGateError("physical call ceiling exceeded")
        self.attempts.extend({
            "problem_id": problem_id,
            "role": role,
            **attempt.to_dict(),
        } for attempt in result.attempts)
        return count

    def as_dict(self) -> dict:
        return {
            "maximum_population": self.maximum_population,
            "maximum_per_task": self.maximum_per_task,
            "physical_population": self.physical_population,
            "excluded_diagnostic_physical_calls":
                EXCLUDED_DIAGNOSTIC_PHYSICAL_CALLS,
            "packet_total_physical_calls": (
                EXCLUDED_DIAGNOSTIC_PHYSICAL_CALLS
                + self.physical_population),
            "packet_physical_call_ceiling": PACKET_PHYSICAL_CALL_CEILING,
            "maximum_repairs_population": MAXIMUM_REPAIRS_POPULATION,
            "repair_requests": self.repair_requests,
            "physical_by_task": {
                str(key): value for key, value
                in sorted(self.physical_by_task.items())},
            "semantic_requests_by_task": {
                str(key): value for key, value
                in sorted(self.semantic_requests_by_task.items())},
            "attempts": self.attempts,
        }


@dataclass
class ModelSpawnedLoopResult:
    role: str
    spawned_loop_id: str
    consumed_intelligence_refs: tuple[str, ...]
    consumed_candidate_refs: tuple[str, ...]
    prompt_sha256: str
    gateway_result: dict
    candidate: CodeCandidate | None
    extraction_error: str
    physical_calls: int
    spawned_loop_intelligence: dict

    def as_dict(self) -> dict:
        return {
            "record_type": "ds1000_model_spawned_loop_result/v1",
            "role": self.role,
            "spawned_loop_id": self.spawned_loop_id,
            "consumed_intelligence_refs": list(
                self.consumed_intelligence_refs),
            "consumed_candidate_refs": list(self.consumed_candidate_refs),
            "prompt_sha256": self.prompt_sha256,
            "gateway_result": self.gateway_result,
            "candidate": self.candidate.as_dict() if self.candidate else None,
            "extraction_error": self.extraction_error,
            "physical_calls": self.physical_calls,
            "spawned_loop_intelligence": self.spawned_loop_intelligence,
        }


def _runtime_from_preflight(preflight: dict) -> RuntimeImage:
    row = preflight["runtime"]
    return RuntimeImage(
        tag=row["tag"],
        image_id=row["image_id"],
        platform=row["platform"],
        base_image_digest=row["base_image_digest"],
        requirements_sha256=row["requirements_sha256"],
        source_execution_sha256=row["source_execution_sha256"],
    )


def _gateway() -> ModelGateway:
    provider_specs = builtin_provider_specs({PROVIDER: ollama_client})
    route = ModelRoute(
        ROUTE_NAME,
        PROVIDER,
        MODEL,
        locality="cloud",
        purposes=("counted_generation",),
    )
    return ModelGateway(providers=provider_specs, routes=(route,))


def _gateway_request(prompt: str, role: str) -> ModelGatewayRequest:
    return ModelGatewayRequest(
        prompt=prompt,
        config=ModelGatewayConfig(
            purpose="counted_generation",
            route_names=(ROUTE_NAME,),
            thinking_power="max",
            allowed_models=(MODEL,),
            allowed_localities=("cloud",),
            allow_failover=False,
            max_route_attempts=1,
            timeout_seconds=900,
            max_output_tokens=MAXIMUM_OUTPUT_TOKENS,
            max_total_tokens=None,
            allow_power_escalation=False,
            max_power_escalations=0,
        ),
        system=SYSTEM_PROMPT,
        temperature=0.25 if role == "candidate_a" else 0.65
        if role == "candidate_b" else 0.2,
        output_contract="Python completion body only",
        trace_id=role,
    )


def _portfolio_block(items) -> str:
    rows = []
    for item in items:
        rows.append(
            f"- {item.loop_ref} [{item.layer}] {item.prompt_text}")
    return "\n".join(rows)


def _candidate_prompt(task: SolverTask, items, role: str) -> str:
    lens_name = (
        "first-principles, missing-constraint, output-shape, and cost"
        if role == "candidate_a"
        else "alternate-method, common-failure, and verification")
    return (
        f"Candidate role: {role}. Use the {lens_name} portfolio.\n\n"
        f"Public DS-1000 prompt:\n{task.prompt}\n\n"
        f"Retrieved intelligence:\n{_portfolio_block(items)}\n\n"
        "Return only the Python completion body."
    )


def _synthesis_prompt(task: SolverTask, items,
                      candidate_a: ModelSpawnedLoopResult,
                      candidate_b: ModelSpawnedLoopResult) -> tuple[str, tuple[str, ...]]:
    def candidate_text(result: ModelSpawnedLoopResult) -> tuple[str, str]:
        if result.candidate is not None:
            ref = f"candidate://{task.problem_id}/{result.role}/" \
                  f"{result.candidate.code_sha256}"
            return result.candidate.code, ref
        ref = f"candidate://{task.problem_id}/{result.role}/unavailable"
        detail = result.extraction_error or result.gateway_result.get(
            "error", "candidate unavailable")
        return f"Candidate unavailable: {detail}", ref

    a_text, a_ref = candidate_text(candidate_a)
    b_text, b_ref = candidate_text(candidate_b)
    prompt = (
        "Compare the two independently generated candidates against the public "
        "task and the retrieved lenses. Synthesize one final completion. Do "
        "not assume either candidate is correct.\n\n"
        f"Public DS-1000 prompt:\n{task.prompt}\n\n"
        f"Candidate A:\n{a_text}\n\n"
        f"Candidate B:\n{b_text}\n\n"
        f"Retrieved intelligence:\n{_portfolio_block(items)}\n\n"
        "Return only the synthesized Python completion body."
    )
    return prompt, (a_ref, b_ref)


def _repair_prompt(task: SolverTask, items, candidate: CodeCandidate,
                   upstream_result: str) -> tuple[str, tuple[str, ...]]:
    candidate_ref = (
        f"candidate://{task.problem_id}/synthesis/{candidate.code_sha256}")
    failure_ref = (
        f"evaluation://{task.problem_id}/{candidate.code_sha256}/failed")
    prompt = (
        "The pinned upstream evaluator rejected the synthesized completion. "
        "Make one failure-specific repair. Do not invent test details beyond "
        "the supplied evaluator result.\n\n"
        f"Public DS-1000 prompt:\n{task.prompt}\n\n"
        f"Rejected synthesized completion:\n{candidate.code}\n\n"
        f"Upstream evaluator result:\n{upstream_result}\n\n"
        f"Retrieved repair intelligence:\n{_portfolio_block(items)}\n\n"
        "Return only the repaired Python completion body."
    )
    return prompt, (candidate_ref, failure_ref)


def _assert_hidden_evaluator(task: SolverTask, evaluator, prompt: str) -> None:
    if evaluator.code_context in prompt:
        raise CampaignGateError(
            f"problem {task.problem_id} prompt contains evaluator context")
    if "def test_execution" in prompt or "def test_string" in prompt:
        raise CampaignGateError(
            f"problem {task.problem_id} prompt contains evaluator functions")


def _invoke_model_spawned_loop(root: Loop, task: SolverTask, evaluator,
                        gateway: ModelGateway, budget: CallBudget, role: str,
                        prompt_factory, preflight: dict, *,
                        extra_history=()) -> ModelSpawnedLoopResult:
    spawned_loop = root.spawn(
        f"model-led {role} for DS-1000 problem {task.problem_id}",
        LoopConfig(
            framework="custom",
            custom_steps=("generate",),
            allowable_modes=("non_deterministic",),
            preferred_modes=("non_deterministic",),
            delegated_modes=("deterministic", "non_deterministic"),
            power="light",
            llm_thinking_power="max",
            max_depth=5,
            stop_condition="run_to_completion",
        ))
    prepared = prepare_spawned_loop_intelligence(
        task, spawned_loop, preflight, role, extra_history=extra_history)
    prompt, candidate_refs = prompt_factory(prepared.prompt_items)
    consumption = prepared.consumption
    consumed_refs = consumption.consumed_refs
    if consumption.consuming_loop_id != spawned_loop.loop_id \
            or consumption.mode != "non_deterministic":
        raise CampaignGateError(
            f"{role} intelligence use is bound to the wrong spawned Loop")
    _assert_hidden_evaluator(task, evaluator, prompt)
    holder: dict = {}
    prompt_sha256 = hashlib.sha256(prompt.encode()).hexdigest()

    def handler(loop, step, context):
        budget.authorize_request(task.problem_id, role)
        response = gateway.invoke(
            _gateway_request(prompt, role), ledger=loop.ledger, parent=loop)
        physical = budget.record_result(task.problem_id, role, response)
        for attempt in response.attempts:
            if attempt.loop_id:
                run_history_fields = consumption.run_history_fields()
                loop.ledger.record(
                    loop_id=attempt.loop_id,
                    event="custom",
                    action="model_context_binding",
                    problem_id=task.problem_id,
                    call_role=role,
                    prompt_sha256=prompt_sha256,
                    consumed_intelligence_refs=run_history_fields[
                        "consumed_refs"],
                    intelligence_portfolio_id=consumption.portfolio_id,
                    intelligence_consumption_record=
                        consumption.record_digest,
                    consumed_candidate_refs=tuple(candidate_refs),
                    maximum_output_tokens=attempt.maximum_output_tokens,
                    maximum_output_source=attempt.maximum_output_source,
                    failover=False,
                )
        candidate = None
        extraction_error = ""
        if response.ok:
            try:
                candidate = safe_extract_code(task, response.text, role)
            except Exception as exc:
                extraction_error = f"{type(exc).__name__}: {exc}"
        else:
            extraction_error = response.error or response.error_code
        holder.update(
            response=response,
            physical=physical,
            candidate=candidate,
            extraction_error=extraction_error,
        )
        loop.ledger.record(
            loop_id=loop.loop_id,
            event="custom",
            action="model_spawned_loop_completed",
            problem_id=task.problem_id,
            call_role=role,
            provider=response.provider or PROVIDER,
            model=response.model or MODEL,
            response_ok=response.ok,
            candidate_sha256=(candidate.code_sha256 if candidate else ""),
            extraction_error=extraction_error,
            physical_calls=physical,
        )
        return StepOutcome(
            output=(f"{role}:candidate:{candidate.code_sha256[:12]}"
                    if candidate else f"{role}:failed"),
            mode="non_deterministic",
            confidence=0.9 if candidate else 0.1,
            failed=candidate is None,
            model_calls=physical,
        )

    result = spawned_loop.run(handler=handler, max_steps=2)
    response = holder["response"]
    return ModelSpawnedLoopResult(
        role=role,
        spawned_loop_id=result.loop_id,
        consumed_intelligence_refs=consumed_refs,
        consumed_candidate_refs=tuple(candidate_refs),
        prompt_sha256=prompt_sha256,
        gateway_result=response.to_dict(),
        candidate=holder["candidate"],
        extraction_error=holder["extraction_error"],
        physical_calls=holder["physical"],
        spawned_loop_intelligence=prepared.as_dict(),
    )


def _evaluate_spawned_loop(root: Loop, candidate: CodeCandidate, evaluator,
                    runtime: RuntimeImage, role: str) -> dict:
    spawned_loop = root.spawn(
        f"compile, execute, and grade {role} for problem {candidate.problem_id}",
        LoopConfig(
            framework="custom",
            custom_steps=("compile_execute_grade",),
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic",),
            power="light",
            max_depth=5,
        ))
    holder: dict = {}

    def handler(loop, step, context):
        try:
            holder["canvas"] = compile_and_run_canvas(
                candidate, evaluator, runtime, parent=loop)
            passed = upstream_passed(holder["canvas"].evaluation)
            return StepOutcome(
                output=f"upstream-evaluation:{'passed' if passed else 'failed'}",
                mode="deterministic",
                confidence=1.0 if passed else 0.2,
                failed=not passed,
            )
        except (CampaignGateError, SpawnedLoopIntelligenceGateError):
            raise
        except Exception as exc:
            holder["error"] = f"{type(exc).__name__}: {exc}"
            loop.ledger.record(
                loop_id=loop.loop_id,
                event="custom",
                action="upstream_evaluation_boundary_failed",
                error=holder["error"],
                candidate_sha256=candidate.code_sha256,
            )
            return StepOutcome(
                output="upstream-evaluation:boundary-failed",
                mode="deterministic",
                confidence=0.0,
                failed=True,
            )

    result = spawned_loop.run(handler=handler, max_steps=2)
    return {
        "role": role,
        "spawned_loop_id": result.loop_id,
        "canvas": holder["canvas"] if "canvas" in holder else None,
        "error": holder.get("error", ""),
        "stopped": result.stopped,
    }


def _root_config() -> LoopConfig:
    template = next(row for row in TEMPLATE_LIBRARY
                    if row["template_id"] == "reference_nine_step")
    admitted = config_from_template(template, power="deep", max_depth=5)
    if admitted.framework != "nine_step":
        raise CampaignGateError("reference_nine_step did not resolve")
    return LoopConfig(
        framework=admitted.framework,
        logical_kind=admitted.logical_kind,
        replay_guarantee="event_equivalent",
        allowable_modes=("non_deterministic",),
        preferred_modes=("non_deterministic",),
        delegated_modes=("deterministic", "non_deterministic"),
        power="deep",
        llm_thinking_power="max",
        max_depth=5,
        stop_condition="run_to_completion",
    )


def _task_path_verification(root: Loop, root_result, run_history: RunHistory,
                            task_calls: int, state: dict) -> dict:
    events = as_ledger_events(run_history.event_log)
    root_steps = [row.get("step") for row in events
                  if row.get("event") == "run_step"
                  and row.get("loop_id") == root.loop_id]
    expected_steps = list(root.steps())
    model_events = [row for row in events if row.get("event") in (
        "model_led", "model_invocation_failed")]
    bindings = [row for row in events
                if row.get("action") == "model_context_binding"]
    canvas_events = [row for row in events
                     if row.get("event") == "solution.loop.completed"]
    exact_attempts = [attempt for call in state.get("model_spawned_loops", [])
                      for attempt in call.gateway_result.get("attempts", [])]
    exact_model_contract = bool(exact_attempts) and all(
        attempt.get("model") == MODEL
        and attempt.get("provider") == PROVIDER
        and attempt.get("maximum_output_tokens") == MAXIMUM_OUTPUT_TOKENS
        and attempt.get("route") == ROUTE_NAME
        for attempt in exact_attempts if attempt.get("loop_id"))
    canonical_consumptions = [
        call.spawned_loop_intelligence.get("consumption", {})
        for call in state.get("model_spawned_loops", [])]
    required_model_roles = [
        state.get("calls", {}).get(role)
        for role in ("candidate_a", "candidate_b", "synthesis")]
    required = {
        "root_reference_nine_step": root_steps == expected_steps,
        "root_selected_mode_non_deterministic": all(
            row.get("mode") == "non_deterministic" for row in events
            if row.get("event") == "run_step"
            and row.get("loop_id") == root.loop_id),
        "all_four_intelligence_layers_queried": bool(
            state.get("intelligence")) and not any(
                search["unqueried"]
                for search in state["intelligence"].searches),
        "registered_code_pack_materialized": bool(state.get("intelligence"))
            and all(record_id in state["intelligence"].items
                    for record_id in planned_portfolio_ids()["candidate_a"]
                    if record_id.startswith("ds1000.code.")),
        "two_candidate_spawned_loops": all(
            role in state.get("calls", {})
            for role in ("candidate_a", "candidate_b")),
        "synthesis_spawned_loop": "synthesis" in state.get("calls", {}),
        "canonical_spawned_loop_consumption_bound": bool(canonical_consumptions)
            and all(
                row.get("mode") == "non_deterministic"
                and len(row.get("consumed_refs", [])) == 7
                and row.get("record_digest")
                for row in canonical_consumptions),
        "active_user_feedback_intelligence_consumed_by_required_models": all(
            call is not None and any(
                item.get("record_id") == USER_RECORD_ID
                for item in call.spawned_loop_intelligence.get(
                    "portfolio", {}).get("items", []))
            for call in required_model_roles),
        "candidate_portfolios_are_distinct": (
            required_model_roles[0] is not None
            and required_model_roles[1] is not None
            and set(required_model_roles[0].consumed_intelligence_refs)
            != set(required_model_roles[1].consumed_intelligence_refs)),
        "model_context_bound_per_physical_call": (
            len(bindings) == task_calls == len(model_events)),
        "exact_model_no_reduced_maximum": exact_model_contract,
        "physical_call_ceiling": task_calls <= MAXIMUM_CALLS_PER_TASK,
        "typed_canvas_compiled_and_executed": bool(canvas_events)
            and bool(state.get("evaluations")),
        "upstream_evaluator_outside_model_judgment": bool(
            state.get("evaluations")),
        "repair_only_after_failed_upstream_evaluation": (
            "repair" not in state.get("calls", {})
            or state.get("repair_trigger") == "upstream_completed_failure"),
        "starting_and_spawned_loops_closed": root.audit_closure()["closed"],
        "run_history_chain_intact": run_history.verify_chain()["intact"],
        "run_history_playback_rendered": bool(state.get("playback")),
        "run_history_report_rendered": bool(state.get("report")),
        "root_terminal": root_result.stopped == "done",
    }
    return {
        "record_type": "ds1000_full_path_verification/v1",
        "eligible": all(required.values()),
        "checks": required,
        "root_steps": root_steps,
        "expected_root_steps": expected_steps,
        "model_events": len(model_events),
        "context_bindings": len(bindings),
        "canvas_component_events": len(canvas_events),
        "closure": root.audit_closure(),
    }


def run_task(task: SolverTask, runtime: RuntimeImage, preflight: dict,
             budget: CallBudget, campaign_id: str, runs_dir: Path,
             result_dir: Path) -> dict:
    started = time.monotonic()
    source_verification = verify_pinned_source(SOURCE_DIR)
    evaluator = load_evaluator_context(SOURCE_DIR, task.problem_id)
    gateway = _gateway()
    root = Loop(
        f"solve DS-1000 problem {task.problem_id} with a model-led Practitioner",
        _root_config())
    run_id = f"{campaign_id}.problem-{task.problem_id}"
    root.enable_run_history(run_id, root_dir=str(runs_dir))
    root.ledger.record(
        loop_id=root.loop_id,
        event="custom",
        action="loop_template_selected",
        template_id="reference_nine_step",
        selected_mode="non_deterministic",
        maximum_physical_calls=MAXIMUM_CALLS_PER_TASK,
    )
    state: dict = {
        "calls": {},
        "model_spawned_loops": [],
        "evaluations": [],
        "error": "",
    }
    task_calls_before = budget.physical_population

    def root_outcome(output: str, *, confidence: float = 0.9,
                     failed: bool = False) -> StepOutcome:
        return StepOutcome(
            output=output,
            mode="non_deterministic",
            confidence=confidence,
            failed=failed,
        )

    def handler(loop, step, context):
        try:
            if step == "orient":
                loop.ledger.record(
                    loop_id=loop.loop_id,
                    event="custom",
                    action="task_oriented",
                    problem_id=task.problem_id,
                    library=task.library,
                    prompt_sha256=task.prompt_sha256,
                    source_commit=source_verification["commit"],
                )
                return root_outcome(
                    f"orient:problem-{task.problem_id}:source-frozen")

            if step == "reconcile_horizon":
                return root_outcome(
                    "reconcile:full-path-only:four-call-ceiling")

            if step == "assess_prepare":
                layers = build_layer_records(preflight)
                state["intelligence"] = retrieve_predecision_intelligence(
                    loop, layers)
                return root_outcome(
                    "assess:all-four-intelligence-layers-materialized")

            if step == "decide_next":
                selection: IntelligenceSelection = state["intelligence"]
                loop.ledger.record(
                    loop_id=loop.loop_id,
                    event="custom",
                    action="predecision_intelligence_selected",
                    selected_refs=tuple(
                        item.loop_ref for item in selection.items.values()),
                    user_feedback_intelligence_ref=selection.items[
                        USER_RECORD_ID].loop_ref,
                    canonical_spawned_loop_portfolios_pending=True,
                )
                return root_outcome(
                    "decide:canonical-portfolios-for-two-model-loops")

            if step == "how":
                return root_outcome(
                    "how:per-loop-intelligence-then-candidates-and-synthesis")

            if step == "act":
                call_a = _invoke_model_spawned_loop(
                    loop, task, evaluator, gateway, budget, "candidate_a",
                    lambda items: (
                        _candidate_prompt(task, items, "candidate_a"), ()),
                    preflight)
                state["calls"]["candidate_a"] = call_a
                state["model_spawned_loops"].append(call_a)
                call_b = _invoke_model_spawned_loop(
                    loop, task, evaluator, gateway, budget, "candidate_b",
                    lambda items: (
                        _candidate_prompt(task, items, "candidate_b"), ()),
                    preflight)
                state["calls"]["candidate_b"] = call_b
                state["model_spawned_loops"].append(call_b)
                if (set(call_a.consumed_intelligence_refs)
                        == set(call_b.consumed_intelligence_refs)):
                    raise CampaignGateError(
                        "candidate spawned Loops consumed identical portfolios")
                synthesis = _invoke_model_spawned_loop(
                    loop, task, evaluator, gateway, budget, "synthesis",
                    lambda items: _synthesis_prompt(
                        task, items, call_a, call_b),
                    preflight)
                state["calls"]["synthesis"] = synthesis
                state["model_spawned_loops"].append(synthesis)
                candidate_refs = synthesis.consumed_candidate_refs
                state["candidate_comparison"] = {
                    "record_type": "ds1000_candidate_comparison/v1",
                    "candidate_a_ref": candidate_refs[0],
                    "candidate_b_ref": candidate_refs[1],
                    "comparison_spawned_loop_id": synthesis.spawned_loop_id,
                    "synthesis_candidate_sha256": (
                        synthesis.candidate.code_sha256
                        if synthesis.candidate else ""),
                    "criteria": [
                        "public task compliance",
                        "first principles",
                        "alternate methods",
                        "missing constraints",
                        "common failures",
                        "verification",
                        "output shape",
                        "cost",
                    ],
                }
                return root_outcome(
                    "act:two-candidates-compared-and-synthesized",
                    confidence=0.9 if synthesis.candidate else 0.1,
                    failed=synthesis.candidate is None)

            if step == "verify":
                synthesis = state["calls"]["synthesis"]
                if synthesis.candidate is None:
                    return root_outcome(
                        "verify:no-synthesized-code-to-evaluate",
                        confidence=0.0,
                        failed=True)
                first_eval = _evaluate_spawned_loop(
                    loop, synthesis.candidate, evaluator, runtime, "synthesis")
                state["evaluations"].append(first_eval)
                canvas: CanvasExecution | None = first_eval["canvas"]
                if canvas is None:
                    return root_outcome(
                        "verify:evaluator-boundary-failed",
                        confidence=0.0,
                        failed=True)
                if upstream_passed(canvas.evaluation):
                    state["selected_role"] = "synthesis"
                    state["selected_candidate"] = synthesis.candidate
                    state["selected_canvas"] = canvas
                    return root_outcome("verify:upstream-passed")
                if canvas.evaluation.status != "completed":
                    return root_outcome(
                        "verify:sandbox-or-evaluator-failed-no-repair",
                        confidence=0.0,
                        failed=True)

                if not budget.repair_available(task.problem_id):
                    state["repair_skipped"] = (
                        "three packet repair calls were already allocated in "
                        "stable task-id order")
                    state["selected_role"] = "synthesis"
                    state["selected_candidate"] = synthesis.candidate
                    state["selected_canvas"] = canvas
                    loop.ledger.record(
                        loop_id=loop.loop_id,
                        event="custom",
                        action="repair_not_allocated",
                        problem_id=task.problem_id,
                        reason=state["repair_skipped"],
                        stable_task_order=True,
                    )
                    return root_outcome(
                        "verify:failed-no-packet-repair-allocation",
                        confidence=0.1,
                        failed=True)

                state["repair_trigger"] = "upstream_completed_failure"
                failure = failure_history_record(
                    task.problem_id,
                    synthesis.candidate.code_sha256,
                    canvas.evaluation.upstream_result)
                repair = _invoke_model_spawned_loop(
                    loop, task, evaluator, gateway, budget, "repair",
                    lambda items: _repair_prompt(
                        task, items, synthesis.candidate,
                        canvas.evaluation.upstream_result),
                    preflight, extra_history=(failure,))
                state["calls"]["repair"] = repair
                state["model_spawned_loops"].append(repair)
                if repair.candidate is None:
                    state["selected_role"] = "synthesis"
                    state["selected_candidate"] = synthesis.candidate
                    state["selected_canvas"] = canvas
                    return root_outcome(
                        "verify:repair-generation-failed",
                        confidence=0.0,
                        failed=True)
                repair_eval = _evaluate_spawned_loop(
                    loop, repair.candidate, evaluator, runtime, "repair")
                state["evaluations"].append(repair_eval)
                repair_canvas: CanvasExecution | None = repair_eval["canvas"]
                if repair_canvas is not None:
                    state["selected_role"] = "repair"
                    state["selected_candidate"] = repair.candidate
                    state["selected_canvas"] = repair_canvas
                    passed = upstream_passed(repair_canvas.evaluation)
                    return root_outcome(
                        f"verify:repair-{'passed' if passed else 'failed'}",
                        confidence=1.0 if passed else 0.1,
                        failed=not passed)
                state["selected_role"] = "synthesis"
                state["selected_candidate"] = synthesis.candidate
                state["selected_canvas"] = canvas
                return root_outcome(
                    "verify:repair-evaluator-boundary-failed",
                    confidence=0.0,
                    failed=True)

            if step == "integrate_commit":
                selected_canvas: CanvasExecution | None = state.get(
                    "selected_canvas")
                state["passed"] = bool(
                    selected_canvas
                    and upstream_passed(selected_canvas.evaluation))
                loop.ledger.record(
                    loop_id=loop.loop_id,
                    event="custom",
                    action="task_result_integrated",
                    problem_id=task.problem_id,
                    selected_role=state.get("selected_role", "none"),
                    selected_candidate_sha256=getattr(
                        state.get("selected_candidate"), "code_sha256", ""),
                    upstream_passed=state["passed"],
                    failures_preserved=True,
                )
                return root_outcome(
                    f"integrate:upstream-passed={state['passed']}",
                    confidence=1.0 if state["passed"] else 0.2,
                    failed=not state["passed"])

            return root_outcome(
                f"route:finish:upstream-passed={state.get('passed', False)}",
                confidence=1.0)
        except (CampaignGateError, SpawnedLoopIntelligenceGateError):
            raise
        except Exception as exc:
            state["error"] = f"{type(exc).__name__}: {exc}"
            loop.ledger.record(
                loop_id=loop.loop_id,
                event="custom",
                action="task_stage_failed",
                step=step,
                error=state["error"],
                failures_preserved=True,
            )
            return root_outcome(
                f"{step}:failed:{type(exc).__name__}",
                confidence=0.0,
                failed=True)

    root_result = root.run(handler=handler, max_steps=len(root.steps()) + 1)
    run_history = RunHistory.load(str(runs_dir), run_id)
    chain = run_history.verify_chain()
    state["playback"] = playback(run_history.event_log)
    loop_report = report_from_run(str(runs_dir), run_id).as_dict()
    selected_canvas = state.get("selected_canvas")
    rendered = render_run_report(
        run_history.event_log,
        canvas=(selected_canvas.canvas if selected_canvas else None),
        title=f"DS-1000 problem {task.problem_id} full Practitioner run")
    state["report"] = rendered
    task_calls = budget.physical_population - task_calls_before
    path = _task_path_verification(
        root, root_result, run_history, task_calls, state)

    call_rows = {key: value.as_dict()
                 for key, value in state["calls"].items()}
    evaluation_rows = []
    for row in state["evaluations"]:
        evaluation_rows.append({
            "role": row["role"],
            "spawned_loop_id": row["spawned_loop_id"],
            "error": row["error"],
            "stopped": row["stopped"],
            "canvas": row["canvas"].as_dict()
            if row["canvas"] else None,
        })
    input_tokens = sum(
        int(attempt.get("input_tokens") or 0)
        for call in call_rows.values()
        for attempt in call["gateway_result"].get("attempts", []))
    output_tokens = sum(
        int(attempt.get("output_tokens") or 0)
        for call in call_rows.values()
        for attempt in call["gateway_result"].get("attempts", []))
    accounting_complete = all(
        attempt.get("input_tokens") is not None
        and attempt.get("output_tokens") is not None
        for call in call_rows.values()
        for attempt in call["gateway_result"].get("attempts", [])
        if attempt.get("loop_id"))
    outcome = {
        "record_type": "ds1000_full_practitioner_task/v1",
        "campaign_id": campaign_id,
        "run_id": run_id,
        "problem_id": task.problem_id,
        "library": task.library,
        "selected_mode": "non_deterministic",
        "provider": PROVIDER,
        "model": MODEL,
        "maximum_output_tokens": MAXIMUM_OUTPUT_TOKENS,
        "failover": False,
        "passed": bool(state.get("passed", False)),
        "selected_role": state.get("selected_role", "none"),
        "selected_candidate_sha256": getattr(
            state.get("selected_candidate"), "code_sha256", ""),
        "physical_model_calls": task_calls,
        "packet_diagnostic_calls_before_selected_run":
            EXCLUDED_DIAGNOSTIC_PHYSICAL_CALLS,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "accounting_complete": accounting_complete,
        "money_cost_usd": None,
        "money_cost_note": "No source-backed model price was configured.",
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "source_commit": source_verification["commit"],
        "runtime": runtime.as_dict(),
        "intelligence": state["intelligence"].as_dict()
        if state.get("intelligence") else None,
        "repair_intelligence": state["repair_intelligence"].as_dict()
        if state.get("repair_intelligence") else None,
        "candidate_comparison": state.get("candidate_comparison"),
        "model_spawned_loops": call_rows,
        "evaluations": evaluation_rows,
        "error": state["error"],
        "repair_skipped": state.get("repair_skipped", ""),
        "failures_preserved": True,
        "run_history": {
            "run_id": run_id,
            "events": len(run_history.event_log),
            "chain": chain,
            "playback": state["playback"],
            "loop_report": loop_report,
        },
        "full_path": path,
    }
    task_dir = result_dir / f"problem-{task.problem_id}"
    task_dir.mkdir(parents=True, exist_ok=False)
    (task_dir / "outcome.json").write_text(
        json.dumps(outcome, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8")
    (task_dir / "playback.txt").write_text(
        "\n".join(state["playback"]) + "\n", encoding="utf-8")
    (task_dir / "loop-report.json").write_text(
        json.dumps(loop_report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8")
    (task_dir / "report.html").write_text(
        rendered["html"], encoding="utf-8")
    (task_dir / "loop-tree.mmd").write_text(
        rendered["mermaid"] + "\n", encoding="utf-8")
    return outcome


def verify_saved_preflight(preflight: dict) -> RuntimeImage:
    if preflight.get("ok") is not True \
            or preflight.get("model_generation_calls") != 0:
        raise CampaignGateError("preflight is not an all-pass zero-call record")
    verify_pinned_source(SOURCE_DIR)
    runtime = _runtime_from_preflight(preflight)
    verify_sandbox(runtime)
    capability = ollama_client.output_capability_for(MODEL)
    if capability.maximum_output_tokens != MAXIMUM_OUTPUT_TOKENS:
        raise CampaignGateError("model maximum changed after preflight")
    live = ollama_client.live_models()
    if MODEL not in live:
        raise CampaignGateError("exact model is not currently listed")
    return runtime


def run_campaign(preflight: dict) -> dict:
    for summary_path in RESULTS_DIR.glob("*/summary.json"):
        try:
            prior = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (prior.get("record_type")
                == "ds1000_full_practitioner_campaign/v1"
                and prior.get("population_id")
                == population()["population_id"]):
            raise CampaignGateError(
                f"the selected population already has a completed run at "
                f"{summary_path}; refusing a duplicate provider campaign")
    runtime = verify_saved_preflight(preflight)
    frozen = population()
    campaign_id = "ds1000-full-v1-" + datetime.now(
        timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    runs_dir = RESULTS_DIR / campaign_id / "run-histories"
    result_dir = RESULTS_DIR / campaign_id / "tasks"
    runs_dir.mkdir(parents=True, exist_ok=False)
    result_dir.mkdir(parents=True, exist_ok=False)
    budget = CallBudget()
    outcomes = []
    for frozen_task in frozen["tasks"]:
        task = load_solver_task(SOURCE_DIR, int(frozen_task["problem_id"]))
        if task.library != frozen_task["library"]:
            raise CampaignGateError(
                f"problem {task.problem_id} label changed before execution")
        outcome = run_task(
            task, runtime, preflight, budget, campaign_id,
            runs_dir, result_dir)
        outcomes.append(outcome)
        print(json.dumps({
            "record_type": "ds1000_task_progress/v1",
            "campaign_id": campaign_id,
            "problem_id": outcome["problem_id"],
            "library": outcome["library"],
            "passed": outcome["passed"],
            "full_path_eligible": outcome["full_path"]["eligible"],
            "physical_model_calls": outcome["physical_model_calls"],
            "input_tokens": outcome["input_tokens"],
            "output_tokens": outcome["output_tokens"],
            "selected_role": outcome["selected_role"],
            "evaluation_statuses": [
                {
                    "role": row["role"],
                    "status": ((row.get("canvas") or {}).get(
                        "evaluation") or {}).get("status", "boundary_failed"),
                    "passed": ((row.get("canvas") or {}).get(
                        "evaluation") or {}).get("passed", False),
                } for row in outcome["evaluations"]],
            "new_packet_calls_so_far": budget.physical_population,
            "packet_total_calls_so_far": (
                EXCLUDED_DIAGNOSTIC_PHYSICAL_CALLS
                + budget.physical_population),
        }, sort_keys=True), flush=True)

    summary = {
        "record_type": "ds1000_full_practitioner_campaign/v1",
        "campaign_id": campaign_id,
        "population_id": frozen["population_id"],
        "population_size": len(outcomes),
        "attempted": len(outcomes),
        "passed": sum(row["passed"] for row in outcomes),
        "execution_accuracy": (
            sum(row["passed"] for row in outcomes) / len(outcomes)),
        "full_path_eligible": sum(
            row["full_path"]["eligible"] for row in outcomes),
        "selected_mode": "non_deterministic",
        "provider": PROVIDER,
        "model": MODEL,
        "maximum_output_tokens": MAXIMUM_OUTPUT_TOKENS,
        "failover": False,
        "budget": budget.as_dict(),
        "excluded_diagnostic": {
            "campaign_id": EXCLUDED_DIAGNOSTIC_CAMPAIGN,
            "physical_model_calls": EXCLUDED_DIAGNOSTIC_PHYSICAL_CALLS,
            "eligible_for_selected_population": False,
            "reason": "operator interruption before the integration-ready signal",
        },
        "packet_total_physical_calls": (
            EXCLUDED_DIAGNOSTIC_PHYSICAL_CALLS
            + budget.physical_population),
        "packet_physical_call_ceiling": PACKET_PHYSICAL_CALL_CEILING,
        "input_tokens": sum(row["input_tokens"] for row in outcomes),
        "output_tokens": sum(row["output_tokens"] for row in outcomes),
        "total_tokens": sum(row["total_tokens"] for row in outcomes),
        "money_cost_usd": None,
        "money_cost_note": "No source-backed model price was configured.",
        "runtime": runtime.as_dict(),
        "source_commit": frozen["source"]["commit"],
        "tasks": [{
            "problem_id": row["problem_id"],
            "library": row["library"],
            "passed": row["passed"],
            "full_path_eligible": row["full_path"]["eligible"],
            "physical_model_calls": row["physical_model_calls"],
            "input_tokens": row["input_tokens"],
            "output_tokens": row["output_tokens"],
            "elapsed_seconds": row["elapsed_seconds"],
            "run_id": row["run_id"],
        } for row in outcomes],
        "limitations": [
            "This is a four-task public smoke population, not the full DS-1000 suite.",
            "Public prompts create high contamination risk.",
            "A smoke result does not cover broader AI, ML, experimentation, or data engineering work.",
            "Money cost remains unknown without a source-backed price for this route.",
        ],
    }
    if summary["packet_total_physical_calls"] > PACKET_PHYSICAL_CALL_CEILING:
        raise CampaignGateError("packet physical call ceiling exceeded")
    campaign_dir = RESULTS_DIR / campaign_id
    (campaign_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preflight", "run", "all"))
    args = parser.parse_args()
    if args.command in ("preflight", "all"):
        try:
            evidence = run_preflight()
        except PreflightGateError as exc:
            save_preflight(exc.evidence)
            print(json.dumps(exc.evidence, indent=2, sort_keys=True, default=str))
            return 2
        save_preflight(evidence)
        print(json.dumps(evidence, indent=2, sort_keys=True, default=str))
        if args.command == "preflight":
            return 0
    else:
        evidence = load_preflight()
    summary = run_campaign(evidence)
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
