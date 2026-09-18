"""Capture operation cost records from real invocations, phase by phase.

The cost ledger already aggregates records per implementation; this module
is how a record gets written by the code that does the work. A capture
times the declared phases with a monotonic clock, keeps unknown what it
never saw, and writes one ``OperationCostRecord`` to the ledger when the
operation ends, with the outcome the caller reports. Model call and token
counts are passed in by the caller from provider-reported usage; a missing
count stays unknown, never zero.

``cheapest_implementation`` answers the question the owner asked: which
implementation of this operation was cheapest among the verified ones.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .operation_cost_records import (COST_OUTCOMES, PHASES, OperationCostError, OperationCostLedger,
                                     OperationCostRecord)


class CostCaptureError(OperationCostError):
    """A capture was used out of order or reported an unknown outcome."""


@dataclass
class OperationCostCapture:
    """Time the phases of one implementation of one operation, then record it."""

    ledger: OperationCostLedger
    operation_id: str
    implementation_id: str
    run_id: str
    clock: object = time.monotonic
    _phase_ms: dict = field(default_factory=dict)
    _open: "tuple[str, float] | None" = None
    _record: "OperationCostRecord | None" = None

    def phase(self, name: str) -> "OperationCostCapture":
        """Start a phase; the previous open phase is closed first."""
        if name not in PHASES:
            raise CostCaptureError(f"phase must be one of {PHASES}")
        if self._record is not None:
            raise CostCaptureError("the capture already ended")
        self._close()
        if name in self._phase_ms:
            raise CostCaptureError(f"phase {name!r} was already timed")
        self._open = (name, self.clock())
        return self

    def _close(self) -> None:
        if self._open is not None:
            name, started = self._open
            self._phase_ms[name] = int(round((self.clock() - started) * 1000))
            self._open = None

    def end(self, outcome: str, *, model_calls: "int | None" = None, input_tokens: "int | None" = None,
            output_tokens: "int | None" = None, monetary_cost: "float | None" = None) -> OperationCostRecord:
        """Close the open phase, mark untimed phases unknown, and write the record."""
        if outcome not in COST_OUTCOMES:
            raise CostCaptureError(f"outcome must be one of {COST_OUTCOMES}")
        if self._record is not None:
            raise CostCaptureError("the capture already ended")
        self._close()
        phases = tuple((name, self._phase_ms.get(name)) for name in PHASES)
        self._record = OperationCostRecord(self.operation_id, self.implementation_id, self.run_id, outcome,
                                           phases, model_calls, input_tokens, output_tokens, monetary_cost)
        self.ledger.add(self._record)
        return self._record

    @property
    def record(self) -> "OperationCostRecord | None":
        return self._record


def cheapest_implementation(ledger: OperationCostLedger, operation_id: str, *, min_samples: int = 2) -> dict:
    """The verified implementation with the lowest mean total time, with the ranking it beat."""
    comparison = ledger.compare(operation_id, min_samples=min_samples)
    ranked = comparison.get("ranked") or []
    return {"record_type": "cheapest_implementation/v1", "operation_id": operation_id,
            "cheapest": ranked[0]["implementation_id"] if ranked else None,
            "ranked": ranked, "excluded": comparison.get("excluded") or [],
            "min_samples": min_samples}


def self_test() -> dict:
    """Phases are timed in order, unknown stays unknown, and the cheapest is named from evidence."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    def refuses(action) -> bool:
        try:
            action()
        except OperationCostError:
            return True
        return False

    ticks = iter(range(0, 1000))

    def clock():
        return next(ticks) / 100.0

    ledger = OperationCostLedger()
    capture = OperationCostCapture(ledger, "conform.name", "resolver:text_conformance", "run-1", clock)
    capture.phase("setup").phase("execution").phase("verification").phase("recovery")
    record = capture.end("verified", model_calls=0)
    check("phases_are_timed_from_the_clock_and_the_record_lands_in_the_ledger",
          dict(record.phase_ms) == {"setup": 10, "execution": 10, "verification": 10, "recovery": 10}
          and record.complete and record.model_calls == 0 and record.input_tokens is None
          and ledger.records == (record,))
    partial = OperationCostCapture(ledger, "conform.name", "model:cloud", "run-1", clock)
    partial.phase("setup").phase("execution")
    partial_record = partial.end("failed", model_calls=1, input_tokens=900)
    check("untimed_phases_stay_unknown_and_the_record_is_incomplete",
          dict(partial_record.phase_ms)["verification"] is None and not partial_record.complete
          and partial_record.input_tokens == 900 and partial_record.output_tokens is None)
    check("captures_refuse_unknown_phases_repeats_bad_outcomes_and_reuse",
          refuses(lambda: OperationCostCapture(ledger, "o", "i", "r", clock).phase("dreaming"))
          and refuses(lambda: OperationCostCapture(ledger, "o", "i", "r", clock).phase("setup").phase("setup"))
          and refuses(lambda: OperationCostCapture(ledger, "o", "i", "r", clock).end("maybe"))
          and refuses(lambda: capture.end("verified")) and refuses(lambda: capture.phase("setup")))
    for run in range(3):
        fast = OperationCostCapture(ledger, "conform.name", "resolver:text_conformance", f"run-{run + 2}", clock)
        fast.phase("setup").phase("execution").phase("verification").phase("recovery")
        fast.end("verified", model_calls=0)
        slow = OperationCostCapture(ledger, "conform.name", "model:cloud", f"run-{run + 2}", clock)
        slow.phase("setup").phase("execution")
        for _ in range(30):
            clock()
        slow.phase("verification").phase("recovery")
        slow.end("verified", model_calls=2, input_tokens=1800)
    cheapest = cheapest_implementation(ledger, "conform.name")
    check("the_cheapest_verified_implementation_is_named_with_its_ranking",
          cheapest["cheapest"] == "resolver:text_conformance" and len(cheapest["ranked"]) == 2
          and cheapest["ranked"][1]["implementation_id"] == "model:cloud"
          and cheapest_implementation(ledger, "unknown.operation")["cheapest"] is None)
    passed = sum(item["passed"] for item in results)
    return {"record_type": "operation_cost_capture_test/v1", "tests": results, "passed": passed,
            "total": len(results), "all_passed": passed == len(results)}
