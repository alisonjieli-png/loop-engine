"""Deterministically regrade recorded outputs after extractor conformance repair.

This never calls a model. It preserves the immutable selected run, replays its
recorded outputs through a full reference-nine-step Practitioner, applies the
upstream-compatible whitespace-preserving extractor, executes the compiled
Canvas in the same locked sandbox, and writes a separate correction run.
"""
from __future__ import annotations

import json
from pathlib import Path

from loop_engine.code_nodes.loop_report import report_from_run
from loop_engine.code_nodes.run_playback import playback, render_run_report
from loop_engine.loop.loop_templates import TEMPLATE_LIBRARY, config_from_template
from loop_engine.loop.recursive_loop import Loop, LoopConfig, StepOutcome
from loop_engine.static_architecture.run_history import RunHistory, as_ledger_events

from code_intelligence import (
    CanvasExecution,
    compile_and_run_canvas,
    load_evaluator_context,
    load_solver_task,
    safe_extract_code,
    upstream_passed,
)
from prepare import SOURCE_DIR
from runtime import RuntimeImage, verify_sandbox


BENCHMARK_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BENCHMARK_DIR / "results"
PARENT_CAMPAIGN = "ds1000-full-v1-20260825T150857Z"
CORRECTION_ID = PARENT_CAMPAIGN + "-extractor-whitespace-correction-v1"


def _runtime(row: dict) -> RuntimeImage:
    return RuntimeImage(
        row["tag"], row["image_id"], row["platform"],
        row["base_image_digest"], row["requirements_sha256"],
        row["source_execution_sha256"])


def _root_config() -> LoopConfig:
    template = next(row for row in TEMPLATE_LIBRARY
                    if row["template_id"] == "reference_nine_step")
    admitted = config_from_template(template, power="deep", max_depth=5)
    return LoopConfig(
        framework=admitted.framework,
        logical_kind=admitted.logical_kind,
        replay_guarantee="event_equivalent",
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",),
        power="deep",
        max_depth=5,
    )


def _replay_recorded_spawned_loops(root: Loop, original: dict) -> list[dict]:
    rows = []
    for role, call in original["model_spawned_loops"].items():
        spawned_loop = root.spawn(
            f"serve recorded {role} output without model execution",
            LoopConfig(
                framework="custom",
                custom_steps=("serve_recorded_output",),
                allowable_modes=("deterministic",),
                preferred_modes=("deterministic",),
                delegated_modes=("deterministic",),
                power="light",
                max_depth=5,
            ))
        holder = {}

        def handler(loop, step, context, role=role, call=call):
            holder["raw_response"] = (
                (call.get("candidate") or {}).get("raw_response")
                or call["gateway_result"].get("text", ""))
            consumption = (call.get("spawned_loop_intelligence") or {}).get(
                "consumption", {})
            loop.ledger.record(
                loop_id=loop.loop_id,
                event="custom",
                action="recorded_model_output_replayed",
                parent_run_id=original["run_id"],
                original_spawned_loop_id=call["spawned_loop_id"],
                call_role=role,
                original_provider=original["provider"],
                original_model=original["model"],
                consumed_intelligence_refs=tuple(
                    consumption.get("consumed_refs", [])),
                intelligence_consumption_record=consumption.get(
                    "record_digest", ""),
                physical_model_calls=0,
            )
            return StepOutcome(
                output=f"recorded-output:{role}",
                mode="deterministic",
                confidence=1.0,
            )

        result = spawned_loop.run(handler=handler, max_steps=2)
        rows.append({
            "role": role,
            "spawned_loop_id": result.loop_id,
            "raw_response_sha256": __import__("hashlib").sha256(
                holder["raw_response"].encode()).hexdigest(),
            "physical_model_calls": 0,
        })
    return rows


def regrade_task(original: dict, runtime: RuntimeImage,
                 runs_dir: Path, tasks_dir: Path) -> dict:
    problem_id = int(original["problem_id"])
    task = load_solver_task(SOURCE_DIR, problem_id)
    evaluator = load_evaluator_context(SOURCE_DIR, problem_id)
    selected_role = original["selected_role"]
    selected_call = original["model_spawned_loops"][selected_role]
    raw_response = selected_call["candidate"]["raw_response"]
    corrected_candidate = safe_extract_code(
        task, raw_response, f"{selected_role}_whitespace_correction")
    original_candidate = selected_call["candidate"]

    run_id = f"{CORRECTION_ID}.problem-{problem_id}"
    root = Loop(
        f"regrade recorded DS-1000 problem {problem_id} output",
        _root_config())
    root.enable_run_history(run_id, root_dir=str(runs_dir))
    root.ledger.record(
        loop_id=root.loop_id,
        event="custom",
        action="derived_evaluation_correction_started",
        parent_run_id=original["run_id"],
        parent_campaign_id=PARENT_CAMPAIGN,
        correction="preserve leading whitespace during safe code extraction",
        physical_model_calls=0,
    )
    state: dict = {}

    def handler(loop, step, context):
        if step == "orient":
            return StepOutcome(
                "orient:immutable-parent-output-loaded",
                mode="deterministic", confidence=1.0)
        if step == "reconcile_horizon":
            return StepOutcome(
                "reconcile:evaluator-adapter-conformance-only",
                mode="deterministic", confidence=1.0)
        if step == "assess_prepare":
            return StepOutcome(
                "assess:no-new-model-call-no-new-solver-information",
                mode="deterministic", confidence=1.0)
        if step == "decide_next":
            return StepOutcome(
                f"decide:regrade-original-selected-role-{selected_role}",
                mode="deterministic", confidence=1.0)
        if step == "how":
            return StepOutcome(
                "how:upstream-compatible-whitespace-preserving-extraction",
                mode="deterministic", confidence=1.0)
        if step == "act":
            state["recorded_spawned_loops"] = _replay_recorded_spawned_loops(
                loop, original)
            state["candidate"] = corrected_candidate
            return StepOutcome(
                f"act:corrected-candidate:{corrected_candidate.code_sha256}",
                mode="deterministic", confidence=1.0)
        if step == "verify":
            evaluator_spawned_loop = loop.spawn(
                f"compile and independently evaluate corrected problem {problem_id}",
                LoopConfig(
                    framework="custom",
                    custom_steps=("compile_execute_grade",),
                    allowable_modes=("deterministic",),
                    preferred_modes=("deterministic",),
                    delegated_modes=("deterministic",),
                    power="light",
                    max_depth=5,
                ))
            holder = {}

            def evaluator_handler(spawned_loop, spawned_loop_step, spawned_loop_context):
                holder["canvas"] = compile_and_run_canvas(
                    corrected_candidate, evaluator, runtime, parent=spawned_loop)
                passed = upstream_passed(holder["canvas"].evaluation)
                return StepOutcome(
                    f"upstream-evaluation:{'passed' if passed else 'failed'}",
                    mode="deterministic",
                    confidence=1.0 if passed else 0.2,
                    failed=not passed,
                )

            evaluator_result = evaluator_spawned_loop.run(
                handler=evaluator_handler, max_steps=2)
            state["canvas"] = holder["canvas"]
            state["evaluator_spawned_loop_id"] = evaluator_result.loop_id
            passed = upstream_passed(state["canvas"].evaluation)
            return StepOutcome(
                f"verify:corrected-upstream-passed={passed}",
                mode="deterministic",
                confidence=1.0 if passed else 0.2,
                failed=not passed,
            )
        if step == "integrate_commit":
            state["passed"] = upstream_passed(state["canvas"].evaluation)
            loop.ledger.record(
                loop_id=loop.loop_id,
                event="custom",
                action="derived_evaluation_correction_integrated",
                problem_id=problem_id,
                parent_run_id=original["run_id"],
                original_candidate_sha256=original_candidate["code_sha256"],
                corrected_candidate_sha256=corrected_candidate.code_sha256,
                corrected_upstream_passed=state["passed"],
                physical_model_calls=0,
            )
            return StepOutcome(
                f"integrate:corrected-passed={state['passed']}",
                mode="deterministic",
                confidence=1.0 if state["passed"] else 0.2,
                failed=not state["passed"])
        return StepOutcome(
            "route:finish-derived-correction",
            mode="deterministic", confidence=1.0)

    root_result = root.run(handler=handler, max_steps=len(root.steps()) + 1)
    saved = RunHistory.load(str(runs_dir), run_id)
    chain = saved.verify_chain()
    events = as_ledger_events(saved.event_log)
    root_steps = [row.get("step") for row in events
                  if row.get("event") == "run_step"
                  and row.get("loop_id") == root.loop_id]
    model_events = [row for row in events if row.get("event") in (
        "model_led", "model_invocation_failed", "model_invocation")]
    transcript = playback(saved.event_log)
    loop_report = report_from_run(str(runs_dir), run_id).as_dict()
    rendered = render_run_report(
        saved.event_log,
        canvas=state["canvas"].canvas,
        title=f"DS-1000 problem {problem_id} deterministic regrade")
    checks = {
        "reference_nine_step": root_steps == list(root.steps()),
        "recorded_model_spawned_loops_replayed": (
            len(state["recorded_spawned_loops"])
            == len(original["model_spawned_loops"])),
        "physical_model_calls_zero": not model_events,
        "same_recorded_raw_response": (
            raw_response == original_candidate["raw_response"]),
        "leading_whitespace_preserved": (
            not raw_response.startswith(" ")
            or corrected_candidate.code.startswith(" ")),
        "typed_canvas_executed": bool(state["canvas"].plan_digest),
        "upstream_evaluator_completed": (
            state["canvas"].evaluation.status == "completed"),
        "run_history_chain_intact": chain["intact"],
        "playback_rendered": bool(transcript),
        "report_rendered": bool(loop_report),
        "starting_and_spawned_loops_closed": root.audit_closure()["closed"],
        "root_terminal": root_result.stopped == "done",
    }
    outcome = {
        "record_type": "ds1000_recorded_output_regrade/v1",
        "correction_id": CORRECTION_ID,
        "parent_campaign_id": PARENT_CAMPAIGN,
        "parent_run_id": original["run_id"],
        "run_id": run_id,
        "problem_id": problem_id,
        "library": task.library,
        "selected_role": selected_role,
        "original_reported_passed": original["passed"],
        "original_candidate_sha256": original_candidate["code_sha256"],
        "corrected_candidate_sha256": corrected_candidate.code_sha256,
        "corrected_passed": state["passed"],
        "corrected_upstream_result":
            state["canvas"].evaluation.upstream_result,
        "correction": (
            "Preserve leading completion whitespace to match the pinned "
            "upstream postprocess behavior."),
        "physical_model_calls": 0,
        "provider_outputs_reused": True,
        "runtime": runtime.as_dict(),
        "canvas": state["canvas"].as_dict(),
        "recorded_spawned_loops": state["recorded_spawned_loops"],
        "run_history": {
            "chain": chain,
            "events": len(saved.event_log),
            "playback": transcript,
            "loop_report": loop_report,
        },
        "full_regrade_path": {
            "eligible": all(checks.values()),
            "checks": checks,
            "root_steps": root_steps,
        },
    }
    task_dir = tasks_dir / f"problem-{problem_id}"
    task_dir.mkdir(parents=True, exist_ok=False)
    (task_dir / "outcome.json").write_text(
        json.dumps(outcome, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8")
    (task_dir / "playback.txt").write_text(
        "\n".join(transcript) + "\n", encoding="utf-8")
    (task_dir / "loop-report.json").write_text(
        json.dumps(loop_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    (task_dir / "report.html").write_text(
        rendered["html"], encoding="utf-8")
    return outcome


def main() -> int:
    parent_dir = RESULTS_DIR / PARENT_CAMPAIGN
    parent_summary = json.loads(
        (parent_dir / "summary.json").read_text(encoding="utf-8"))
    runtime = _runtime(parent_summary["runtime"])
    verify_sandbox(runtime)
    correction_dir = RESULTS_DIR / CORRECTION_ID
    if correction_dir.exists():
        raise FileExistsError(
            f"immutable correction already exists at {correction_dir}")
    runs_dir = correction_dir / "run-histories"
    tasks_dir = correction_dir / "tasks"
    runs_dir.mkdir(parents=True, exist_ok=False)
    tasks_dir.mkdir(parents=True, exist_ok=False)
    outcomes = []
    for task_row in parent_summary["tasks"]:
        original = json.loads((
            parent_dir / "tasks" / f"problem-{task_row['problem_id']}"
            / "outcome.json").read_text(encoding="utf-8"))
        outcomes.append(regrade_task(
            original, runtime, runs_dir, tasks_dir))
    summary = {
        "record_type": "ds1000_recorded_output_regrade_campaign/v1",
        "correction_id": CORRECTION_ID,
        "parent_campaign_id": PARENT_CAMPAIGN,
        "parent_result_preserved": True,
        "parent_reported_execution_accuracy":
            parent_summary["execution_accuracy"],
        "parent_score_status": (
            "invalidated by nonconforming leading-whitespace extraction"),
        "corrected_passed": sum(row["corrected_passed"] for row in outcomes),
        "population_size": len(outcomes),
        "corrected_execution_accuracy": (
            sum(row["corrected_passed"] for row in outcomes) / len(outcomes)),
        "full_regrade_path_eligible": sum(
            row["full_regrade_path"]["eligible"] for row in outcomes),
        "physical_model_calls": 0,
        "packet_total_physical_calls_unchanged":
            parent_summary["packet_total_physical_calls"],
        "runtime": runtime.as_dict(),
        "tasks": [{
            "problem_id": row["problem_id"],
            "library": row["library"],
            "original_reported_passed": row["original_reported_passed"],
            "corrected_passed": row["corrected_passed"],
            "selected_role": row["selected_role"],
            "full_regrade_path_eligible":
                row["full_regrade_path"]["eligible"],
        } for row in outcomes],
        "interpretation": (
            "This correction reuses the exact recorded provider responses. It "
            "changes only deterministic extraction and upstream evaluation; "
            "it is not a new model run."),
    }
    (correction_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
