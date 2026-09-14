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
import os
from dataclasses import dataclass
from collections import Counter
from pathlib import Path
from typing import Callable

import duckdb

from loop_engine.core.run_history import MODEL_INVOCATION_EVENT, RunHistory, SavedRunBundle, load_saved_run_bundle
from loop_engine.core.adaptive_practitioner_source import _open_source
from loop_engine.core.product_outcome_store import matches_bound_product_outcome
from .systematic_records import canonical

from .task_database_campaign import TRIAL_FAILED, TRIAL_FINISHED

REPORT_RECORD_TYPE = "trial_evidence_report/v3"
APPLIED_STATUSES = ("applied_in_memory", "unchanged")
ARTIFACT_DIGEST_FIELDS = ("sha256", "digest", "content_digest")
#: Links the report re-verifies from disk; the rest are taken as recorded.
REVERIFIED_LINKS = ("applied_configuration", "step_history", "run_history_intact",
                    "model_calls_accounted", "delivered_artifacts")
REQUIRED_LINKS = ("trial_state", "task_sources", "applied_configuration", "step_history", "outcome",
                  "run_history_intact", "model_calls_accounted", "delivered_artifacts",
                  "independent_evaluation", "every_invocation_configured",
                  "every_invocation_checkpointed", "source_snapshot_verified")


@dataclass(frozen=True)
class TrialEvidenceServices:
    """An independently supplied, read-only evaluator-evidence resolver.

    The resolver must verify the qualified evaluator and exact subject against
    the host's existing authoritative records. A verdict label is not a
    resolver. Missing service means missing qualification, never acceptance.
    """

    resolve_evaluation: Callable[[dict, SavedRunBundle], bool] | None = None

    def __post_init__(self):
        if self.resolve_evaluation is not None and not callable(self.resolve_evaluation):
            raise TypeError("evaluation evidence resolution requires a callable host service")


def _projection_rows(path):
    """Every latest record in the cell's projection, by namespace and id;
    None when the projection cannot be read now (a running worker holds
    the writer lock on the cell it is executing), which the report says
    rather than reading as an empty cell."""
    try:
        connection = duckdb.connect(str(path), read_only=True)
    except duckdb.Error:
        return None
    try:
        rows = connection.execute(
            "SELECT namespace, record_id, payload, digest FROM experiment_records r WHERE revision = "
            "(SELECT max(revision) FROM experiment_records s WHERE s.namespace = r.namespace "
            "AND s.record_id = r.record_id) ORDER BY namespace, record_id").fetchall()
    finally:
        connection.close()
    latest = {}
    for namespace, record_id, payload, expected in rows:
        value = json.loads(payload)
        if hashlib.sha256(canonical(value).encode()).hexdigest() != expected:
            return None
        latest.setdefault(namespace, {})[record_id] = value
    return latest


def _step_history_verified(row, checkpoint_cache=None) -> bool:
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
            if type(revision) is not int or revision < 0:
                return False
            key = str(saved.absolute())
            cache = checkpoint_cache if checkpoint_cache is not None else {}
            if key not in cache:
                cache[key] = RunHistory.verified_checkpoints(str(saved.parent), saved.name)
            return cache[key].get(revision) is True
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
    if not target.is_file() or target.is_symlink():
        return False
    expected_values = []
    for field in ARTIFACT_DIGEST_FIELDS:
        recorded = entry.get(field)
        if isinstance(recorded, str) and recorded:
            expected = recorded.removeprefix('sha256:')
            if len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
                return False
            expected_values.append(expected)
    if not expected_values or len(set(expected_values)) != 1:
        return False
    try:
        with os.fdopen(_open_source(target.absolute()), 'rb') as source:
            before = os.fstat(source.fileno())
            digest = hashlib.sha256()
            for block in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(block)
            after = os.fstat(source.fileno())
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            return False
        if 'byte_count' in entry and (type(entry['byte_count']) is not int
                                     or entry['byte_count'] != after.st_size):
            return False
        return digest.hexdigest() == expected_values[0]
    except OSError:
        return False


def _configuration_applied(row, configuration) -> bool:
    """The setter reported the value applied (or already so) and the row's
    configuration is the trial's own, so no call ran under another."""
    report = row.get("setting_report") or {}
    if report.get("status") not in APPLIED_STATUSES:
        return False
    return configuration is None or row.get("configuration") == configuration


def trial_evidence_report(cell, *, services=TrialEvidenceServices()) -> dict:
    """The evidence links one trial cell holds, each present or missing."""
    cell = Path(cell)
    if not isinstance(services, TrialEvidenceServices):
        raise TypeError("trial evidence services must be typed")
    if not cell.is_dir():
        raise ValueError("a trial cell is a directory the runner wrote")
    projection = cell / "projection.duckdb"
    records = _projection_rows(projection) if projection.is_file() else {}
    projection_readable = records is not None
    records = records or {}
    state = records.get("trial", {}).get("state") or {}
    status_export = cell / "status.json"
    if not state and status_export.is_file():
        # The exported status stands in while the projection is locked; it
        # is the writer's own export, and the report says so.
        try:
            state = json.loads(status_export.read_text())
        except ValueError:
            state = {}
    sources = records.get("task_sources", {}).get("selected") or {}
    applied = records.get("applied_configuration", {})
    effective = records.get("effective_configuration", {})
    steps = records.get("step_history", {})
    configuration = state.get("configuration") if isinstance(state.get("configuration"), dict) else None
    outcome_path = cell / "outcome.json"
    outcome = json.loads(outcome_path.read_text()) if outcome_path.is_file() else {}
    run_id = outcome.get("run_id") or ""
    history_intact, physical_calls, history_error = False, None, ""
    bundle = None
    outcome_bound = False
    expected_calls = Counter()
    if run_id:
        try:
            bundle = load_saved_run_bundle(str(cell / "runs"), run_id)
            history_intact = bool(bundle.history.verify_chain().get("intact"))
            outcome_bound = matches_bound_product_outcome(outcome, bundle)
            if not outcome_bound:
                history_error = 'outcome_binding_mismatch'
            model_events = [event for event in bundle.history.event_log
                            if event.event_type == MODEL_INVOCATION_EVENT]
            physical_calls = sum(event.detail['provider_physical_requests']
                if type(event.detail.get('provider_physical_requests')) is int else 1
                for event in model_events)
            expected_calls = Counter((event.loop_id, event.detail.get('semantic_call_id', ''))
                                     for event in model_events)
        except Exception as exc:  # the report names the failure; it never guesses the history
            history_error = type(exc).__name__
    claimed = outcome.get("model_calls")
    accounting_complete = bool(outcome.get("model_call_accounting_complete"))
    artifacts = outcome.get("artifacts") or []
    verification = outcome.get("verification") or {}
    evaluation_present = bool(verification.get("independent") or verification.get("evaluator_ref")
                              or verification.get("verdict"))
    evaluation_qualified = False
    if services.resolve_evaluation is not None and bundle is not None and history_intact and outcome_bound:
        try:
            evaluation_qualified = services.resolve_evaluation(outcome, bundle) is True
        except Exception:
            evaluation_qualified = False
    configured_calls, checkpointed_calls = Counter(), Counter()
    checkpoint_cache = {}
    verified_steps = {operation: _step_history_verified(row, checkpoint_cache)
                      for operation, row in steps.items()}
    for operation, observed in effective.items():
        attempts = Counter((attempt.get('loop_id', ''), attempt.get('semantic_call_id', ''))
                           for attempt in observed.get('provider_attempts', ()) if attempt.get('loop_id'))
        if operation in applied and _configuration_applied(applied[operation], configuration):
            configured_calls.update(attempts)
        if verified_steps.get(operation):
            checkpointed_calls.update(attempts)
    source_checks = records.get('source_verification', {})
    before, after = source_checks.get('before', {}), source_checks.get('after', {})
    source_verified = (before.get('state') == after.get('state') == 'verified'
                       and bool(before.get('source_snapshot_digest'))
                       and before.get('source_snapshot_digest') == after.get('source_snapshot_digest')
                       == sources.get('source_snapshot_digest'))
    applied_verified = sum(1 for row in applied.values() if _configuration_applied(row, configuration))
    steps_recorded = sum(1 for row in steps.values() if (row.get("integrity") or {}).get("intact"))
    steps_verified = sum(verified_steps.values())
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
        "outcome": outcome_bound and bool(outcome) and outcome.get("record_type", "").startswith("solve_outcome/"),
        "run_history_intact": history_intact,
        "model_calls_accounted": (physical_calls is not None and claimed is not None
                                  and accounting_complete and physical_calls == claimed),
        # Only artifacts that exist, with their recorded digest when one
        # was recorded, count as delivered.
        "delivered_artifacts": artifacts_verified,
        "independent_evaluation": evaluation_qualified,
        "every_invocation_configured": history_intact and configured_calls == expected_calls,
        "every_invocation_checkpointed": history_intact and checkpointed_calls == expected_calls,
        "source_snapshot_verified": source_verified,
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
            "projection_readable": projection_readable,
            "reverified_links": list(REVERIFIED_LINKS),
            "recorded": recorded, "disagreements": disagreements,
            "physical_model_calls": physical_calls, "claimed_model_calls": claimed,
            "accounting_complete": accounting_complete, "history_error": history_error,
            "outcome_bound_to_history": outcome_bound,
            "evaluation_record_present": evaluation_present,
            "evaluation_qualification": "verified_by_host_resolver" if evaluation_qualified else "unqualified",
            "expected_invocation_occurrences": sum(expected_calls.values()),
            "configured_invocation_occurrences": sum(configured_calls.values()),
            "checkpointed_invocation_occurrences": sum(checkpointed_calls.values()),
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
            "projection_locked": sum(1 for report in reports if not report["projection_readable"]),
            "finished": sum(1 for report in reports if report["status"] == TRIAL_FINISHED),
            "failed": sum(1 for report in reports if report["status"] == TRIAL_FAILED),
            "gaps": dict(sorted(by_gap.items())), "reports": reports}
