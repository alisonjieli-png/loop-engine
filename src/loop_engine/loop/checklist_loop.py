"""Gated checklist: "nothing is weird, move on" as one deterministic Loop.

Architectural role: the colleague who looks at the data, runs down a checklist,
and only asks for help when an item fails. The checklist is a deterministic
``Loop`` running the ``gated_checklist`` template under the
``practitioner.checklist`` profile. It evaluates ordered typed checks against a
passive state mapping, records every evaluation on its ledger, and when a
blocking item fails it records that the gate fired and hands the failed items
to an escalation callable that may spawn a Loop (model-led if the
parent's delegation authority permits). On the clean path the Loop makes zero
model calls and spawns nothing; that is the distillation the owner asked for:
a step that used to need reasoning becomes a gate that only escalates when
the gate fires.

Owns:
    - ChecklistItem: one deterministic check with a severity.
    - ChecklistItemResult, ChecklistOutcome: passive result records.
    - ChecklistRequest: the parameter object for one checklist run.
    - run_checklist(): the one operation, executed through the canonical Loop.

Does not own: the checks' domain logic (callers supply them), the escalation
Loop's behavior (the callable and its profile decide), or the profile and
template records (loop.loop_profile_catalog, loop.loop_templates).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from .loop_role import LoopRole, LoopRoleIdentity
from .recursive_loop import Loop, LoopConfig, LoopError, StepOutcome

CHECKLIST_PROFILE_ID = "practitioner.checklist"
CHECKLIST_TEMPLATE_ID = "gated_checklist"
CHECKLIST_STEPS = ("inspect", "gate")
SEVERITIES = ("blocking", "advisory")


class ChecklistError(ValueError):
    """A checklist request or item was invalid."""


@dataclass(frozen=True)
class ChecklistItem:
    """One deterministic check. ``check(state)`` returns bool or (bool, detail)."""

    item_id: str
    description: str
    check: Callable[[Mapping], object]
    severity: str = "blocking"

    def __post_init__(self) -> None:
        if not self.item_id.strip() or not self.description.strip():
            raise ChecklistError("a checklist item needs an id and description")
        if not callable(self.check):
            raise ChecklistError(f"item {self.item_id!r} check must be callable")
        if self.severity not in SEVERITIES:
            raise ChecklistError(f"severity must be one of {SEVERITIES}")


@dataclass(frozen=True)
class ChecklistItemResult:
    """The recorded evaluation of one item."""

    item_id: str
    passed: bool
    severity: str
    detail: str

    def to_dict(self) -> dict:
        return {"item_id": self.item_id, "passed": self.passed,
                "severity": self.severity, "detail": self.detail}


@dataclass(frozen=True)
class ChecklistRequest:
    """Everything one checklist run needs, as one parameter object."""

    goal: str
    items: tuple[ChecklistItem, ...]
    state: Mapping
    escalation: "Callable[[Loop, tuple[ChecklistItemResult, ...]], object] | None" = None
    parent: "Loop | None" = None
    profile_id: str = CHECKLIST_PROFILE_ID

    def __post_init__(self) -> None:
        if not self.goal.strip():
            raise ChecklistError("a checklist needs a goal")
        items = tuple(self.items)
        if not items:
            raise ChecklistError("a checklist needs at least one item")
        if len({item.item_id for item in items}) != len(items):
            raise ChecklistError("checklist item ids must be unique")
        if not isinstance(self.state, Mapping):
            raise ChecklistError("state must be a mapping of typed facts")
        if self.escalation is not None and not callable(self.escalation):
            raise ChecklistError("escalation must be callable when provided")
        object.__setattr__(self, "items", items)


@dataclass(frozen=True)
class ChecklistOutcome:
    """What the checklist Loop decided, with its accounting."""

    loop_id: str
    terminal_code: str
    results: tuple[ChecklistItemResult, ...]
    gate_fired: bool
    blocking_failures: tuple[str, ...]
    advisory_failures: tuple[str, ...]
    escalation_loop_id: str
    model_calls: int
    spawned: int
    ledger_events: int

    def to_dict(self) -> dict:
        return {
            "loop_id": self.loop_id, "terminal_code": self.terminal_code,
            "results": [item.to_dict() for item in self.results],
            "gate_fired": self.gate_fired,
            "blocking_failures": list(self.blocking_failures),
            "advisory_failures": list(self.advisory_failures),
            "escalation_loop_id": self.escalation_loop_id,
            "model_calls": self.model_calls, "spawned": self.spawned,
            "ledger_events": self.ledger_events,
        }


def checklist_config() -> LoopConfig:
    """The deterministic-only configuration every checklist Loop runs under."""
    return LoopConfig(
        framework="custom", custom_steps=CHECKLIST_STEPS,
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        exit_condition="steps_complete")


def _evaluate(item: ChecklistItem, state: Mapping) -> ChecklistItemResult:
    try:
        verdict = item.check(state)
    except Exception as exc:  # a raising check is a failed check, recorded
        return ChecklistItemResult(
            item.item_id, False, item.severity,
            f"check raised {type(exc).__name__}: {exc}"[:400])
    if isinstance(verdict, tuple) and len(verdict) == 2:
        passed, detail = bool(verdict[0]), str(verdict[1])
    else:
        passed, detail = bool(verdict), ""
    return ChecklistItemResult(item.item_id, passed, item.severity, detail)


def run_checklist(request: ChecklistRequest) -> ChecklistOutcome:
    """Run one gated checklist through the canonical Loop.

    Step ``inspect`` evaluates every item and records each result. Step
    ``gate`` records whether a blocking item failed; when it did and an
    escalation callable exists, the callable receives the Loop and the failed
    results and may spawn and run a Loop. When the gate fires with no
    escalation available, the gate step is recorded as failed, so the
    outcome text and the accepted-success count stay honest.
    """
    if not isinstance(request, ChecklistRequest):
        raise ChecklistError("run_checklist needs a ChecklistRequest")
    identity = LoopRoleIdentity(LoopRole.PRACTITIONER, request.profile_id)
    if request.parent is not None:
        loop = request.parent.spawn(
            request.goal, checklist_config(), identity=identity)
    else:
        loop = Loop(request.goal, checklist_config(), identity=identity)
    scratch: dict = {"results": (), "escalation_loop_id": ""}

    def handler(active: Loop, step: str, context: dict) -> StepOutcome:
        if step == "inspect":
            results = tuple(_evaluate(item, request.state)
                            for item in request.items)
            for result in results:
                active.ledger.record(
                    loop_id=active.loop_id, event="custom",
                    custom_kind="checklist_item_evaluated",
                    item_id=result.item_id, passed=result.passed,
                    severity=result.severity, detail=result.detail)
            scratch["results"] = results
            failed = sum(1 for item in results if not item.passed)
            return StepOutcome(
                output=f"inspected {len(results)} items; {failed} failed",
                mode="deterministic", confidence=1.0)
        if step == "gate":
            results = scratch["results"]
            blocking = tuple(item.item_id for item in results
                             if not item.passed and item.severity == "blocking")
            if not blocking:
                active.ledger.record(
                    loop_id=active.loop_id, event="custom",
                    custom_kind="checklist_gate_clear",
                    items=len(results))
                return StepOutcome(output="clear", mode="deterministic",
                                   confidence=1.0)
            active.ledger.record(
                loop_id=active.loop_id, event="custom",
                custom_kind="checklist_gate_fired",
                blocking_failures=blocking)
            if request.escalation is None:
                return StepOutcome(
                    output=f"gate fired on {', '.join(blocking)}; no "
                           "escalation available", mode="deterministic",
                    confidence=0.0, failed=True)
            failed_results = tuple(item for item in results
                                   if item.item_id in blocking)
            spawned_loop = request.escalation(active, failed_results)
            spawned_id = getattr(spawned_loop, "loop_id", "") if spawned_loop is not None else ""
            scratch["escalation_loop_id"] = spawned_id
            active.ledger.record(
                loop_id=active.loop_id, event="custom",
                custom_kind="checklist_escalated",
                escalation_loop_id=spawned_id, blocking_failures=blocking)
            return StepOutcome(
                output=f"escalated {', '.join(blocking)} to "
                       f"{spawned_id or 'the escalation handler'}",
                mode="deterministic", confidence=1.0)
        raise LoopError(f"unexpected checklist step {step!r}")

    result = loop.run(handler=handler)
    results = scratch["results"]
    blocking = tuple(item.item_id for item in results
                     if not item.passed and item.severity == "blocking")
    advisory = tuple(item.item_id for item in results
                     if not item.passed and item.severity == "advisory")
    return ChecklistOutcome(
        loop_id=loop.loop_id, terminal_code=result.terminal_code,
        results=results, gate_fired=bool(blocking),
        blocking_failures=blocking, advisory_failures=advisory,
        escalation_loop_id=scratch["escalation_loop_id"],
        model_calls=result.model_calls, spawned=result.spawned,
        ledger_events=len(loop.ledger.events))


def self_test() -> dict:
    """Prove zero-call clean runs, recorded gates, escalation, and honesty."""
    items = (
        ChecklistItem("rows_present", "the table has rows",
                      lambda s: s["rows"] > 0),
        ChecklistItem("no_null_target", "the target column has no nulls",
                      lambda s: (s["null_target"] == 0,
                                 f"{s['null_target']} nulls")),
        ChecklistItem("balanced_enough", "positives are within 5 to 95 percent",
                      lambda s: 0.05 <= s["positive_rate"] <= 0.95,
                      severity="advisory"),
    )
    # A parent Loop shares its ledger with every checklist it spawns, so the
    # recorded kinds can be read back without any second event store.
    parent = Loop("prepare the training table", LoopConfig(
        framework="custom", custom_steps=("act",),
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",)))

    def kinds_for(loop_id: str) -> list:
        return [event.get("custom_kind") for event in parent.ledger.events
                if event.get("event") == "custom"
                and event.get("loop_id") == loop_id]

    clean = run_checklist(ChecklistRequest(
        "inspect the training table", items,
        {"rows": 200, "null_target": 0, "positive_rate": 0.44}, parent=parent))
    advisory_only = run_checklist(ChecklistRequest(
        "inspect a skewed table", items,
        {"rows": 200, "null_target": 0, "positive_rate": 0.01}))
    unattended = run_checklist(ChecklistRequest(
        "inspect a broken table", items,
        {"rows": 200, "null_target": 7, "positive_rate": 0.44}))

    spawned_ids: list = []

    def escalate(loop: Loop, failed):
        spawned_loop = loop.spawn(
            "decide what to do about " + ", ".join(
                item.item_id for item in failed),
            LoopConfig(framework="custom", custom_steps=("act",),
                       allowable_modes=("deterministic",),
                       preferred_modes=("deterministic",)))
        spawned_loop.run(handler=lambda l, step, ctx: StepOutcome(
            output="drop rows with a null target", mode="deterministic"))
        spawned_ids.append(spawned_loop.loop_id)
        return spawned_loop

    escalated = run_checklist(ChecklistRequest(
        "inspect a broken table with help available", items,
        {"rows": 200, "null_target": 7, "positive_rate": 0.44},
        escalation=escalate, parent=parent))
    raising = run_checklist(ChecklistRequest(
        "inspect a table missing a column", items, {"rows": 200},
        escalation=escalate))

    rejected = 0
    for bad in (
            lambda: ChecklistRequest("g", (), {}),
            lambda: ChecklistRequest("g", (items[0], items[0]), {}),
            lambda: ChecklistItem("x", "y", "not callable"),
            lambda: ChecklistItem("x", "y", lambda s: True, severity="loud"),
    ):
        try:
            bad()
        except ChecklistError:
            rejected += 1
    clean_kinds = kinds_for(clean.loop_id)
    escalated_kinds = kinds_for(escalated.loop_id)
    tests = [{
        "test": "clean_checklist_completes_with_zero_model_calls_and_no_spawn",
        "passed": (clean.terminal_code == "ACCEPTED" and not clean.gate_fired
                   and clean.model_calls == 0 and clean.spawned == 0
                   and all(item.passed for item in clean.results)),
        "detail": f"{clean.terminal_code} calls={clean.model_calls}",
    }, {
        "test": "advisory_failure_is_recorded_but_does_not_fire_the_gate",
        "passed": (not advisory_only.gate_fired
                   and advisory_only.advisory_failures == ("balanced_enough",)
                   and advisory_only.model_calls == 0),
        "detail": str(advisory_only.advisory_failures),
    }, {
        "test": "blocking_failure_without_escalation_is_an_honest_failed_gate",
        "passed": (unattended.gate_fired
                   and unattended.blocking_failures == ("no_null_target",)
                   and unattended.escalation_loop_id == ""
                   and unattended.results[1].detail == "7 nulls"
                   and unattended.terminal_code == "VERIFICATION_REJECTED"),
        "detail": unattended.terminal_code,
    }, {
        "test": "blocking_failure_with_escalation_spawns_a_recorded_spawned_loop",
        "passed": (escalated.gate_fired and escalated.spawned == 1
                   and escalated.escalation_loop_id == spawned_ids[0]
                   and escalated.terminal_code == "ACCEPTED"),
        "detail": escalated.escalation_loop_id,
    }, {
        "test": "a_raising_check_is_a_failed_item_not_a_crash",
        "passed": (raising.gate_fired
                   and raising.blocking_failures == ("no_null_target",)
                   and "KeyError" in raising.results[1].detail
                   and raising.results[0].passed),
        "detail": raising.results[1].detail[:80],
    }, {
        "test": "every_evaluation_and_gate_decision_is_on_the_shared_ledger",
        "passed": (clean_kinds.count("checklist_item_evaluated") == 3
                   and "checklist_gate_clear" in clean_kinds
                   and escalated_kinds.count("checklist_item_evaluated") == 3
                   and "checklist_gate_fired" in escalated_kinds
                   and "checklist_escalated" in escalated_kinds
                   and clean.loop_id != escalated.loop_id),
        "detail": str(escalated_kinds),
    }, {
        "test": "invalid_requests_and_items_fail_closed",
        "passed": rejected == 4,
        "detail": f"{rejected}/4 rejected",
    }]
    return {"module": "loop.checklist_loop",
            "passed": all(item["passed"] for item in tests),
            "tests": tests}
