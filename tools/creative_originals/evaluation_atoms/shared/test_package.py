"""The self-test every evaluation atom package runs: its card, its files, every known answer and known-wrong case.

    python3 -m unittest test_package

The test reads component.json, imports the item module the card names and checks that
- every file's SHA-256 matches the card, and a corrupted copy is refused;
- every contract case calls a declared entry point, and every entry point is a function of the module;
- every known answer returns its expected value within its tolerance, or raises ValueError when the case says so;
- every known-wrong case returns something other than the declared wrong value, and each item declares one;
- a perturbed copy of each expected value is refused by the same comparison, so the comparison is not vacuous;
- the JSON command line reproduces the first known answer and refuses an unknown call;
- the shared numerics and schema helpers reproduce their own known answers.

A case is {"name", "call", "arguments", "select"?, "expect" | "raises", "tolerance"?}; a known-wrong case has
"reject" and "why" in place of "expect". "select" is a list of keys and indices applied to the result. Numbers match
when |actual - expected| <= tolerance * max(1, |expected|), the default tolerance being 1e-9.
"""
from __future__ import annotations

import hashlib
import importlib
import io
import json
import math
import unittest
from pathlib import Path

import atom_cli
import numerics
import schema_lite

ROOT = Path(__file__).resolve().parent
CARD = json.loads((ROOT / "component.json").read_text(encoding="utf-8"))
CONTRACT = CARD["contract"]
MODULE = importlib.import_module(CARD["job"]["identity"])
DEFAULT_TOLERANCE = 1e-9


def _select(value, path):
    for key in path:
        value = value[key]
    return value


def _matches(actual, expected, tolerance):
    if expected is None or isinstance(expected, (bool, str)):
        return type(actual) is type(expected) and actual == expected
    if isinstance(expected, (int, float)):
        if isinstance(actual, bool) or not isinstance(actual, (int, float)) or not math.isfinite(actual):
            return False
        return abs(actual - expected) <= tolerance * max(1.0, abs(expected))
    if isinstance(expected, list):
        return (isinstance(actual, list) and len(actual) == len(expected)
                and all(_matches(a, e, tolerance) for a, e in zip(actual, expected)))
    if isinstance(expected, dict):
        return (isinstance(actual, dict) and set(actual) == set(expected)
                and all(_matches(actual[key], expected[key], tolerance) for key in expected))
    return False


def _perturbed(expected, tolerance):
    """A copy of ``expected`` that differs from it by more than ``tolerance`` in one place."""
    if isinstance(expected, bool):
        return not expected
    if expected is None:
        return 0
    if isinstance(expected, str):
        return expected + "_changed"
    if isinstance(expected, (int, float)):
        return expected + max(1e-6, 1000.0 * tolerance) * max(1.0, abs(expected))
    if isinstance(expected, list):
        return [_perturbed(expected[0], tolerance)] + expected[1:] if expected else [0]
    if isinstance(expected, dict):
        if not expected:
            return {"changed": 0}
        first = sorted(expected)[0]
        return {**expected, first: _perturbed(expected[first], tolerance)}
    raise AssertionError(f"unsupported expected value {expected!r}")


def _evaluate(case):
    function = getattr(MODULE, case["call"])
    return numerics.json_safe(function(**case["arguments"]))


class CardTests(unittest.TestCase):
    def test_files_match_card(self):
        for row in CARD["files"]:
            data = (ROOT / row["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"], row["path"])

    def test_corrupted_copy_is_refused(self):
        row = CARD["files"][0]
        data = bytearray((ROOT / row["path"]).read_bytes())
        data[len(data) // 2] ^= 0x01
        self.assertNotEqual(hashlib.sha256(bytes(data)).hexdigest(), row["sha256"])

    def test_readme_starts_with_title(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# " + CARD["title"] + "\n"))

    def test_contract_shape(self):
        for key in ("entry_points", "assumptions", "guarantees", "known_answers", "known_wrong"):
            self.assertTrue(CONTRACT.get(key), f"contract declares no {key}")
        names = [row["name"] for row in CONTRACT["entry_points"]]
        self.assertEqual(len(names), len(set(names)))
        for row in CONTRACT["entry_points"]:
            self.assertEqual(set(row), {"name", "arguments", "returns"})
            self.assertTrue(callable(getattr(MODULE, row["name"], None)), row["name"])
        cases = CONTRACT["known_answers"] + CONTRACT["known_wrong"]
        self.assertEqual(len({case["name"] for case in cases}), len(cases), "case names repeat")
        for case in cases:
            self.assertIn(case["call"], names, case["name"])
            self.assertIsInstance(case["arguments"], dict)
        for case in CONTRACT["known_wrong"]:
            self.assertIn("reject", case)
            self.assertTrue(case.get("why"), case["name"])


class KnownAnswerTests(unittest.TestCase):
    def test_known_answers(self):
        for case in CONTRACT["known_answers"]:
            with self.subTest(case=case["name"]):
                if "raises" in case:
                    self.assertEqual(case["raises"], "ValueError")
                    with self.assertRaises(ValueError):
                        _evaluate(case)
                    continue
                actual = _select(_evaluate(case), case.get("select", []))
                tolerance = case.get("tolerance", DEFAULT_TOLERANCE)
                self.assertTrue(_matches(actual, case["expect"], tolerance),
                                f"{case['name']}: got {actual!r}, expected {case['expect']!r}")

    def test_known_wrong_values_are_rejected(self):
        for case in CONTRACT["known_wrong"]:
            with self.subTest(case=case["name"]):
                actual = _select(_evaluate(case), case.get("select", []))
                tolerance = case.get("tolerance", DEFAULT_TOLERANCE)
                self.assertFalse(_matches(actual, case["reject"], tolerance),
                                 f"{case['name']}: the result equals the known-wrong value {case['reject']!r}")

    def test_comparison_refuses_perturbed_expectations(self):
        for case in CONTRACT["known_answers"]:
            if "expect" not in case:
                continue
            with self.subTest(case=case["name"]):
                tolerance = case.get("tolerance", DEFAULT_TOLERANCE)
                actual = _select(_evaluate(case), case.get("select", []))
                self.assertFalse(_matches(actual, _perturbed(case["expect"], tolerance), tolerance))


class CommandLineTests(unittest.TestCase):
    def test_command_line_reproduces_first_known_answer(self):
        case = next(case for case in CONTRACT["known_answers"] if "expect" in case)
        output = io.StringIO()
        request = json.dumps({"call": case["call"], "arguments": case["arguments"]})
        status = MODULE.main([], io.StringIO(request), output)
        self.assertEqual(status, 0, output.getvalue())
        reply = json.loads(output.getvalue())
        actual = _select(reply["result"], case.get("select", []))
        self.assertTrue(_matches(actual, case["expect"], case.get("tolerance", DEFAULT_TOLERANCE)))

    def test_command_line_refuses_unknown_call_and_lists_entry_points(self):
        output = io.StringIO()
        status = MODULE.main([], io.StringIO(json.dumps({"call": "no_such_call", "arguments": {}})), output)
        self.assertEqual(status, 2)
        self.assertIn("error", json.loads(output.getvalue()))
        listing = io.StringIO()
        self.assertEqual(MODULE.main(["--list"], io.StringIO(""), listing), 0)
        listed = {row["name"] for row in json.loads(listing.getvalue())}
        self.assertTrue({row["name"] for row in CONTRACT["entry_points"]} <= listed)

    def test_command_line_reports_invalid_arguments(self):
        case = next((case for case in CONTRACT["known_answers"] if "raises" in case), None)
        if case is None:
            self.skipTest("the item declares no refused input")
        output = io.StringIO()
        status = MODULE.main([], io.StringIO(json.dumps({"call": case["call"], "arguments": case["arguments"]})),
                             output)
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(output.getvalue())["error"]["type"], "ValueError")


class SharedHelperTests(unittest.TestCase):
    def test_linear_algebra_known_answers(self):
        self.assertTrue(_matches(numerics.solve([[2, 1], [1, 3]], [3, 5]), [0.8, 1.4], 1e-12))
        self.assertTrue(_matches(numerics.inverse([[4, 7], [2, 6]]), [[0.6, -0.7], [-0.2, 0.4]], 1e-12))
        self.assertTrue(_matches(numerics.determinant([[1, 2], [3, 4]]), -2.0, 1e-12))
        self.assertTrue(_matches(numerics.cholesky([[4, 2], [2, 3]]), [[2, 0], [1, math.sqrt(2)]], 1e-12))
        values, vectors = numerics.symmetric_eigen([[2, 1], [1, 2]])
        self.assertTrue(_matches(values, [3.0, 1.0], 1e-12))
        self.assertTrue(_matches(numerics.least_squares([[1, 0], [1, 1], [1, 2]], [1, 3, 5]), [1.0, 2.0], 1e-12))
        with self.assertRaises(ValueError):
            numerics.solve([[1, 2], [2, 4]], [1, 1])  # known-wrong control: a singular matrix is refused
        with self.assertRaises(ValueError):
            numerics.cholesky([[1, 2], [2, 1]])  # indefinite

    def test_distribution_known_answers(self):
        self.assertTrue(_matches(numerics.normal_quantile(0.975), 1.959963984540054, 1e-12))
        self.assertTrue(_matches(numerics.regularized_beta(0.3, 1, 1), 0.3, 1e-12))
        self.assertTrue(_matches(numerics.chi_square_survival(2.0, 2), math.exp(-1.0), 1e-12))
        self.assertTrue(_matches(numerics.student_t_two_sided_p(1.0, 1), 0.5, 1e-12))
        self.assertTrue(_matches(numerics.f_survival(3.0, 2, 6), (1.0 + 1.0) ** -3, 1e-12))
        self.assertTrue(_matches(numerics.binomial_cdf(1, 10, 0.5), 11 / 1024, 1e-12))
        self.assertTrue(_matches(numerics.average_ranks([10, 20, 20, 30]), [1.0, 2.5, 2.5, 4.0], 0.0))

    def test_seeded_draws_are_fixed(self):
        self.assertEqual(numerics.seeded_random(1).random(), 0.13436424411240122)
        self.assertEqual(numerics.shuffled(numerics.seeded_random(3), range(10)), [1, 5, 7, 6, 0, 3, 8, 9, 4, 2])
        self.assertTrue(_matches(numerics.standard_normals(numerics.seeded_random(0), 2),
                                 [0.02905342918396547, -0.5808287773537824], 1e-12))

    def test_validation_refuses_non_finite_and_boolean_input(self):
        for bad in (float("nan"), float("inf"), True, None, "1"):
            with self.subTest(value=bad), self.assertRaises(ValueError):
                numerics.finite_number(bad)
        with self.assertRaises(ValueError):
            numerics.json_safe({"value": float("nan")})

    def test_schema_subset(self):
        schema = {"type": "object", "required": ["kind"], "additionalProperties": False,
                  "properties": {"kind": {"enum": ["a", "b"]}, "count": {"type": "integer", "minimum": 0}}}
        self.assertEqual(schema_lite.validate({"kind": "a", "count": 2}, schema), [])
        self.assertTrue(schema_lite.validate({"kind": "c"}, schema))
        self.assertTrue(schema_lite.validate({"kind": "a", "extra": 1}, schema))
        self.assertTrue(schema_lite.validate({"kind": "a", "count": -1}, schema))
        self.assertTrue(schema_lite.validate({"kind": "a", "count": True}, schema))
        with self.assertRaises(ValueError):
            schema_lite.check_schema({"if": {"type": "object"}})

    def test_command_line_helper(self):
        reply, status = atom_cli.handle({"double": lambda value: 2 * value}, {"call": "double", "arguments": {"value": 4}})
        self.assertEqual((reply["result"], status), (8, 0))
        reply, status = atom_cli.handle({"bad": lambda: float("nan")}, {"call": "bad", "arguments": {}})
        self.assertEqual(status, 2)


if __name__ == "__main__":
    unittest.main()
