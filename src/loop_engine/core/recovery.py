"""What should happen after a failure, decided by reasoning rather than a table.

A retry table encodes task-conditioned decisions — which failures are worth
another attempt, how many, how long to wait, what to shrink — as constants
chosen by whoever wrote it, from however many runs they had seen. It cannot
distinguish a route that is briefly busy from one that will never answer, and
it never records why it did what it did, so nothing accumulates that could
justify a better table later.

This module supplies the failure and the mechanically eligible responses, and
asks a reasoning route to choose among them through the one standard choice
contract. The runtime keeps the facts: which routes have credentials, which
windows can hold the request, how many attempts have been spent, what work is
already verified. It keeps the enforcement too: a selection outside the offer
is refused. What it gives up is the choosing.

The bootstrapping problem is real and is handled narrowly. Something has to
decide what to do when the thing that decides is the thing that failed. A
continuity broker — deterministic, and as small as it can be — enumerates
routes, removes the mechanically impossible, and tries to reach any authorized
reasoner. Its only job is restoring access to reasoning. It does not
reinterpret the task, choose what to discard, or declare recovery successful.
When it can reach nothing, the answer is NO_REASONING_ROUTE_AVAILABLE and the
caller preserves its incumbent, waits, or returns a blocker: it does not
quietly become a different kind of run.

Owns:
    - recovery_options(): the mechanically eligible responses to a failure.
    - choose_recovery(): the decision, put to a reasoning route.
    - RecoveryOutcome: what was chosen, by whom, and what it cost.

Does not own: performing the recovery (the caller does), the choice contract
(core.choice), or the ownership count (core.semantic_decision).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .choice import (ChoiceOption, ChoiceRequest, ChoiceResponse,
                     admitted_choice, render_choice)
from .model_capabilities import ModelOutputAllocation

RECOVERY_RECORD_TYPE = "recovery_decision/v1"

#: Returned when nothing can reason. Not a failure of the task and not a
#: licence to solve it another way: the caller waits, preserves what it has,
#: asks for authority, or returns a blocker.
NO_REASONING_ROUTE_AVAILABLE = "NO_REASONING_ROUTE_AVAILABLE"

#: Who decided. Kept explicit because a recovery chosen by the table when no
#: reasoner could be reached must not be counted as a reasoned decision.
CHOSEN_BY_REASONING = "llm"
CHOSEN_BY_CONTINUITY_BROKER = "deterministic"


@dataclass(frozen=True)
class RecoveryOutcome:
    """What to do next after a failure, and who said so."""

    selected: tuple[str, ...] = ()
    adjustments: dict = field(default_factory=dict)
    novel: dict = field(default_factory=dict)
    chosen_by: str = CHOSEN_BY_CONTINUITY_BROKER
    reason: str = ""
    expected_observation: str = ""
    exit_condition: str = ""
    blocker: str = ""
    refused: tuple[str, ...] = ()
    output_allocation: ModelOutputAllocation | None = None

    @property
    def reasoned(self) -> bool:
        return self.chosen_by == CHOSEN_BY_REASONING

    def to_dict(self) -> dict:
        return {
            "record_type": RECOVERY_RECORD_TYPE,
            "selected": list(self.selected),
            "adjustments": dict(self.adjustments),
            "novel": dict(self.novel),
            "chosen_by": self.chosen_by,
            "reason": self.reason,
            "expected_observation": self.expected_observation,
            "exit_condition": self.exit_condition,
            "blocker": self.blocker,
            "refused": list(self.refused),
            "output_allocation": (self.output_allocation.summary()
                                  if self.output_allocation is not None else None),
        }


def recovery_options(facts: dict) -> tuple[ChoiceOption, ...]:
    """The responses to this failure that are mechanically possible.

    This caller currently implements exactly two outcomes: put the unchanged
    authorized model plan through the same session again, or stop the step and
    preserve its work. Route replacement, context recompilation, waiting, and
    setting changes must not appear as selectable until their callers can
    execute and verify them.
    """
    attempts = int(facts.get("attempts_so_far") or 0)
    error_code = str(facts.get("error_code") or "")
    responded = bool(facts.get("provider_responded"))
    return (
        ChoiceOption(
            "retry_same_route",
            "Put the unchanged request through the same authorized model "
            "plan again",
            facts={"attempts_so_far": attempts, "error_code": error_code,
                   "provider_responded": responded}),
        ChoiceOption(
            "abandon_step",
            "Stop trying this step and report why, preserving completed work",
            facts={"completed_work": facts.get("completed_work") or []}),
    )


def _recovery_question(facts: dict) -> str:
    """State the failure without implying what it means."""
    return (
        f"A model call failed with {facts.get('error_code')!r} after "
        f"{facts.get('attempts_so_far', 0)} attempt(s). The provider "
        + ("did respond" if facts.get("provider_responded")
           else "did not respond")
        + ". What should happen next?")


def choose_recovery(facts: dict, ask, *, parameters=()) -> RecoveryOutcome:
    """Put the recovery decision to a reasoning route.

    ``ask`` is a callable taking one prompt and returning response text, or
    None when no reasoning route can be reached. It is supplied by the caller
    so that this module never opens a transport of its own, and so a recovery
    decision can never recurse into another recovery decision.
    """
    request = ChoiceRequest(
        decision_kind="choose_recovery",
        question=_recovery_question(facts),
        options=recovery_options(facts),
        evidence={key: facts[key] for key in (
            "task", "responsibility", "response_contract_ref",
            "error_code", "attempts_so_far", "provider_responded",
            "latest_model_failure", "history_refs", "context_policy",
            "step", "completed_work", "output_capacity", "allocation_guidance") if key in facts},
        parameters=tuple(parameters), authority=(), allow_multiple=False, allow_novel=False)
    try:
        text = ask(render_choice(request))
    except Exception as exc:                              # noqa: BLE001
        return RecoveryOutcome(
            chosen_by=CHOSEN_BY_CONTINUITY_BROKER,
            blocker=NO_REASONING_ROUTE_AVAILABLE,
            reason=f"no reasoning route answered ({type(exc).__name__})")
    if not text:
        return RecoveryOutcome(
            chosen_by=CHOSEN_BY_CONTINUITY_BROKER,
            blocker=NO_REASONING_ROUTE_AVAILABLE,
            reason="no reasoning route was available to choose a recovery")
    answer = _read(text, request)
    if answer is None:
        return RecoveryOutcome(
            chosen_by=CHOSEN_BY_CONTINUITY_BROKER,
            blocker=NO_REASONING_ROUTE_AVAILABLE,
            reason="the recovery answer could not be read")
    return RecoveryOutcome(
        selected=answer.selected, adjustments=(answer.adjustments
            if answer.selected == ("retry_same_route",) else {}),
        novel=answer.novel, chosen_by=CHOSEN_BY_REASONING,
        reason=answer.reason,
        expected_observation=answer.expected_observation,
        exit_condition=answer.exit_condition, refused=answer.refused)


def _read(text: str, request: ChoiceRequest) -> "ChoiceResponse | None":
    """The answer, or nothing when it was not one."""
    body = (text or "").strip()
    start, end = body.find("{"), body.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        return admitted_choice(json.loads(body[start:end + 1]), request)
    except (ValueError, TypeError):
        return None


def self_test() -> dict:
    """Offline checks. No provider is contacted."""
    tests = []

    def check(name, ok, detail=""):
        tests.append({"test": name, "passed": bool(ok), "detail": detail})

    facts = {
        "error_code": "output_validation_failed",
        "attempts_so_far": 2,
        "provider_responded": True,
        "completed_work": ["dataset inventory"],
        "task": "Recover one bounded model-backed task.",
        "responsibility": "produce the admitted response record",
        "response_contract_ref": "inline:sha256:fixture",
        "latest_model_failure": {
            "route": "fixture.route", "maximum_output_tokens": 8192,
            "error_code": "output_validation_failed"},
        "history_refs": ["artifact:prior-attempt"],
        "context_policy": {"policy_id": "fixture", "version": "1"},
    }
    options = recovery_options(facts)
    ids = {item.option_id for item in options}
    check("only executable recovery actions are offered",
          ids == {"retry_same_route", "abandon_step"})

    reasoned = choose_recovery(
        facts,
        lambda _prompt: json.dumps({
            "selected": ["retry_same_route"],
            "adjustments": {"max_output_tokens": 4096},
            "reason": "the route answered but produced no answer twice",
            "exit_condition": "stop after one unchanged attempt"}))
    check("a reasoned executable choice is admitted without a fake setting",
          reasoned.reasoned
          and reasoned.selected == ("retry_same_route",)
          and not reasoned.adjustments
          and "adjustment:max_output_tokens" in reasoned.refused)

    reaching = choose_recovery(
        facts, lambda _p: json.dumps({"selected": ["route:unbound"]}))
    check("an unimplemented route replacement is refused, not performed",
          reaching.selected == ()
          and "route:unbound" in reaching.refused)

    silent = choose_recovery(facts, lambda _p: "")
    check("no reasoning route yields a blocker, never a chosen recovery",
          silent.blocker == NO_REASONING_ROUTE_AVAILABLE
          and not silent.reasoned and silent.selected == ())

    def explode(_prompt):
        raise ConnectionError("every route is down")

    broken = choose_recovery(facts, explode)
    check("a failing recovery call cannot raise into the caller",
          broken.blocker == NO_REASONING_ROUTE_AVAILABLE
          and "ConnectionError" in broken.reason)

    garbled = choose_recovery(facts, lambda _p: "I think you should retry")
    check("an unreadable answer is not treated as a decision",
          garbled.blocker == NO_REASONING_ROUTE_AVAILABLE
          and not garbled.reasoned)

    novel = choose_recovery(facts, lambda _p: json.dumps({
        "selected": [],
        "novel": {"summary": "split the step into two smaller calls",
                  "why": "neither route can hold this request whole"}}))
    check("an unimplemented novel recovery is refused, not advertised",
          novel.reasoned and not novel.novel and "novel" in novel.refused)

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "recovery_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=1))
