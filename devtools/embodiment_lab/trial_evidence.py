"""What one campaign trial cell proves, and what it lacks.

A trial is complete evidence only when its records link the task and its
source digests, the configuration applied on every model call, the
step-history checkpoints, the outcome with an intact Run History, the
physical model calls counted against the calls claimed, the delivered
artifacts, and an independent evaluation. This report names each link as
present or missing over the cell the runner wrote, so a reviewer, the
worker, or a self-improvement Loop can count a trial as verified only when
every link is there. Where a link can be re-verified from what is on disk
(a saved step history's chain, a delivered artifact's existence and
digest, an applied configuration's agreement with the trial's own) the
report re-verifies it rather than trusting the writer's flag, and says
which links were re-verified and which are taken as recorded. It reads the
cell and runs nothing; it never fills a gap it finds.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb

from loop_engine.core.run_history import MODEL_INVOCATION_EVENT, RunHistory, load_saved_run_bundle

from .task_database_campaign import TRIAL_FAILED, TRIAL_FINISHED

REPORT_RECORD_TYPE = "trial_evidence_report/v2"
APPLIED_STATUSES = ("applied_in_memory", "unchanged")
ARTIFACT_DIGEST_FIELDS = ("sha256", "digest", "content_digest")
#: Links the report re-verifies from disk; the rest are taken as recorded.
REVERIFIED_LINKS = ("applied_configuration", "step_history", "run_history_intact",
                    "model_calls_accounted", "delivered_artifacts")
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


def _step_history_verified(row) -> bool:
    """The saved step history re-loads and its chain verifies intact; the
    writer's own ``integrity`` flag is not enough. A row that names a
    checkpoint in an append-only store is verified at that revision; a
    row that names a full saved copy is verified as saved."""
    location = row.get("history")
    if not isinstance(location, str) or not location:
        return False
    saved = Path(location)
    if not saved.is_dir():
        return False
    try:
        if (saved / "checkpoints.jsonl").is_file():
            revision = row.get("revision")
            history = RunHistory.load_checkpoint(
                str(saved.parent), saved.name,
                revision if type(revision) is int else None)
        else:
            history = RunHistory.load(str(saved.parent), saved.name)
        return bool(history.verify_chain().get("intact"))
    except Exception:  # a broken or foreign directory is a missing link, not a crash
        return False


def _artifact_verified(entry) -> bool:
    """The artifact exists on disk and, when the record carries a digest,
    the bytes still match it."""
    if not isinstance(entry, dict):
        return False
    path = entry.get("path") or entry.get("artifact_ref")
    if not isinstance(path, str) or not path:
        return False
    target = Path(path)
    if not target.is_file():
        return False
    for field in ARTIFACT_DIGEST_FIELDS:
        recorded = entry.get(field)
        if isinstance(recorded, str) and recorded:
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            expected = recorded.split(":")[-1]
            return digest == expected
    return True


def _configuration_applied(row, configuration) -> bool:
    """The setter reported the value applied (or already so) and the row's
    configuration is the trial's own, so no call ran under another."""
    report = row.get("setting_report") or {}
    if report.get("status") not in APPLIED_STATUSES:
        return False
    return configuration is None or row.get("configuration") == configuration


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
    configuration = state.get("configuration") if isinstance(state.get("configuration"), dict) else None
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
    applied_verified = sum(1 for row in applied.values() if _configuration_applied(row, configuration))
    steps_recorded = sum(1 for row in steps.values() if (row.get("integrity") or {}).get("intact"))
    steps_verified = sum(1 for row in steps.values() if _step_history_verified(row))
    artifacts_verified = sum(1 for entry in artifacts if _artifact_verified(entry))
    links = {
        "trial_state": bool(state) and state.get("status") in (TRIAL_FINISHED, TRIAL_FAILED),
        "task_sources": bool(sources) and "input_digest" in sources and "source_digests" in sources,
        # Only calls whose configuration was applied and is the trial's own
        # count; a call that ran under a refused or different configuration
        # is not evidence for this cell.
        "applied_configuration": applied_verified,
        # Only step histories whose saved chain re-verifies count.
        "step_history": steps_verified,
        "outcome": bool(outcome) and outcome.get("record_type", "").startswith("solve_outcome/"),
        "run_history_intact": history_intact,
        "model_calls_accounted": (physical_calls is not None and claimed is not None
                                  and accounting_complete and physical_calls == claimed),
        # Only artifacts that exist, with their recorded digest when one
        # was recorded, count as delivered.
        "delivered_artifacts": artifacts_verified,
        "independent_evaluation": evaluation_present,
    }
    gaps = [name for name in REQUIRED_LINKS if not links[name]]
    # What the writer recorded beside what this report could confirm, so a
    # reader sees where the two disagree instead of one number.
    recorded = {"applied_configuration": len(applied), "step_history": steps_recorded,
                "delivered_artifacts": len(artifacts)}
    disagreements = {name: {"recorded": recorded[name], "verified": links[name]}
                     for name in recorded if recorded[name] != links[name]}
    return {"record_type": REPORT_RECORD_TYPE, "cell": str(cell), "task_id": state.get("task_id"),
            "status": state.get("status"), "engine_terminal": state.get("engine_terminal"),
            "run_id": run_id, "links": links, "gaps": gaps, "complete": not gaps,
            "reverified_links": list(REVERIFIED_LINKS),
            "recorded": recorded, "disagreements": disagreements,
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
    return {"record_type": "campaign_evidence_summary/v2", "root": str(root), "trials": len(reports),
            "complete": sum(1 for report in reports if report["complete"]),
            "with_disagreements": sum(1 for report in reports if report["disagreements"]),
            "finished": sum(1 for report in reports if report["status"] == TRIAL_FINISHED),
            "failed": sum(1 for report in reports if report["status"] == TRIAL_FAILED),
            "gaps": dict(sorted(by_gap.items())), "reports": reports}
