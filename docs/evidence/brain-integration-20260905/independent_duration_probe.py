"""Independent integer-duration oracle. Run only inside the review container."""
from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import json
import random
import sys
import unittest
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--module", required=True)
    parser.add_argument("--function", required=True)
    args = parser.parse_args()
    sys.path.insert(0, args.project_root)
    function = getattr(importlib.import_module(args.module), args.function)
    if not callable(function):
        raise TypeError("selected public API is not callable")
    day, hour, minute = 24 * 60 * 60, 60 * 60, 60
    cases = []

    def returned(label, value, expected, group):
        try:
            actual = function(value)
            outcome = {"returned_type": type(actual).__name__,
                       "returned_integer": actual if type(actual) is int else None}
            passed = type(actual) is int and actual == expected
        except BaseException as exc:
            outcome, passed = {"exception_type": type(exc).__name__}, False
        cases.append({"case": label, "group": group, "input": value,
                      "expected_integer": expected, "passed": passed, **outcome})

    examples = (
        ("P3DT4H5M", 3 * day + 4 * hour + 5 * minute),
        ("PT30S", 30),
        ("P1Y2M10DT2H30M", (365 + 2 * 30 + 10) * day + 2 * hour + 30 * minute),
    )
    for index, (value, expected) in enumerate(examples):
        returned("user_example_" + str(index + 1), value, expected, "user_examples")
    fixed = (
        ("P1Y", 365 * day), ("P1M", 30 * day), ("P1D", day),
        ("PT1H", hour), ("PT1M", minute), ("PT1S", 1),
        ("P0D", 0), ("PT0S", 0), ("PT0H0M0S", 0), ("P0Y0M0DT0H0M0S", 0),
        ("PT60S", minute), ("PT60M", hour), ("PT24H", day),
        ("P12M", 12 * 30 * day), ("P365D", 365 * day),
        ("P0001Y02M03DT004H005M006S", (365 + 60 + 3) * day + 4 * hour + 5 * minute + 6),
        ("PT10000000000000000000000007S", 10 ** 25 + 7),
    )
    for index, (value, expected) in enumerate(fixed):
        returned("unit_or_boundary_" + str(index + 1), value, expected, "integer_units_and_boundaries")
    rng = random.Random(20260905)
    for index in range(128):
        year, month, date, hours, minutes, seconds = (
            rng.randrange(10), rng.randrange(37), rng.randrange(801),
            rng.randrange(101), rng.randrange(201), rng.randrange(201))
        value = f"P{year}Y{month}M{date}DT{hours}H{minutes}M{seconds}S"
        expected = (365 * year + 30 * month + date) * day + hours * hour + minutes * minute + seconds
        returned("composition_" + str(index), value, expected, "generated_integer_compositions")

    malformed = (
        "", "P", "PT", "P1DT", "1D", "P1D2H", "PT1D", "P1Y1Y", "P1D2D",
        "P1M1Y", "P1D1M", "PT1S1M", "PT1M1H", "P1Q", "PT1Q", "P1D2",
        "junkPT30S", "PT30Sjunk", "P1D garbage", "PT1 H", "P1DTT1H",
        "PT30S\nJUNK", "PT30S\n", "P1D\n",
    )
    for index, value in enumerate(malformed):
        try:
            result = function(value)
            outcome = {"returned_type": type(result).__name__,
                       "returned_integer": result if type(result) is int else None}
            passed = False
        except BaseException as exc:
            outcome = {"exception_type": type(exc).__name__}
            passed = isinstance(exc, ValueError)
        cases.append({"case": "malformed_string_" + str(index), "group": "malformed_strings",
                      "input": value, "expected_exception": "ValueError", "passed": passed, **outcome})
    for value in (None, 0, 1.5, True, b"PT30S", [], {}):
        try:
            function(value)
            outcome, passed = {"returned": True}, False
        except BaseException as exc:
            outcome, passed = {"exception_type": type(exc).__name__}, isinstance(exc, ValueError)
        cases.append({"case": "malformed_type_" + type(value).__name__,
                      "group": "input_type_error_contract", "input_type": type(value).__name__,
                      "expected_exception": "ValueError", "passed": passed, **outcome})

    optional = []
    for value in ("P1W", "PT0.5S", "PT1.5H", "-P1D", "PT١S"):
        try:
            actual = function(value)
            observation = {"returned_type": type(actual).__name__,
                           "returned_integer": actual if type(actual) is int else None}
        except BaseException as exc:
            observation = {"exception_type": type(exc).__name__}
        optional.append({"input": value, "acceptance_required": False, **observation})

    suite = unittest.defaultTestLoader.discover(args.project_root, pattern="test*.py")
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        native = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
    groups = {}
    for group in sorted({case["group"] for case in cases}):
        selected = [case for case in cases if case["group"] == group]
        groups[group] = {"passed": sum(case["passed"] for case in selected), "total": len(selected)}
    report = {
        "record_type": "independent_duration_oracle/v1",
        "api": args.module + ":" + args.function,
        "scope": "integer Y/M/D and T-H/M/S designator strings; year365days,month30days",
        "oracle_basis": "independent arithmetic, not a second duration parser",
        "scope_notes": [
            "Weeks, fractions, signs and non-ASCII digits are observations, not added required features.",
            "Non-string errors are a separately reported API boundary; the candidate annotates str.",
            "A terminal newline is checked as trailing non-duration input, consistent with strict whole-string parsing.",
            "This finite suite does not establish complete ISO-8601 conformance."],
        "groups": groups, "passed": sum(case["passed"] for case in cases), "total": len(cases),
        "all_passed": all(case["passed"] for case in cases),
        "cases": cases, "broader_form_observations": optional,
        "candidate_own_suite": {"tests_run": native.testsRun, "failures": len(native.failures),
                                "errors": len(native.errors), "skipped": len(native.skipped),
                                "successful": native.wasSuccessful()},
        "model_calls": 0, "network_calls": 0,
    }
    print(json.dumps(report, sort_keys=True, ensure_ascii=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
