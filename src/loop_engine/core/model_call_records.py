"""Learnable model call records: the join a training pass reads, and its export.

A run publishes one trace event when a model step starts, one when the
answer is admitted, and others when the transport fails, the answer is
rejected, or an admitted answer deviates from its suggested output. The run
result says whether the task was solved and what the independent verifier
found. Each of those is useful alone; a training pass needs them joined per
call and labeled by the verified outcome, with the run split so that no
run's calls straddle the training and holdout sides, and with every string
scanned for secrets before it leaves.

This module owns that join and that export. It never reads prompt text: the
packet artifact holds it, and a record cites the digest. A derived record
that carries the synthetic marker is excluded from the export, and an
unverified outcome is excluded by default, so the pass learns from what an
independent process accepted, not from what a producer reported.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .reuse_evidence import SYNTHETIC_MARKER

RECORD_TYPE = "model_call_learning_record/v1"
STARTED = "model.step.started"
COMPLETED = "model.step.completed"
TRANSPORT_FAILED = "model.step.transport_failed"
REJECTED = "model.step.response_rejected"
DEVIATION = "model.step.suggested_output_deviation"
OUTCOME_LABELS = ("verified", "failed", "unknown")
VERIFIED, FAILED, UNKNOWN = OUTCOME_LABELS
_FORBIDDEN_PATHS = Path(__file__).resolve().parents[1] / "forbidden_paths.json"


class ModelCallRecordsError(ValueError):
    """A record, a policy, or an export input is invalid."""


def default_secret_patterns() -> tuple[str, ...]:
    """The repository's secret patterns, the same ones the conformance scan uses."""
    try:
        return tuple(json.loads(_FORBIDDEN_PATHS.read_text(encoding="utf-8"))["secret_patterns"])
    except (OSError, ValueError, KeyError) as exc:
        raise ModelCallRecordsError(f"cannot read the secret patterns: {exc}") from exc


@dataclass(frozen=True)
class ModelCallLearningRecord:
    """One model call as a training pass sees it: digests, labels, no text."""

    run_id: str
    step: str
    model_call_number: int
    pass_number: int = 0
    contract_id: str = ""
    prompt_digest: str = ""
    prompt_bytes: int = 0
    output_schema_digest: str = ""
    output_digest: str = ""
    output_bytes: "int | None" = None
    admitted_strategy: str = ""
    completed: bool = False
    transport_failures: int = 0
    rejections: int = 0
    deviation_problems: tuple[str, ...] = ()
    objective: str = ""
    outcome_label: str = UNKNOWN
    markers: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.run_id or not self.step:
            raise ModelCallRecordsError("a learning record needs its run and step")
        if type(self.model_call_number) is not int or self.model_call_number < 1:
            raise ModelCallRecordsError("model_call_number counts from 1")
        if self.outcome_label not in OUTCOME_LABELS:
            raise ModelCallRecordsError(f"outcome label must be one of {OUTCOME_LABELS}")

    @property
    def record_id(self) -> str:
        return f"{self.run_id}:{self.step}:{self.model_call_number}"

    def to_dict(self) -> dict:
        return {"record_type": RECORD_TYPE, "record_id": self.record_id, **{
            name: (list(value) if isinstance(value, tuple) else value)
            for name, value in ((name, getattr(self, name)) for name in self.__dataclass_fields__)}}


def outcome_label(result: "dict | None") -> str:
    """The label a run's result earns: verified only by an independent pass."""
    if not isinstance(result, dict):
        return UNKNOWN
    reports = [item for item in result.get("independent_verification_records") or ()
               if isinstance(item, dict)]
    passed = any(item.get("status") == "passed" for item in reports)
    failed = any(item.get("status") == "failed" for item in reports)
    if result.get("solved") is True and passed:
        return VERIFIED
    if result.get("solved") is False or failed:
        return FAILED
    return UNKNOWN


def learning_records(events, result: "dict | None" = None) -> list[ModelCallLearningRecord]:
    """Join a run's progress events into one record per started model call."""
    label = outcome_label(result)
    started: dict[tuple, dict] = {}
    order: list[tuple] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        kind = event.get("event_type")
        key = (str(event.get("step", "")), event.get("format_attempt"), event.get("transport_attempt"))
        if kind == STARTED:
            record = {"run_id": str(event.get("run_id") or ""), "step": key[0],
                      "model_call_number": int(event.get("model_call_number") or 0),
                      "pass_number": int(event.get("pass_number") or 0),
                      "contract_id": str(event.get("output_contract_id") or ""),
                      "prompt_digest": str(event.get("prompt_digest") or ""),
                      "prompt_bytes": int(event.get("prompt_bytes") or 0),
                      "output_schema_digest": str(event.get("output_schema_digest") or ""),
                      "objective": str(event.get("objective") or ""),
                      "transport_failures": 0, "rejections": 0, "deviation_problems": ()}
            started[key] = record
            order.append(key)
        elif key in started:
            record = started[key]
            if kind == COMPLETED:
                record.update(completed=True, output_digest=str(event.get("output_digest") or ""),
                              output_bytes=event.get("output_bytes"),
                              admitted_strategy=str(event.get("admitted_strategy") or ""))
            elif kind == TRANSPORT_FAILED:
                record["transport_failures"] += 1
            elif kind == REJECTED:
                record["rejections"] += 1
            elif kind == DEVIATION:
                record["deviation_problems"] = tuple(str(item) for item in event.get("problems") or ())
    records = []
    for key in order:
        record = started[key]
        if record["model_call_number"] < 1 or not record["run_id"]:
            continue
        records.append(ModelCallLearningRecord(outcome_label=label, **record))
    return records


@dataclass(frozen=True)
class TrainingExportPolicy:
    """How records become training rows: split by run, exclude, and scan."""

    holdout_fraction: float = 0.2
    salt: str = ""
    include_unverified: bool = False
    include_incomplete: bool = False
    secret_patterns: tuple[str, ...] = field(default_factory=default_secret_patterns)
    synthetic_markers: tuple[str, ...] = (SYNTHETIC_MARKER,)
    version: str = "1.0.0"

    def __post_init__(self):
        if not 0 <= self.holdout_fraction < 1:
            raise ModelCallRecordsError("holdout fraction is in [0, 1)")
        object.__setattr__(self, "secret_patterns", tuple(self.secret_patterns))
        for pattern in self.secret_patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ModelCallRecordsError(f"bad secret pattern {pattern!r}: {exc}") from exc

    def holdout(self, run_id: str) -> bool:
        """Deterministic, per run: every call of a run lands on the same side."""
        digest = hashlib.sha256(f"{self.salt}:{run_id}".encode("utf-8")).hexdigest()
        return int(digest[:8], 16) / 0xFFFFFFFF < self.holdout_fraction


def _contains_secret(row: dict, patterns: tuple[str, ...]) -> "str | None":
    text = json.dumps(row, sort_keys=True, default=str)
    for pattern in patterns:
        if re.search(pattern, text):
            return pattern
    return None


def export_training_rows(records, policy: "TrainingExportPolicy | None" = None) -> dict:
    """Split, exclude, and scan; the result names why each excluded row was left out."""
    policy = policy or TrainingExportPolicy()
    train, holdout, excluded = [], [], []
    for record in records:
        if not isinstance(record, ModelCallLearningRecord):
            raise ModelCallRecordsError("training rows are built from ModelCallLearningRecord")
        row = record.to_dict()
        if any(marker in record.markers for marker in policy.synthetic_markers):
            excluded.append({"record_id": record.record_id, "reason": "synthetic_marker"})
            continue
        if record.outcome_label == UNKNOWN and not policy.include_unverified:
            excluded.append({"record_id": record.record_id, "reason": "unverified_outcome"})
            continue
        if not record.completed and not policy.include_incomplete:
            excluded.append({"record_id": record.record_id, "reason": "incomplete_call"})
            continue
        pattern = _contains_secret(row, policy.secret_patterns)
        if pattern is not None:
            excluded.append({"record_id": record.record_id, "reason": "secret_pattern"})
            continue
        (holdout if policy.holdout(record.run_id) else train).append(row)
    return {"record_type": "model_call_training_export/v1", "policy_version": policy.version,
            "holdout_fraction": policy.holdout_fraction, "train": train, "holdout": holdout,
            "excluded": excluded,
            "content_digest": hashlib.sha256(json.dumps(
                {"train": train, "holdout": holdout}, sort_keys=True).encode("utf-8")).hexdigest()}


def self_test() -> dict:
    """The join, the labels, the split by run, and the exclusions."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def run_events(run_id, calls, deviation=False, fail_first=False):
        events = []
        for number, step in enumerate(calls, start=1):
            base = {"run_id": run_id, "step": step, "format_attempt": 1, "transport_attempt": 1,
                    "pass_number": 1}
            events.append({**base, "event_type": STARTED, "model_call_number": number,
                           "prompt_digest": "p" * 64, "prompt_bytes": 1200,
                           "output_schema_digest": "s" * 64, "objective": f"do {step}",
                           "output_contract_id": "practitioner." + step})
            if fail_first and number == 1:
                events.append({**base, "event_type": TRANSPORT_FAILED, "error_code": "timeout"})
                events.append({**base, "event_type": STARTED, "transport_attempt": 2,
                               "model_call_number": number + 1, "prompt_digest": "p" * 64,
                               "output_contract_id": "practitioner." + step})
                base = {**base, "transport_attempt": 2}
            if deviation and step == "decide_next":
                events.append({**base, "event_type": DEVIATION, "problems": ["11 rows exceed 10"]})
            events.append({**base, "event_type": COMPLETED, "output_digest": "o" * 64,
                           "output_bytes": 300, "admitted_strategy": "strict_json"})
        return events

    solved = {"solved": True, "independent_verification_records": [{"status": "passed"}]}
    unsolved = {"solved": False, "independent_verification_records": [{"status": "failed"}]}
    records = learning_records(run_events("run-1", ("orient", "decide_next", "verify"), deviation=True), solved)
    check("events_join_into_one_record_per_call_with_digests_and_labels",
          len(records) == 3 and all(item.completed for item in records)
          and records[1].contract_id == "practitioner.decide_next"
          and records[1].deviation_problems == ("11 rows exceed 10",)
          and all(item.outcome_label == VERIFIED for item in records)
          and "do orient" in records[0].objective
          and "prompt_text" not in json.dumps(records[0].to_dict()))
    retried = learning_records(run_events("run-2", ("orient",), fail_first=True), unsolved)
    check("a_transport_failure_stays_on_its_attempt_and_the_retry_is_its_own_record",
          len(retried) == 2 and retried[0].transport_failures == 1 and not retried[0].completed
          and retried[1].completed and all(item.outcome_label == FAILED for item in retried))
    check("an_unverified_run_labels_its_calls_unknown",
          learning_records(run_events("run-3", ("orient",)), {"solved": True})[0].outcome_label == UNKNOWN
          and learning_records(run_events("run-4", ("orient",)), None)[0].outcome_label == UNKNOWN)
    policy = TrainingExportPolicy(holdout_fraction=0.5, salt="fixture", secret_patterns=("sk-[A-Za-z0-9]{20,}",))
    many = []
    for index in range(40):
        many.extend(learning_records(run_events(f"run-{index}", ("orient", "verify")), solved))
    export = export_training_rows(many, policy)
    sides = {}
    for side in ("train", "holdout"):
        for row in export[side]:
            sides.setdefault(row["run_id"], set()).add(side)
    check("the_split_is_by_run_deterministic_and_near_the_declared_fraction",
          all(len(value) == 1 for value in sides.values()) and export["train"] and export["holdout"]
          and 0.3 <= len(export["holdout"]) / (len(export["train"]) + len(export["holdout"])) <= 0.7
          and export_training_rows(many, policy)["content_digest"] == export["content_digest"])
    leaking = learning_records(run_events("run-x", ("orient",)), solved)[0]
    leaking = ModelCallLearningRecord(**{**{k: getattr(leaking, k) for k in leaking.__dataclass_fields__},
                                         "objective": "use key " + "sk-" + "a" * 26})
    synthetic = ModelCallLearningRecord(**{**{k: getattr(leaking, k) for k in leaking.__dataclass_fields__},
                                           "objective": "derived", "markers": (SYNTHETIC_MARKER,)})
    export = export_training_rows([leaking, synthetic, retried[0], *learning_records(
        run_events("run-5", ("orient",)), {"solved": True})], policy)
    reasons = sorted(item["reason"] for item in export["excluded"])
    check("secrets_synthetic_records_incomplete_calls_and_unverified_outcomes_are_excluded_by_name",
          reasons == ["incomplete_call", "secret_pattern", "synthetic_marker", "unverified_outcome"]
          and not export["train"] and not export["holdout"])
    check("the_default_secret_patterns_come_from_the_repository_and_policies_are_validated",
          len(default_secret_patterns()) >= 5
          and all(_refuses(action) for action in (
              lambda: TrainingExportPolicy(holdout_fraction=1.0),
              lambda: TrainingExportPolicy(secret_patterns=("(",)),
              lambda: ModelCallLearningRecord("", "orient", 1),
              lambda: ModelCallLearningRecord("run", "orient", 0),
              lambda: export_training_rows([{"run_id": "run"}], policy))))
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "model_call_records_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}


def _refuses(action) -> bool:
    try:
        action()
    except ModelCallRecordsError:
        return True
    return False
