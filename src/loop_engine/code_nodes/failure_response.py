"""Failure response — how the loop is biased when an attempt ERRORS.

Owner ask (2026-08-23): when we try to implement something and hit errors, we
should have biases toward diagnose-and-repair, research, try-another-method, and
so on.  This module is that: a deterministic selector that reads the FAILURE
SIGNAL and proposes a biased response, emitting real ``CandidateAction`` moves.

The one rule that keeps it from thrashing: DON'T KEEP HITTING THE SAME WALL.  A
first failure biases toward diagnose-and-repair; the SAME failure signature seen
again biases toward a DIFFERENT method (or research); repeated failure or an
exhausted budget escalates, then abstains.  Every response names an adversarial
alternative, so the bias is demotable through the same paired-evidence governance
as the standing biases (see [[biases.py]] / [[follow_up.py]]).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ..loop.kernel import CandidateAction

FAILURE_KINDS = ("crash", "timeout", "contract_violation", "degenerate_result",
                 "empty_result", "logic_error", "resource_exhausted",
                 "transport_error", "unknown")
FAILURE_RESPONSES = ("retry_transport", "adapt", "diagnose_and_repair",
                     "research", "try_other_method", "decompose", "simplify",
                     "escalate", "abstain")


@dataclass
class FailureSignal:
    kind: str = "unknown"
    message: str = ""
    times_seen: int = 1                 # times THIS signature has failed
    reversible: bool = True
    budget_left_frac: float = 1.0       # 0..1 of the run budget remaining
    has_known_adapter: bool = False     # for contract_violation

    def __post_init__(self):
        if self.kind not in FAILURE_KINDS:
            raise ValueError(f"kind must be one of {FAILURE_KINDS}")


@dataclass
class FailureResponse:
    response: str
    rationale: str
    alternative: str                    # the adversarial alternative (demotable)
    action: CandidateAction

    def __post_init__(self):
        if self.response not in FAILURE_RESPONSES:
            raise ValueError(f"response must be one of {FAILURE_RESPONSES}")


def _act(intent: str, why: str, *, cost: float, value: float,
         reversibility: float = 1.0) -> CandidateAction:
    return CandidateAction(action=f"onfail::{intent}", kind="failure_response",
                           rationale=why, estimated_cost=cost,
                           expected_value=value, information_gain=0.4,
                           reversibility=reversibility)


def respond_to_failure_on_the_record(sig: FailureSignal, *, ledger=None,
                                     loop_id: str = "") -> FailureResponse:
    """``respond_to_failure`` with the failure and its recovery ON the run's
    timeline: ``failure.detected`` for the signal, then ``recovery.started``
    and ``recovery.completed`` around choosing the response.

    Three declared event families had no emitter while this deterministic
    responder ran on every failure — the run knew it had failed and recovered,
    and the record did not. The decision itself is unchanged; only its
    visibility is."""
    if ledger is not None:
        ledger.record(loop_id=loop_id, event="failure.detected",
                      kind=sig.kind, times_seen=sig.times_seen,
                      budget_left_frac=sig.budget_left_frac,
                      message=str(sig.message)[:120])
        ledger.record(loop_id=loop_id, event="recovery.started",
                      kind=sig.kind)
    resp = respond_to_failure(sig)
    if ledger is not None:
        ledger.record(loop_id=loop_id, event="recovery.completed",
                      kind=sig.kind, response=resp.response,
                      alternative=resp.alternative)
    return resp


def respond_to_failure(sig: FailureSignal) -> FailureResponse:
    """Choose the biased response to a failure — deterministic, from the signal.

    Precedence: cheap exact recoveries first (transport retry, a known adapter),
    then diagnose on a first failure, then a DIFFERENT method once the same wall
    recurs, then escalate/abstain when exhausted."""
    exhausted = sig.budget_left_frac < 0.15
    repeated = sig.times_seen >= 2
    many = sig.times_seen >= 3

    # 0. exhausted budget or many repeats of an irreversible failure -> stop safely.
    if many or (exhausted and repeated):
        if exhausted:
            return FailureResponse(
                "abstain", "repeated failure with the budget nearly exhausted — "
                "abstain rather than burn the remainder", "escalate",
                _act("abstain", "stop safely; return the best partial + the "
                     "failure record", cost=0.0, value=0.4))
        return FailureResponse(
            "escalate", f"the same failure {sig.times_seen}x — escalate for "
            "human judgement or a stronger model", "try_other_method",
            _act("escalate", "hand up with the diagnosis and what was tried",
                 cost=1.0, value=0.5))

    # 1. transport error -> retry the identical request (a NEW pass), exact.
    if sig.kind == "transport_error" and not repeated:
        return FailureResponse(
            "retry_transport", "a provider transport failure — retry the exact "
            "request as a new pass", "try_other_method",
            _act("retry_transport", "same prompt/model/params, new pass",
                 cost=1.0, value=0.6))

    # 2. contract violation with a known adapter -> adapt (deterministic, exact).
    if sig.kind == "contract_violation" and sig.has_known_adapter and not repeated:
        return FailureResponse(
            "adapt", "the output missed the contract but a known adapter bridges "
            "it — convert explicitly, then re-validate", "diagnose_and_repair",
            _act("adapt", "apply the explicit adapter, then re-check the contract",
                 cost=0.5, value=0.7))

    # 3. the SAME wall again -> a DIFFERENT method (don't repeat the failure).
    if repeated:
        if sig.kind in ("degenerate_result", "empty_result"):
            return FailureResponse(
                "research", "the method keeps producing a degenerate result — "
                "research WHY before trying again", "try_other_method",
                _act("research", "understand the failure cause, then re-decide",
                     cost=1.5, value=0.55))
        return FailureResponse(
            "try_other_method", f"this method failed {sig.times_seen}x — switch "
            "approach rather than hitting the same wall", "diagnose_and_repair",
            _act("try_other_method", "pick a structurally different method",
                 cost=2.0, value=0.55))

    # 4. resource exhaustion -> simplify / decompose the work.
    if sig.kind == "resource_exhausted":
        return FailureResponse(
            "simplify", "ran out of resources — simplify or split the work into "
            "smaller pieces", "decompose",
            _act("simplify", "reduce scope / batch size, or decompose the task",
                 cost=1.0, value=0.55))

    # 5. a degenerate/empty result the first time -> research the cause.
    if sig.kind in ("degenerate_result", "empty_result"):
        return FailureResponse(
            "research", "the result carries no information — research the cause "
            "(leakage, wrong metric, bad inputs) before retrying", "diagnose_and_repair",
            _act("research", "diagnose why the output is degenerate", cost=1.5,
                 value=0.55))

    # 6. first crash / logic error / timeout / contract miss -> diagnose & repair.
    return FailureResponse(
        "diagnose_and_repair", "a first failure — read the error, form a specific "
        "hypothesis, and make the minimal repair", "try_other_method",
        _act("diagnose_and_repair", "inspect stderr/contract, repair the exact "
             "cause", cost=1.0, value=0.6, reversibility=1.0))


def response_records() -> list:
    """The failure-response biases as searchable strategy records."""
    from ..static_architecture.store_serve import StoreRecord
    seed = [
        ("first_failure", "crash / logic error / timeout, first time",
         "diagnose_and_repair"),
        ("repeated_failure", "same signature seen again", "try_other_method"),
        ("degenerate", "constant / chance-level / empty result", "research"),
        ("transport", "provider transport failure", "retry_transport"),
        ("contract_miss_adaptable", "output missed a contract, adapter known",
         "adapt"),
        ("resource", "resource exhausted", "simplify"),
        ("exhausted", "many failures / low budget", "escalate then abstain"),
    ]
    return [StoreRecord(
        record_id=f"onfail.{name}", kind="strategy",
        title=f"On {when} → {resp}", body={"when": when, "response": resp},
        tags=("failure_response", "scheduler_bias", resp, "step:route",
              "step:decide_next"), tier="core") for name, when, resp in seed]


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. a first crash biases toward diagnose-and-repair.
    r = respond_to_failure(FailureSignal("crash", "IndexError", times_seen=1))
    check("first_failure_biases_diagnose_and_repair",
          r.response == "diagnose_and_repair"
          and isinstance(r.action, CandidateAction),
          f"{r.response}")

    # 2. THE RULE: the same wall again biases toward a DIFFERENT method.
    r2 = respond_to_failure(FailureSignal("crash", "IndexError", times_seen=2))
    check("repeated_failure_switches_method_not_repeats",
          r2.response == "try_other_method",
          "don't keep hitting the same wall")

    # 3. a degenerate result biases toward research (understand why).
    r3 = respond_to_failure(FailureSignal("degenerate_result", "AUC=0.5"))
    check("degenerate_result_biases_research",
          r3.response == "research",
          "a chance-level result -> research the cause, not blind retry")

    # 4. a transport error retries the exact request (a new pass).
    r4 = respond_to_failure(FailureSignal("transport_error", "503"))
    check("transport_error_retries_exactly",
          r4.response == "retry_transport",
          "same request, new pass — the only exact retry")

    # 5. a contract miss with a known adapter adapts deterministically.
    r5 = respond_to_failure(FailureSignal("contract_violation",
                                          "needs_review not in enum",
                                          has_known_adapter=True))
    check("contract_miss_with_adapter_adapts",
          r5.response == "adapt",
          "bridge explicitly then re-validate — no silent coercion")

    # 6. many repeats escalate; an exhausted budget abstains.
    esc = respond_to_failure(FailureSignal("crash", "x", times_seen=3))
    ab = respond_to_failure(FailureSignal("crash", "x", times_seen=2,
                                          budget_left_frac=0.05))
    check("exhaustion_escalates_then_abstains",
          esc.response == "escalate" and ab.response == "abstain",
          "stop safely rather than burning the remainder")

    # 7. every response names an adversarial alternative (demotable bias).
    check("every_response_has_an_alternative",
          all(respond_to_failure(FailureSignal(k)).alternative
              for k in FAILURE_KINDS),
          "each failure bias can be paired-trialed and demoted")

    # 8. failure-response biases are searchable strategies.
    from ..static_architecture.store_serve import SolverStore
    store = SolverStore(core_records=response_records())
    hit = store.search("what to do when the same method keeps failing",
                       kind="strategy")
    check("failure_responses_are_searchable",
          hit["hits"] and any("onfail." in h["record_id"] for h in hit["hits"]),
          "the failure-response rail is findable through the one search DAG")

    # D-4: three declared families had no emitter while this deterministic
    # responder ran on EVERY failure — the run knew it had failed and
    # recovered, and the record did not.  The decision is unchanged; only its
    # visibility is, and the canonical projection proves it.
    from ..loop.recursive_loop import LoopLedger
    from ..static_architecture.run_history import to_canonical_events
    _lg = LoopLedger()
    _sig = FailureSignal(kind="timeout", times_seen=1)
    _quiet = respond_to_failure(_sig)
    _loud = respond_to_failure_on_the_record(_sig, ledger=_lg, loop_id="l1")
    _fams = [c["type"] for c in to_canonical_events(_lg.events)]
    check("failure_and_recovery_reach_the_record_without_changing_the_choice",
          _loud.response == _quiet.response
          and _loud.alternative == _quiet.alternative
          and _fams == ["failure.detected", "recovery.started",
                        "recovery.completed"],
          f"same decision ({_loud.response}), now visible as {_fams}")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "failure_response_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
