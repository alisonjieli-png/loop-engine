"""Evaluation suites: a frozen population, registered graders, and exact denominators.

An evaluation product answers one question honestly: on this frozen set of
cases, graded this way, how did this solver do? The suite is a typed record
with a digest, so two reports can be compared only when they scored the
same population with the same graders. Every report names the denominator
(cases in the population), how many were attempted, passed, failed, and
errored, per grader and per tag, and the failures are kept with the same
prominence as the passes.

Graders are deterministic and registered by name: exact, canonical text,
JSON equality, numeric tolerance, set overlap, and regular expression. A
model-judged grader is a different product surface and is not offered
here; nothing in this module calls a model.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field

GRADERS = ("exact", "canonical_text", "json_equal", "numeric_tolerance", "set_overlap", "regex")
CASE_STATUSES = ("passed", "failed", "errored", "skipped")
SUITE_RECORD_TYPE = "evaluation_suite/v1"
REPORT_RECORD_TYPE = "evaluation_report/v1"
COMPARISON_RECORD_TYPE = "evaluation_comparison/v1"


class EvaluationSuiteError(ValueError):
    """A suite, case, grader, or report is invalid."""


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     default=str).encode("utf-8")).hexdigest()


def _canonical_text(value) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().lower()


def grade(grader: str, expected, observed, parameters: dict | None = None) -> bool:
    """Apply one registered grader; unknown graders are refused by name."""
    parameters = parameters or {}
    if grader == "exact":
        return expected == observed
    if grader == "canonical_text":
        return _canonical_text(expected) == _canonical_text(observed)
    if grader == "json_equal":
        return json.dumps(expected, sort_keys=True, default=str) == json.dumps(observed, sort_keys=True, default=str)
    if grader == "numeric_tolerance":
        try:
            return abs(float(expected) - float(observed)) <= float(parameters.get("tolerance", 1e-9))
        except (TypeError, ValueError):
            return False
    if grader == "set_overlap":
        try:
            left, right = set(expected), set(observed)
        except TypeError:
            return False
        if not left and not right:
            return True
        overlap = len(left & right) / len(left | right)
        return overlap >= float(parameters.get("minimum_overlap", 1.0))
    if grader == "regex":
        pattern = str(parameters.get("pattern") or expected)
        return re.search(pattern, str(observed)) is not None
    raise EvaluationSuiteError(f"grader must be one of {GRADERS}")


@dataclass(frozen=True)
class EvaluationCase:
    """One frozen case: input, expected output, grader, and tags."""

    case_id: str
    input: object
    expected: object
    grader: str = "exact"
    grader_parameters: dict = field(default_factory=dict)
    tags: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.case_id:
            raise EvaluationSuiteError("a case needs an identifier")
        if self.grader not in GRADERS:
            raise EvaluationSuiteError(f"grader must be one of {GRADERS}")
        try:
            json.dumps([self.input, self.expected, self.grader_parameters], allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise EvaluationSuiteError("case input, expected, and parameters must be strict JSON") from exc
        object.__setattr__(self, "tags", tuple(self.tags))

    def to_dict(self) -> dict:
        return {"case_id": self.case_id, "input": self.input, "expected": self.expected,
                "grader": self.grader, "grader_parameters": dict(self.grader_parameters),
                "tags": list(self.tags)}


@dataclass(frozen=True)
class EvaluationSuite:
    """A frozen population with a digest; the same digest means the same test."""

    suite_id: str
    version: str
    cases: tuple[EvaluationCase, ...]
    description: str = ""

    def __post_init__(self):
        if not self.suite_id or not self.version:
            raise EvaluationSuiteError("a suite needs an identifier and a version")
        cases = tuple(self.cases)
        if not cases or any(not isinstance(item, EvaluationCase) for item in cases):
            raise EvaluationSuiteError("a suite holds at least one typed case")
        ids = [item.case_id for item in cases]
        if len(set(ids)) != len(ids):
            raise EvaluationSuiteError("case identifiers must be unique")
        object.__setattr__(self, "cases", cases)

    @property
    def population_digest(self) -> str:
        return _digest([item.to_dict() for item in self.cases])

    def to_dict(self) -> dict:
        return {"record_type": SUITE_RECORD_TYPE, "suite_id": self.suite_id, "version": self.version,
                "description": self.description, "cases": [item.to_dict() for item in self.cases],
                "population_digest": self.population_digest}

    @classmethod
    def from_dict(cls, value: dict) -> "EvaluationSuite":
        if not isinstance(value, dict) or value.get("record_type") != SUITE_RECORD_TYPE:
            raise EvaluationSuiteError(f"a suite record needs record_type {SUITE_RECORD_TYPE}")
        return cls(str(value.get("suite_id", "")), str(value.get("version", "")),
                   tuple(EvaluationCase(str(item.get("case_id", "")), item.get("input"), item.get("expected"),
                                        str(item.get("grader", "exact")), dict(item.get("grader_parameters") or {}),
                                        tuple(item.get("tags") or ()))
                         for item in value.get("cases") or ()),
                   str(value.get("description") or ""))

    def split(self, holdout_fraction: float, *, salt: str = "") -> tuple["EvaluationSuite", "EvaluationSuite"]:
        """A deterministic train and holdout split by case digest; both keep the suite identity."""
        if not 0 < holdout_fraction < 1:
            raise EvaluationSuiteError("holdout_fraction lies in (0, 1)")
        train, holdout = [], []
        for case in self.cases:
            digest = hashlib.sha256(f"{salt}:{case.case_id}".encode("utf-8")).hexdigest()
            (holdout if int(digest[:8], 16) / 0xFFFFFFFF < holdout_fraction else train).append(case)
        if not train or not holdout:
            raise EvaluationSuiteError("the split left one side empty; change the fraction or the salt")
        return (EvaluationSuite(self.suite_id, self.version, tuple(train), self.description + " (train)"),
                EvaluationSuite(self.suite_id, self.version, tuple(holdout), self.description + " (holdout)"))


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    status: str
    observed: object = None
    error: str = ""
    elapsed_ms: int = 0

    def to_dict(self) -> dict:
        return {"case_id": self.case_id, "status": self.status, "observed": self.observed,
                "error": self.error, "elapsed_ms": self.elapsed_ms}


@dataclass(frozen=True)
class EvaluationReport:
    """Exact counts over the frozen population, with failures kept."""

    suite_id: str
    suite_version: str
    population_digest: str
    solver_id: str
    results: tuple[CaseResult, ...]
    grader_counts: dict
    tag_counts: dict

    @property
    def denominator(self) -> int:
        return len(self.results)

    def count(self, status: str) -> int:
        return sum(1 for item in self.results if item.status == status)

    @property
    def pass_rate(self) -> float:
        return self.count("passed") / self.denominator if self.denominator else 0.0

    def to_dict(self) -> dict:
        body = {"record_type": REPORT_RECORD_TYPE, "suite_id": self.suite_id,
                "suite_version": self.suite_version, "population_digest": self.population_digest,
                "solver_id": self.solver_id, "denominator": self.denominator,
                "attempted": self.denominator - self.count("skipped"),
                "passed": self.count("passed"), "failed": self.count("failed"),
                "errored": self.count("errored"), "skipped": self.count("skipped"),
                "pass_rate": round(self.pass_rate, 6), "grader_counts": self.grader_counts,
                "tag_counts": self.tag_counts, "results": [item.to_dict() for item in self.results],
                "failures": [item.to_dict() for item in self.results if item.status != "passed"]}
        body["content_digest"] = _digest({key: value for key, value in body.items() if key != "results"})
        return body


def evaluate_suite(suite: EvaluationSuite, solver, *, solver_id: str) -> EvaluationReport:
    """Run the solver on every case and grade it; an exception is an errored case, never a pass."""
    if not isinstance(suite, EvaluationSuite):
        raise EvaluationSuiteError("evaluate_suite takes a typed EvaluationSuite")
    if not solver_id:
        raise EvaluationSuiteError("a report names its solver")
    results = []
    grader_counts: dict = {}
    tag_counts: dict = {}
    for case in suite.cases:
        started = time.perf_counter()
        try:
            observed = solver(case)
            passed = grade(case.grader, case.expected, observed, case.grader_parameters)
            result = CaseResult(case.case_id, "passed" if passed else "failed", observed,
                                elapsed_ms=int((time.perf_counter() - started) * 1000))
        except Exception as exc:
            result = CaseResult(case.case_id, "errored", None, f"{type(exc).__name__}: {exc}"[:500],
                                int((time.perf_counter() - started) * 1000))
        results.append(result)
        bucket = grader_counts.setdefault(case.grader, {status: 0 for status in CASE_STATUSES})
        bucket[result.status] += 1
        for tag in case.tags:
            tag_bucket = tag_counts.setdefault(tag, {status: 0 for status in CASE_STATUSES})
            tag_bucket[result.status] += 1
    return EvaluationReport(suite.suite_id, suite.version, suite.population_digest, solver_id,
                            tuple(results), grader_counts, tag_counts)


def compare_reports(baseline: EvaluationReport, candidate: EvaluationReport) -> dict:
    """Case-level comparison; refused when the populations differ."""
    if baseline.population_digest != candidate.population_digest:
        raise EvaluationSuiteError("reports compare only over the same frozen population")
    base = {item.case_id: item.status for item in baseline.results}
    cand = {item.case_id: item.status for item in candidate.results}
    gained = sorted(case for case in base if base[case] != "passed" and cand.get(case) == "passed")
    lost = sorted(case for case in base if base[case] == "passed" and cand.get(case) != "passed")
    return {"record_type": COMPARISON_RECORD_TYPE, "population_digest": baseline.population_digest,
            "baseline_solver": baseline.solver_id, "candidate_solver": candidate.solver_id,
            "denominator": baseline.denominator, "baseline_passed": baseline.count("passed"),
            "candidate_passed": candidate.count("passed"), "gained": gained, "lost": lost,
            "net": len(gained) - len(lost)}


def self_test() -> dict:
    """Denominators are exact, errors never pass, graders are named, and comparisons need one population."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    def refuses(action) -> bool:
        try:
            action()
        except EvaluationSuiteError:
            return True
        return False

    suite = EvaluationSuite("fixture.conform", "1.0.0", (
        EvaluationCase("c1", "ACME CORP", "Acme Corp", "exact", tags=("case",)),
        EvaluationCase("c2", "  beta  ", "beta", "canonical_text", tags=("whitespace",)),
        EvaluationCase("c3", {"a": 1}, {"a": 1}, "json_equal"),
        EvaluationCase("c4", "3.14159", 3.1416, "numeric_tolerance", {"tolerance": 0.001}),
        EvaluationCase("c5", ["x", "y"], ["x", "y", "z"], "set_overlap", {"minimum_overlap": 0.6}),
        EvaluationCase("c6", "boom", "Acme", "regex", {"pattern": "^Acme"}),
    ), "fixture")

    def solver(case):
        if case.case_id == "c1":
            return "Acme Corp"
        if case.case_id == "c2":
            return "BETA"
        if case.case_id == "c3":
            return {"a": 1}
        if case.case_id == "c4":
            return "3.1412"
        if case.case_id == "c5":
            return ["y"]
        raise RuntimeError("solver crashed")

    report = evaluate_suite(suite, solver, solver_id="fixture.solver@1")
    check("the_report_counts_every_case_with_exact_denominators_and_keeps_failures",
          report.denominator == 6 and report.count("passed") == 4 and report.count("failed") == 1
          and report.count("errored") == 1 and report.to_dict()["attempted"] == 6
          and [item["case_id"] for item in report.to_dict()["failures"]] == ["c5", "c6"]
          and "solver crashed" in report.to_dict()["failures"][1]["error"]
          and report.grader_counts["regex"]["errored"] == 1 and report.tag_counts["case"]["passed"] == 1)
    check("graders_are_deterministic_and_named",
          grade("exact", 1, 1) and not grade("exact", 1, "1")
          and grade("canonical_text", "A  b", "a b") and grade("json_equal", {"b": 1, "a": 2}, {"a": 2, "b": 1})
          and grade("numeric_tolerance", 1.0, 1.0005, {"tolerance": 0.001})
          and not grade("numeric_tolerance", 1.0, 1.5, {"tolerance": 0.001})
          and not grade("numeric_tolerance", 1.0, 1.0005)
          and not grade("numeric_tolerance", "x", 1)
          and grade("set_overlap", [1, 2], [2, 1]) and not grade("set_overlap", [1, 2], [3])
          and grade("regex", "^a", "abc") and refuses(lambda: grade("oracle", 1, 1)))
    reloaded = EvaluationSuite.from_dict(json.loads(json.dumps(suite.to_dict())))
    check("a_suite_round_trips_with_a_stable_population_digest",
          reloaded.population_digest == suite.population_digest and len(reloaded.cases) == 6
          and refuses(lambda: EvaluationSuite("s", "1", ()))
          and refuses(lambda: EvaluationSuite("s", "1", (suite.cases[0], suite.cases[0])))
          and refuses(lambda: EvaluationCase("", 1, 1)) and refuses(lambda: EvaluationCase("c", 1, 1, "guess")))
    better = evaluate_suite(suite, lambda case: {"c1": "Acme Corp", "c2": "beta", "c3": {"a": 1},
                                                 "c4": "3.1416", "c5": ["x", "y", "z"], "c6": "Acme"}[case.case_id],
                            solver_id="fixture.solver@2")
    comparison = compare_reports(report, better)
    check("comparisons_are_case_level_and_need_the_same_population",
          comparison["gained"] == ["c5", "c6"] and comparison["lost"] == [] and comparison["net"] == 2
          and comparison["denominator"] == 6
          and refuses(lambda: compare_reports(report, evaluate_suite(
              EvaluationSuite("other", "1.0.0", suite.cases[:2]), solver, solver_id="x"))))
    train, holdout = suite.split(0.34, salt="fixture")
    check("a_split_is_deterministic_and_keeps_the_suite_identity",
          len(train.cases) + len(holdout.cases) == 6 and train.suite_id == holdout.suite_id
          and suite.split(0.34, salt="fixture")[0].population_digest == train.population_digest
          and refuses(lambda: suite.split(1.5)))
    passed = sum(item["passed"] for item in results)
    return {"record_type": "evaluation_suite_test/v1", "tests": results, "passed": passed,
            "total": len(results), "all_passed": passed == len(results)}
