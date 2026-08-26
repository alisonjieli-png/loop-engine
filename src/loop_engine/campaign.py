"""Capability Proving Campaign: bounded task-based proof of the engine.

A sibling Loop Engine application that plans, runs, verifies, and
learns from real tasks. It runs on the canonical Loop runtime; there
is no CampaignNode and no second engine. Every result preserves exact
versions, evidence, and failures.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CapabilityTaskDefinition:
    """One typed task the campaign may execute."""

    task_id: str
    version: str
    title: str
    task_family: str
    description: str = ""
    required_capabilities: tuple[str, ...] = ()
    input_contract: str = ""
    output_contract: str = ""
    acceptance_criteria: tuple[str, ...] = ()
    allowed_effects: tuple[str, ...] = ()
    time_budget_seconds: float = 60.0
    seed: int = 42

    def __post_init__(self) -> None:
        if not self.task_id or not self.version or not self.title:
            raise ValueError("task needs id, version, and title")
        if self.time_budget_seconds <= 0:
            raise ValueError("time budget must be positive")


@dataclass(frozen=True)
class CampaignRunManifest:
    """Exact environment facts for one campaign run."""

    run_id: str
    campaign_id: str
    task_refs: tuple[str, ...]
    repository_commit: str = ""
    environment_digest: str = ""
    started_at: str = ""

    def digest(self) -> str:
        serialized = json.dumps({
            "run_id": self.run_id, "campaign_id": self.campaign_id,
            "task_refs": list(self.task_refs),
            "repository_commit": self.repository_commit,
            "environment_digest": self.environment_digest,
        }, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TaskRunResult:
    """One task execution with exact evidence."""

    run_id: str
    task_id: str
    status: str
    metrics: dict = field(default_factory=dict)
    failures: tuple[str, ...] = ()
    elapsed_seconds: float = 0.0
    artifacts: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in ("passed", "failed", "blocked", "skipped",
                               "timed_out"):
            raise ValueError(f"unknown task status {self.status!r}")

    def to_dict(self) -> dict:
        return {"run_id": self.run_id, "task_id": self.task_id,
                "status": self.status, "metrics": self.metrics,
                "failures": list(self.failures),
                "elapsed_seconds": self.elapsed_seconds,
                "artifacts": list(self.artifacts),
                "evidence_refs": list(self.evidence_refs)}


@dataclass
class CampaignState:
    """Accumulated state for one campaign, persisted as JSONL."""

    campaign_id: str
    runs: list = field(default_factory=list)
    failures: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    def record(self, result: TaskRunResult) -> None:
        self.runs.append(result.to_dict())
        if result.status == "failed":
            self.failures.append({
                "task_id": result.task_id,
                "run_id": result.run_id,
                "failures": list(result.failures),
            })

    def to_dict(self) -> dict:
        return {"campaign_id": self.campaign_id,
                "runs": list(self.runs),
                "failures": list(self.failures),
                "notes": list(self.notes)}

    def report(self) -> dict:
        total = len(self.runs)
        passed = sum(1 for r in self.runs if r["status"] == "passed")
        failed = sum(1 for r in self.runs if r["status"] == "failed")
        blocked = sum(1 for r in self.runs if r["status"] == "blocked")
        return {"campaign_id": self.campaign_id,
                "total": total, "passed": passed, "failed": failed,
                "blocked": blocked,
                "all_passed": total > 0 and passed == total}


def run_task_through_loop(task: CapabilityTaskDefinition,
                          fn, *, manifest: CampaignRunManifest
                          ) -> TaskRunResult:
    """Execute one task function through the canonical Loop runtime.

    The task function runs inside a deterministic Practitioner Loop.
    Failures are preserved, never hidden. Elapsed time is measured at
    the Loop boundary.
    """
    from loop_engine.loop.encapsulate import as_practitioner_loop

    started = time.monotonic()
    try:
        result = as_practitioner_loop(
            f"campaign task: {task.title}",
            lambda _inputs=None: {"value": fn()})
        elapsed = time.monotonic() - started
        value = result["value"]["value"]
        status = "passed"
        metrics = value if isinstance(value, dict) else {
            "value": str(value)}
        failures = ()
    except Exception as exc:                                  # noqa: BLE001
        elapsed = time.monotonic() - started
        status = "failed"
        metrics = {}
        failures = (f"{type(exc).__name__}: {exc}",)
    if elapsed > task.time_budget_seconds:
        status = "timed_out"
        failures = failures + (f"exceeded budget "
                               f"{task.time_budget_seconds}s",)
    return TaskRunResult(run_id=manifest.run_id,
                         task_id=task.task_id,
                         status=status,
                         metrics=metrics,
                         failures=failures,
                         elapsed_seconds=round(elapsed, 3))


def self_test() -> dict:
    """Prove the campaign runs typed tasks through the canonical Loop."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    task = CapabilityTaskDefinition(
        task_id="task.constant", version="1.0.0",
        title="return a constant",
        task_family="atomic",
        required_capabilities=("loop_runtime",),
        input_contract="none", output_contract="constant")
    manifest = CampaignRunManifest(
        run_id="campaign-run-1", campaign_id="camp-1",
        task_refs=("task.constant",), repository_commit="head")

    result = run_task_through_loop(
        task, lambda: {"answer": 42}, manifest=manifest)
    check("task_runs_through_canonical_loop",
          result.status == "passed"
          and result.metrics == {"answer": 42}
          and result.run_id == "campaign-run-1")

    failing = CapabilityTaskDefinition(
        task_id="task.failing", version="1.0.0",
        title="always fails", task_family="atomic")
    failed_result = run_task_through_loop(
        failing, lambda: (_ for _ in ()).throw(RuntimeError("boom")),
        manifest=manifest)
    check("failures_are_preserved_not_hidden",
          failed_result.status == "failed"
          and any("always fails" in f for f in failed_result.failures))

    state = CampaignState(campaign_id="camp-1")
    state.record(result)
    state.record(failed_result)
    report = state.report()
    check("campaign_report_counts_all_results",
          report["total"] == 2 and report["passed"] == 1
          and report["failed"] == 1
          and report["all_passed"] is False)

    try:
        CapabilityTaskDefinition(task_id="x", version="1.0.0",
                                 title="x", task_family="atomic",
                                 time_budget_seconds=0)
        check("zero_time_budget_is_refused", False)
    except ValueError:
        check("zero_time_budget_is_refused", True)
    return {"tests": results}
