"""Compile five text-only tasks in autonomous interaction mode."""
from __future__ import annotations

from pathlib import Path

from loop_engine.templates.compiler import TaskCompileRequest, compile_task

from scenario_definitions import TASK_SCENARIOS


def compile_text_tasks(tasks_dir: Path) -> tuple[dict, ...]:
    results = []
    for filename, scenario_id, mode, expected_status in TASK_SCENARIOS:
        path = tasks_dir / filename
        compiled = compile_task(TaskCompileRequest(
            path.read_text(encoding="utf-8").strip(),
            task_id=f"example:{scenario_id}",
            source_kind="text",
            interaction_mode=mode))
        binding = compiled["compiled_task"]["binding"]
        status = (
            "abstain_required" if binding["requires_abstention"] else
            "needs_clarification" if binding["requires_clarification"] else
            "ready")
        if status != expected_status:
            raise RuntimeError(
                f"{path.name} expected {expected_status!r}, got {status!r}")
        results.append({
            "task": path.name,
            "scenario_id": scenario_id,
            "loop_id": compiled["loop_id"],
            "model_calls": compiled["model_calls"],
            "interaction_mode": mode.value,
            "template_id": binding["template_id"],
            "binding_mode": binding["binding_mode"],
            "status": status,
            "delegated_requirements": binding["delegated_requirements"],
        })
    if len(results) != 5:
        raise RuntimeError("the example requires exactly five text tasks")
    if any(result["model_calls"] != 0 for result in results):
        raise RuntimeError("text task compilation must make zero model calls")
    observed = {result["task"]: result["status"] for result in results}
    expected = {item[0]: item[3] for item in TASK_SCENARIOS}
    if observed != expected:
        raise RuntimeError(
            f"text task disposition changed: {observed!r}")
    return tuple(results)


def main() -> int:
    results = compile_text_tasks(Path(__file__).parent / "tasks")
    for result in results:
        print(
            f"{result['task']}: {result['status']} | "
            f"interaction={result['interaction_mode']} | "
            f"template={result['template_id'] or 'open'} | "
            f"model_calls={result['model_calls']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
