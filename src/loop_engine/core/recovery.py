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

from .choice import (CHOICE_RESPONSE_CONTRACT, ChoiceOption, ChoiceRequest,
                     ChoiceResponse, ParameterSpec,
                     admitted_choice, render_choice)

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
        }


def recovery_options(facts: dict) -> tuple[ChoiceOption, ...]:
    """The responses to this failure that are mechanically possible.

    ``facts`` carries only what the runtime knows for certain: the error, how
    many attempts have gone, what each route can hold, which providers have
    credentials, and whether the packet can be made smaller. Nothing here
    ranks the options or hints at a preference; an option that cannot be used
    says why, so a reader does not keep reaching for it.
    """
    attempts = int(facts.get("attempts_so_far") or 0)
    error_code = str(facts.get("error_code") or "")
    responded = bool(facts.get("provider_responded"))
    options = [
        ChoiceOption(
            "retry_same_route",
            "Put the same request to the same route again",
            facts={"attempts_so_far": attempts, "error_code": error_code,
                   "provider_responded": responded}),
    ]
    for route in facts.get("alternate_routes") or ():
        usable = bool(route.get("eligible", True))
        options.append(ChoiceOption(
            f"route:{route.get('name')}",
            f"{route.get('provider')} / {route.get('model')}",
            eligible=usable,
            ineligible_reason=str(route.get("ineligible_reason") or ""),
            facts={key: route[key] for key in
                   ("max_context", "max_output_tokens", "same_provider")
                   if key in route}))
    packet_tokens = facts.get("packet_estimated_tokens")
    window = facts.get("route_context_window")
    can_shrink = bool(facts.get("packet_can_be_rebuilt"))
    options.append(ChoiceOption(
        "compact_and_resubmit",
        "Rebuild the request smaller and put the same logical call again",
        eligible=can_shrink,
        ineligible_reason="" if can_shrink else
        "this caller cannot rebuild the request for this attempt",
        facts={"packet_estimated_tokens": packet_tokens,
               "route_context_window": window}))
    options.append(ChoiceOption(
        "wait_then_retry", "Wait, then put the same request again",
        facts={"seconds_waited_so_far": facts.get("seconds_waited", 0)}))
    options.append(ChoiceOption(
        "abandon_step",
        "Stop trying this step and report why, preserving completed work",
        facts={"verified_work": facts.get("completed_work") or []}))
    return tuple(options)


def _recovery_question(facts: dict) -> str:
    """State the failure without implying what it means."""
    return (
        f"A model call failed with {facts.get('error_code')!r} after "
        f"{facts.get('attempts_so_far', 0)} attempt(s). The provider "
        + ("did respond" if facts.get("provider_responded")
           else "did not respond")
        + ". What should happen next?")


def choose_recovery(facts: dict, ask, *, parameters=(),
                    authority=()) -> RecoveryOutcome:
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
            "error_code", "attempts_so_far", "provider_responded",
            "provider_stop_reason", "output_limit_reached", "step",
            "completed_work") if key in facts},
        parameters=tuple(parameters),
        authority=tuple(authority))
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
        selected=answer.selected, adjustments=answer.adjustments,
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
        "provider_stop_reason": "stop",
        "packet_can_be_rebuilt": False,
        "completed_work": ["dataset inventory"],
        "alternate_routes": (
            {"name": "cloud.hard", "provider": "ollama_cloud",
             "model": "big", "same_provider": True, "max_context": 131072},
            {"name": "cloud.mistral", "provider": "mistral", "model": "m",
             "eligible": False,
             "ineligible_reason": "no MISTRAL_API_KEY in environment"}),
    }
    options = recovery_options(facts)
    ids = {item.option_id for item in options}
    check("the mechanically impossible option is offered with its reason",
          any(item.option_id == "route:cloud.mistral" and not item.eligible
              and "MISTRAL" in item.ineligible_reason for item in options))
    check("an option the caller cannot perform is marked unavailable",
          any(item.option_id == "compact_and_resubmit" and not item.eligible
              for item in options))
    check("abandoning the step is always on the table",
          "abandon_step" in ids and "retry_same_route" in ids)

    reasoned = choose_recovery(
        facts,
        lambda _prompt: json.dumps({
            "selected": ["route:cloud.hard"],
            "adjustments": {"max_output_tokens": 4096},
            "reason": "the route answered but produced no answer twice",
            "exit_condition": "stop after one changed attempt"}),
        parameters=(ParameterSpec("p.out", "max_output_tokens", "integer",
                                  8192, minimum=512, maximum=65536,
                                  unit="tokens"),))
    check("a reasoned recovery is attributed to reasoning",
          reasoned.reasoned and reasoned.selected == ("route:cloud.hard",)
          and reasoned.adjustments == {"max_output_tokens": 4096})

    reaching = choose_recovery(
        facts, lambda _p: json.dumps({"selected": ["route:cloud.mistral"]}))
    check("an unavailable recovery is refused, not performed",
          reaching.selected == ()
          and "route:cloud.mistral" in reaching.refused)

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
    check("a recovery nobody enumerated is carried, and is reasoned",
          novel.reasoned
          and novel.novel["summary"].startswith("split the step"))

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "recovery_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


if __name__ == "__main__":
    print(json.dumps(self_test(), indent=1))
