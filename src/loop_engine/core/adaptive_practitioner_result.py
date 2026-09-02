"""Terminal result and Run History projection for adaptive Practitioner runs.

This module serializes accepted, failed, interrupted, and exact deterministic
outcomes. It does not decide task semantics, call a model, or execute tools.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from ..loop.recursive_loop import Loop, StepOutcome
from .adaptive_practitioner_records import (
    ADAPTIVE_PRACTITIONER_RECORD_TYPE, AdaptivePractitionerError,
    AdaptiveRunServices)
from .adaptive_practitioner_source import saved_source_inspections


def loop_details(events: list[dict]) -> list[dict]:
    """Project Loop identities, steps, and terminal reasons."""
    terminal = {item.get("loop_id"): item for item in events
                if item.get("event") == "terminal"}
    steps: dict[str, list[dict]] = {}
    for item in events:
        if item.get("event") == "run_step":
            steps.setdefault(str(item.get("loop_id")), []).append({
                "step": item.get("step"), "mode": item.get("mode"),
                "output": item.get("output"),
                "accepted": item.get("accepted"),
            })
    return [{
        "loop_id": item.get("loop_id"), "goal": item.get("goal"),
        "role": item.get("role"), "profile_id": item.get("profile_id"),
        "relationship": item.get("relationship_kind"),
        "input_roles": list(item.get("input_roles") or ()),
        "output_roles": list(item.get("output_roles") or ()),
        "loop_condition": item.get("loop_condition"),
        "exit_condition": item.get("exit_condition"),
        "steps": steps.get(str(item.get("loop_id")), []),
        "terminal_reason": (terminal.get(item.get("loop_id")) or {}).get(
            "reason", ""),
    } for item in events if item.get("event") == "init"]


def save_adaptive_result(history: dict, output: dict) -> None:
    """Write the internal adaptive result only when persistence is enabled."""
    if not history.get("path"):
        return
    result_path = Path(history["path"]) / "adaptive-result.json"
    result_path.write_text(json.dumps(
        output, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
    output["result_path"] = str(result_path)


def safe_model_usage(services: AdaptiveRunServices) -> list[dict]:
    """Remove model text while preserving exact provider accounting."""
    if services.model_session is None:
        return []
    rows = []
    for result in services.model_session.results:
        value = result.to_dict()
        value.pop("text", None)
        rows.append(value)
    return rows


def finish_deterministic_attempt(
        owner: Loop, services: AdaptiveRunServices,
        history_builder: Callable[[], dict]) -> dict:
    """Terminate and save an explicitly selected exact reuse run."""
    trace = services.deterministic_attempt
    if trace is None:
        raise AdaptivePractitionerError(
            "deterministic attempt trace is missing")
    resolved = trace.status == "COMPLETED"
    result_value = dict(trace.outputs).get("result") if resolved else None

    def handler(_active, step, _context):
        if step == "act":
            return StepOutcome(
                "deterministic:executed" if resolved
                else "deterministic:no_verified_capability",
                "deterministic", 1.0 if resolved else 0.0,
                failed=not resolved)
        if step == "verify":
            return StepOutcome(
                "verify:passed" if resolved else "verify:not_satisfied",
                "deterministic", 1.0 if resolved else 0.0,
                failed=not resolved)
        return StepOutcome(
            f"{step}:trace_preserved", "deterministic",
            1.0 if resolved else 0.5)

    owner.run(handler=handler, max_steps=len(owner.steps()) + 1)
    history = history_builder()
    output = {
        "record_type": ADAPTIVE_PRACTITIONER_RECORD_TYPE,
        "run_id": services.run_id,
        "status": "VERIFIED_WORKING" if resolved else "NOT_YET_PROVEN",
        "solved": resolved,
        "failure_code": "" if resolved else trace.status,
        "result": result_value, "original_task": services.request.task,
        "task_feedback": [item.to_dict()
                          for item in services.request.feedback],
        "mode": services.request.mode,
        "deterministic_attempt": trace.to_dict(), "passes": 1,
        "final_route": "stop_success" if resolved else "stop_unprofitable",
        "failures": [] if resolved else list(trace.errors),
        "model_calls": 0, "loop_details": loop_details(owner.ledger.events),
        "run_history": history,
    }
    save_adaptive_result(history, output)
    return output


def failed_adaptive_output(
        owner: Loop, services: AdaptiveRunServices,
        failure_code: str, failure: str,
        history_builder: Callable[[], dict]) -> dict:
    """Persist one failed or interrupted run through canonical history."""
    history = history_builder()
    output = {
        "record_type": ADAPTIVE_PRACTITIONER_RECORD_TYPE,
        "run_id": services.run_id, "status": "NOT_YET_PROVEN",
        "solved": False, "failure_code": failure_code,
        "failure": failure[:1000], "original_task": services.request.task,
        "mode": services.request.mode,
        "task_feedback": [item.to_dict()
                          for item in services.request.feedback],
        "deterministic_attempt": services.deterministic_attempt.to_dict(),
        "model_calls": services.model_session.calls_used,
        "model_usage": safe_model_usage(services),
        "option_selection": services.selection_tally.to_dict(),
        "orientations": [item.to_dict()
                         for item in services.orientation_by_version.values()],
        "action_decisions": services.action_history,
        "context_snapshots": services.context_snapshots,
        "candidate_solution_canvases": services.candidate_canvases,
        "selected_solution_canvas": services.plan_details.get(
            "active_canvas", {}),
        "web_search_candidates": services.web_search_results,
        "web_evidence": services.web_results,
        "source_inspections": saved_source_inspections(
            services.source_inspections),
        "project_attempts": services.project_attempts,
        "verification": services.verification_records,
        "supervision": services.supervision_findings,
        "recovery_directives": services.recovery_directives,
        "generated_file_checkpoints":
            services.generated_file_checkpoint_summaries(),
        "loop_details": loop_details(owner.ledger.events),
        "run_history": history,
    }
    save_adaptive_result(history, output)
    return output


def self_test() -> dict:
    """Prove the Loop detail projection preserves steps and termination."""
    value = loop_details([
        {"event": "init", "loop_id": "loop1", "goal": "test",
         "role": "practitioner", "profile_id": "practitioner.solver",
         "relationship_kind": "starting", "input_roles": (),
         "output_roles": ("result",), "loop_condition": "steps_remain",
         "exit_condition": "steps_complete"},
        {"event": "run_step", "loop_id": "loop1", "step": "act",
         "mode": "deterministic", "output": "done", "accepted": True},
        {"event": "terminal", "loop_id": "loop1", "reason": "done"},
    ])
    passed = (len(value) == 1 and value[0]["steps"][0]["step"] == "act"
              and value[0]["terminal_reason"] == "done")
    tests = [{"test": "adaptive_result_preserves_loop_detail",
              "passed": passed, "detail": str(value)}]
    return {"record_type": "adaptive_result_projection_test/v1",
            "tests": tests, "passed": int(passed), "total": 1,
            "all_passed": passed}


__all__ = (
    "failed_adaptive_output", "finish_deterministic_attempt",
    "loop_details", "safe_model_usage",
    "save_adaptive_result",
)
