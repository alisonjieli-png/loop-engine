"""Inspect open task standardization on five different text tasks."""
from __future__ import annotations

from pathlib import Path

from loop_engine.templates.compiler import TaskCompileRequest, compile_task

from scenario_definitions import TASK_SCENARIOS


def inspect_text_tasks(tasks_dir: Path) -> tuple[dict, ...]:
    results = []
    for filename, scenario_id, mode, _expected_status in TASK_SCENARIOS:
        path = tasks_dir / filename
        compiled = compile_task(TaskCompileRequest(
            path.read_text(encoding="utf-8").strip(),
            task_id=f"example:{scenario_id}",
            source_kind="text",
            interaction_mode=mode))
        task = compiled["compiled_task"]
        results.append({
            "task": path.name,
            "scenario_id": scenario_id,
            "loop_id": compiled["loop_id"],
            "model_calls": compiled["model_calls"],
            "interaction_mode": mode.value,
            "template_candidates": [
                item["template_id"] for item in task["template_candidates"]],
            "template_selection_authority": task[
                "template_selection_authority"],
            "binding": task["binding"],
            "task_type": task["task_type"],
        })
    if len(results) != 5:
        raise RuntimeError("the example requires exactly five text tasks")
    if any(result["model_calls"] != 0 for result in results):
        raise RuntimeError("text task compilation must make zero model calls")
    if any(result["binding"] is not None
           or result["task_type"] != "unknown"
           or result["template_selection_authority"] != "model_only"
           for result in results):
        raise RuntimeError("task standardization selected semantics or a template")
    return tuple(results)


def main() -> int:
    results = inspect_text_tasks(Path(__file__).parent / "tasks")
    for result in results:
        print(
            f"{result['task']}: open | "
            f"interaction={result['interaction_mode']} | "
            f"candidate_templates={len(result['template_candidates'])} | "
            f"model_calls={result['model_calls']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
