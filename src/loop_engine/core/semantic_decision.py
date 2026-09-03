"""Who decided what this run should do, recorded so the answer can be counted.

A run can be entirely composed of Loops and still not be an LLM-led network.
The question that separates the two is not whether an operation executed
inside a Loop but who made the task-conditioned choice the operation carries:
what the task means, what to try next, which evidence matters, whether a
prior capability applies, whether the result is good enough.

A task-conditioned decision is one whose correct answer depends on the
content, objective, uncertainty or evolving state of *this* task. Deciding
that a request is valid JSON, that a path sits inside the workspace, or that
a digest matches is not one of those; those are mechanics and they should stay
deterministic. Deciding that the target column is `exam_score`, that the
validation split leaks, or that a run should stop, is.

This module owns the record of the first kind and the arithmetic over it.
It does not require hidden reasoning: a decision carries the alternatives that
were open, the one taken, a short reason, and what was expected to follow.

Owns:
    - SemanticDecisionRecord: one task-conditioned decision and its owner.
    - SemanticAutonomyTally: the per-run counts and the coverage they imply.
    - DECISION_OWNERS: who a decision can belong to.

Does not own: making the decisions (the Practitioner's Loops), or judging
whether one was correct (verification). A low coverage number is a finding
about the architecture, never about the answer that came out of it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

SEMANTIC_DECISION_RECORD_TYPE = "semantic_decision/v1"
SEMANTIC_AUTONOMY_RECORD_TYPE = "semantic_autonomy_coverage/v1"

#: Who a task-conditioned decision belongs to. The first two are the ones that
#: count toward autonomy; the third is the one worth finding.
DECISION_OWNERS = ("llm", "user", "deterministic")

#: Decision kinds seen so far. Deliberately not closed: a run that makes a
#: kind of choice nobody enumerated should be recorded as having made it, not
#: refused for lacking a name. An unknown kind is counted and reported.
KNOWN_DECISION_KINDS = (
    "interpret_task", "select_next_operation", "decompose", "generate_question",
    "select_context", "select_capability", "select_tool", "form_hypothesis",
    "diagnose_failure", "choose_repair", "compare_solutions",
    "propose_stop", "propose_learning", "mutate_graph", "apply_prior_solution",
)


class SemanticDecisionError(ValueError):
    """A semantic decision record violated its contract."""


@dataclass(frozen=True)
class SemanticDecisionRecord:
    """One task-conditioned decision, and who made it.

    ``alternatives`` is what was actually open at the moment of choosing. A
    decision with one alternative is not a decision, and recording it as one
    inflates the coverage number; that case is worth seeing rather than
    hiding, so it is recorded and counted separately instead of refused.
    """

    decision_id: str
    run_id: str
    loop_id: str
    decision_kind: str
    owner: str
    selected: str
    alternatives: tuple[str, ...] = ()
    reason_summary: str = ""
    evidence_refs: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    uncertainties: tuple[str, ...] = ()
    expected_observation: str = ""
    model_identity: str = ""
    context_manifest_ref: str = ""
    branch_id: str = ""
    state_snapshot_ref: str = ""

    def __post_init__(self):
        if self.owner not in DECISION_OWNERS:
            raise SemanticDecisionError(
                f"decision owner {self.owner!r} is not one of "
                f"{list(DECISION_OWNERS)}")
        for name in ("decision_id", "run_id", "decision_kind", "selected"):
            if not str(getattr(self, name) or "").strip():
                raise SemanticDecisionError(f"{name} is required")

    @property
    def unattributed(self) -> bool:
        """Whether this decision was made without an LLM or a person."""
        return self.owner == "deterministic"

    @property
    def uncontested(self) -> bool:
        """Whether anything else was actually open at the time."""
        return len(self.alternatives) < 2

    def to_dict(self) -> dict:
        return {
            "record_type": SEMANTIC_DECISION_RECORD_TYPE,
            "decision_id": self.decision_id,
            "run_id": self.run_id,
            "loop_id": self.loop_id,
            "branch_id": self.branch_id,
            "decision_kind": self.decision_kind,
            "owner": self.owner,
            "selected": self.selected,
            "alternatives_considered": list(self.alternatives),
            "reason_summary": self.reason_summary,
            "evidence_refs": list(self.evidence_refs),
            "assumptions": list(self.assumptions),
            "uncertainties": list(self.uncertainties),
            "expected_observation": self.expected_observation,
            "model_identity": self.model_identity,
            "context_manifest_ref": self.context_manifest_ref,
            "state_snapshot_ref": self.state_snapshot_ref,
        }


@dataclass
class SemanticAutonomyTally:
    """What one run's task-conditioned decisions add up to.

    Coverage is the share of task-conditioned decisions attributable to an
    LLM or an explicit user instruction. It is a property of the architecture
    rather than of the answer: a run can score 1.0 and be wrong, or 0.4 and be
    right. What a low number says is that something other than reasoning chose
    what this run did.
    """

    decisions: list = field(default_factory=list)
    #: Counted apart because each is a different way the number can mislead.
    unattributed_kinds: dict = field(default_factory=dict)
    uncontested: int = 0

    def note(self, record: SemanticDecisionRecord) -> None:
        """Add one decision to the run's account."""
        self.decisions.append(record)
        if record.unattributed:
            kind = record.decision_kind
            self.unattributed_kinds[kind] = (
                self.unattributed_kinds.get(kind, 0) + 1)
        if record.uncontested:
            self.uncontested += 1

    @property
    def total(self) -> int:
        return len(self.decisions)

    @property
    def attributable(self) -> int:
        return sum(1 for item in self.decisions if not item.unattributed)

    @property
    def coverage(self) -> "float | None":
        """The share owned by reasoning, or nothing when nothing was decided.

        A run with no recorded decisions has no coverage rather than perfect
        coverage. Returning 1.0 for an empty account would make the least
        instrumented run look like the most autonomous one.
        """
        if not self.decisions:
            return None
        return round(self.attributable / self.total, 4)

    def by_owner(self) -> dict:
        counts = {owner: 0 for owner in DECISION_OWNERS}
        for item in self.decisions:
            counts[item.owner] += 1
        return counts

    def by_kind(self) -> dict:
        counts: dict = {}
        for item in self.decisions:
            counts[item.decision_kind] = counts.get(item.decision_kind, 0) + 1
        return dict(sorted(counts.items()))

    def unnamed_kinds(self) -> list:
        """Decision kinds this module had not anticipated. Not an error."""
        return sorted({item.decision_kind for item in self.decisions}
                      - set(KNOWN_DECISION_KINDS))

    def to_dict(self) -> dict:
        return {
            "record_type": SEMANTIC_AUTONOMY_RECORD_TYPE,
            "semantic_autonomy_coverage": self.coverage,
            "decisions_recorded": self.total,
            "attributable_to_reasoning": self.attributable,
            "by_owner": self.by_owner(),
            "by_decision_kind": self.by_kind(),
            # The ones worth reading before believing the coverage figure.
            "unattributed_by_kind": dict(sorted(
                self.unattributed_kinds.items())),
            "uncontested_decisions": self.uncontested,
            "decision_kinds_not_anticipated": self.unnamed_kinds(),
            "reading": _reading(self),
        }


def _reading(tally: SemanticAutonomyTally) -> str:
    """One sentence a person can act on, or the reason there isn't one."""
    if not tally.decisions:
        return ("no task-conditioned decisions were recorded, so this run "
                "says nothing about semantic ownership either way")
    if tally.unattributed_kinds:
        worst = max(tally.unattributed_kinds.items(), key=lambda row: row[1])
        return (f"{tally.attributable} of {tally.total} decisions were "
                f"reasoned; the largest unattributed kind is {worst[0]!r} "
                f"({worst[1]})")
    if tally.uncontested == tally.total:
        return (f"all {tally.total} decisions were reasoned, but none had a "
                "second alternative open, so the coverage figure is weak "
                "evidence on its own")
    return (f"all {tally.total} recorded decisions were owned by reasoning, "
            f"{tally.total - tally.uncontested} of them with alternatives")


def note_decision(services, **fields) -> None:
    """Record who made one task-conditioned decision, and never fail on it.

    Instrumentation that can end a run is worse than no instrumentation: an
    early version of this raised NameError from inside orientation and turned
    two passing fixture solves into unsolved runs. Observation must not be
    able to change the outcome it observes, so every error here becomes a
    diagnostic and the run continues uninstrumented for that decision.
    """
    from ..loop.kernel_runtime import current_kernel_owner
    try:
        active = current_kernel_owner()
        record = SemanticDecisionRecord(
            run_id=services.run_id,
            loop_id=getattr(active, "loop_id", ""),
            **fields)
        services.semantic_decisions.note(record)
        # Followed from here: a decision never joined to what came of it
        # says what was chosen and nothing about whether it was right.
        services.decision_outcomes.open(record)
    except Exception as exc:                            # noqa: BLE001
        try:
            services.diagnostic("semantic_decision_not_recorded", {
                "error_type": type(exc).__name__,
                "decision_kind": str(fields.get("decision_kind", ""))})
        except Exception:                               # noqa: BLE001
            pass


def self_test() -> dict:
    """Offline checks. No provider is contacted."""
    tests = []

    def check(name, ok, detail=""):
        tests.append({"test": name, "passed": bool(ok), "detail": detail})

    def record(owner="llm", kind="select_next_operation", alts=("a", "b")):
        return SemanticDecisionRecord(
            decision_id="d1", run_id="r1", loop_id="loop1",
            decision_kind=kind, owner=owner, selected="a", alternatives=alts)

    refused = False
    try:
        record(owner="the_runtime_felt_like_it")
    except SemanticDecisionError:
        refused = True
    check("an owner outside the register is refused", refused)

    empty = SemanticAutonomyTally()
    check("an empty run has no coverage rather than perfect coverage",
          empty.coverage is None
          and "says nothing about semantic ownership" in empty.to_dict()[
              "reading"])

    mixed = SemanticAutonomyTally()
    for _ in range(3):
        mixed.note(record())
    mixed.note(record(owner="deterministic", kind="apply_prior_solution"))
    value = mixed.to_dict()
    check("coverage counts reasoning against every recorded decision",
          value["semantic_autonomy_coverage"] == 0.75
          and value["by_owner"] == {"llm": 3, "user": 0, "deterministic": 1})
    check("the unattributed decision is named by kind, not just counted",
          value["unattributed_by_kind"] == {"apply_prior_solution": 1}
          and "apply_prior_solution" in value["reading"])

    thin = SemanticAutonomyTally()
    thin.note(record(alts=("only_one",)))
    check("a decision with nothing else open is counted but flagged",
          thin.to_dict()["semantic_autonomy_coverage"] == 1.0
          and thin.to_dict()["uncontested_decisions"] == 1
          and "weak evidence" in thin.to_dict()["reading"])

    novel = SemanticAutonomyTally()
    novel.note(record(kind="inspect_temporal_leakage_risk"))
    check("a decision kind nobody anticipated is recorded, not refused",
          novel.to_dict()["decision_kinds_not_anticipated"]
          == ["inspect_temporal_leakage_risk"]
          and novel.coverage == 1.0)

    check("a user instruction counts as owning a decision",
          SemanticAutonomyTally.__call__ is not None
          and record(owner="user").unattributed is False)

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "semantic_decision_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=1))
