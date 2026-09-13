"""What one campaign trial cell proves, and what it lacks.

A trial is complete evidence only when its records link the task and its
source digests, the configuration applied on every model call, the
step-history checkpoints, the outcome with an intact Run History, the
physical model calls counted against the calls claimed, the delivered
artifacts, and an independent evaluation. This report names each link as
present or missing over the cell the runner wrote, so a reviewer, the
worker, or a self-improvement Loop can count a trial as verified only when
every link is there. It reads the cell and runs nothing; it never fills a
gap it finds.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

from loop_engine.core.run_history import MODEL_INVOCATION_EVENT, load_saved_run_bundle

from .task_database_campaign import TRIAL_FAILED, TRIAL_FINISHED

REPORT_RECORD_TYPE = "trial_evidence_report/v1"
REQUIRED_LINKS = ("trial_state", "task_sources", "applied_configuration", "step_history", "outcome",
                  "run_history_intact", "model_calls_accounted", "delivered_artifacts",
                  "independent_evaluation")


def _projection_rows(path):
    """Every latest record in the cell's projection, by namespace and id."""
    connection = duckdb.connect(str(path), read_only=True)
    try:
        rows = connection.execute(
            "SELECT namespace, record_id, payload FROM experiment_records r WHERE revision = "
            "(SELECT max(revision) FROM experiment_records s WHERE s.namespace = r.namespace "
            "AND s.record_id = r.record_id) ORDER BY namespace, record_id").fetchall()
    finally:
        connection.close()
    latest = {}
    for namespace, record_id, payload in rows:
        latest.setdefault(namespace, {})[record_id] = json.loads(payload)
    return latest


def trial_evidence_report(cell) -> dict:
    """The evidence links one trial cell holds, each present or missing."""
    cell = Path(cell)
    if not cell.is_dir():
        raise ValueError("a trial cell is a directory the runner wrote")
    projection = cell / "projection.duckdb"
    records = _projection_rows(projection) if projection.is_file() else {}
    state = records.get("trial", {}).get("state") or {}
    sources = records.get("task_sources", {}).get("selected") or {}
    applied = records.get("applied_configuration", {})
    steps = records.get("step_history", {})
    outcome_path = cell / "outcome.json"
    outcome = json.loads(outcome_path.read_text()) if outcome_path.is_file() else {}
    run_id = outcome.get("run_id") or ""
    history_intact, physical_calls, history_error = False, None, ""
    if run_id:
        try:
            bundle = load_saved_run_bundle(str(cell / "runs"), run_id)
            history_intact = bool(bundle.history.verify_chain().get("intact"))
            physical_calls = sum(1 for event in bundle.history.event_log
                                 if event.event_type == MODEL_INVOCATION_EVENT)
        except Exception as exc:  # the report names the failure; it never guesses the history
            history_error = type(exc).__name__
    claimed = outcome.get("model_calls")
    accounting_complete = bool(outcome.get("model_call_accounting_complete"))
    artifacts = outcome.get("artifacts") or []
    verification = outcome.get("verification") or {}
    evaluation_present = bool(verification.get("independent") or verification.get("evaluator_ref")
                              or verification.get("verdict"))
    links = {
        "trial_state": bool(state) and state.get("status") in (TRIAL_FINISHED, TRIAL_FAILED),
        "task_sources": bool(sources) and "input_digest" in sources and "source_digests" in sources,
        "applied_configuration": len(applied),
        "step_history": sum(1 for row in steps.values() if row.get("integrity", {}).get("intact")),
        "outcome": bool(outcome) and outcome.get("record_type", "").startswith("solve_outcome/"),
        "run_history_intact": history_intact,
        "model_calls_accounted": (physical_calls is not None and claimed is not None
                                  and accounting_complete and physical_calls == claimed),
        "delivered_artifacts": len(artifacts),
        "independent_evaluation": evaluation_present,
    }
    gaps = [name for name in REQUIRED_LINKS if not links[name]]
    return {"record_type": REPORT_RECORD_TYPE, "cell": str(cell), "task_id": state.get("task_id"),
            "status": state.get("status"), "engine_terminal": state.get("engine_terminal"),
            "run_id": run_id, "links": links, "gaps": gaps, "complete": not gaps,
            "physical_model_calls": physical_calls, "claimed_model_calls": claimed,
            "accounting_complete": accounting_complete, "history_error": history_error,
            "applied_configuration_calls": sorted(applied),
            "task_accepted": bool(state.get("task_accepted")),
            "campaign_acceptance": state.get("campaign_acceptance")}


def campaign_evidence_summary(root) -> dict:
    """Every trial cell under a campaign root, counted by completeness and by
    the gap that keeps it from being complete."""
    root = Path(root)
    reports = [trial_evidence_report(cell) for cell in sorted((root / "trials").glob("*/*"))
               if cell.is_dir()] if (root / "trials").is_dir() else []
    by_gap = {}
    for report in reports:
        for gap in report["gaps"]:
            by_gap[gap] = by_gap.get(gap, 0) + 1
    return {"record_type": "campaign_evidence_summary/v1", "root": str(root), "trials": len(reports),
            "complete": sum(1 for report in reports if report["complete"]),
            "finished": sum(1 for report in reports if report["status"] == TRIAL_FINISHED),
            "failed": sum(1 for report in reports if report["status"] == TRIAL_FAILED),
            "gaps": dict(sorted(by_gap.items())), "reports": reports}
