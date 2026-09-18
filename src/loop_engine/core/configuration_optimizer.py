"""Optimize a configuration over a frozen suite with an acceptance gate.

The optimizer proposes cells from a declared parameter space, evaluates
each on the training side of a frozen suite with deterministic graders,
and accepts a candidate only when it beats the baseline on the training
side and does not lose on the held-out side. Every cell is counted
separately as represented, dispatched, evaluated, and accepted, so an
adaptive search is never reported as exhaustive coverage. Nothing here
calls a model; a prompt or harness variant is one more parameter value
that the caller's evaluate function knows how to apply.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import random
from dataclasses import dataclass, field

from .evaluation_suite import EvaluationReport, EvaluationSuite, EvaluationSuiteError, compare_reports

STRATEGIES = ("exact_enumeration", "stratified_sampling")
RESULT_RECORD_TYPE = "optimization_result/v1"


class OptimizerError(ValueError):
    """A space, strategy, or acceptance request is invalid."""


@dataclass(frozen=True)
class ParameterAxis:
    """One dimension with its finite declared values, first value first."""

    name: str
    values: tuple

    def __post_init__(self):
        if not self.name:
            raise OptimizerError("an axis needs a name")
        values = tuple(self.values)
        if not values:
            raise OptimizerError(f"axis {self.name!r} needs at least one value")
        try:
            json.dumps(values, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise OptimizerError(f"axis {self.name!r} values must be strict JSON") from exc
        if len({json.dumps(item, sort_keys=True) for item in values}) != len(values):
            raise OptimizerError(f"axis {self.name!r} values must be distinct")
        object.__setattr__(self, "values", values)


@dataclass(frozen=True)
class ParameterSpace:
    """A finite declared grid; its size is the represented count."""

    axes: tuple[ParameterAxis, ...]

    def __post_init__(self):
        axes = tuple(self.axes)
        if not axes or any(not isinstance(item, ParameterAxis) for item in axes):
            raise OptimizerError("a space holds at least one typed axis")
        if len({item.name for item in axes}) != len(axes):
            raise OptimizerError("axis names must be unique")
        object.__setattr__(self, "axes", axes)

    @property
    def size(self) -> int:
        total = 1
        for axis in self.axes:
            total *= len(axis.values)
        return total

    @property
    def baseline(self) -> dict:
        return {axis.name: axis.values[0] for axis in self.axes}

    def cells(self, strategy: str, *, seed: int = 0, limit: int | None = None) -> list[dict]:
        """Cells in a deterministic order; sampling never claims exhaustive coverage."""
        if strategy not in STRATEGIES:
            raise OptimizerError(f"strategy must be one of {STRATEGIES}")
        names = [axis.name for axis in self.axes]
        if strategy == STRATEGIES[0]:
            cells = [dict(zip(names, combination))
                     for combination in itertools.product(*(axis.values for axis in self.axes))]
            return cells if limit is None else cells[:limit]
        if limit is None or limit < 1:
            raise OptimizerError("stratified sampling needs a positive limit")
        rng = random.Random(seed)
        seen = set()
        cells = []
        attempts = 0
        while len(cells) < min(limit, self.size) and attempts < limit * 20:
            attempts += 1
            cell = {axis.name: rng.choice(axis.values) for axis in self.axes}
            key = json.dumps(cell, sort_keys=True)
            if key not in seen:
                seen.add(key)
                cells.append(cell)
        return cells


@dataclass(frozen=True)
class AcceptancePolicy:
    """When a candidate replaces the baseline."""

    minimum_train_gain: int = 1
    maximum_holdout_loss: int = 0
    version: str = "1.0.0"

    def __post_init__(self):
        if type(self.minimum_train_gain) is not int or self.minimum_train_gain < 1:
            raise OptimizerError("minimum_train_gain is a positive integer")
        if type(self.maximum_holdout_loss) is not int or self.maximum_holdout_loss < 0:
            raise OptimizerError("maximum_holdout_loss is a non-negative integer")


@dataclass(frozen=True)
class CellEvaluation:
    cell: dict
    train_report: EvaluationReport
    holdout_report: EvaluationReport

    @property
    def cell_digest(self) -> str:
        return hashlib.sha256(json.dumps(self.cell, sort_keys=True).encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class OptimizationResult:
    """The outcome with separate counts, the accepted cell if any, and the reason."""

    space_size: int
    strategy: str
    represented: int
    dispatched: int
    evaluated: int
    accepted: bool
    baseline_cell: dict
    best_cell: dict
    reason: str
    comparisons: tuple[dict, ...] = ()
    exhaustive: bool = False
    policy_version: str = ""

    def to_dict(self) -> dict:
        return {"record_type": RESULT_RECORD_TYPE, **{
            name: (list(value) if isinstance(value, tuple) else value)
            for name, value in ((name, getattr(self, name)) for name in self.__dataclass_fields__)}}


def optimize(space: ParameterSpace, train: EvaluationSuite, holdout: EvaluationSuite, evaluate, *,
             strategy: str = STRATEGIES[0], seed: int = 0, limit: int | None = None,
             policy: AcceptancePolicy | None = None) -> OptimizationResult:
    """Evaluate cells and accept the best one only under the policy.

    ``evaluate(cell, suite, solver_id)`` returns an ``EvaluationReport`` for
    that cell on that suite; the optimizer never sees how the cell is
    applied. The baseline is the first value of every axis.
    """
    if not isinstance(space, ParameterSpace):
        raise OptimizerError("optimize takes a typed ParameterSpace")
    if train.population_digest == holdout.population_digest:
        raise OptimizerError("train and holdout must be different populations")
    policy = policy or AcceptancePolicy()
    cells = space.cells(strategy, seed=seed, limit=limit)
    baseline_cell = space.baseline
    baseline = CellEvaluation(baseline_cell,
                              _report(evaluate, baseline_cell, train, "baseline"),
                              _report(evaluate, baseline_cell, holdout, "baseline"))
    dispatched = 0
    evaluated = 0
    best = baseline
    best_gain = 0
    comparisons = []
    for cell in cells:
        if cell == baseline_cell:
            continue
        dispatched += 1
        try:
            evaluation = CellEvaluation(cell, _report(evaluate, cell, train, "candidate"),
                                        _report(evaluate, cell, holdout, "candidate"))
        except EvaluationSuiteError as exc:
            comparisons.append({"cell": cell, "error": str(exc)[:300]})
            continue
        evaluated += 1
        train_comparison = compare_reports(baseline.train_report, evaluation.train_report)
        holdout_comparison = compare_reports(baseline.holdout_report, evaluation.holdout_report)
        gain = train_comparison["net"]
        loss = -holdout_comparison["net"]
        qualifies = gain >= policy.minimum_train_gain and loss <= policy.maximum_holdout_loss
        comparisons.append({"cell": cell, "train_net": gain, "holdout_net": holdout_comparison["net"],
                            "qualifies": qualifies})
        if qualifies and gain > best_gain:
            best, best_gain = evaluation, gain
    accepted = best is not baseline
    exhaustive = strategy == STRATEGIES[0] and limit is None
    reason = (f"cell {best.cell_digest} gained {best_gain} training cases and lost none beyond the "
              f"allowed {policy.maximum_holdout_loss} on holdout" if accepted
              else f"no evaluated cell gained at least {policy.minimum_train_gain} training cases without "
                   f"losing more than {policy.maximum_holdout_loss} holdout cases; the baseline stands")
    return OptimizationResult(space.size, strategy, len(cells), dispatched, evaluated, accepted,
                              baseline_cell, best.cell, reason, tuple(comparisons), exhaustive, policy.version)


def _report(evaluate, cell: dict, suite: EvaluationSuite, role: str) -> EvaluationReport:
    report = evaluate(cell, suite, f"{role}:{hashlib.sha256(json.dumps(cell, sort_keys=True).encode()).hexdigest()[:12]}")
    if not isinstance(report, EvaluationReport):
        raise OptimizerError("evaluate must return an EvaluationReport")
    if report.population_digest != suite.population_digest:
        raise OptimizerError("evaluate returned a report for a different population")
    return report


def self_test() -> dict:
    """Cells are counted separately, a gain on train that loses on holdout is refused, sampling is not exhaustive."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    def refuses(action) -> bool:
        try:
            action()
        except OptimizerError:
            return True
        return False

    from .evaluation_suite import EvaluationCase, evaluate_suite
    cases = tuple(EvaluationCase(f"c{i}", i, i % 3 == 0, "exact") for i in range(12))
    suite = EvaluationSuite("fixture.threshold", "1.0.0", cases)
    train, holdout = suite.split(0.34, salt="s")
    space = ParameterSpace((ParameterAxis("modulus", (2, 3, 4)), ParameterAxis("offset", (0, 1))))
    check("the_space_size_baseline_and_cells_are_deterministic",
          space.size == 6 and space.baseline == {"modulus": 2, "offset": 0}
          and len(space.cells("exact_enumeration")) == 6
          and space.cells("stratified_sampling", seed=1, limit=3) == space.cells("stratified_sampling", seed=1, limit=3)
          and len(space.cells("stratified_sampling", seed=1, limit=3)) == 3
          and refuses(lambda: space.cells("random_walk")) and refuses(lambda: space.cells("stratified_sampling")))

    def evaluate(cell, part, solver_id):
        return evaluate_suite(part, lambda case: (case.input + cell["offset"]) % cell["modulus"] == 0,
                              solver_id=solver_id)

    result = optimize(space, train, holdout, evaluate)
    check("exhaustive_enumeration_finds_the_true_cell_and_counts_every_stage",
          result.accepted and result.best_cell == {"modulus": 3, "offset": 0}
          and result.represented == 6 and result.dispatched == 5 and result.evaluated == 5
          and result.exhaustive and result.space_size == 6 and "gained" in result.reason)
    sampled = optimize(space, train, holdout, evaluate, strategy="stratified_sampling", seed=3, limit=2)
    check("sampling_never_claims_exhaustive_coverage",
          not sampled.exhaustive and sampled.represented == 2 and sampled.dispatched <= 2)

    def leaky(cell, part, solver_id):
        # the baseline answers False everywhere; the candidate memorizes the
        # training answers and inverts them on every other case
        train_ids = {case.case_id for case in train.cases}
        return evaluate_suite(part, lambda case: (case.expected if case.case_id in train_ids
                                                  else not case.expected)
                              if cell["modulus"] == 4 else False, solver_id=solver_id)

    refused = optimize(ParameterSpace((ParameterAxis("modulus", (2, 4)),)), train, holdout, leaky)
    check("a_cell_that_gains_on_train_but_loses_on_holdout_is_refused",
          not refused.accepted and refused.best_cell == {"modulus": 2}
          and any(item.get("train_net", 0) > 0 and item.get("holdout_net", 0) < 0 for item in refused.comparisons)
          and "baseline stands" in refused.reason)
    check("invalid_spaces_policies_and_populations_are_refused",
          refuses(lambda: ParameterAxis("a", ())) and refuses(lambda: ParameterAxis("a", (1, 1)))
          and refuses(lambda: ParameterSpace(())) and refuses(lambda: AcceptancePolicy(minimum_train_gain=0))
          and refuses(lambda: optimize(space, train, train, evaluate))
          and refuses(lambda: optimize(space, train, holdout, lambda cell, part, solver_id: "not a report")))
    passed = sum(item["passed"] for item in results)
    return {"record_type": "configuration_optimizer_test/v1", "tests": results, "passed": passed,
            "total": len(results), "all_passed": passed == len(results)}
