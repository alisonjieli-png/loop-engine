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


PERTURBATIONS = ("whitespace", "case", "typographic_quotes", "extra_token")
CONVERGENCE_RECORD_TYPE = "convergence_report/v1"


EXTRA_TOKENS = ("inc", "llc", "the", "and", "co")
_PERTURBATION_FUNCTIONS = {
    PERTURBATIONS[0]: lambda value, rng: "  " + "  ".join(value.split(" ")) + " \t",
    PERTURBATIONS[1]: lambda value, rng: "".join(ch.upper() if rng.random() < 0.5 else ch.lower() for ch in value),
    PERTURBATIONS[2]: lambda value, rng: value.replace("'", "’").replace('"', "”"),
    PERTURBATIONS[3]: lambda value, rng: value + " " + rng.choice(EXTRA_TOKENS),
}


def perturb_text(value: str, kind: str, seed: int) -> str:
    """One deterministic perturbation of a text input; non-text inputs pass through."""
    if kind not in _PERTURBATION_FUNCTIONS:
        raise OptimizerError(f"perturbation must be one of {PERTURBATIONS}")
    return _PERTURBATION_FUNCTIONS[kind](value, random.Random(f"{kind}:{seed}:{value}"))


def perturb_suite(suite: EvaluationSuite, kind: str, *, seed: int = 0) -> EvaluationSuite:
    """The same cases with perturbed text inputs and unchanged expectations."""
    from .evaluation_suite import EvaluationCase
    cases = tuple(
        EvaluationCase(case.case_id, perturb_text(case.input, kind, seed) if isinstance(case.input, str)
                       else case.input, case.expected, case.grader, dict(case.grader_parameters), case.tags)
        for case in suite.cases)
    return EvaluationSuite(suite.suite_id, f"{suite.version}+{kind}", cases, f"{suite.description} ({kind} perturbed)")


def optimize_with_noise(space: ParameterSpace, train: EvaluationSuite, holdout: EvaluationSuite, evaluate, *,
                        perturbations: tuple[str, ...] = PERTURBATIONS[:2], seed: int = 0,
                        strategy: str = STRATEGIES[0], limit: int | None = None,
                        policy: AcceptancePolicy | None = None) -> OptimizationResult:
    """Accept a cell only when it also holds its gain on every perturbed holdout suite.

    A cell that wins on clean inputs and loses on noisy ones learned the noise
    of the training set, not the task; it is refused with the perturbation
    named, and the baseline stands.
    """
    if not perturbations:
        raise OptimizerError("optimize_with_noise needs at least one perturbation")
    clean = optimize(space, train, holdout, evaluate, strategy=strategy, seed=seed, limit=limit, policy=policy)
    if not clean.accepted:
        return clean
    policy = policy or AcceptancePolicy()
    noisy_checks = []
    for kind in perturbations:
        perturbed = perturb_suite(holdout, kind, seed=seed)
        baseline_report = _report(evaluate, clean.baseline_cell, perturbed, "baseline")
        candidate_report = _report(evaluate, clean.best_cell, perturbed, "candidate")
        comparison = compare_reports(baseline_report, candidate_report)
        noisy_checks.append({"perturbation": kind, "holdout_net": comparison["net"],
                             "holds": -comparison["net"] <= policy.maximum_holdout_loss})
    if all(item["holds"] for item in noisy_checks):
        return OptimizationResult(clean.space_size, clean.strategy, clean.represented, clean.dispatched,
                                  clean.evaluated, True, clean.baseline_cell, clean.best_cell,
                                  clean.reason + "; the gain held on " + ", ".join(perturbations) + " perturbations",
                                  (*clean.comparisons, *noisy_checks), clean.exhaustive, clean.policy_version)
    failing = [item["perturbation"] for item in noisy_checks if not item["holds"]]
    return OptimizationResult(clean.space_size, clean.strategy, clean.represented, clean.dispatched,
                              clean.evaluated, False, clean.baseline_cell, clean.baseline_cell,
                              f"cell refused: it lost held-out cases under {', '.join(failing)} perturbation, "
                              "so its gain was not robust; the baseline stands",
                              (*clean.comparisons, *noisy_checks), clean.exhaustive, clean.policy_version)


def converge(space: ParameterSpace, train: EvaluationSuite, holdout: EvaluationSuite, evaluate, *,
             rounds: int = 3, limit: int | None = None, strategy: "str | None" = None,
             stable_rounds: int = 2, policy: AcceptancePolicy | None = None) -> dict:
    """Repeated sampled rounds with different seeds; converged when the best cell stops changing.

    The report keeps every round, the separate counts, and says whether the
    best cell was the same for the last ``stable_rounds`` rounds. Without a
    limit the space is enumerated exhaustively and reported as converged
    after one round because there is nothing left to sample.
    """
    if type(rounds) is not int or rounds < 1 or type(stable_rounds) is not int or stable_rounds < 1:
        raise OptimizerError("rounds and stable_rounds are positive integers")
    if strategy is None:
        strategy = STRATEGIES[0] if limit is None else STRATEGIES[1]
    history = []
    best_cells = []
    for round_index in range(rounds):
        result = optimize(space, train, holdout, evaluate, strategy=strategy, seed=round_index,
                          limit=limit, policy=policy)
        history.append({"round": round_index, "seed": round_index, "accepted": result.accepted,
                        "best_cell": result.best_cell, "dispatched": result.dispatched,
                        "evaluated": result.evaluated, "exhaustive": result.exhaustive})
        best_cells.append(json.dumps(result.best_cell, sort_keys=True))
        if result.exhaustive:
            break
    tail = best_cells[-stable_rounds:]
    converged = (history[-1]["exhaustive"] or (len(best_cells) >= stable_rounds and len(set(tail)) == 1))
    return {"record_type": CONVERGENCE_RECORD_TYPE, "rounds_run": len(history), "rounds_requested": rounds,
            "strategy": strategy, "space_size": space.size, "converged": converged,
            "best_cell": json.loads(best_cells[-1]), "stable_rounds": stable_rounds,
            "dispatched": sum(item["dispatched"] for item in history),
            "evaluated": sum(item["evaluated"] for item in history), "history": history,
            "exhaustive": history[-1]["exhaustive"]}


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
    text_cases = tuple(EvaluationCase(f"t{i}", f"{'ACME' if i % 2 == 0 else 'BETA'} {i}",
                                      f"{'acme' if i % 2 == 0 else 'beta'} {i}", "canonical_text")
                       for i in range(12))
    text_suite = EvaluationSuite("fixture.text", "1.0.0", text_cases)
    text_train, text_holdout = text_suite.split(0.3, salt="noise")
    text_space = ParameterSpace((ParameterAxis("mode", ("prefix_only", "lower_clean_only")),))

    def text_evaluate(cell, part, solver_id):
        def solver(case):
            if cell["mode"] == "prefix_only":
                # the baseline handles one family robustly and fails the other
                return case.input.lower() if case.input.lstrip().startswith("ACME") else "wrong"
            # a memorizing candidate: correct on every clean input, broken by any noise
            clean = case.input == case.input.strip() and "  " not in case.input and "\t" not in case.input
            return case.input.lower() if clean else "noise"
        return evaluate_suite(part, solver, solver_id=solver_id)

    robust = optimize_with_noise(text_space, text_train, text_holdout, text_evaluate,
                                 perturbations=("whitespace",))
    check("a_cell_that_wins_only_on_clean_inputs_is_refused_by_noise_injection",
          not robust.accepted and robust.best_cell == {"mode": "prefix_only"}
          and "whitespace" in robust.reason and any(item.get("holds") is False for item in robust.comparisons)
          and optimize(text_space, text_train, text_holdout, text_evaluate).accepted
          and perturb_text("Acme Corp", "whitespace", 0) != "Acme Corp"
          and perturb_text("Acme's", "typographic_quotes", 0) == "Acme’s"
          and refuses(lambda: perturb_text("x", "gravity", 0))
          and refuses(lambda: optimize_with_noise(text_space, text_train, text_holdout, text_evaluate, perturbations=())))
    report = converge(space, train, holdout, evaluate, rounds=3, limit=3, strategy="stratified_sampling")
    check("convergence_reports_rounds_counts_and_whether_the_best_cell_stabilized",
          report["rounds_run"] == 3 and report["dispatched"] > 0 and isinstance(report["converged"], bool)
          and report["best_cell"] in ({"modulus": 3, "offset": 0}, {"modulus": 2, "offset": 0})
          and converge(space, train, holdout, evaluate, rounds=3)["rounds_run"] == 1
          and converge(space, train, holdout, evaluate, rounds=3)["converged"] is True
          and converge(space, train, holdout, evaluate, rounds=1, limit=1, stable_rounds=2)["converged"] is False
          and refuses(lambda: converge(space, train, holdout, evaluate, rounds=0)))
    check("invalid_spaces_policies_and_populations_are_refused",
          refuses(lambda: ParameterAxis("a", ())) and refuses(lambda: ParameterAxis("a", (1, 1)))
          and refuses(lambda: ParameterSpace(())) and refuses(lambda: AcceptancePolicy(minimum_train_gain=0))
          and refuses(lambda: optimize(space, train, train, evaluate))
          and refuses(lambda: optimize(space, train, holdout, lambda cell, part, solver_id: "not a report")))
    passed = sum(item["passed"] for item in results)
    return {"record_type": "configuration_optimizer_test/v1", "tests": results, "passed": passed,
            "total": len(results), "all_passed": passed == len(results)}
