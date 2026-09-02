"""Compare one engine across several competitions.

Running one competition says whether the engine can solve that competition.
Running several says whether it generalizes, which is a different question and
the only one worth asking of a universal solver. This module reads a set of
finished runs and reports them side by side against the independently read
contract for each, so the answer rests on what the files establish rather than
on what a run claimed.

Discovery and execution are reported apart. A run that identified the right
target and failed to execute has shown something different from one that
produced a perfectly shaped submission for the wrong column, and collapsing
them into pass or fail destroys the distinction that matters most when the
question is generalization.

Owns:
    - CompetitionResult and read_result(): one run read against its contract.
    - compare_competitions(): the cross-competition reading.
    - render_table(): the console form.

Does not own: the contract rubric (contract.py), the submission reading
(loop_engine.kaggle_report), or the solve.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from contract import CompetitionContract, grade_discovery, read_contract

COMPARISON_RECORD_TYPE = "kaggle_competition_comparison/v1"


@dataclass
class CompetitionResult:
    """One competition's contract, run outcome, and submission reading."""

    competition: str
    contract: dict = field(default_factory=dict)
    outcome: dict = field(default_factory=dict)
    submission: dict = field(default_factory=dict)
    grade: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"competition": self.competition, "contract": self.contract,
                "outcome": self.outcome, "submission": self.submission,
                "grade": self.grade}


def _newest(paths) -> str:
    newest, newest_time = "", -1.0
    for path in paths:
        try:
            stamp = os.path.getmtime(path)
        except OSError:
            continue
        if stamp > newest_time:
            newest, newest_time = path, stamp
    return newest


def _find_adaptive_result(run_root: str) -> dict:
    """The newest saved adaptive result under a run directory."""
    found = []
    for base, _dirs, names in os.walk(run_root):
        for name in names:
            if name == "adaptive-result.json":
                found.append(os.path.join(base, name))
    path = _newest(found)
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}


def _discovered_contract(result: dict, submission_path: str = "") -> dict:
    """What the run actually decided, read from what it produced.

    The submission is the strongest evidence available: its prediction column
    is the target the run committed to, whatever any report claims. A run's
    own metrics file is a secondary source, used only to fill in what the
    submission cannot show. Grading a run on its self-report would credit a
    run that described the right target and predicted another, and would fail
    a run that got it right without writing a report.
    """
    from loop_engine.kaggle_report import describe_submission

    discovered = {}
    if submission_path:
        reading = describe_submission(submission_path)
        columns = reading.get("columns") or []
        if len(columns) >= 2:
            discovered = {"target": columns[-1], "identifier": columns[0],
                          "source": "submission.csv"}
    for attempt in reversed(result.get("project_attempts") or []):
        for artifact in attempt.get("artifacts") or []:
            path = str(artifact.get("path") or "")
            if path.endswith("metrics.json") and os.path.isfile(path):
                try:
                    with open(path, encoding="utf-8") as handle:
                        metrics = json.load(handle)
                except (OSError, json.JSONDecodeError):
                    continue
                return {**discovered,
                        "task_type": metrics.get("task_type"),
                        "metrics_target": metrics.get("target"),
                        "source": discovered.get("source") or "metrics.json"}
    return discovered


def read_result(competition: str, data_dir: str, run_root: str) -> CompetitionResult:
    """Read one competition's contract and the run that attempted it."""
    from loop_engine.kaggle_report import describe_submission

    contract = read_contract(data_dir, competition)
    result = _find_adaptive_result(run_root)
    submission_path = ""
    for base, _dirs, names in os.walk(run_root):
        if "submission.csv" in names:
            candidate = os.path.join(base, "submission.csv")
            if not submission_path or os.path.getmtime(candidate) > \
                    os.path.getmtime(submission_path):
                submission_path = candidate
    reading = describe_submission(submission_path)
    discovered = _discovered_contract(result, submission_path)
    outcome = {
        "status": result.get("status") or "NOT_RUN",
        "solved": bool(result.get("solved")),
        "model_calls": result.get("model_calls"),
        "elapsed_seconds": result.get("elapsed_seconds"),
        "failure": str(result.get("failure") or "")[:300],
        "run_id": result.get("run_id"),
    }
    return CompetitionResult(
        competition=competition, contract=contract.to_dict(), outcome=outcome,
        submission=reading, grade=grade_discovery(contract, discovered))


def compare_competitions(results) -> dict:
    """State what the set of runs shows about generalization."""
    rows = [item.to_dict() if isinstance(item, CompetitionResult) else item
            for item in results]
    attempted = [row for row in rows if row["outcome"]["status"] != "NOT_RUN"]
    solved = [row for row in attempted if row["outcome"]["solved"]]
    produced = [row for row in attempted if row["submission"].get("readable")]
    right_target = [row for row in attempted if row["grade"]["target_correct"]]
    constant = [row for row in produced if row["submission"].get("constant")]
    with_trap = [row for row in rows if row["contract"].get("trap")]
    return {
        "record_type": COMPARISON_RECORD_TYPE,
        "competitions": len(rows),
        "attempted": len(attempted),
        "verified": len(solved),
        "produced_a_submission": len(produced),
        "discovered_the_right_target": len(right_target),
        "submissions_that_never_vary": len(constant),
        "competitions_with_a_known_trap": len(with_trap),
        "results": rows,
        "note": ("discovery and execution are counted apart: identifying the "
                 "right target and failing to run is a different outcome "
                 "from running cleanly on the wrong column"),
    }


def render_table(comparison: dict) -> str:
    """The console form: one line per competition, shape and outcome first."""
    lines = ["",
             f"{'competition':<26}{'shape':<26}{'target':<8}{'rows':>9}"
             f"{'calls':>7}  outcome",
             "-" * 96]
    for row in comparison["results"]:
        contract, outcome = row["contract"], row["outcome"]
        reading = row["submission"]
        target = "ok" if row["grade"]["target_correct"] else (
            "wrong" if row["grade"]["found_target"] else "-")
        rows_out = reading.get("rows")
        lines.append(
            f"{row['competition'][:25]:<26}"
            f"{contract.get('task_shape', '?')[:25]:<26}"
            f"{target:<8}"
            f"{(f'{rows_out:,}' if isinstance(rows_out, int) else '-'):>9}"
            f"{str(outcome.get('model_calls') or '-'):>7}  "
            f"{outcome.get('status')}")
        if contract.get("trap"):
            lines.append(f"    trap: {contract['trap'][:86]}")
        if reading.get("constant"):
            lines.append("    ! every prediction is the same value")
    lines += ["-" * 96,
              f"  {comparison['verified']}/{comparison['attempted']} verified"
              f"   {comparison['produced_a_submission']}"
              f"/{comparison['attempted']} produced a submission"
              f"   {comparison['discovered_the_right_target']}"
              f"/{comparison['attempted']} found the right target", ""]
    return "\n".join(lines)
