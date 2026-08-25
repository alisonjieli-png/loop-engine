"""Invoke a selected Static Architecture capability as a loop.

Architectural role: loop envelope for manually registered capabilities.

Owns: handshake validation, a typed effect-bearing loop contract, one selected
capability attempt, and preservation of typed provider failures. Discovery
remains local and effect-free.

Does not own: capability registration, provider transport, secret storage,
retry scheduling, or fallback selection.

Verification: ``self_test()`` proves discovery makes no call, invocation binds
the declared effects to the loop identity, and a typed endpoint failure remains
available to Route instead of becoming a generic exception.
"""
from __future__ import annotations


class CapabilityLoopError(RuntimeError):
    """The selected capability cannot be admitted to a loop."""


_FAILURE_TERMINAL_CODES = {
    "internet_access_denied": "POLICY_DENIED",
    "invalid_request": "INVALID_SPEC",
    "missing_secret": "BLOCKED",
    "secret_lookup_failed": "BLOCKED",
    "rate_limited": "BLOCKED",
    "invalid_provider_response": "VERIFICATION_REJECTED",
    "invalid_transport_response": "VERIFICATION_REJECTED",
    "response_too_large": "VERIFICATION_REJECTED",
}


class _LoopScopedLedger:
    """Give directory tool events the identity of the loop that caused them."""

    def __init__(self, ledger, loop_id: str):
        self._ledger = ledger
        self._loop_id = loop_id

    def record(self, **event) -> None:
        if not event.get("loop_id"):
            event["loop_id"] = self._loop_id
        self._ledger.record(**event)


def _new_loop(*, goal: str, config, contract, ledger=None, parent=None):
    """Create a root or child loop while retaining the explicit contract."""
    from .recursive_loop import Loop, LoopError

    if parent is None:
        return Loop(goal, config, ledger=ledger, contract=contract)
    if parent.depth + 1 > parent.config.max_depth:
        raise CapabilityLoopError(
            f"max recursion depth {parent.config.max_depth} reached")
    if ledger is not None and ledger is not parent.ledger:
        raise CapabilityLoopError(
            "a child capability loop must use its parent's shared ledger")

    try:
        child = parent.spawn(goal, config, contract=contract)
    except LoopError as exc:
        raise CapabilityLoopError(str(exc)) from exc
    return child


def run_capability_ref_as_loop(directory, ref, operation: str, *,
                               request=None, ledger=None, parent=None,
                               **kwargs) -> dict:
    """Verify and invoke a Capability Directory LoopRef.

    Local discovery returns only the reference. This function binds the
    selected reference to the current registered handshake before the effectful
    capability loop starts.
    """
    import hashlib
    import json
    from .loop_capsule import LoopRef

    if not isinstance(ref, LoopRef):
        raise CapabilityLoopError("capability invocation requires a LoopRef")
    surface = ref.handshake.loop_id
    if (ref.handshake.role != "code_intelligence"
            or ref.payload_ref != f"capability://{surface}"):
        raise CapabilityLoopError("the selected ref is not a Static Architecture capability")
    handshake = directory.handshake(surface)
    current_digest = hashlib.sha256(json.dumps(
        handshake.describe(), sort_keys=True, default=str).encode()).hexdigest()
    if not ref.payload_digest or ref.payload_digest != current_digest:
        raise CapabilityLoopError(
            "the selected capability handshake changed after discovery")
    return run_capability_as_loop(
        directory, surface, operation, request=request, ledger=ledger,
        parent=parent, **kwargs)


def run_capability_as_loop(directory, surface: str, operation: str, *,
                           request=None, ledger=None, parent=None,
                           **kwargs) -> dict:
    """Attempt one selected capability inside an effect-bearing loop.

    The objective is to make exactly one governed attempt and report its
    outcome. A provider refusal therefore completes the attempt loop while the
    returned ``ok`` remains false. This preserves rate/reset metadata for Route
    without misreporting provider success or hiding a retry in the adapter.
    """
    handshake = directory.handshake(surface)
    if not handshake.supports(operation):
        raise CapabilityLoopError(
            f"{surface!r} does not support operation {operation!r}")

    from .loop_contract import LoopContract
    from .recursive_loop import LoopConfig, StepOutcome

    goal = (f"attempt Static Architecture capability {surface}.{operation} "
            "once and report its outcome")
    contract = LoopContract(
        name=f"{surface}.{operation}", execution_mode="code_only",
        input_roles=(handshake.input_schema or "capability_request",),
        output_roles=(handshake.output_schema or "capability_result",),
        effects=tuple(handshake.effects), locality=handshake.locality,
        cost_class=handshake.cost_class, role="static_architecture")
    config = LoopConfig(
        framework="custom", custom_steps=("invoke",), power="light",
        logical_kind="execution", replay_guarantee="event_equivalent",
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",), stop_condition="success_once")
    loop = _new_loop(goal=goal, config=config, contract=contract,
                     ledger=ledger, parent=parent)
    loop.ledger.record(
        loop_id=loop.loop_id, event="spec", capability_surface=surface,
        capability_operation=operation, input_schema=handshake.input_schema,
        output_schema=handshake.output_schema,
        effects=tuple(handshake.effects), locality=handshake.locality,
        cost_class=handshake.cost_class)
    holder = {}

    def handler(lp, step, context):
        call_kwargs = dict(kwargs)
        if request is not None:
            call_kwargs["request"] = request
        result = directory.call(
            surface, operation,
            ledger=_LoopScopedLedger(lp.ledger, lp.loop_id), **call_kwargs)
        value = result.value
        if value is None:
            value = {"ok": False, "error_code": "capability_call_failed"}
        holder["call"] = result
        holder["value"] = value
        if not result.ok:
            code = (value.get("error_code", "capability_call_failed")
                    if isinstance(value, dict)
                    else "capability_call_failed")
            lp.ledger.record(loop_id=lp.loop_id, event="failure.detected",
                             failure_kind=code, surface=surface,
                             operation=operation)
        # The governed attempt and its typed report completed. Provider success
        # remains the separate result.ok flag returned below.
        return StepOutcome(
            output=("invoke:reported:success" if result.ok
                    else "invoke:reported:failure"),
            mode="deterministic", confidence=1.0)

    loop_result = loop.run(handler=handler, max_steps=1)
    call_result = holder["call"]
    error_code = (holder["value"].get("error_code", "")
                  if isinstance(holder["value"], dict) else "")
    capability_terminal = ("ACCEPTED" if call_result.ok else
                           _FAILURE_TERMINAL_CODES.get(
                               error_code, "EFFECT_FAILED"))
    return {
        "record_type": "capability_loop_result/v1",
        "surface": surface, "operation": operation,
        "ok": bool(call_result.ok),
        "effects": list(contract.effects), "locality": contract.locality,
        "cost_class": contract.cost_class,
        "input_schema": handshake.input_schema,
        "output_schema": handshake.output_schema,
        "value": holder["value"], "loop_id": loop_result.loop_id,
        "model_calls": loop_result.model_calls,
        "attempts": loop_result.attempts,
        "accepted_attempt_reports": loop_result.accepted_successes,
        "stopped": loop_result.stopped,
        # The attempt loop can complete successfully while the attempted
        # provider effect fails. Keep those terminal meanings separate.
        "terminal_code": loop_result.terminal_code,
        "capability_terminal_code": capability_terminal,
    }


def self_test() -> dict:
    from ..static_architecture.capability_directory import (
        CapabilityDirectory, CapabilityHandshake, Endpoint)
    from .recursive_loop import LoopLedger

    calls = []
    directory = CapabilityDirectory()
    directory.register(CapabilityHandshake(
        "fixture_search", "static_component", "search a fixture index",
        operations=("search",), input_schema="query/v1",
        output_schema="results/v1", effects=("network",),
        locality="api_calling", cost_class="metered"),
        [Endpoint("search", lambda request:
                  calls.append(request) or {"ok": True, "items": ["ok"]})])
    directory.register(CapabilityHandshake(
        "fixture_rate_limit", "static_component", "return a typed refusal",
        operations=("search",), input_schema="query/v1",
        output_schema="results/v1", effects=("network",),
        locality="api_calling", cost_class="metered"),
        [Endpoint("search", lambda request: {
            "ok": False, "error_code": "rate_limited",
            "retry_after_reset": "1"})])

    refs = directory.search_static_architecture("search fixture")
    search_ref = next(ref for ref in refs
                      if ref.handshake.loop_id == "fixture_search")
    before = len(calls)
    ledger = LoopLedger()
    run = run_capability_ref_as_loop(
        directory, search_ref, "search", request={"q": "x"}, ledger=ledger)
    refused = run_capability_as_loop(
        directory, "fixture_rate_limit", "search", request={"q": "x"},
        ledger=ledger)
    run_init = next(event for event in ledger.events
                    if event.get("event") == "init"
                    and event.get("loop_id") == run["loop_id"])
    run_spec = next(event for event in ledger.events
                    if event.get("event") == "spec"
                    and event.get("loop_id") == run["loop_id"])
    tool_events = [event for event in ledger.events
                   if str(event.get("event", "")).startswith("tool_invocation")]
    from .loop_capsule import LoopRef
    changed_ref = LoopRef(
        search_ref.loop_ref, search_ref.handshake, search_ref.payload_ref,
        "0" * 64, search_ref.digest, search_ref.score, search_ref.source)
    changed_ref_refused = False
    try:
        run_capability_ref_as_loop(
            directory, changed_ref, "search", request={"q": "x"})
    except CapabilityLoopError:
        changed_ref_refused = True
    tests = [{
        "test": "static_discovery_is_effect_free_and_selected_call_is_a_loop",
        "passed": bool(
            refs and before == 0 and len(calls) == 1
            and run["value"]["items"] == ["ok"] and run["ok"]
            and run["model_calls"] == 0 and run["terminal_code"] == "ACCEPTED"
            and run_init["loop_id"] == run["loop_id"]
            and run_spec["effects"] == ("network",)
            and all(event["loop_id"] for event in tool_events)
            and changed_ref_refused and len(calls) == 1),
    }, {
        "test": "typed_capability_failure_survives_the_loop_for_route",
        "passed": bool(
            not refused["ok"]
            and refused["value"]["error_code"] == "rate_limited"
            and refused["value"]["retry_after_reset"] == "1"
            and refused["model_calls"] == 0
            and refused["terminal_code"] == "ACCEPTED"
            and refused["capability_terminal_code"] == "BLOCKED"),
    }]
    passed = sum(1 for test in tests if test["passed"])
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
