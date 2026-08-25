#!/usr/bin/env python3
"""Recheck the saved OpenML-CC18 campaign without provider calls or fitting."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPOSITORY_ROOT = HERE.parents[1]
for candidate in (str(REPOSITORY_ROOT), str(REPOSITORY_ROOT / "src")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from benchmarks.openml_cc18.openml_runtime import (  # noqa: E402
    FoldPrediction,
    FoldPredictionArtifact,
    evaluate_accuracy,
    load_task_bundle,
)
from benchmarks.openml_cc18.run import load_track_contract  # noqa: E402
from loop_engine.static_architecture.run_history import RunHistory  # noqa: E402


EXPECTED_STEPS = [
    "orient",
    "reconcile_horizon",
    "assess_prepare",
    "decide_next",
    "how",
    "act",
    "verify",
    "integrate_commit",
    "route",
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def prediction_artifact(body: dict) -> FoldPredictionArtifact:
    folds = []
    for raw in body["folds"]:
        folds.append(
            FoldPrediction(
                repeat=int(raw["repeat"]),
                fold=int(raw["fold"]),
                test_row_ids=tuple(raw["test_row_ids"]),
                y_true=tuple(raw["y_true"]),
                y_pred=tuple(raw["y_pred"]),
                fit_seconds=float(raw["fit_seconds"]),
                predict_seconds=float(raw["predict_seconds"]),
            )
        )
    return FoldPredictionArtifact(
        record_type=body["record_type"],
        task_id=int(body["task_id"]),
        algorithm=body["algorithm"],
        folds=tuple(folds),
        executor_version=body["executor_version"],
    )


def main() -> int:
    pointer = load_json(HERE / "verified-result.json")
    campaign_result_path = REPOSITORY_ROOT / pointer["campaign_result"]
    campaign = load_json(campaign_result_path)
    campaign_root = campaign_result_path.parent
    track = load_track_contract()
    task_specs = {int(item["task_id"]): item for item in track["tasks"]}
    call_rows = [
        json.loads(line)
        for line in (campaign_root / "model-calls.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert len(call_rows) == campaign["provider_usage"]["physical_calls"] == 10
    assert sum(bool(row["token_accounting_complete"]) for row in call_rows) == 9
    assert sum(not row["token_accounting_complete"] for row in call_rows) == 1
    assert all(
        row["provider"] == "ollama_cloud"
        and row["model"] == "deepseek-v4-flash:0731"
        and row["maximum_output_tokens"] == 65536
        and len(row["consumed_intelligence_refs"]) == 7
        and row["intelligence_consumption_digest"]
        and not row["cross_provider_failover"]
        for row in call_rows
    )
    unknown = [row for row in call_rows if not row["token_accounting_complete"]]
    assert len(unknown) == 1
    assert unknown[0]["task_id"] == 3560
    assert unknown[0]["call_role"] == "synthesis_selection"
    assert unknown[0]["error_code"] == "provider_failed"

    task_checks = []
    for task_id in (11, 10101, 3560):
        result = load_json(campaign_root / "tasks" / f"task-{task_id}" / "task-result.json")
        spec = task_specs[task_id]
        bundle = load_task_bundle(
            spec,
            dataset_path=HERE / "data" / f"task-{task_id}-dataset.arff",
            split_path=HERE / "data" / f"task-{task_id}-splits.arff",
        )
        saved_predictions = prediction_artifact(
            load_json(campaign_root / "tasks" / f"task-{task_id}" / "predictions.json")
        )
        recomputed = evaluate_accuracy(saved_predictions, bundle)
        assert math.isclose(
            recomputed["mean_accuracy"],
            result["evaluation"]["mean_accuracy"],
            rel_tol=0.0,
            abs_tol=1e-15,
        )
        # The saved v1 task used `accepted` to mean only that a valid score
        # existed. It did not declare a quality threshold.
        assert result["accepted"]
        assert recomputed["artifact_valid"] and recomputed["score_valid"]
        assert recomputed["quality_acceptance_rule"] == "not_defined"
        assert recomputed["quality_accepted"] is None
        assert result["root_result"]["stage_order"] == EXPECTED_STEPS
        assert result["root_result"]["steps_run"] == 9
        assert result["official_folds_executed"] == 10
        assert result["canvas_compiled"] and result["canvas_executed"]
        run_id = result["run_history"]["run_id"]
        run_history = RunHistory.load(str(campaign_root / "run-histories"), run_id)
        assert run_history.verify_chain()["intact"]
        assert sum(
            event.event_type == "model_invocation" for event in run_history.event_log
        ) == result["physical_calls"]
        solution_kinds = {
            str(event.detail.get("_ledger_event")) for event in run_history.event_log
        }
        assert {
            "solution.canvas.updated",
            "solution.loop.started",
            "solution.loop.completed",
            "solution_finalized",
        } <= solution_kinds
        intelligence = load_json(
            campaign_root / "tasks" / f"task-{task_id}" / "intelligence-portfolios.json"
        )
        assert not intelligence["payload_bodies_exported"]
        assert intelligence["consumption"]["consuming_loop_count"] == result[
            "intelligence_portfolios"
        ]["consumption_count"]
        assert all(
            len(refs) == 7
            for refs in intelligence["consumption"]["by_consuming_loop"].values()
        )
        task_checks.append(
            {
                "task_id": task_id,
                "algorithm": result["selected_algorithm"],
                "mean_accuracy": recomputed["mean_accuracy"],
                "physical_calls": result["physical_calls"],
                "run_history_events": len(run_history.event_log),
                "run_history_chain_intact": True,
            }
        )

    assert campaign["population_denominator"] == 3
    assert campaign["tasks_accepted"] == 3
    assert campaign["physical_calls_including_excluded_attempts"] == 12
    assert campaign["packet_physical_call_ceiling"] == 14
    assert campaign["packet_physical_call_ceiling_respected"]
    assert campaign["provider_cost_state"] == "unknown"
    output = {
        "record_type": "openml_cc18_saved_campaign_verification/v2",
        "campaign_id": campaign["campaign_id"],
        "verified": True,
        "model_calls_made_by_verification": 0,
        "fold_training_made_by_verification": False,
        "selected_physical_calls": len(call_rows),
        "packet_physical_calls": campaign["physical_calls_including_excluded_attempts"],
        "packet_physical_call_ceiling": campaign["packet_physical_call_ceiling"],
        "known_packet_tokens_subtotal": campaign["packet_provider_usage"][
            "known_total_tokens_subtotal"
        ],
        "packet_calls_with_unknown_token_usage": campaign["packet_provider_usage"][
            "calls_with_unknown_token_usage"
        ],
        "provider_cost_state": "unknown",
        "tasks_artifact_valid": 3,
        "tasks_score_valid": 3,
        "quality_acceptance_rule": "not_defined",
        "tasks_quality_accepted": None,
        "legacy_state_note": (
            "The saved campaign field tasks_accepted meant score-valid only; "
            "no quality acceptance threshold was declared."
        ),
        "tasks": task_checks,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
