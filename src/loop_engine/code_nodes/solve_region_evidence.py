"""Region evidence for one solve: what earlier runs in this task region say.

Architectural role: the solve path's pre-check projection. Before the first
model call, saved runs in the task's region are turned into region statistics,
an advisory shortcut decision, and a tuning decision that picks the context
budget variant from recorded prompt experiments. The result is one passive
mapping the Practitioner receives as an advisory context block and the
outcome records under ``intelligence.region_evidence``. Nothing here selects a
solution or skips the Practitioner; it makes the region's history visible and
chooses one run setting from evidence with a seeded exploration rate.

Owns:
    - region_evidence_for_solve(): the projection and the tuned budget.

Does not own: the statistics (core.task_region_statistics), the experiment
records (core.prompt_experiment), the selector (core.self_tuning), or the
solve path that applies the result (code_nodes.solve_runtime).
"""
from __future__ import annotations

import hashlib

from ..core.prompt_experiment import (prompt_experiments_from_adaptive_result,
                                      task_region_ref)
from ..core.self_tuning import choose_context_budget
from ..core.task_region_statistics import (build_region_statistics,
                                           load_adaptive_results,
                                           recommend_shortcut)


def _region_of(item: dict) -> str:
    task = item.get("original_task")
    text = (task.get("original_input") or task.get("text") or ""
            if isinstance(task, dict) else str(task or ""))
    return task_region_ref(str(text))


def region_evidence_for_solve(request) -> tuple:
    """Return (evidence mapping, tuned ContextBudgetPolicy or None).

    ``request`` is a ``SolveRequest``. The budget is tuned only when the
    caller did not pin one; the evidence mapping is always returned so a run
    with no history still records that nothing was known about its region.
    """
    text = request.intake.original_input
    region = task_region_ref(text)
    evidence: dict = {"region_ref": region, "advisory": True,
                      "region_statistics": None, "shortcut_decision": None,
                      "tuning_decision": None}
    if not request.runs_dir:
        return evidence, None
    results = load_adaptive_results(request.runs_dir)
    statistics = next((item for item in build_region_statistics(
        request.runs_dir) if item.region_ref == region), None)
    if statistics is not None:
        unsolved = [str(item.get("run_id")) for item in results
                    if _region_of(item) == region and not item.get("solved")]
        evidence["region_statistics"] = statistics.to_dict()
        evidence["shortcut_decision"] = recommend_shortcut(
            statistics, unsolved_run_ids=unsolved).to_dict()
    records = []
    for item in results:
        try:
            records.extend(prompt_experiments_from_adaptive_result(item))
        except ValueError:
            continue
    tuned = None
    if request.context_budget is None:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
        tuned, decision = choose_context_budget(
            records, region_ref=region, salt=f"{len(results)}:{digest}")
        evidence["tuning_decision"] = decision.to_dict()
    return evidence, tuned


def self_test() -> dict:
    """Prove the no-history case and the tuned-budget case offline."""
    import json
    import os
    import tempfile
    from types import SimpleNamespace

    def request(runs_dir: str, text: str, budget=None):
        return SimpleNamespace(
            intake=SimpleNamespace(original_input=text), runs_dir=runs_dir,
            context_budget=budget)

    empty_evidence, empty_budget = region_evidence_for_solve(
        request("", "Predict the target column"))
    with tempfile.TemporaryDirectory(prefix="loop-engine-region-") as root:
        for index in range(3):
            os.makedirs(os.path.join(root, f"r{index}"))
            with open(os.path.join(root, f"r{index}",
                                   "adaptive-result.json"), "w") as handle:
                json.dump({"run_id": f"r{index}", "solved": index < 2,
                           "status": "VERIFIED_WORKING" if index < 2
                           else "VERIFICATION_FAILED",
                           "original_task": {"original_input":
                                             "Predict the target column"},
                           "passes": 2, "model_calls": 3,
                           "model_usage": [{"ok": True, "input_tokens": 100,
                                            "output_tokens": 5}] * 3,
                           "context_snapshots": [
                               {"step": "act", "prompt_assembly": {
                                   "assembly_id": "a", "prompt_digest": "b" * 64,
                                   "estimated_tokens": 90},
                                "total_estimated_tokens": 90}] * 3,
                           "verification": [{"verdict": "accept"}] * 2},
                          handle)
        evidence, tuned = region_evidence_for_solve(
            request(root, "predict the TARGET column"))
        pinned_evidence, pinned = region_evidence_for_solve(
            request(root, "predict the TARGET column", budget=object()))
    stats = evidence["region_statistics"] or {}
    shortcut = evidence["shortcut_decision"] or {}
    tuning = evidence["tuning_decision"] or {}
    tests = [{
        "test": "no_runs_directory_yields_advisory_evidence_with_nothing_known",
        "passed": (empty_evidence["region_statistics"] is None
                   and empty_evidence["tuning_decision"] is None
                   and empty_budget is None and empty_evidence["advisory"]),
        "detail": empty_evidence["region_ref"],
    }, {
        "test": "saved_runs_project_into_statistics_and_an_advisory_shortcut",
        "passed": (stats.get("runs") == 3 and stats.get("solved_runs") == 2
                   and shortcut.get("taken") is False
                   and shortcut.get("negative_evidence") == ["r2"]),
        "detail": str(shortcut.get("reason", ""))[:100],
    }, {
        "test": "budget_is_tuned_only_when_the_caller_did_not_pin_one",
        "passed": (tuned is not None and tuning.get("setting") == "context_budget"
                   and pinned is None
                   and pinned_evidence["tuning_decision"] is None),
        "detail": str(tuning.get("chosen_variant_key")),
    }]
    return {"module": "code_nodes.solve_region_evidence",
            "passed": all(item["passed"] for item in tests), "tests": tests}
