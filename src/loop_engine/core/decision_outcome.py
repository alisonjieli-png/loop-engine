"""What became of a decision after it was made.

A decision record says what was chosen and who chose it. On its own that
supports one kind of finding — how often something was picked — and not the
one that matters: whether picking it helped. A corpus of choices without
outcomes teaches that models compacted context 63% of the time. A corpus with
outcomes teaches that compaction succeeded 72% of the time here, cost rework
31% of the time there, and never worked on this shape of task at all. Only the
second can become policy; the first is a popularity table.

So a decision is joined forward, in stages, as the run learns what happened:

    proposed      the choice, and what it expected to observe
    admitted      what survived validation, and what was refused
    executed      what actually ran
    observed      what came back, against what was expected
    verified      whether a check accepted it
    contributed   whether the task ultimately succeeded

Each stage may be missing. A decision whose outcome never arrived is recorded
as unresolved rather than as a success, because an unfinished join that reads
as agreement is how a corpus quietly fills with confirmations.

Later invalidation is kept as new evidence rather than as a correction: a
choice that looked right for an hour and was overturned is one of the more
informative rows in the set, and editing it away would remove exactly what a
future policy needs to avoid.

Owns:
    - DecisionOutcome: one decision's fate, joined as far as it got.
    - OutcomeLedger: the run's joins, and what can be concluded from them.

Does not own: making decisions (core.semantic_decision), the choice contract
(core.choice), or judging correctness (verification).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

DECISION_OUTCOME_RECORD_TYPE = "decision_outcome/v1"
OUTCOME_LEDGER_RECORD_TYPE = "decision_outcome_ledger/v1"

#: How far a decision has been followed. Ordered: a later stage implies the
#: earlier ones were reached.
PROPOSED, ADMITTED, EXECUTED, OBSERVED, VERIFIED, CONTRIBUTED = (
    "proposed", "admitted", "executed", "observed", "verified", "contributed")
OUTCOME_STAGES = (PROPOSED, ADMITTED, EXECUTED, OBSERVED, VERIFIED,
                  CONTRIBUTED)

#: What the observation did to the expectation the decision carried.
MATCHED, DIVERGED, UNOBSERVED = "matched", "diverged", "unobserved"

#: How a decision is counted once its fate is known. The third is not a
#: failure to measure but a measurement: most decisions in most runs end here,
#: and a reading that omits it invites conclusions the evidence cannot carry.
HELPED, HURT, UNKNOWN = "helped", "hurt", "unknown"


class DecisionOutcomeError(ValueError):
    """A decision outcome violated its contract."""


@dataclass
class DecisionOutcome:
    """One decision, joined forward to whatever became of it.

    Mutable on purpose: a decision's fate arrives in pieces, over minutes or
    passes, and forcing it to be complete at construction would mean either
    inventing the missing parts or not recording the decision at all.
    """

    decision_id: str
    run_id: str
    decision_kind: str = ""
    owner: str = ""
    selected: str = ""
    expected_observation: str = ""

    stage: str = PROPOSED
    refused: tuple[str, ...] = ()
    executed_action: str = ""
    observation: str = ""
    expectation_result: str = UNOBSERVED
    verification_passed: "bool | None" = None
    task_succeeded: "bool | None" = None

    #: Kept rather than corrected. A choice that was right and then overturned
    #: is worth more to a future policy than one that was simply right.
    invalidated_later: bool = False
    invalidation_reason: str = ""

    model_calls: int = 0
    elapsed_seconds: "float | None" = None

    def __post_init__(self):
        if not str(self.decision_id or "").strip():
            raise DecisionOutcomeError("a decision outcome needs a decision_id")
        if self.stage not in OUTCOME_STAGES:
            raise DecisionOutcomeError(f"unknown stage {self.stage!r}")

    def advance(self, stage: str, **fields) -> "DecisionOutcome":
        """Record the next thing known about this decision.

        A stage never moves backwards. A late report about an earlier stage
        still records its fields, because the information is real even when
        it arrives out of order.
        """
        if stage not in OUTCOME_STAGES:
            raise DecisionOutcomeError(f"unknown stage {stage!r}")
        for name, value in fields.items():
            if not hasattr(self, name):
                raise DecisionOutcomeError(f"unknown outcome field {name!r}")
            setattr(self, name, value)
        if OUTCOME_STAGES.index(stage) > OUTCOME_STAGES.index(self.stage):
            self.stage = stage
        return self

    @property
    def resolved(self) -> bool:
        """Whether anything is known about what this decision led to."""
        return OUTCOME_STAGES.index(self.stage) >= OUTCOME_STAGES.index(
            OBSERVED)

    @property
    def helped(self) -> "bool | None":
        """Whether this decision is known to have helped. None is honest.

        Verification is the evidence, and the task outcome qualifies it: a
        decision that passed its check inside a run that then failed is not
        known to have helped, and calling it a success would be the exact
        overclaim this record exists to prevent.
        """
        if self.invalidated_later:
            return False
        if self.verification_passed is None:
            return None
        if not self.verification_passed:
            return False
        if self.task_succeeded is None:
            return None
        return bool(self.task_succeeded)

    @property
    def verdict(self) -> str:
        """This decision's fate as one named value rather than a tri-state.

        Callers counting outcomes should not have to branch on an absent
        boolean; unknown is a result here, not a missing one.
        """
        helped = self.helped
        if helped is None:
            return UNKNOWN
        return HELPED if helped else HURT

    def to_dict(self) -> dict:
        return {
            "record_type": DECISION_OUTCOME_RECORD_TYPE,
            "decision_id": self.decision_id, "run_id": self.run_id,
            "decision_kind": self.decision_kind, "owner": self.owner,
            "selected": self.selected,
            "expected_observation": self.expected_observation,
            "stage": self.stage, "refused": list(self.refused),
            "executed_action": self.executed_action,
            "observation": self.observation,
            "expectation_result": self.expectation_result,
            "verification_passed": self.verification_passed,
            "task_succeeded": self.task_succeeded,
            "invalidated_later": self.invalidated_later,
            "invalidation_reason": self.invalidation_reason,
            "helped": self.helped,
            "model_calls": self.model_calls,
            "elapsed_seconds": self.elapsed_seconds,
        }


@dataclass
class OutcomeLedger:
    """Every decision of a run, and how far each was followed."""

    outcomes: dict = field(default_factory=dict)
    #: Whether verification was joined per decision or for the run as a
    #: whole. A rate computed from run-level joins describes chains, not
    #: individual choices, and a reader should be told which they have.
    verification_granularity: str = ""

    def open(self, decision, **fields) -> DecisionOutcome:
        """Begin following one decision. Accepts a record or its fields."""
        if hasattr(decision, "decision_id"):
            fields = {
                "decision_kind": getattr(decision, "decision_kind", ""),
                "owner": getattr(decision, "owner", ""),
                "selected": getattr(decision, "selected", ""),
                "expected_observation": getattr(
                    decision, "expected_observation", ""),
                "run_id": getattr(decision, "run_id", ""), **fields}
            decision = decision.decision_id
        outcome = DecisionOutcome(decision_id=str(decision), **fields)
        self.outcomes[outcome.decision_id] = outcome
        return outcome

    def advance(self, decision_id: str, stage: str, **fields):
        """Record what became of one decision, if it is being followed."""
        outcome = self.outcomes.get(str(decision_id))
        # Advancing a decision nobody followed is not an error: instrumentation
        # that raises on its own gaps stops the run it was meant to observe.
        return outcome.advance(stage, **fields) if outcome else None

    def close_run(self, task_succeeded: "bool | None",
                  verification_passed: "bool | None" = None,
                  granularity: str = "run") -> None:
        """Tell every followed decision how the run it belonged to ended.

        Applied to all of them because a decision's contribution is not
        knowable from the decision alone; a run that failed casts its result
        over every choice that led there, including the reasonable ones.
        """
        self.verification_granularity = granularity
        for outcome in self.outcomes.values():
            outcome.task_succeeded = task_succeeded
            # A run-level verdict is the finest verification this run
            # produced. Applying it to every decision is coarse and is
            # recorded as coarse: it says the chain these decisions formed
            # was checked, not that each was checked on its own.
            if (verification_passed is not None
                    and outcome.verification_passed is None):
                outcome.advance(VERIFIED,
                                verification_passed=verification_passed)
            if (task_succeeded is not None
                    and outcome.verification_passed is not None):
                outcome.advance(CONTRIBUTED)

    def by_stage(self) -> dict:
        counts = {stage: 0 for stage in OUTCOME_STAGES}
        for outcome in self.outcomes.values():
            counts[outcome.stage] += 1
        return counts

    def helped_by_kind(self) -> dict:
        """Per decision kind: how many helped, hurt, and remain unknown.

        The unknown column is reported first among equals on purpose. It is
        usually the largest, and a reading that hides it invites conclusions
        the evidence does not carry.
        """
        rows: dict = {}
        for outcome in self.outcomes.values():
            row = rows.setdefault(outcome.decision_kind or "unnamed",
                                  {HELPED: 0, HURT: 0, UNKNOWN: 0})
            row[outcome.verdict] += 1
        return dict(sorted(rows.items()))

    def to_dict(self) -> dict:
        total = len(self.outcomes)
        resolved = sum(1 for item in self.outcomes.values() if item.resolved)
        known = [item.helped for item in self.outcomes.values()
                 if item.helped is not None]
        return {
            "record_type": OUTCOME_LEDGER_RECORD_TYPE,
            "decisions_followed": total,
            "reached_an_observation": resolved,
            "outcome_known": len(known),
            "helped": sum(1 for item in known if item),
            "by_stage": self.by_stage(),
            "by_decision_kind": self.helped_by_kind(),
            "invalidated_later": sum(
                1 for item in self.outcomes.values() if item.invalidated_later),
            "verification_granularity": self.verification_granularity,
            "reading": _reading(total, resolved, known),
        }


def _reading(total: int, resolved: int, known: list) -> str:
    """One sentence about what these joins can and cannot support."""
    if not total:
        return "no decisions were followed, so nothing here bears on outcomes"
    if not known:
        return (f"{total} decisions were followed and none reached a known "
                "outcome; this run says what was chosen and nothing about "
                "whether it helped")
    share = f"{len(known)} of {total}"
    if len(known) < total // 2:
        return (f"only {share} decisions have a known outcome, so any rate "
                "computed from them describes the resolved minority")
    return (f"{share} decisions have a known outcome, of which "
            f"{sum(1 for item in known if item)} helped")


def self_test() -> dict:
    """Offline checks. No provider is contacted."""
    tests = []

    def check(name, ok, detail=""):
        tests.append({"test": name, "passed": bool(ok), "detail": detail})

    empty = OutcomeLedger()
    check("a ledger with no joins concludes nothing",
          empty.to_dict()["outcome_known"] == 0
          and "nothing here bears on outcomes" in empty.to_dict()["reading"])

    ledger = OutcomeLedger()
    one = ledger.open("d1", run_id="r", decision_kind="choose_repair",
                      owner="llm", selected="retry_same_route",
                      expected_observation="a schema-valid answer")
    check("a decision with no outcome yet is not counted as a success",
          one.helped is None and not one.resolved)

    ledger.advance("d1", EXECUTED, executed_action="retry")
    ledger.advance("d1", OBSERVED, observation="answer arrived",
                   expectation_result=MATCHED)
    check("a decision followed to an observation is resolved",
          one.resolved and one.helped is None)

    ledger.advance("d1", VERIFIED, verification_passed=True)
    check("passing a check is still not knowing the task succeeded",
          one.helped is None,
          "verification alone must not read as contribution")

    ledger.close_run(task_succeeded=True)
    check("the run's result decides the contribution",
          one.helped is True and one.stage == CONTRIBUTED)

    failed = OutcomeLedger()
    two = failed.open("d2", run_id="r", decision_kind="choose_repair")
    failed.advance("d2", VERIFIED, verification_passed=True)
    failed.close_run(task_succeeded=False)
    check("a checked decision inside a failed run did not help",
          two.helped is False,
          "a locally valid choice in a run that failed is not a success")

    overturned = OutcomeLedger()
    three = overturned.open("d3", run_id="r", decision_kind="interpret_task")
    overturned.advance("d3", VERIFIED, verification_passed=True)
    overturned.close_run(task_succeeded=True)
    three.invalidated_later = True
    three.invalidation_reason = "the target column was wrong"
    check("a later invalidation overrides an earlier success",
          three.helped is False
          and overturned.to_dict()["invalidated_later"] == 1)

    mixed = OutcomeLedger()
    for index in range(4):
        mixed.open(f"m{index}", run_id="r", decision_kind="select_context")
    mixed.advance("m0", VERIFIED, verification_passed=True)
    mixed.close_run(task_succeeded=True)
    value = mixed.to_dict()
    coarse = OutcomeLedger()
    for index in range(3):
        coarse.open(f"c{index}", run_id="r", decision_kind="choose_repair")
    coarse.close_run(task_succeeded=True, verification_passed=True)
    value_coarse = coarse.to_dict()
    check("a run-level verdict reaches every followed decision",
          value_coarse["outcome_known"] == 3 and value_coarse["helped"] == 3)
    check("a coarse join says it is coarse",
          value_coarse["verification_granularity"] == "run",
          "a rate from run-level joins describes chains, not choices")

    check("a partial join says it describes only the resolved minority",
          value["outcome_known"] == 1
          and "resolved minority" in value["reading"])
    check("the unknown column is reported per decision kind",
          value["by_decision_kind"]["select_context"]
          == {"helped": 1, "hurt": 0, "unknown": 3})

    check("a stage never moves backwards",
          ledger.outcomes["d1"].advance(PROPOSED).stage == CONTRIBUTED)
    check("advancing a decision nobody followed is not an error",
          ledger.advance("never-seen", VERIFIED) is None)

    bad = False
    try:
        DecisionOutcome(decision_id="d", run_id="r", stage="finished")
    except DecisionOutcomeError:
        bad = True
    check("an unknown stage is refused", bad)

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "decision_outcome_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=1))
