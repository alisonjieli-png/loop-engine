"""Prompt experiment records: conditional evidence per model call.

Architectural role: the seed of the prompt-engineering database the product
definition asks for. It is not a list of best prompts; it is one passive
record per model invocation linking the task region, Practitioner stage,
prompt assembly identity, context budget policy, context pack, provider,
model, route, tokens, latency when known, failure class, and the pass
verdict that followed. Records are projected from a saved adaptive result,
so any run written to Run History can be turned into experiments after the
fact, and aggregates over many runs can rank prompt and context choices per
task region with evidence rather than opinion.

Owns:
    - PromptExperimentRecord: the passive per-call record.
    - prompt_experiments_from_adaptive_result(): the deterministic projection.
    - summarize_experiments(): grouped counts and token means per stage.

Does not own: prompt assembly (core.adaptive_practitioner_prompting), the
context budget (core.context_budget), or provider accounting
(core.model_gateway).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

PROMPT_EXPERIMENT_SCHEMA_VERSION = "prompt_experiment/v1"


class PromptExperimentError(ValueError):
    """A prompt experiment record violated its typed contract."""


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def task_region_ref(original_task: str) -> str:
    """A coarse region key: normalized task words, digested.

    This is Stage 1 of the deterministic front end: exact identity after
    whitespace and case normalization. It is a grouping key for evidence, not
    an authority for selecting a solution.
    """
    words = re.findall(r"[a-z0-9]+", str(original_task or "").lower())
    return "region." + _digest({"words": words})[:16]


@dataclass(frozen=True)
class PromptExperimentRecord:
    """One model call as a conditional experiment."""

    experiment_id: str
    run_id: str
    task_region_ref: str
    practitioner_stage: str
    pass_number: int
    prompt_assembly_id: str
    prompt_digest: str
    context_policy_id: str
    context_policy_version: str
    context_pack_id: str
    provider_id: str
    model_id: str
    route_id: str
    estimated_input_tokens: int
    input_tokens: "int | None"
    output_tokens: "int | None"
    ok: bool
    failure_class: str
    pass_verdict: str
    record_type: str = PROMPT_EXPERIMENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.record_type != PROMPT_EXPERIMENT_SCHEMA_VERSION:
            raise PromptExperimentError("unsupported experiment schema version")
        for name in ("experiment_id", "run_id", "task_region_ref",
                     "practitioner_stage"):
            if not str(getattr(self, name)).strip():
                raise PromptExperimentError(f"{name} cannot be empty")
        if isinstance(self.pass_number, bool) or self.pass_number < 0:
            raise PromptExperimentError("pass_number must be a count")
        for name in ("estimated_input_tokens", "input_tokens",
                     "output_tokens"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool)
                                      or not isinstance(value, int)
                                      or value < 0):
                raise PromptExperimentError(
                    f"{name} must be a non-negative integer or None")
        if self.ok and self.failure_class:
            raise PromptExperimentError(
                "a successful call cannot carry a failure class")

    @property
    def estimate_ratio(self) -> "float | None":
        """Provider-reported input over the estimate, for calibration."""
        if not self.input_tokens or not self.estimated_input_tokens:
            return None
        return round(self.input_tokens / self.estimated_input_tokens, 4)

    def to_dict(self) -> dict:
        return {
            "record_type": self.record_type,
            "experiment_id": self.experiment_id, "run_id": self.run_id,
            "task_region_ref": self.task_region_ref,
            "practitioner_stage": self.practitioner_stage,
            "pass_number": self.pass_number,
            "prompt_assembly_id": self.prompt_assembly_id,
            "prompt_digest": self.prompt_digest,
            "context_policy_id": self.context_policy_id,
            "context_policy_version": self.context_policy_version,
            "context_pack_id": self.context_pack_id,
            "provider_id": self.provider_id, "model_id": self.model_id,
            "route_id": self.route_id,
            "estimated_input_tokens": self.estimated_input_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimate_ratio": self.estimate_ratio,
            "ok": self.ok, "failure_class": self.failure_class,
            "pass_verdict": self.pass_verdict,
        }


def _pass_of(snapshot: dict, index: int, passes: int, total: int) -> int:
    explicit = snapshot.get("pass_number")
    if isinstance(explicit, int) and explicit > 0:
        return explicit
    if passes <= 0 or total <= 0:
        return 0
    return min(passes, 1 + (index * passes) // total)


def prompt_experiments_from_adaptive_result(result: dict) -> tuple:
    """Join context snapshots, model usage, and verdicts into experiments.

    The ``n``-th context snapshot and the ``n``-th model usage record describe
    the same call in the order the Practitioner made them; when the run
    recorded fewer usage records than snapshots (a refused call has a packet
    but no provider result), the usage fields stay unknown rather than zero.
    The pass verdict is the verification verdict recorded for the pass the
    call belongs to.
    """
    if not isinstance(result, dict):
        raise PromptExperimentError("projection needs the result mapping")
    run_id = str(result.get("run_id") or "run")
    task = result.get("original_task")
    task_text = (task.get("original_input") or task.get("text") or ""
                 if isinstance(task, dict) else str(task or ""))
    region = task_region_ref(task_text)
    snapshots = list(result.get("context_snapshots") or ())
    usage = list(result.get("model_usage") or ())
    verdicts = [str((item or {}).get("verdict") or "")
                for item in (result.get("verification") or ())]
    passes = int(result.get("passes") or len(verdicts) or 0)
    records = []
    for index, snapshot in enumerate(snapshots):
        if not isinstance(snapshot, dict):
            continue
        used = usage[index] if index < len(usage) and isinstance(
            usage[index], dict) else {}
        assembly = snapshot.get("prompt_assembly") or {}
        pack = snapshot.get("context_pack") or {}
        pass_number = _pass_of(snapshot, index, passes, len(snapshots))
        verdict = (verdicts[pass_number - 1]
                   if 0 < pass_number <= len(verdicts) else "")
        ok = bool(used.get("ok")) if used else False
        failure = ""
        if used and not ok:
            attempts = used.get("attempts") or ()
            codes = [str(a.get("error_code") or a.get("failure_class") or "")
                     for a in attempts if isinstance(a, dict)]
            failure = next((c for c in codes if c), "provider_failed")
        elif not used:
            failure = "not_recorded"
        prompt_digest = str(assembly.get("prompt_digest")
                            or snapshot.get("packet_digest") or "")
        records.append(PromptExperimentRecord(
            experiment_id="experiment." + _digest({
                "run": run_id, "index": index, "prompt": prompt_digest})[:16],
            run_id=run_id, task_region_ref=region,
            practitioner_stage=str(snapshot.get("step") or "unknown"),
            pass_number=pass_number,
            prompt_assembly_id=str(assembly.get("assembly_id") or ""),
            prompt_digest=prompt_digest,
            context_policy_id=str(pack.get("policy_id")
                                  or "adaptive_practitioner.context_budget"),
            context_policy_version=str(pack.get("policy_version") or ""),
            context_pack_id=str(pack.get("context_pack_id") or ""),
            provider_id=str(used.get("provider") or ""),
            model_id=str(used.get("model") or ""),
            route_id=str(used.get("route") or ""),
            estimated_input_tokens=int(
                snapshot.get("total_estimated_tokens")
                or assembly.get("estimated_tokens") or 0),
            input_tokens=(int(used["input_tokens"])
                          if isinstance(used.get("input_tokens"), int)
                          else None),
            output_tokens=(int(used["output_tokens"])
                           if isinstance(used.get("output_tokens"), int)
                           else None),
            ok=ok, failure_class=failure, pass_verdict=verdict))
    return tuple(records)


def summarize_experiments(records) -> dict:
    """Group by stage: calls, successes, token means, estimate calibration."""
    groups: dict = {}
    for record in records:
        group = groups.setdefault(record.practitioner_stage, {
            "calls": 0, "ok": 0, "input_tokens": 0, "with_input": 0,
            "estimated": 0, "ratios": [], "verdicts": {}})
        group["calls"] += 1
        group["ok"] += 1 if record.ok else 0
        group["estimated"] += record.estimated_input_tokens
        if record.input_tokens is not None:
            group["input_tokens"] += record.input_tokens
            group["with_input"] += 1
        if record.estimate_ratio is not None:
            group["ratios"].append(record.estimate_ratio)
        if record.pass_verdict:
            group["verdicts"][record.pass_verdict] = group["verdicts"].get(
                record.pass_verdict, 0) + 1
    summary = {}
    for stage, group in sorted(groups.items()):
        ratios = group.pop("ratios")
        with_input = group["with_input"]
        summary[stage] = {
            **group,
            "mean_input_tokens": (round(group["input_tokens"] / with_input)
                                  if with_input else None),
            "mean_estimated_tokens": round(
                group["estimated"] / group["calls"]) if group["calls"] else 0,
            "mean_estimate_ratio": (round(sum(ratios) / len(ratios), 4)
                                    if ratios else None),
        }
    return summary


def self_test() -> dict:
    """Prove the join, unknown-not-zero accounting, and region keys."""
    result = {
        "run_id": "run-x", "passes": 2,
        "original_task": {"original_input": "Predict  the TARGET column"},
        "context_snapshots": [
            {"step": "orient", "prompt_assembly": {
                "assembly_id": "assembly.1", "prompt_digest": "a" * 64,
                "estimated_tokens": 1000},
             "context_pack": {"policy_id": "p", "policy_version": "1.1.0",
                              "context_pack_id": "context-pack.abc"},
             "total_estimated_tokens": 1000},
            {"step": "decide", "prompt_assembly": {
                "assembly_id": "assembly.2", "prompt_digest": "b" * 64,
                "estimated_tokens": 2000}, "total_estimated_tokens": 2000},
            {"step": "decide", "prompt_assembly": {
                "assembly_id": "assembly.3", "prompt_digest": "c" * 64,
                "estimated_tokens": 500}, "total_estimated_tokens": 500},
        ],
        "model_usage": [
            {"ok": True, "provider": "ollama_cloud", "model": "m",
             "route": "cloud.default", "input_tokens": 1200,
             "output_tokens": 300},
            {"ok": False, "provider": "ollama_cloud", "model": "m",
             "route": "cloud.default",
             "attempts": [{"error_code": "context_window_exceeded"}]},
        ],
        "verification": [{"verdict": "repair"}, {"verdict": "accept"}],
    }
    records = prompt_experiments_from_adaptive_result(result)
    summary = summarize_experiments(records)
    same_region = task_region_ref("predict the target column")
    other_region = task_region_ref("predict the price column")
    rejected = 0
    for bad in (
            lambda: PromptExperimentRecord(
                "e", "r", "region", "orient", 1, "", "", "p", "1", "", "", "",
                "", 10, 5, 5, True, "boom", ""),
            lambda: PromptExperimentRecord(
                "e", "r", "region", "", 1, "", "", "p", "1", "", "", "",
                "", 10, None, None, False, "x", ""),
    ):
        try:
            bad()
        except PromptExperimentError:
            rejected += 1
    tests = [{
        "test": "each_call_becomes_one_experiment_joined_to_its_usage_and_pass_verdict",
        "passed": (len(records) == 3 and records[0].ok
                   and records[0].estimate_ratio == 1.2
                   and records[0].pass_verdict == "repair"
                   and records[1].failure_class == "context_window_exceeded"
                   and records[2].failure_class == "not_recorded"
                   and records[2].input_tokens is None
                   and records[2].pass_verdict == "accept"),
        "detail": [r.failure_class for r in records].__repr__(),
    }, {
        "test": "summary_reports_unknown_usage_as_unknown_not_zero",
        "passed": (summary["decide"]["calls"] == 2
                   and summary["decide"]["with_input"] == 0
                   and summary["decide"]["mean_input_tokens"] is None
                   and summary["orient"]["mean_estimate_ratio"] == 1.2),
        "detail": str(summary["decide"]),
    }, {
        "test": "region_key_normalizes_case_and_whitespace_only",
        "passed": (records[0].task_region_ref == same_region
                   and same_region != other_region
                   and same_region.startswith("region.")),
        "detail": same_region,
    }, {
        "test": "invalid_records_fail_closed",
        "passed": rejected == 2,
        "detail": f"{rejected}/2 rejected",
    }]
    return {"module": "core.prompt_experiment",
            "passed": all(item["passed"] for item in tests), "tests": tests}
