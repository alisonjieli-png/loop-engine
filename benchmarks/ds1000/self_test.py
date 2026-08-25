"""Fail-closed preflight for the four-task DS-1000 campaign."""
from __future__ import annotations

import json
import os
from pathlib import Path

from loop_engine.code_nodes import loop_report, run_playback, solution_canvas
from loop_engine.loop import loop_templates
from loop_engine.loop.recursive_loop import Loop, LoopConfig, StepOutcome
from loop_engine.static_architecture import (
    run_history,
    intelligence_layers,
    intelligence_portfolio,
    model_gateway,
    ollama_client,
)
from loop_engine.static_architecture.model_gateway import ModelGatewayConfig

from code_intelligence import (
    CodeCandidate,
    compile_and_run_canvas,
    load_evaluator_context,
    load_reference_for_admission,
    load_solver_task,
    safe_extract_code,
    upstream_passed,
    validate_code_intelligence_pack,
    verify_pinned_source,
)
from canonical_portfolio import prepare_spawned_loop_intelligence
from intelligence import USER_RECORD_ID
from intelligence import preflight_selection
from prepare import SOURCE_DIR, population, prepare_source, row_by_id
from runtime import RuntimeImage, build_runtime, verify_sandbox


BENCHMARK_DIR = Path(__file__).resolve().parent
PREFLIGHT_PATH = BENCHMARK_DIR / ".cache" / "preflight.json"


class PreflightGateError(RuntimeError):
    """At least one required source, engine, provider, or sandbox gate failed."""

    def __init__(self, message: str, evidence: dict):
        super().__init__(message)
        self.evidence = evidence


def _engine_gates() -> list[dict]:
    checks = (
        ("reference_loop_template", loop_templates.self_test),
        ("solution_canvas", solution_canvas.self_test),
        ("model_gateway", model_gateway.self_test),
        ("run_history", run_history.self_test),
        ("intelligence_layers", intelligence_layers.self_test),
        ("intelligence_portfolio", intelligence_portfolio.self_test),
        ("run_playback", run_playback.self_test),
        ("loop_report", loop_report.self_test),
    )
    results = []
    for name, function in checks:
        try:
            detail = function()
            passed = bool(detail.get("all_passed"))
            error = "" if passed else "one or more module checks failed"
        except BaseException as exc:
            detail = {}
            passed = False
            error = f"{type(exc).__name__}: {exc}"
        results.append({
            "name": name,
            "passed": passed,
            "error": error,
            "detail": detail,
        })
    return results


def _canvas_admission(candidate: CodeCandidate, runtime: RuntimeImage) -> dict:
    evaluator = load_evaluator_context(SOURCE_DIR, candidate.problem_id)
    root = Loop(
        f"admit DS-1000 Canvas for problem {candidate.problem_id}",
        LoopConfig(
            framework="custom",
            custom_steps=("compile_execute_grade",),
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic",),
            power="light",
            max_depth=4,
        ))
    holder = {}

    def handler(loop, step, context):
        holder["canvas"] = compile_and_run_canvas(
            candidate, evaluator, runtime, parent=loop)
        return StepOutcome(
            output="canvas:executed:upstream-graded",
            mode="deterministic",
            confidence=1.0,
        )

    result = root.run(handler=handler, max_steps=2)
    canvas = holder["canvas"]
    return {
        "problem_id": candidate.problem_id,
        "library": candidate.library,
        "candidate_sha256": candidate.code_sha256,
        "passed": upstream_passed(canvas.evaluation),
        "upstream_result": canvas.evaluation.upstream_result,
        "evaluation_status": canvas.evaluation.status,
        "canvas_plan_digest": canvas.plan_digest,
        "root_stopped": result.stopped,
        "closure": root.audit_closure(),
    }


def run_preflight() -> dict:
    evidence = {
        "record_type": "ds1000_full_run_preflight/v1",
        "ok": False,
        "model_generation_calls": 0,
    }
    try:
        evidence["source"] = prepare_source()
        runtime = build_runtime()
        evidence["runtime"] = runtime.as_dict()
        evidence["sandbox"] = verify_sandbox(runtime)
        evidence["code_intelligence"] = validate_code_intelligence_pack()

        task_checks = []
        for frozen in population()["tasks"]:
            problem_id = int(frozen["problem_id"])
            task = load_solver_task(SOURCE_DIR, problem_id)
            hidden = row_by_id(SOURCE_DIR, problem_id)
            task_view = task.as_dict()
            hidden_fields_absent = (
                "reference_code" not in task_view
                and "code_context" not in task_view
                and str(hidden["reference_code"]) not in task.prompt
                and str(hidden["code_context"]) not in task.prompt
            )
            if not hidden_fields_absent:
                raise PreflightGateError(
                    f"solver task {problem_id} exposes hidden evaluator data",
                    evidence)
            task_checks.append({
                "problem_id": problem_id,
                "library": task.library,
                "prompt_sha256": task.prompt_sha256,
                "hidden_fields_absent": True,
            })
        evidence["solver_task_boundary"] = task_checks

        extraction_task = load_solver_task(SOURCE_DIR, 72)
        extraction = safe_extract_code(
            extraction_task,
            "```python\nresult = value\n```",
            "admission_non_executing_fixture")
        indented_extraction = safe_extract_code(
            extraction_task,
            "    return value",
            "admission_leading_whitespace_fixture")
        evidence["safe_extractor"] = {
            "passed": (
                extraction.code.strip() == "result = value"
                and indented_extraction.code.startswith("    ")),
            "candidate_sha256": extraction.code_sha256,
            "strategy": extraction.extraction_strategy,
            "executed": False,
            "leading_whitespace_preserved":
                indented_extraction.code.startswith("    "),
        }
        if (extraction.code.strip() != "result = value"
                or not indented_extraction.code.startswith("    ")):
            raise PreflightGateError("safe extractor fixture failed", evidence)

        evidence["engine_gates"] = _engine_gates()
        failed_engine = [row["name"] for row in evidence["engine_gates"]
                         if not row["passed"]]
        if failed_engine:
            raise PreflightGateError(
                f"Loop Engine gates failed: {failed_engine}", evidence)

        reference_checks = []
        for frozen in population()["tasks"]:
            candidate = load_reference_for_admission(
                SOURCE_DIR, int(frozen["problem_id"]))
            check = _canvas_admission(candidate, runtime)
            reference_checks.append(check)
            if not check["passed"] or not check["closure"]["closed"]:
                raise PreflightGateError(
                    f"reference self-check failed for {candidate.problem_id}",
                    evidence)
        evidence["reference_self_checks"] = reference_checks

        task = load_solver_task(SOURCE_DIR, 72)
        bad_code = "raise RuntimeError('intentional negative evaluator check')"
        negative = CodeCandidate(
            task.problem_id,
            task.library,
            "admission_negative_not_solver_output",
            "",
            bad_code,
            __import__("hashlib").sha256(bad_code.encode()).hexdigest(),
            "negative_fixture",
        )
        negative_check = _canvas_admission(negative, runtime)
        evidence["negative_evaluator_check"] = negative_check
        if negative_check["passed"]:
            raise PreflightGateError(
                "upstream evaluator accepted the intentional negative", evidence)

        key_present = bool(os.environ.get("OLLAMA_API_KEY"))
        live_models = ollama_client.live_models() if key_present else []
        capability = ollama_client.output_capability_for(
            "deepseek-v4-flash:0731")
        config = ModelGatewayConfig(
            route_names=("cloud.default",),
            allowed_models=("deepseek-v4-flash:0731",),
            allowed_localities=("cloud",),
            allow_failover=False,
            max_route_attempts=1,
            max_output_tokens=65536,
            timeout_seconds=900,
            max_total_tokens=None,
            thinking_power="max",
        )
        evidence["provider_gate"] = {
            "credential_present": key_present,
            "exact_model": "deepseek-v4-flash:0731",
            "exact_model_listed": "deepseek-v4-flash:0731" in live_models,
            "maximum_output_tokens": capability.maximum_output_tokens,
            "maximum_output_source": capability.source,
            "failover": config.allow_failover,
            "maximum_route_attempts": config.max_route_attempts,
            "model_generation_calls": 0,
        }
        if (not key_present
                or "deepseek-v4-flash:0731" not in live_models
                or capability.maximum_output_tokens != 65536
                or config.allow_failover
                or config.max_route_attempts != 1):
            raise PreflightGateError("exact Ollama Cloud gate failed", evidence)

        evidence["intelligence"] = preflight_selection(evidence)
        selected_ids = set(evidence["intelligence"]["selection"]["items"])
        required_code_ids = {
            row["record_id"]
            for row in evidence["code_intelligence"]["records"]
        }
        required_layers = set(evidence["intelligence"]["selection"]
                              ["queried_layers"])
        if not required_code_ids <= selected_ids or required_layers != {
                "context_intelligence", "code_intelligence",
                "runtime_history_solution_intelligence", "user_feedback_intelligence"}:
            raise PreflightGateError(
                "intelligence search or materialization gate failed", evidence)

        portfolio_root = Loop(
            "preflight canonical non-deterministic spawned_loop consumption",
            LoopConfig(
                framework="custom",
                custom_steps=("preflight",),
                allowable_modes=("non_deterministic",),
                preferred_modes=("non_deterministic",),
                delegated_modes=("deterministic", "non_deterministic"),
                power="light",
                llm_thinking_power="max",
                max_depth=5,
            ))
        canonical_rows = []
        for role in ("candidate_a", "candidate_b", "synthesis"):
            spawned_loop = portfolio_root.spawn(
                f"preflight {role} intelligence consumption",
                LoopConfig(
                    framework="custom",
                    custom_steps=("consume",),
                    allowable_modes=("non_deterministic",),
                    preferred_modes=("non_deterministic",),
                    delegated_modes=("deterministic",),
                    power="light",
                    llm_thinking_power="max",
                    max_depth=5,
                ))
            prepared = prepare_spawned_loop_intelligence(
                load_solver_task(SOURCE_DIR, 72), spawned_loop, evidence, role)
            spawned_loop.cancel("zero-model canonical portfolio preflight")
            canonical_rows.append({
                "role": role,
                **prepared.as_dict(),
            })
        portfolio_root.cancel("zero-model canonical portfolio preflight")
        a_refs = set(canonical_rows[0]["consumption"]["consumed_refs"])
        b_refs = set(canonical_rows[1]["consumption"]["consumed_refs"])
        canonical_ok = (
            a_refs != b_refs
            and all(row["consumption"]["mode"] == "non_deterministic"
                    and len(row["consumption"]["consumed_refs"]) == 7
                    and row["consumption"]["record_digest"]
                    and any(item["record_id"] == USER_RECORD_ID
                            for item in row["portfolio"]["items"])
                    for row in canonical_rows)
        )
        evidence["canonical_spawned_loop_intelligence"] = {
            "ok": canonical_ok,
            "model_generation_calls": 0,
            "spawned_loops": canonical_rows,
        }
        if not canonical_ok:
            raise PreflightGateError(
                "canonical spawned_loop intelligence integration failed", evidence)

        evidence["call_plan"] = {
            "tasks": 4,
            "candidate_spawned_loops_per_task": 2,
            "synthesis_spawned_loops_per_task": 1,
            "maximum_repair_spawned_loops_per_task": 1,
            "expected_physical_calls_without_repairs": 12,
            "maximum_physical_calls_per_task": 4,
            "maximum_new_physical_calls_population": 15,
            "maximum_repairs_population": 3,
            "excluded_diagnostic_physical_calls": 1,
            "packet_physical_call_ceiling": 16,
            "maximum_output_tokens_each_call": 65536,
            "failover": False,
        }
        evidence["ok"] = True
        return evidence
    except PreflightGateError:
        raise
    except BaseException as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
        raise PreflightGateError(evidence["error"], evidence) from exc


def save_preflight(evidence: dict) -> Path:
    PREFLIGHT_PATH.parent.mkdir(parents=True, exist_ok=True)
    PREFLIGHT_PATH.write_text(
        json.dumps(evidence, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8")
    return PREFLIGHT_PATH


def load_preflight() -> dict:
    evidence = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    if evidence.get("ok") is not True \
            or evidence.get("model_generation_calls") != 0:
        raise PreflightGateError(
            "saved preflight is not an all-pass zero-generation record",
            evidence)
    return evidence
