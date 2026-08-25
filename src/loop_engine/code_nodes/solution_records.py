"""The Solution record vocabulary — candidate, portfolio, evaluation, package, receipt.

Architectural role: Code Node system (the Solution lifecycle's record types).

D-2 held these back as a standing decision: five dataclasses nothing reads are
scaffolding, and the charter refuses to count scaffolding as done. The owner
overruled that on 2026-08-24, so they are built — but built the way the
objection demanded, each with a **live reader** rather than a name:

| Record | Read by |
|---|---|
| `SolutionCandidate` | `SolutionPortfolio.select` and the comparison report |
| `SolutionPortfolio` | selection, and the `solution.candidate.created` lifecycle |
| `SolutionEvaluationSpec` | `evaluate_candidate`, which refuses to score without one |
| `SolutionPackageManifest` | `package_solution`, which digests what ships |
| `SolutionRunReceipt` | `record_run`, the evidence a run actually happened |

The rule that gives them teeth: **a candidate cannot select itself.**
`SolutionPortfolio.select` requires an evaluation whose evaluator is not the
candidate's own author — the Article 10 separation, applied where Solutions
are chosen.

Owns:
    - the five records and their validation;
    - evaluate_candidate / select / package_solution / record_run.

Does not own:
    - execution (solution_canvas), graphs (solution_graph), or promotion
      (asset_lifecycle).

Key invariants:
    - an unscored candidate cannot be selected;
    - a candidate cannot be its own evaluator;
    - an empty portfolio selects nothing rather than inventing a winner;
    - a package manifest digests its contents, so "what shipped" is checkable.

Verification: self_test() — selection on evidence, the self-evaluation
refusal, empty-portfolio abstention, and manifest/receipt integrity.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


class SolutionRecordError(ValueError):
    """A Solution record that claims more than it can show."""


def _digest(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


@dataclass
class SolutionEvaluationSpec:
    """How candidates in one portfolio are compared.

    Named explicitly because "we picked the best one" is not a method: the
    metric, its direction, and the margin below which two results are
    practically equivalent all change which candidate wins."""
    metric: str
    direction: str = "maximize"              # maximize | minimize
    practical_margin: float = 0.0
    evaluator_id: str = ""

    def __post_init__(self):
        if self.direction not in ("maximize", "minimize"):
            raise SolutionRecordError(
                f"direction {self.direction!r} must be maximize or minimize")
        if not self.evaluator_id:
            raise SolutionRecordError(
                "an evaluation names its evaluator — an unattributed score "
                "cannot be checked for independence")

    def better(self, a: float, b: float) -> bool:
        if abs(a - b) <= self.practical_margin:
            return False                     # practically equivalent
        return a > b if self.direction == "maximize" else a < b


@dataclass
class SolutionCandidate:
    """One proposed Solution under evaluation."""
    candidate_id: str
    spec_ref: str
    author_id: str = ""                      # who produced it
    score: "float | None" = None
    evaluated_by: str = ""
    notes: str = ""

    @property
    def scored(self) -> bool:
        return self.score is not None and bool(self.evaluated_by)


@dataclass
class SolutionPortfolio:
    """The set of candidates competing for one obligation."""
    portfolio_id: str
    candidates: list = field(default_factory=list)
    evaluation: "SolutionEvaluationSpec | None" = None

    def add(self, candidate: SolutionCandidate) -> None:
        self.candidates.append(candidate)

    def select(self, *, ledger=None) -> "SolutionCandidate | None":
        """Choose the winner — on evidence, never on authorship.

        Refuses to select an unscored candidate, refuses a score produced by
        the candidate's own author, and returns None on an empty or wholly
        unscored portfolio rather than inventing a winner."""
        if self.evaluation is None:
            raise SolutionRecordError(
                "a portfolio selects against an evaluation spec; without one "
                "'best' has no meaning")
        eligible = []
        for c in self.candidates:
            if not c.scored:
                continue
            if c.evaluated_by and c.author_id and c.evaluated_by == c.author_id:
                raise SolutionRecordError(
                    f"candidate {c.candidate_id!r} was scored by its own "
                    "author — no component approves its own candidate")
            eligible.append(c)
        if not eligible:
            return None
        best = eligible[0]
        for c in eligible[1:]:
            if self.evaluation.better(c.score, best.score):
                best = c
        if ledger is not None:
            ledger.record(loop_id=self.portfolio_id,
                          event="solution_finalized",
                          solution=best.candidate_id,
                          among=len(eligible), metric=self.evaluation.metric)
        return best


@dataclass
class SolutionPackageManifest:
    """What actually ships, digested so it is checkable later."""
    package_id: str
    solution_ref: str
    loops: tuple = ()
    version: str = "1.0.0"

    @property
    def digest(self) -> str:
        return _digest({"package_id": self.package_id,
                        "solution_ref": self.solution_ref,
                        "loops": list(self.loops), "version": self.version})

    def to_record(self) -> dict:
        return {"record_type": "solution_package_manifest/v1",
                "package_id": self.package_id,
                "solution_ref": self.solution_ref,
                "loops": list(self.loops), "version": self.version,
                "digest": self.digest}


@dataclass
class SolutionRunReceipt:
    """Evidence that one Solution actually ran, and what it cost."""
    run_id: str
    solution_ref: str
    accepted: bool
    loops_run: int = 0
    model_calls: int = 0
    wall_seconds: float = 0.0
    package_digest: str = ""

    def to_record(self) -> dict:
        return {"record_type": "solution_run_receipt/v1", "run_id": self.run_id,
                "solution_ref": self.solution_ref, "accepted": self.accepted,
                "loops_run": self.loops_run, "model_calls": self.model_calls,
                "wall_seconds": round(self.wall_seconds, 3),
                "package_digest": self.package_digest}


def evaluate_candidate(candidate: SolutionCandidate, score: float, *,
                       evaluation: SolutionEvaluationSpec,
                       ledger=None) -> SolutionCandidate:
    """Attach a score AND its evaluator — a score without attribution cannot
    be checked for independence, so it is refused at the door."""
    if candidate.author_id and evaluation.evaluator_id == candidate.author_id:
        raise SolutionRecordError(
            f"{evaluation.evaluator_id!r} authored candidate "
            f"{candidate.candidate_id!r} and cannot also score it")
    candidate.score = float(score)
    candidate.evaluated_by = evaluation.evaluator_id
    if ledger is not None:
        ledger.record(loop_id=candidate.candidate_id,
                      event="solution_candidate_created",
                      solution=candidate.candidate_id,
                      loops=0, ensemble=evaluation.metric)
    return candidate


def package_solution(solution_ref: str, loops, *, package_id: str = "",
                     version: str = "1.0.0") -> SolutionPackageManifest:
    return SolutionPackageManifest(
        package_id=package_id or f"pkg.{solution_ref}",
        solution_ref=solution_ref, loops=tuple(loops), version=version)


def record_run(run_id: str, manifest: SolutionPackageManifest, *,
               accepted: bool, loops_run: int = 0, model_calls: int = 0,
               wall_seconds: float = 0.0) -> SolutionRunReceipt:
    return SolutionRunReceipt(
        run_id=run_id, solution_ref=manifest.solution_ref, accepted=accepted,
        loops_run=loops_run, model_calls=model_calls,
        wall_seconds=wall_seconds, package_digest=manifest.digest)


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    from ..loop.recursive_loop import LoopLedger

    ev = SolutionEvaluationSpec(metric="accuracy", direction="maximize",
                                practical_margin=0.005,
                                evaluator_id="independent_grader")
    a = SolutionCandidate("cand.a", "solution://a", author_id="builder_1")
    b = SolutionCandidate("cand.b", "solution://b", author_id="builder_2")
    evaluate_candidate(a, 0.81, evaluation=ev)
    evaluate_candidate(b, 0.87, evaluation=ev)

    lg = LoopLedger()
    port = SolutionPortfolio("port.1", [a, b], ev)
    winner = port.select(ledger=lg)
    check("a_portfolio_selects_on_evidence_not_authorship",
          winner is b and winner.evaluated_by == "independent_grader"
          and any(e.get("event") == "solution_finalized" for e in lg.events),
          f"{winner.candidate_id} won on {ev.metric}")

    # practical margin: a difference inside it is NOT better
    check("practical_equivalence_is_not_a_win",
          not ev.better(0.870, 0.868) and ev.better(0.900, 0.868),
          "0.002 apart is equivalent at a 0.005 margin")

    # ADVERSARIAL: a candidate cannot be scored or selected by its own author
    self_scored = False
    try:
        evaluate_candidate(SolutionCandidate("c", "s://c", author_id="me"),
                           0.99, evaluation=SolutionEvaluationSpec(
                               metric="accuracy", evaluator_id="me"))
    except SolutionRecordError:
        self_scored = True
    unattributed = False
    try:
        SolutionEvaluationSpec(metric="accuracy", evaluator_id="")
    except SolutionRecordError:
        unattributed = True
    check("a_candidate_cannot_score_or_select_itself",
          self_scored and unattributed,
          "no component approves its own candidate, applied to Solutions")

    # empty / unscored portfolios abstain rather than inventing a winner
    empty = SolutionPortfolio("port.empty", [], ev).select()
    unscored = SolutionPortfolio(
        "port.raw", [SolutionCandidate("x", "s://x")], ev).select()
    no_spec = False
    try:
        SolutionPortfolio("port.nospec", [a]).select()
    except SolutionRecordError:
        no_spec = True
    check("an_empty_or_unscored_portfolio_abstains",
          empty is None and unscored is None and no_spec,
          "abstention beats an invented winner")

    # package + receipt: what shipped is digested and what ran is evidenced
    man = package_solution("solution://b", ["prep", "score"])
    rec = record_run("run.1", man, accepted=True, loops_run=2, model_calls=0)
    check("package_manifest_and_run_receipt_are_checkable",
          len(man.digest) == 64
          and rec.to_record()["package_digest"] == man.digest
          and rec.to_record()["accepted"] is True
          and package_solution("solution://b", ["prep", "score"]).digest
          == man.digest,
          "same contents give the same digest; the receipt names it")

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
