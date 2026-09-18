"""Operation cost records: what each implementation of an operation cost.

The owner's September 18 direction is that the quickest, lowest-overhead
implementation that satisfies a step's contract should be preferred, and
that the engine should learn that preference from historical runs rather
than from opinion. That needs a record of what each implementation of one
logical operation actually cost, phase by phase, with the outcome the run
earned, and a comparison that ranks implementations only on verified
outcomes with complete timings.

An operation is the logical step (locate a target, decide the next action,
verify a deliverable); an implementation is what ran it (a registered
resolver, a small model, a language model route, a tool written for it).
Unknown counts and unknown costs stay unknown: a missing phase timing makes
the record incomplete, and an incomplete record is never averaged as if it
were zero. The comparison is advice for a selector; it promotes nothing.
"""
from __future__ import annotations

from dataclasses import dataclass

PHASES = ("setup", "execution", "verification", "recovery")
COST_OUTCOMES = ("verified", "failed", "unknown")
RECORD_TYPE = "operation_cost_record/v1"


class OperationCostError(ValueError):
    """A cost record or a comparison request is invalid."""


def _count_or_unknown(name: str, value):
    if value is not None and (type(value) is not int or value < 0):
        raise OperationCostError(f"{name} must be unknown or a non-negative integer")
    return value


@dataclass(frozen=True)
class OperationCostRecord:
    """One implementation of one operation in one run, with phase timings."""

    operation_id: str
    implementation_id: str
    run_id: str
    outcome: str
    phase_ms: tuple[tuple[str, "int | None"], ...] = ()
    model_calls: "int | None" = None
    input_tokens: "int | None" = None
    output_tokens: "int | None" = None
    monetary_cost: "float | None" = None

    def __post_init__(self):
        for name in ("operation_id", "implementation_id", "run_id"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise OperationCostError(f"a cost record needs its {name}")
        if self.outcome not in COST_OUTCOMES:
            raise OperationCostError(f"outcome must be one of {COST_OUTCOMES}")
        phases = {}
        for phase, value in self.phase_ms:
            if phase not in PHASES:
                raise OperationCostError(f"phase must be one of {PHASES}")
            if phase in phases:
                raise OperationCostError(f"phase {phase!r} is recorded twice")
            phases[phase] = _count_or_unknown(f"{phase} milliseconds", value)
        object.__setattr__(self, "phase_ms", tuple(phases.items()))
        for name in ("model_calls", "input_tokens", "output_tokens"):
            _count_or_unknown(name, getattr(self, name))
        if self.monetary_cost is not None and (
                type(self.monetary_cost) not in (int, float) or self.monetary_cost < 0):
            raise OperationCostError("monetary cost must be unknown or a non-negative number")

    @property
    def complete(self) -> bool:
        """Every phase has a known timing; only complete records are averaged."""
        known = dict(self.phase_ms)
        return all(phase in known and known[phase] is not None for phase in PHASES)

    @property
    def total_ms(self) -> "int | None":
        return sum(value for _phase, value in self.phase_ms if value is not None) if self.complete else None

    def to_dict(self) -> dict:
        return {"record_type": RECORD_TYPE, "operation_id": self.operation_id,
                "implementation_id": self.implementation_id, "run_id": self.run_id,
                "outcome": self.outcome, "phase_ms": dict(self.phase_ms),
                "complete": self.complete, "total_ms": self.total_ms,
                "model_calls": self.model_calls, "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens, "monetary_cost": self.monetary_cost}


@dataclass(frozen=True)
class ImplementationCost:
    """The aggregate for one implementation of one operation."""

    implementation_id: str
    records: int
    verified: int
    failed: int
    unknown: int
    complete_verified: int
    mean_total_ms: "float | None"
    mean_model_calls: "float | None"
    mean_input_tokens: "float | None"

    def to_dict(self) -> dict:
        return {"record_type": "implementation_cost/v1", **{
            name: getattr(self, name) for name in self.__dataclass_fields__}}


def _mean(values) -> "float | None":
    known = [value for value in values if value is not None]
    return sum(known) / len(known) if known else None


class OperationCostLedger:
    """An append-only list of cost records with one comparison per operation."""

    def __init__(self, records=()):
        self._records: list[OperationCostRecord] = []
        for record in records:
            self.add(record)

    def add(self, record: OperationCostRecord) -> None:
        if not isinstance(record, OperationCostRecord):
            raise OperationCostError("the ledger holds typed OperationCostRecord values")
        self._records.append(record)

    @property
    def records(self) -> tuple[OperationCostRecord, ...]:
        return tuple(self._records)

    def implementations(self, operation_id: str) -> tuple[ImplementationCost, ...]:
        groups: dict[str, list[OperationCostRecord]] = {}
        for record in self._records:
            if record.operation_id == operation_id:
                groups.setdefault(record.implementation_id, []).append(record)
        result = []
        for implementation_id, items in sorted(groups.items()):
            verified = [item for item in items if item.outcome == COST_OUTCOMES[0]]
            complete_verified = [item for item in verified if item.complete]
            result.append(ImplementationCost(
                implementation_id=implementation_id, records=len(items), verified=len(verified),
                failed=sum(item.outcome == COST_OUTCOMES[1] for item in items),
                unknown=sum(item.outcome == COST_OUTCOMES[2] for item in items),
                complete_verified=len(complete_verified),
                mean_total_ms=_mean(item.total_ms for item in complete_verified),
                mean_model_calls=_mean(item.model_calls for item in verified),
                mean_input_tokens=_mean(item.input_tokens for item in verified)))
        return tuple(result)

    def compare(self, operation_id: str, *, min_samples: int = 2) -> dict:
        """Rank implementations by mean total time over verified, complete records.

        An implementation without enough verified, complete records is listed
        under ``insufficient`` with the reason, never ranked on a guess.
        """
        if type(min_samples) is not int or min_samples < 1:
            raise OperationCostError("min_samples is a positive integer")
        ranked, insufficient = [], []
        for item in self.implementations(operation_id):
            if item.complete_verified >= min_samples:
                ranked.append(item)
            else:
                insufficient.append({"implementation_id": item.implementation_id,
                                     "reason": f"{item.complete_verified} verified complete "
                                               f"records, {min_samples} needed"})
        ranked.sort(key=lambda item: (
            item.mean_total_ms if item.mean_total_ms is not None else float("inf"),
            item.mean_model_calls if item.mean_model_calls is not None else float("inf")))
        return {"record_type": "operation_cost_comparison/v1", "operation_id": operation_id,
                "basis": "mean total milliseconds over verified outcomes with every phase timed",
                "min_samples": min_samples, "ranked": [item.to_dict() for item in ranked],
                "insufficient": insufficient,
                "preferred": ranked[0].implementation_id if ranked else None}


def self_test() -> dict:
    """Unknowns stay unknown, only verified complete records rank, and ties break on calls."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except OperationCostError:
            return True
        return False

    def record(implementation, run, outcome, total, calls=None, complete=True):
        phases = (("setup", 10), ("execution", total - 30), ("verification", 15),
                  ("recovery", 5 if complete else None))
        return OperationCostRecord("locate_target", implementation, run, outcome, phases,
                                   model_calls=calls, input_tokens=None if calls is None else calls * 900)
    ledger = OperationCostLedger([
        record("model:cloud", "run-1", "verified", 4000, calls=3),
        record("model:cloud", "run-2", "verified", 3600, calls=3),
        record("resolver:template", "run-3", "verified", 120, calls=0),
        record("resolver:template", "run-4", "verified", 140, calls=0),
        record("resolver:template", "run-5", "failed", 130, calls=0),
        record("tool:detector", "run-6", "verified", 300, calls=0, complete=False),
        record("tool:detector", "run-7", "verified", 280, calls=0),
        record("model:small", "run-8", "unknown", 900),
    ])
    comparison = ledger.compare("locate_target")
    check("the_cheapest_verified_implementation_is_preferred",
          comparison["preferred"] == "resolver:template"
          and [item["implementation_id"] for item in comparison["ranked"]]
          == ["resolver:template", "model:cloud"], str(comparison["ranked"]))
    check("implementations_without_enough_verified_complete_records_are_listed_not_ranked",
          sorted(item["implementation_id"] for item in comparison["insufficient"])
          == ["model:small", "tool:detector"]
          and all("needed" in item["reason"] for item in comparison["insufficient"]))
    incomplete = record("tool:detector", "run-6", "verified", 300, calls=0, complete=False)
    check("an_incomplete_record_has_no_total_and_is_never_averaged_as_zero",
          incomplete.total_ms is None and not incomplete.complete
          and next(item for item in ledger.implementations("locate_target")
                   if item.implementation_id == "tool:detector").mean_total_ms == 280.0)
    check("failed_and_unknown_outcomes_are_counted_but_do_not_shape_the_mean",
          next(item for item in ledger.implementations("locate_target")
               if item.implementation_id == "resolver:template").failed == 1
          and next(item for item in ledger.implementations("locate_target")
                   if item.implementation_id == "resolver:template").mean_total_ms == 130.0
          and next(item for item in ledger.implementations("locate_target")
                   if item.implementation_id == "model:small").mean_model_calls is None)
    tied = OperationCostLedger([record("a", "r1", "verified", 500, calls=2), record("a", "r2", "verified", 500, calls=2),
                                record("b", "r3", "verified", 500, calls=0), record("b", "r4", "verified", 500, calls=0)])
    check("a_time_tie_breaks_on_fewer_model_calls",
          tied.compare("locate_target")["preferred"] == "b")
    check("records_and_requests_are_validated",
          all(refuses(action) for action in (
              lambda: OperationCostRecord("", "x", "r", "verified"),
              lambda: OperationCostRecord("op", "x", "r", "maybe"),
              lambda: OperationCostRecord("op", "x", "r", "verified", (("warmup", 1),)),
              lambda: OperationCostRecord("op", "x", "r", "verified", (("setup", 1), ("setup", 2))),
              lambda: OperationCostRecord("op", "x", "r", "verified", (("setup", -1),)),
              lambda: OperationCostRecord("op", "x", "r", "verified", model_calls=1.5),
              lambda: ledger.compare("locate_target", min_samples=0),
              lambda: OperationCostLedger([{"operation_id": "op"}])))
          and record("model:cloud", "run-9", "verified", 4000, calls=3).to_dict()["total_ms"] == 4000)
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "operation_cost_records_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
