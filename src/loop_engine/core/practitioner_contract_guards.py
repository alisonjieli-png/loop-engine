"""Checks that hold a contract to what the code on both sides of it does.

Owns: the guards that compare one written-down statement of a contract
against another — the orientation schema shown to a model against the record
enforced on its answer, and the retry classification against what each error
code actually says about the provider.

Belongs to: the adaptive Practitioner's self-test surface.  Never: runtime
behaviour. Nothing here runs during a solve; these exist because both defects
they catch produce a run that merely ends, which no other gate can see.
"""
from __future__ import annotations


def schema_matches_record() -> dict:
    """Check the schema shown to the model against the record enforced on it.

    These are two hand-written copies of one field list: the example in
    ``orient`` documents a type per field, the record validates on exact set
    equality. When they drift the model is asked for one shape and refused
    for returning it, and the refusal names the record, never the example.
    That failure is silent in every gate that does not compare them here.
    """
    import ast
    import pathlib
    from dataclasses import fields as _fields
    from .adaptive_practitioner_records import TaskOrientationResult
    source = ast.parse((pathlib.Path(__file__).parent
                        / "adaptive_practitioner.py").read_text())
    shown = set()
    for node in ast.walk(source):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "attr", "") != "dumps" or not node.args:
            continue
        argument = node.args[0]
        if not isinstance(argument, ast.Dict):
            continue
        keys = {key.value for key in argument.keys
                if isinstance(key, ast.Constant)}
        if "original_task_ref" in keys:
            shown = keys
            break
    enforced = {item.name for item in _fields(TaskOrientationResult)}
    return {"test": "the orient schema shown matches the record enforced",
            "passed": shown == enforced,
            "detail": "" if shown == enforced else
                      f"shown-only {sorted(shown - enforced)}; "
                      f"enforced-only {sorted(enforced - shown)}"}


def retry_classification() -> list:
    """Hold the line between an unlucky attempt and a refused request.

    A retryable code says the next identical call may well succeed; a
    deterministic one says it cannot. Getting this wrong is expensive in
    both directions — a fatal code discards a whole run over one bad sample,
    and a retryable one spends three calls to earn the same refusal — and
    neither shows up in any other gate, because both produce a run that
    merely ends.
    """
    from .adaptive_practitioner_records import _RETRYABLE_TRANSPORT_ERRORS
    #: Outcomes of one attempt: the same request may fare better next time.
    transient = ("network_unreachable", "provider_unavailable", "timeout",
                 "gateway_timeout", "rate_limited",
                 "output_validation_failed")
    #: Properties of the request itself: a second identical call is refused
    #: identically, so retrying only spends calls to learn nothing.
    settled = ("invalid_request", "model_not_found",
               "model_identity_mismatch")
    missing = [code for code in transient
               if code not in _RETRYABLE_TRANSPORT_ERRORS]
    wrong = [code for code in settled if code in _RETRYABLE_TRANSPORT_ERRORS]
    from .adaptive_practitioner_records import (
        _ATTEMPTS_FOR_ERROR, _MAXIMUM_TRANSPORT_ATTEMPTS)
    empty = _ATTEMPTS_FOR_ERROR.get("output_validation_failed", 0)
    return [
        {"test": "a response that arrived empty is tried more than a dark socket",
         "passed": empty > _MAXIMUM_TRANSPORT_ATTEMPTS,
         "detail": f"empty-answer attempts {empty}, "
                   f"transport attempts {_MAXIMUM_TRANSPORT_ATTEMPTS}"},
        {"test": "an attempt-level failure is tried again",
         "passed": not missing,
         "detail": "" if not missing else f"not retried: {missing}"},
        {"test": "a settled refusal is not tried again",
         "passed": not wrong,
         "detail": "" if not wrong else f"retried pointlessly: {wrong}"},
    ]


def extra_fields_are_information() -> list:
    """Hold the rule that absence is a defect and surplus is not.

    Every record here is parsed from something a model wrote. A model with
    more to say than the schema names will occasionally say it, and a
    validator built on exact-set equality answers that by discarding the
    whole reply — the orientation, the file, the review — along with the
    work that produced it. One such key ended runs across a twelve
    competition campaign before anything said which field was at fault.

    Records parsed from storage or from an untrusted external service are
    deliberately absent from this list. Both sides of those are code, or the
    strictness is itself the guard.
    """
    from dataclasses import fields as _fields
    from .adaptive_practitioner_records import (
        NextActionDecision, TaskOrientationResult)

    def outcome(record, mapping) -> str:
        """What the record makes of one mapping, success or refusal alike."""
        try:
            record.from_mapping(mapping)
            return "accepted"
        except Exception as exc:                       # noqa: BLE001
            return str(exc)

    checks = []
    for record in (TaskOrientationResult, NextActionDecision):
        complete = {item.name: "" for item in _fields(record)}
        surplus = {**complete, "a_field_no_schema_names": "still information"}
        # Compared against the same mapping without the surplus field, so the
        # check isolates the surplus itself and does not depend on the values
        # being valid for every other reason a record may refuse them.
        unchanged = outcome(record, complete) == outcome(record, surplus)
        short = {key: item for key, item in complete.items()
                 if key != sorted(complete)[0]}
        named = "missing" in outcome(record, short).lower()
        checks.append({
            "test": f"{record.__name__} keeps an answer that says more",
            "passed": unchanged,
            "detail": "" if unchanged else
                      "a surplus field changed the verdict on the whole reply"})
        checks.append({
            "test": f"{record.__name__} still refuses an answer that says less",
            "passed": named,
            "detail": "" if named else "absence was not named as the defect"})
    return checks


def stated_wait_is_honoured_and_bounded() -> list:
    """A provider that states its wait is waited for, up to the ceiling,
    and the ledger says what was stated, what was waited, and whether the
    ceiling cut it; a result that states nothing waits nothing."""
    from types import SimpleNamespace
    from .adaptive_practitioner_records import (
        _MAXIMUM_STATED_WAIT_SECONDS, _honour_stated_wait, _stated_wait_seconds)
    events = []
    slept = []
    owner = SimpleNamespace(loop_id="guard-owner", ledger=SimpleNamespace(
        record=lambda **fields: events.append(fields)))
    request = SimpleNamespace(step_id="guard-step")

    def result(retry_after):
        return SimpleNamespace(attempts=(SimpleNamespace(retry_after_seconds=retry_after),))

    short = _honour_stated_wait(owner, request, result(7), "rate_limited", 1, sleep=slept.append)
    long = _honour_stated_wait(owner, request, result(7200), "usage_limit_reached", 2,
                               sleep=slept.append)
    throttled = _honour_stated_wait(owner, request, result(None), "rate_limited", 1,
                                    sleep=slept.append)
    none = _honour_stated_wait(owner, request, result(None), "timeout", 1, sleep=slept.append)
    empty = _honour_stated_wait(owner, request, SimpleNamespace(attempts=()), "timeout", 1,
                                sleep=slept.append)
    return [
        {"test": "a short stated wait is waited in full and recorded",
         "passed": short == 7.0 and slept[:1] == [7.0] and events
         and events[0]["custom_kind"] == "provider_stated_wait_honoured"
         and events[0]["stated_wait_seconds"] == 7.0 and events[0]["cut_at_ceiling"] is False,
         "detail": str(events[:1])[:160]},
        {"test": "a long stated wait is cut at the ceiling and the record says so",
         "passed": long == float(_MAXIMUM_STATED_WAIT_SECONDS) and len(events) >= 2
         and events[1]["cut_at_ceiling"] is True and events[1]["stated_wait_seconds"] == 7200.0,
         "detail": str(events[1:2])[:160]},
        {"test": "an unstated throttle gets the slow backoff and the record says it is unstated",
         "passed": throttled == 15.0 and len(events) == 3
         and events[2]["custom_kind"] == "throttle_backoff_applied"
         and events[2]["stated_wait_seconds"] is None and events[2]["waited_seconds"] == 15.0,
         "detail": str(events[2:3])[:160]},
        {"test": "no stated wait and no throttle means no wait and no record",
         "passed": none == 0.0 and empty == 0.0 and len(slept) == 3 and len(events) == 3
         and _stated_wait_seconds(result(True)) is None and _stated_wait_seconds(None) is None,
         "detail": ""},
    ]


def contract_guard_checks() -> list:
    """Every contract guard, as one list of test records."""
    return [schema_matches_record(), *retry_classification(),
            *extra_fields_are_information(), *stated_wait_is_honoured_and_bounded()]


def self_test() -> dict:
    """Prove the guards themselves report rather than assert."""
    tests = contract_guard_checks()
    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "practitioner_contract_guard_test/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
