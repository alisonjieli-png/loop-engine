"""Every outcome has a valid example, fields of one outcome are refused in another, and a lenient check is caught."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import schema_lite
from work_result_type import SCHEMA, TERMINAL, classify_work_result, make_work_result, validate_work_result

ARTIFACT = {"kind": "file", "locator": "src/report.py"}
EVIDENCE = [{"claim": "unit tests pass", "method": "test", "reference": {"kind": "record", "locator": "runs/42"}}]
EXAMPLES = {
    "completed": {"artifact": ARTIFACT, "evidence": EVIDENCE},
    "no_change_needed": {"evidence": [{"claim": "timeout already 30 s", "method": "inspection",
                                       "reference": {"kind": "file", "locator": "config.toml"}}]},
    "needs_input": {"required_fields": [{"name": "region", "description": "deployment region", "type": "choice",
                                         "choices": ["us", "eu"]}]},
    "needs_scope_expansion": {"reason": "the fix touches the shared parser", "proposed_scope": {"add": ["src/parser.py"]}},
    "unsupported": {"reason": "the task needs a GPU and none is available"},
    "budget_exhausted": {"checkpoint": {"kind": "commit", "locator": "a1b2c3d"},
                         "remaining_obligations": ["migrate table b"], "consumed": {"model_tokens": 120000}},
}


def _full(outcome, fields):
    return {"record_type": "work_result/v1", "outcome": outcome, **copy.deepcopy(fields)}


def _lenient(result):
    """Known-wrong validator: accepts any object whose outcome is one of the six names."""
    return isinstance(result, dict) and result.get("outcome") in TERMINAL


class WorkResultTests(unittest.TestCase):
    def test_embedded_schema_equals_schema_file(self):
        on_disk = json.loads((Path(__file__).resolve().parent / "schema.json").read_text(encoding="utf-8"))
        self.assertEqual(on_disk, SCHEMA)
        schema_lite.check_schema(SCHEMA)

    def test_every_outcome_has_a_valid_example(self):
        for outcome, fields in EXAMPLES.items():
            with self.subTest(outcome=outcome):
                report = validate_work_result(_full(outcome, fields))
                self.assertEqual((report["valid"], report["outcome"], report["errors"]), (True, outcome, []))
                self.assertEqual(classify_work_result(_full(outcome, fields))["terminal"], TERMINAL[outcome])

    def test_fields_of_another_outcome_are_refused(self):
        for outcome, fields in EXAMPLES.items():
            for other, other_fields in EXAMPLES.items():
                foreign = set(other_fields) - set(SCHEMA["$defs"][outcome]["properties"])
                for name in sorted(foreign):
                    with self.subTest(outcome=outcome, foreign=name):
                        mixed = _full(outcome, fields)
                        mixed[name] = copy.deepcopy(other_fields[name])
                        self.assertFalse(validate_work_result(mixed)["valid"])

    def test_lenient_check_is_caught(self):
        no_evidence = _full("completed", {"artifact": ARTIFACT, "evidence": []})
        self_cited = _full("completed", {"artifact": ARTIFACT, "evidence": [
            {"claim": "the file exists", "method": "inspection", "reference": ARTIFACT}]})
        for bad in (no_evidence, self_cited, _full("needs_input", {"required_fields": []})):
            with self.subTest(bad=bad):
                self.assertTrue(_lenient(bad), "the control accepts it")
                self.assertFalse(validate_work_result(bad)["valid"])

    def test_semantic_rules(self):
        duplicate = _full("needs_input", {"required_fields": [{"name": "a", "description": "x"},
                                                              {"name": "a", "description": "y"}]})
        choice_without_choices = _full("needs_input", {"required_fields": [{"name": "a", "description": "x",
                                                                            "type": "choice"}]})
        repeated = _full("budget_exhausted", {"checkpoint": {"kind": "commit", "locator": "abc"},
                                              "remaining_obligations": ["a", "a"]})
        overlap = _full("needs_scope_expansion", {"reason": "x", "proposed_scope": {"add": ["a"], "remove": ["a"]}})
        for bad in (duplicate, choice_without_choices, repeated, overlap):
            with self.subTest(bad=bad["outcome"]):
                report = validate_work_result(bad)
                self.assertFalse(report["valid"])
                self.assertTrue(report["errors"])

    def test_constructor_and_classifier_refuse_invalid_results(self):
        self.assertEqual(make_work_result("unsupported", {"reason": "needs a GPU"})["outcome"], "unsupported")
        with self.assertRaises(ValueError):
            make_work_result("completed", {"artifact": ARTIFACT, "evidence": []})
        with self.assertRaises(ValueError):
            make_work_result("finished", {})
        with self.assertRaises(ValueError):
            classify_work_result({"outcome": "completed"})
        self.assertFalse(validate_work_result("completed")["valid"])


if __name__ == "__main__":
    unittest.main()
