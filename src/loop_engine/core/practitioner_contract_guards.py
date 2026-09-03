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


def contract_guard_checks() -> list:
    """Every contract guard, as one list of test records."""
    return [schema_matches_record(), *retry_classification()]


def self_test() -> dict:
    """Prove the guards themselves report rather than assert."""
    tests = contract_guard_checks()
    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "practitioner_contract_guard_test/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
