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
    #: What the runs in this region drew on from the portfolio they were
    #: offered, split by whether the run was solved. An option used only by
    #: runs that failed and an option used by every run that succeeded are
    #: the same number until the split is kept, so it is kept here rather
    #: than summed away. Absent from a run saved before selection was
    #: observed, which counts as no evidence, not as evidence of no use.
    option_use_solved: dict
    option_use_unsolved: dict
    #: Steps that made a call, and steps whose caller reported drawing on
    #: something. A step present in the first and absent from the second is
    #: reasoning nobody's portfolio ever reached.
    step_call_histogram: dict
    #: What callers said they needed and were not offered, kept verbatim.
    #: This is the only channel by which the portfolio learns what is
    #: missing rather than what is unused.
    unmet_option_requests: tuple
    runs_reporting_selection: int
    evidence_run_ids: tuple
    record_type: str = REGION_STATISTICS_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.record_type != REGION_STATISTICS_SCHEMA_VERSION:
            raise TaskRegionStatisticsError("unsupported statistics schema")
        if not self.region_ref.strip():
            raise TaskRegionStatisticsError("region_ref cannot be empty")
        for name in ("runs", "solved_runs", "runs_with_usage",
                     "model_calls_total", "input_tokens_total",
                     "passes_total", "runs_reporting_selection"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise TaskRegionStatisticsError(f"{name} must be a count")
        if self.solved_runs > self.runs or self.runs_with_usage > self.runs:
            raise TaskRegionStatisticsError("solved and usage counts exceed runs")
        if self.runs_reporting_selection > self.runs:
            raise TaskRegionStatisticsError(
                "runs reporting selection exceed runs")
        object.__setattr__(self, "evidence_run_ids",
                           tuple(self.evidence_run_ids))
        object.__setattr__(self, "unmet_option_requests",
                           tuple(self.unmet_option_requests))

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


def _accumulate_option_use(group: dict, result) -> None:
    """Fold one run's option tally into its region, keeping the solved split.

    A run saved before selection was observed carries no tally. It is left
    out of the option counts entirely rather than counted as a run that used
    nothing, because those two are different claims and only one of them is
    supported by the file.
    """
    tally = result.get("option_selection")
    if not isinstance(tally, dict):
        return
    for step, count in (tally.get("steps_offered") or {}).items():
        key = str(step)
        group["step_calls"][key] = group["step_calls"].get(key, 0) + int(count or 0)
    for item in tally.get("wanted_but_absent") or ():
        if isinstance(item, dict) and item.get("text"):
            group["unmet"].append({"step": str(item.get("step") or ""),
                                   "text": str(item["text"])[:280],
                                   "run_id": str(result.get("run_id") or "")})
    counted = False
    target = group["use_solved"] if result.get("solved") else group["use_unsolved"]
    for kind in ("perspectives", "question_refs", "guidance_refs"):
        for ref, count in (tally.get(kind) or {}).items():
            key = f"{kind}:{ref}"
            target[key] = target.get(key, 0) + int(count or 0)
            counted = True
    if counted or tally.get("reports"):
        group["reporting"] += 1


def build_region_statistics(runs_root: str) -> tuple:
    """Group saved adaptive results by task region and count them."""
    groups: dict = {}
    for result in load_adaptive_results(runs_root):
        text = _task_text(result)
        region = task_region_ref(text)
        group = groups.setdefault(region, {
            "sample": text.strip()[:120], "runs": 0, "solved": 0,
            "with_usage": 0, "calls": 0, "tokens": 0, "passes": 0,
            "first": {}, "terminal": {}, "ids": [],
            "use_solved": {}, "use_unsolved": {}, "step_calls": {},
            "unmet": [], "reporting": 0})
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
        _accumulate_option_use(group, result)
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
        option_use_solved=dict(sorted(group["use_solved"].items())),
        option_use_unsolved=dict(sorted(group["use_unsolved"].items())),
        step_call_histogram=dict(sorted(group["step_calls"].items())),
        unmet_option_requests=tuple(group["unmet"]),
        runs_reporting_selection=group["reporting"],
        evidence_run_ids=tuple(group["ids"]))
        for region, group in sorted(groups.items()))


def option_evidence(statistics) -> dict:
    """What the accumulated runs say about each offered option.

    Three populations, kept apart because they mean different things. An
    option **used** carries the runs it appeared in and how they ended. An
    option **never reported** across runs that did report is a candidate for
    review, and nothing more: it may be dead weight, or it may be the one
    perspective that matters on the rare task this region has not seen yet.
    An option **asked for and absent** is the portfolio's own gap list.

    This is a reading, not a decision. It never removes an option and never
    narrows what a call is offered; a person weighs it and edits the
    portfolio. Rates are reported only with the counts behind them, and a
    region with too little evidence says so rather than returning a number
    that looks like a finding.
    """
    used: dict = {}
    for source, solved in (("option_use_solved", True),
                           ("option_use_unsolved", False)):
        for key, count in (getattr(statistics, source, None) or {}).items():
            row = used.setdefault(key, {"solved_uses": 0, "unsolved_uses": 0})
            row["solved_uses" if solved else "unsolved_uses"] += int(count or 0)
    for key, row in used.items():
        total = row["solved_uses"] + row["unsolved_uses"]
        row["uses"] = total
        row["solved_share"] = (round(row["solved_uses"] / total, 4)
                               if total else None)
    reporting = int(getattr(statistics, "runs_reporting_selection", 0) or 0)
    steps = getattr(statistics, "step_call_histogram", None) or {}
    return {
        "record_type": "option_evidence_reading/v1",
        "region_ref": statistics.region_ref,
        "runs": statistics.runs,
        "runs_reporting_selection": reporting,
        "evidence_is_thin": reporting < 3,
        "why_thin": ("fewer than three runs in this region reported what "
                     "they drew on; read the counts, not the rates"
                     if reporting < 3 else ""),
        "options_used": dict(sorted(
            used.items(), key=lambda item: (-item[1]["uses"], item[0]))),
        "steps_called": dict(sorted(steps.items())),
        "asked_for_and_absent": list(
            getattr(statistics, "unmet_option_requests", ()) or ()),
        "authority": ("advisory; this reading never narrows what a call is "
                      "offered, and an unused option stays on the menu until "
                      "a person decides otherwise"),
    }


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

    def write_run(root, run_id, task, solved, calls, tokens, first, status,
                  tally=None):
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
                **({"option_selection": tally} if tally else {}),
            }, handle)

    with tempfile.TemporaryDirectory(prefix="loop-engine-regions-") as root:
        write_run(root, "r1", "Predict the target column", True, 10, 1000,
                  "COMPOSE_SOLUTION", "VERIFIED_WORKING", tally={
                      "perspectives": {"core.persona.adversary": 3,
                                       "core.persona.researcher": 1},
                      "guidance_refs": {"core.guidance.one_next_action": 2},
                      "question_refs": {},
                      "steps_offered": {"orient": 2, "decide_next": 2},
                      "wanted_but_absent": [],
                      "reports": 4, "calls": 10})
        write_run(root, "r2", "predict  the TARGET column", True, 8, None,
                  "COMPOSE_SOLUTION", "VERIFIED_WORKING")
        write_run(root, "r3", "Predict the target column", True, 6, 600,
                  "RESEARCH_SOURCE", "VERIFIED_WORKING")
        write_run(root, "r4", "Summarize the quarterly report", False, 4, 400,
                  "RESEARCH_SOURCE", "VERIFICATION_FAILED", tally={
                      "perspectives": {"core.persona.adversary": 2},
                      "guidance_refs": {},
                      "question_refs": {},
                      "steps_offered": {"orient": 1, "verify": 3},
                      "wanted_but_absent": [
                          {"step": "verify", "text": "a cost perspective"}],
                      "reports": 2, "calls": 4})
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
    }, {
        "test": "option_use_keeps_the_solved_and_unsolved_split_apart",
        "passed": (predict.option_use_solved.get(
                       "perspectives:core.persona.adversary") == 3
                   and not predict.option_use_unsolved
                   and summarize.option_use_unsolved.get(
                       "perspectives:core.persona.adversary") == 2
                   and not summarize.option_use_solved),
        "detail": json.dumps(predict.option_use_solved),
    }, {
        "test": "a_run_saved_without_a_tally_is_absent_not_counted_as_zero",
        "passed": (predict.runs == 3
                   and predict.runs_reporting_selection == 1),
        "detail": (f"{predict.runs_reporting_selection} of {predict.runs} "
                   "runs reported"),
    }, {
        "test": "steps_that_made_a_call_are_counted_per_region",
        "passed": (predict.step_call_histogram == {"decide_next": 2,
                                                   "orient": 2}
                   and summarize.step_call_histogram == {"orient": 1,
                                                         "verify": 3}),
        "detail": json.dumps(predict.step_call_histogram),
    }, {
        "test": "an_option_asked_for_and_absent_is_kept_verbatim_with_its_run",
        "passed": (len(summarize.unmet_option_requests) == 1
                   and summarize.unmet_option_requests[0]["text"]
                   == "a cost perspective"
                   and summarize.unmet_option_requests[0]["run_id"] == "r4"),
        "detail": json.dumps(list(summarize.unmet_option_requests)),
    }, {
        "test": "the_reading_is_advisory_and_says_when_evidence_is_thin",
        "passed": (option_evidence(predict)["evidence_is_thin"]
                   and "three runs" in option_evidence(predict)["why_thin"]
                   and option_evidence(predict)["options_used"][
                       "perspectives:core.persona.adversary"][
                           "solved_share"] == 1.0
                   and option_evidence(summarize)["options_used"][
                       "perspectives:core.persona.adversary"][
                           "solved_share"] == 0.0
                   and "never narrows"
                   in option_evidence(predict)["authority"]),
        "detail": json.dumps(option_evidence(predict))[:300],
    }]
    return {"module": "core.task_region_statistics",
            "passed": all(item["passed"] for item in tests), "tests": tests}
