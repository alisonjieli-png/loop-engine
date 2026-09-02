"""Task region statistics: what saved runs say about a task region.

Architectural role: a rebuildable projection over saved Run History that
groups runs by a coarse task region and counts what happened there: runs,
solved runs, model calls, input tokens, passes, first actions, and terminal
codes. It is the record the shortcut path reads before spending a model
call. The projection never selects a solution; ``recommend_shortcut`` returns
an advisory decision with its thresholds and negative evidence spelled out,
and a consumer Loop decides whether to act on it. Unknown quantities stay
unknown; a run that recorded no usage does not count as zero tokens.

Owns:
    - TaskRegionStatistics: the passive per-region aggregate.
    - build_region_statistics(): the projection over a runs directory.
    - ShortcutDecision and recommend_shortcut(): the advisory decision.

Does not own: the region key (core.prompt_experiment.task_region_ref), Run
History persistence (core.run_history), or the solve path that may consult
the decision (code_nodes.solve_runtime).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from .prompt_experiment import task_region_ref

REGION_STATISTICS_SCHEMA_VERSION = "task_region_statistics/v1"
SHORTCUT_DECISION_SCHEMA_VERSION = "shortcut_decision/v1"


class TaskRegionStatisticsError(ValueError):
    """A statistics record or decision violated its typed contract."""


@dataclass(frozen=True)
class TaskRegionStatistics:
    """Counts for one task region, rebuilt from saved adaptive results."""

    region_ref: str
    sample_task: str
    runs: int
    solved_runs: int
    runs_with_usage: int
    model_calls_total: int
    input_tokens_total: int
    passes_total: int
    first_action_histogram: dict
    terminal_histogram: dict
    evidence_run_ids: tuple
    record_type: str = REGION_STATISTICS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.record_type != REGION_STATISTICS_SCHEMA_VERSION:
            raise TaskRegionStatisticsError("unsupported statistics schema")
        if not self.region_ref.strip():
            raise TaskRegionStatisticsError("region_ref cannot be empty")
        for name in ("runs", "solved_runs", "runs_with_usage",
                     "model_calls_total", "input_tokens_total",
                     "passes_total"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise TaskRegionStatisticsError(f"{name} must be a count")
        if self.solved_runs > self.runs or self.runs_with_usage > self.runs:
            raise TaskRegionStatisticsError("solved and usage counts exceed runs")
        object.__setattr__(self, "evidence_run_ids",
                           tuple(self.evidence_run_ids))

    @property
    def accepted_rate(self) -> "float | None":
        return round(self.solved_runs / self.runs, 4) if self.runs else None

    @property
    def mean_model_calls_per_run(self) -> "float | None":
        return (round(self.model_calls_total / self.runs, 2)
                if self.runs else None)

    @property
    def mean_input_tokens_per_call(self) -> "float | None":
        if not self.runs_with_usage or not self.model_calls_total:
            return None
        return round(self.input_tokens_total / self.model_calls_total, 1)

    @property
    def most_common_first_action(self) -> "str | None":
        if not self.first_action_histogram:
            return None
        return max(sorted(self.first_action_histogram),
                   key=lambda key: self.first_action_histogram[key])

    def to_dict(self) -> dict:
        return {
            "record_type": self.record_type, "region_ref": self.region_ref,
            "sample_task": self.sample_task, "runs": self.runs,
            "solved_runs": self.solved_runs,
            "accepted_rate": self.accepted_rate,
            "runs_with_usage": self.runs_with_usage,
            "model_calls_total": self.model_calls_total,
            "mean_model_calls_per_run": self.mean_model_calls_per_run,
            "input_tokens_total": self.input_tokens_total,
            "mean_input_tokens_per_call": self.mean_input_tokens_per_call,
            "passes_total": self.passes_total,
            "first_action_histogram": dict(self.first_action_histogram),
            "most_common_first_action": self.most_common_first_action,
            "terminal_histogram": dict(self.terminal_histogram),
            "evidence_run_ids": list(self.evidence_run_ids),
        }


def _task_text(result: dict) -> str:
    task = result.get("original_task")
    if isinstance(task, dict):
        return str(task.get("original_input") or task.get("text") or "")
    return str(task or "")


def decision_actions(decision) -> list:
    """The action list of one recorded decision, whichever shape saved it."""
    if not isinstance(decision, dict):
        return []
    if decision.get("action_kind") or decision.get("kind"):
        return [decision]  # one saved decision record is one action
    actions = decision.get("actions")
    if actions is None and isinstance(decision.get("decision"), dict):
        actions = decision["decision"].get("actions")
    return [action for action in (actions or ()) if isinstance(action, dict)]


def action_kind(action: dict) -> str:
    return str(action.get("action_kind") or action.get("kind") or "")


def _first_action(result: dict) -> str:
    for decision in result.get("action_decisions") or ():
        for action in decision_actions(decision):
            if action_kind(action):
                return action_kind(action)
    return ""


def load_adaptive_results(runs_root: str) -> list:
    """Every readable adaptive result under a runs directory, sorted by id."""
    results = []
    if not os.path.isdir(runs_root):
        return results
    for name in sorted(os.listdir(runs_root)):
        path = os.path.join(runs_root, name, "adaptive-result.json")
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as handle:
                value = json.load(handle)
        except (OSError, ValueError):
            continue
        if isinstance(value, dict):
            value.setdefault("run_id", name)
            results.append(value)
    return results


def build_region_statistics(runs_root: str) -> tuple:
    """Group saved adaptive results by task region and count them."""
    groups: dict = {}
    for result in load_adaptive_results(runs_root):
        text = _task_text(result)
        region = task_region_ref(text)
        group = groups.setdefault(region, {
            "sample": text.strip()[:120], "runs": 0, "solved": 0,
            "with_usage": 0, "calls": 0, "tokens": 0, "passes": 0,
            "first": {}, "terminal": {}, "ids": []})
        group["runs"] += 1
        group["solved"] += 1 if result.get("solved") else 0
        usage = [u for u in (result.get("model_usage") or ())
                 if isinstance(u, dict)]
        calls = int(result.get("model_calls") or len(usage) or 0)
        group["calls"] += calls
        if usage and any(isinstance(u.get("input_tokens"), int) for u in usage):
            group["with_usage"] += 1
            group["tokens"] += sum(int(u.get("input_tokens") or 0)
                                   for u in usage)
        group["passes"] += int(result.get("passes") or 0)
        first = _first_action(result)
        if first:
            group["first"][first] = group["first"].get(first, 0) + 1
        terminal = str(result.get("status") or result.get("terminal_code")
                       or "unknown")
        group["terminal"][terminal] = group["terminal"].get(terminal, 0) + 1
        group["ids"].append(str(result.get("run_id")))
    return tuple(TaskRegionStatistics(
        region_ref=region, sample_task=group["sample"], runs=group["runs"],
        solved_runs=group["solved"], runs_with_usage=group["with_usage"],
        model_calls_total=group["calls"], input_tokens_total=group["tokens"],
        passes_total=group["passes"],
        first_action_histogram=dict(group["first"]),
        terminal_histogram=dict(group["terminal"]),
        evidence_run_ids=tuple(group["ids"]))
        for region, group in sorted(groups.items()))


@dataclass(frozen=True)
class ShortcutDecision:
    """Advisory: may a solved region skip reasoning, and on what evidence."""

    region_ref: str
    taken: bool
    reason: str
    minimum_runs: int
    minimum_accepted_rate: float
    observed_runs: int
    observed_accepted_rate: "float | None"
    negative_evidence: tuple
    recommended_first_action: "str | None"
    advisory: bool = True
    record_type: str = SHORTCUT_DECISION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.record_type != SHORTCUT_DECISION_SCHEMA_VERSION:
            raise TaskRegionStatisticsError("unsupported decision schema")
        if not self.region_ref.strip() or not self.reason.strip():
            raise TaskRegionStatisticsError("a decision needs a region and reason")
        if self.minimum_runs < 1 or not (0.0 < self.minimum_accepted_rate <= 1.0):
            raise TaskRegionStatisticsError("thresholds are out of range")
        if self.taken and self.negative_evidence:
            raise TaskRegionStatisticsError(
                "a shortcut cannot be taken over unsolved evidence")
        if not self.advisory:
            raise TaskRegionStatisticsError(
                "a shortcut decision is advisory; a Loop must act on it")
        object.__setattr__(self, "negative_evidence",
                           tuple(self.negative_evidence))

    def to_dict(self) -> dict:
        return {
            "record_type": self.record_type, "region_ref": self.region_ref,
            "taken": self.taken, "reason": self.reason,
            "minimum_runs": self.minimum_runs,
            "minimum_accepted_rate": self.minimum_accepted_rate,
            "observed_runs": self.observed_runs,
            "observed_accepted_rate": self.observed_accepted_rate,
            "negative_evidence": list(self.negative_evidence),
            "recommended_first_action": self.recommended_first_action,
            "advisory": self.advisory,
        }


def recommend_shortcut(statistics: TaskRegionStatistics, *,
                       minimum_runs: int = 3,
                       minimum_accepted_rate: float = 0.8,
                       unsolved_run_ids=()) -> ShortcutDecision:
    """Decide, advisorily, whether a region's evidence supports a shortcut.

    A shortcut is recommended only when the region has at least
    ``minimum_runs`` saved runs, its accepted rate meets the threshold, and
    no unsolved run stands as negative evidence. The reason names the
    threshold that failed so a reader never has to infer it.
    """
    negative = tuple(str(item) for item in unsolved_run_ids)
    rate = statistics.accepted_rate
    if statistics.runs < minimum_runs:
        reason = (f"only {statistics.runs} saved run(s) in this region; "
                  f"{minimum_runs} required before a shortcut")
        taken = False
    elif rate is None or rate < minimum_accepted_rate:
        reason = (f"accepted rate {rate} is below {minimum_accepted_rate}")
        taken = False
    elif negative:
        reason = (f"{len(negative)} unsolved run(s) in this region are "
                  "negative evidence against a shortcut")
        taken = False
    else:
        reason = (f"{statistics.runs} runs at accepted rate {rate} with no "
                  "unsolved evidence; the region's best-known first action "
                  "may be proposed without a model call")
        taken = True
    return ShortcutDecision(
        region_ref=statistics.region_ref, taken=taken, reason=reason,
        minimum_runs=minimum_runs, minimum_accepted_rate=minimum_accepted_rate,
        observed_runs=statistics.runs, observed_accepted_rate=rate,
        negative_evidence=negative if not taken else (),
        recommended_first_action=(statistics.most_common_first_action
                                  if taken else None))


def self_test() -> dict:
    """Prove grouping, unknown-not-zero usage, and advisory shortcut rules."""
    import tempfile

    def write_run(root, run_id, task, solved, calls, tokens, first, status):
        os.makedirs(os.path.join(root, run_id), exist_ok=True)
        usage = ([{"input_tokens": tokens // max(1, calls),
                   "output_tokens": 10}] * calls) if tokens is not None else (
            [{"ok": True}] * calls)
        with open(os.path.join(root, run_id, "adaptive-result.json"), "w",
                  encoding="utf-8") as handle:
            json.dump({
                "run_id": run_id, "solved": solved, "status": status,
                "original_task": {"original_input": task}, "passes": 2,
                "model_calls": calls, "model_usage": usage,
                "action_decisions": [{"actions": [
                    {"action_kind": first, "goal": "g"}]}],
            }, handle)

    with tempfile.TemporaryDirectory(prefix="loop-engine-regions-") as root:
        write_run(root, "r1", "Predict the target column", True, 10, 1000,
                  "COMPOSE_SOLUTION", "VERIFIED_WORKING")
        write_run(root, "r2", "predict  the TARGET column", True, 8, None,
                  "COMPOSE_SOLUTION", "VERIFIED_WORKING")
        write_run(root, "r3", "Predict the target column", True, 6, 600,
                  "RESEARCH_SOURCE", "VERIFIED_WORKING")
        write_run(root, "r4", "Summarize the quarterly report", False, 4, 400,
                  "RESEARCH_SOURCE", "VERIFICATION_FAILED")
        with open(os.path.join(root, "broken.json"), "w") as handle:
            handle.write("{not json")
        stats = build_region_statistics(root)
    by_region = {item.region_ref: item for item in stats}
    predict = by_region[task_region_ref("predict the target column")]
    summarize = by_region[task_region_ref("Summarize the quarterly report")]
    taken = recommend_shortcut(predict)
    refused_small = recommend_shortcut(summarize)
    refused_negative = recommend_shortcut(
        predict, unsolved_run_ids=("r9",))
    rejected = 0
    for bad in (
            lambda: ShortcutDecision("r", True, "x", 3, 0.8, 3, 1.0, ("r9",), None),
            lambda: ShortcutDecision("r", False, "x", 0, 0.8, 0, None, (), None),
            lambda: ShortcutDecision("r", False, "x", 3, 0.8, 0, None, (), None,
                                     advisory=False),
    ):
        try:
            bad()
        except TaskRegionStatisticsError:
            rejected += 1
    tests = [{
        "test": "runs_group_by_normalized_region_and_count_solved_calls_and_passes",
        "passed": (len(stats) == 2 and predict.runs == 3
                   and predict.solved_runs == 3 and predict.accepted_rate == 1.0
                   and predict.model_calls_total == 24 and predict.passes_total == 6
                   and predict.most_common_first_action == "COMPOSE_SOLUTION"
                   and predict.terminal_histogram == {"VERIFIED_WORKING": 3}),
        "detail": json.dumps(predict.to_dict())[:200],
    }, {
        "test": "token_means_count_only_runs_that_recorded_usage",
        "passed": (predict.runs_with_usage == 2
                   and predict.input_tokens_total == 1600
                   and predict.mean_input_tokens_per_call is not None
                   and summarize.mean_input_tokens_per_call == 100.0),
        "detail": f"{predict.runs_with_usage} runs with usage",
    }, {
        "test": "shortcut_is_advisory_and_refused_on_thin_or_negative_evidence",
        "passed": (taken.taken and taken.recommended_first_action
                   == "COMPOSE_SOLUTION" and taken.advisory
                   and not refused_small.taken and "3 required" in
                   refused_small.reason and not refused_negative.taken
                   and refused_negative.negative_evidence == ("r9",)),
        "detail": refused_negative.reason,
    }, {
        "test": "invalid_decisions_fail_closed",
        "passed": rejected == 3,
        "detail": f"{rejected}/3 rejected",
    }]
    return {"module": "core.task_region_statistics",
            "passed": all(item["passed"] for item in tests), "tests": tests}
