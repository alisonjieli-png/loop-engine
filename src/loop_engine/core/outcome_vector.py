"""What a decision actually contributed, kept apart from how its run ended.

A run succeeds, so every decision inside it is marked as having helped. That
is the sentence this module exists to stop being true.

A successful run contains wasted loops, redundant retrieval, and locally
correct work that changed nothing. A failed run contains good orientation, a
sound diagnosis, and a valid experiment whose only crime was arriving after
the budget ran out. Training a shortcut on a run-level boolean teaches it
that everything the winning run touched was wise, including the parts that
were abandoned, and that everything the losing run touched was foolish,
including the part that was right.

So credit is a vector of separate signals rather than one boolean, and every
signal may be unknown. Unknown is not false. A stage nobody verified is not a
stage that failed verification, and the difference decides whether the record
is evidence or noise.

Three verdicts, not two. A decision that was locally correct and reached
nothing is NEUTRAL, not HURT: the wasted loop and the harmful one need
telling apart, because one is a cost and the other is a defect.

The granularity travels beside the evidence. When the only thing known about a
stage is that its run succeeded, the stage credit remains UNKNOWN. The run
outcome is still recorded, but it is not converted into a label about the
stage. Anyone joining these rows can therefore use the run outcome as context
without accidentally training on it as local contribution.

Owns:
    - OutcomeVector: the separate signals, their granularity, and the verdict.
    - observe(): fold a newly known signal in, recording disagreement.
    - SIGNAL_SCOPES: which signals are stage-local, derived from the fields.

Does not own: when signals are observed (the Loops that verify, consume, and
close), storage (core.stage_store), or any authority to decide a run's fate.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, fields, replace

OUTCOME_VECTOR_RECORD_TYPE = "outcome_vector/v1"

#: What a decision did. `NEUTRAL` is the one the run-level boolean could not
#: express: correct work that reached nothing.
HELPED, NEUTRAL, HURT, UNKNOWN = "helped", "neutral", "hurt", "unknown"
CREDIT_VERDICTS = (HELPED, NEUTRAL, HURT, UNKNOWN)

#: How much the verdict is actually about this stage. `RUN` means the only
#: evidence is how the whole run ended, which is a fact about the chain the
#: stage sat in rather than about the stage.
STAGE, RUN, NONE = "stage", "run", "none"
CREDIT_GRANULARITIES = (STAGE, RUN, NONE)

#: Scope markers used in field metadata. A signal is stage-local when it was
#: observed at this decision's own boundary.
_STAGE_LOCAL = "stage_local"
_RUN_LEVEL = "run_level"


def _signal(scope: str, describes: str):
    return field(default=None, metadata={"scope": scope, "describes": describes})


@dataclass(frozen=True)
class OutcomeVector:
    """The separate things that can be known about one decision's fate.

    Every signal is tri-valued. `None` means nobody looked, which is the
    common case early and must never be read as failure.
    """

    #: Did the answer satisfy the contract it was given? A mechanical fact
    #: about the response, and deliberately not the same question as whether
    #: the work was any good: well-formed output that is wrong passes this
    #: and fails the next one.
    output_admitted: bool | None = _signal(
        _STAGE_LOCAL, "the answer satisfied the contract it was given")

    #: Did the work this decision produced hold up when it was checked?
    local_verification: bool | None = _signal(
        _STAGE_LOCAL, "the work held up when it was verified")

    #: Did anything later actually consume what this decision produced?
    downstream_use: bool | None = _signal(
        _STAGE_LOCAL, "later work consumed this decision's output")

    #: Did it end up on the branch that was accepted, or on one abandoned?
    branch_contribution: bool | None = _signal(
        _STAGE_LOCAL, "the decision reached the accepted branch")

    #: Was it revised, retracted, or contradicted after the fact?
    later_invalidated: bool | None = _signal(
        _STAGE_LOCAL, "the decision was retracted or contradicted afterwards")

    #: How the run that contained it ended. True of every stage in that run,
    #: which is exactly why it cannot stand alone as stage credit.
    task_outcome: bool | None = _signal(
        _RUN_LEVEL, "the run containing the decision succeeded")

    #: Signals that were observed twice with different answers. Kept rather
    #: than raised: two parts of the system disagreeing about one stage is
    #: information, and losing it to an exception loses the run as well.
    contradictions: tuple[str, ...] = ()

    @property
    def known(self) -> tuple[str, ...]:
        """Signals somebody actually observed."""
        return tuple(item.name for item in _signal_fields()
                     if getattr(self, item.name) is not None)

    @property
    def unknown(self) -> tuple[str, ...]:
        """Signals nobody looked at. Not failures."""
        return tuple(item.name for item in _signal_fields()
                     if getattr(self, item.name) is None)

    @property
    def contradicted(self) -> bool:
        """Whether any signal was observed with two different answers."""
        return bool(self.contradictions)

    @property
    def granularity(self) -> str:
        """How much this verdict is about the stage rather than the run."""
        if any(getattr(self, item.name) is not None
               for item in _signal_fields()
               if item.metadata["scope"] == _STAGE_LOCAL):
            return STAGE
        return RUN if self.task_outcome is not None else NONE

    @property
    def credit(self) -> str:
        """What this decision did, on the evidence available.

        Ordered by how strongly each signal speaks. Being retracted later
        outranks everything, including the run succeeding: a decision the
        system itself took back did not help, whatever happened around it.
        """
        # Disputed evidence is not positive or negative training material.
        # Keeping the first observation preserves the chronology, but a
        # consumer must not turn that first writer into an authority winner.
        if self.contradicted:
            return UNKNOWN
        if self.later_invalidated is True:
            return HURT
        if self.output_admitted is False:
            return HURT
        if self.local_verification is False:
            return HURT
        if (self.downstream_use is False
                or self.branch_contribution is False):
            # Only verified work can be called a harmless dead end. Without
            # that local check, an abandoned answer may simply be wrong.
            return NEUTRAL if self.local_verification is True else UNKNOWN
        if self.local_verification is True:
            # Local verification is the first signal that establishes the
            # stage's own work held up. Admission, consumption, and placement
            # on a branch do not establish that by themselves.
            return HELPED
        # A run outcome, schema admission, downstream consumption, or branch
        # placement alone never becomes stage credit. They remain useful
        # dimensions, but local contribution has not been established.
        return UNKNOWN

    @property
    def reading(self) -> str:
        """What this row is worth, in one sentence."""
        if self.granularity == NONE:
            return "nothing is known about this decision's outcome"
        if self.granularity == RUN:
            return ("only the run's outcome is known, so this describes the "
                    "chain the decision sat in, not the decision")
        seen = ", ".join(self.known)
        note = " (signals disagreed)" if self.contradicted else ""
        return f"{self.credit} on stage-local evidence: {seen}{note}"

    def to_dict(self) -> dict:
        payload = {"record_type": OUTCOME_VECTOR_RECORD_TYPE,
                   "credit": self.credit,
                   "granularity": self.granularity,
                   "known": list(self.known),
                   "unknown": list(self.unknown),
                   "contradictions": list(self.contradictions),
                   "reading": self.reading}
        for item in _signal_fields():
            payload[item.name] = getattr(self, item.name)
        return payload


def _signal_fields() -> tuple:
    """The tri-valued signals, taken from the dataclass rather than a list.

    A second hand-kept copy of this list would drift the first time a signal
    was added, and the drift would be silent.
    """
    return tuple(item for item in fields(OutcomeVector)
                 if item.metadata.get("scope"))


#: Which scope each signal belongs to, derived rather than restated.
SIGNAL_SCOPES = {item.name: item.metadata["scope"] for item in _signal_fields()}

#: What each signal means, for rendering to a model that must fill one in.
SIGNAL_DESCRIPTIONS = {item.name: item.metadata["describes"]
                       for item in _signal_fields()}


def observe(vector: OutcomeVector, **signals) -> OutcomeVector:
    """Fold newly observed signals into a vector.

    Re-stating a signal with the same value is ordinary: several parts of the
    system may notice the same thing. Stating it with a different value is a
    disagreement, and is recorded rather than raised — the run should not die
    because two observers differ, and the difference is worth keeping.
    """
    known = SIGNAL_SCOPES
    updates, clashes = {}, list(vector.contradictions)
    for name, value in signals.items():
        if name not in known:
            raise ValueError(
                f"unknown outcome signal {name!r}; "
                f"known signals are {', '.join(sorted(known))}")
        if value is None:
            continue
        if not isinstance(value, bool):
            raise ValueError(
                f"outcome signal {name!r} must be bool or None")
        current = getattr(vector, name)
        if current is not None and current != value:
            if name not in clashes:
                clashes.append(name)
            continue
        updates[name] = value
    return replace(vector, contradictions=tuple(clashes), **updates)


def self_test() -> dict:
    """Offline checks. No provider is contacted."""
    tests = []

    def check(name, ok, detail=""):
        tests.append({"test": name, "passed": bool(ok), "detail": detail})

    empty = OutcomeVector()
    check("a decision nobody looked at is unknown, not failed",
          empty.credit == UNKNOWN and empty.granularity == NONE,
          "unknown must never be read as false")

    run_only = OutcomeVector(task_outcome=True)
    check("a successful run alone leaves stage credit unknown",
          run_only.credit == UNKNOWN and run_only.granularity == RUN,
          "the run outcome is context, not a label about one stage")
    check("run-level credit says so in its reading",
          "not the decision" in run_only.reading)

    # The wasted loop inside a winning run.
    wasted = OutcomeVector(local_verification=True, branch_contribution=False,
                           task_outcome=True)
    check("correct work that reached nothing is neutral, not helped",
          wasted.credit == NEUTRAL,
          "the run-level boolean called this helped")
    check("a wasted loop is not counted as harmful either",
          wasted.credit != HURT,
          "a cost and a defect need telling apart")

    # The good decision inside a losing run.
    salvage = OutcomeVector(local_verification=True, branch_contribution=True,
                            task_outcome=False)
    check("a verified contributing decision in a failed run is not hurt",
          salvage.credit == HELPED and salvage.granularity == STAGE,
          "the run-level boolean called this hurt")

    retracted = OutcomeVector(local_verification=True, branch_contribution=True,
                              task_outcome=True, later_invalidated=True)
    check("a decision retracted later did not help, whatever the run did",
          retracted.credit == HURT,
          "later invalidation outranks every other signal")

    failed_check = OutcomeVector(local_verification=False, task_outcome=True)
    check("a decision that failed its own checks is hurt inside a good run",
          failed_check.credit == HURT)

    check("stage-local evidence outranks the run for granularity",
          OutcomeVector(downstream_use=True, task_outcome=True
                        ).granularity == STAGE)

    check("unknown signals are listed rather than assumed",
          set(OutcomeVector(task_outcome=True).unknown)
          == {"output_admitted", "local_verification", "downstream_use",
              "branch_contribution", "later_invalidated"})

    check("well-formed output that fails verification is not credited",
          OutcomeVector(output_admitted=True, local_verification=False,
                        task_outcome=True).credit == HURT,
          "passing a schema is not the same as being right")
    check("admission alone does not become positive stage credit",
          OutcomeVector(output_admitted=True).granularity == STAGE
          and OutcomeVector(output_admitted=True).credit == UNKNOWN,
          "schema-valid output can still be semantically wrong")
    check("failed admission is a local mechanical failure",
          OutcomeVector(output_admitted=False).credit == HURT)
    check("consumption alone does not become positive stage credit",
          OutcomeVector(downstream_use=True, task_outcome=True).credit == UNKNOWN,
          "using an unchecked answer does not prove it helped")
    check("branch placement alone does not become positive stage credit",
          OutcomeVector(branch_contribution=True,
                        task_outcome=True).credit == UNKNOWN,
          "a winning branch can still contain an unchecked stage")

    folded = observe(OutcomeVector(), local_verification=True)
    folded = observe(folded, task_outcome=True)
    check("signals can be folded in as they are observed",
          folded.local_verification is True and folded.task_outcome is True
          and not folded.contradicted)

    check("re-stating a signal with the same value is not a disagreement",
          not observe(folded, local_verification=True).contradicted,
          "several observers may notice the same thing")

    clash = observe(folded, local_verification=False)
    check("observers that disagree are recorded, not raised",
          clash.contradicted and "local_verification" in clash.contradictions)
    check("a disagreement leaves the first observation standing",
          clash.local_verification is True,
          "the run must not die because two observers differ")
    check("a disagreement cannot become stage credit",
          clash.credit == UNKNOWN,
          "disputed evidence must not train the positive or negative class")
    check("a disagreement is visible in the reading",
          "signals disagreed" in clash.reading)

    check("folding None changes nothing",
          observe(OutcomeVector(), local_verification=None).credit == UNKNOWN)

    check("verified work explicitly unused downstream is neutral",
          OutcomeVector(local_verification=True,
                        downstream_use=False).credit == NEUTRAL,
          "locally sound work that reached nothing is a cost, not a benefit")

    non_boolean_refused = False
    try:
        observe(OutcomeVector(), local_verification="false")
    except ValueError:
        non_boolean_refused = True
    check("non_boolean outcome signals are refused", non_boolean_refused)

    try:
        observe(OutcomeVector(), invented_signal=True)
        named = False
    except ValueError as exc:
        named = "invented_signal" in str(exc) and "known signals" in str(exc)
    check("an unknown signal name is refused and the refusal names it",
          named, "a refusal that names nothing cannot be repaired")

    check("the signal list is derived from the fields, not restated",
          set(SIGNAL_SCOPES) == {item.name for item in _signal_fields()}
          and "task_outcome" in SIGNAL_SCOPES)
    check("exactly one signal is run-level",
          [name for name, scope in SIGNAL_SCOPES.items()
           if scope == _RUN_LEVEL] == ["task_outcome"])
    check("every signal carries a description for rendering",
          all(SIGNAL_DESCRIPTIONS.get(name) for name in SIGNAL_SCOPES))

    payload = wasted.to_dict()
    check("the record carries credit, granularity and what was unknown",
          payload["credit"] == NEUTRAL and payload["granularity"] == STAGE
          and "downstream_use" in payload["unknown"])
    check("the record round-trips through json",
          json.loads(json.dumps(payload))["credit"] == NEUTRAL)

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "outcome_vector_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=1))
