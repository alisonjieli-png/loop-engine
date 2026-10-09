"""Package tests shared by every public good analysis item, driven by the item's component.json.

They check that the files match their recorded digests and that a corrupted copy does not; that the schemas in the
card are the module's schemas and use only the validator's keywords; that the SDG association is a well-formed
proposal (goals 1 to 17, targets of those goals, indicators of those targets, a written basis) and that the card
names the dataset shape the item was built for; that the known-good example and every known answer give exactly
their expected output, through the function and through the command line, and conform to the output schema; that
the known-wrong example is refused with its declared reason; that a known-good input missing a required field is
refused; and that the validator answers its own known cases. When the item's public functions are replaced by ones
that raise, these tests fail.
"""
from __future__ import annotations

import copy
import hashlib
import importlib
import io
import json
import re
import unittest
from pathlib import Path

import kit_schema

ROOT = Path(__file__).resolve().parent
CARD = json.loads((ROOT / "component.json").read_text(encoding="utf-8"))
CONTRACT = CARD["contract"]
ENTRY = CONTRACT["entry_points"]
MODULE = importlib.import_module(ENTRY["module"])
GOOD = json.loads((ROOT / CONTRACT["examples"]["known_good"]).read_text(encoding="utf-8"))
WRONG = json.loads((ROOT / CONTRACT["examples"]["known_wrong"]).read_text(encoding="utf-8"))
ANSWERS = json.loads((ROOT / CONTRACT["examples"]["known_answers"]).read_text(encoding="utf-8"))
#: SDG goal, target and indicator identifiers as the global indicator framework writes them (9.c, 10.7.3).
TARGET = re.compile(r"(?:[1-9]|1[0-7])\.(?:[0-9]{1,2}|[a-z])")
INDICATOR = re.compile(r"(?:[1-9]|1[0-7])\.(?:[0-9]{1,2}|[a-z])\.[0-9]{1,2}")
DATASET = re.compile(r"[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*")


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


class CardTests(unittest.TestCase):
    def test_files_match_their_recorded_digests(self):
        self.assertTrue(CARD["files"])
        for row in CARD["files"]:
            data = (ROOT / row["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"], row["path"])

    def test_a_corrupted_copy_does_not_match_its_digest(self):
        row = next(item for item in CARD["files"] if item["path"] == ENTRY["module"] + ".py")
        data = (ROOT / row["path"]).read_bytes() + b"\n# corrupted copy\n"
        self.assertNotEqual(hashlib.sha256(data).hexdigest(), row["sha256"])

    def test_card_schemas_are_the_module_schemas_and_supported(self):
        self.assertEqual(canonical(CONTRACT["input_schema"]), canonical(MODULE.INPUT_SCHEMA))
        self.assertEqual(canonical(CONTRACT["output_schema"]), canonical(MODULE.OUTPUT_SCHEMA))
        self.assertEqual(kit_schema.schema_problems(MODULE.INPUT_SCHEMA), [])
        self.assertEqual(kit_schema.schema_problems(MODULE.OUTPUT_SCHEMA), [])
        self.assertEqual(MODULE.INPUT_SCHEMA.get("type"), "object")

    def test_every_declared_refusal_reason_is_listed(self):
        self.assertIn("input_invalid", CONTRACT["refusal_reasons"])
        self.assertEqual(sorted(CONTRACT["refusal_reasons"]), sorted(MODULE.REFUSALS))
        self.assertIn(WRONG["expected_refusal"]["reason"], CONTRACT["refusal_reasons"])

    def test_the_sdg_association_is_a_well_formed_proposal(self):
        sdg = CONTRACT["sdg"]
        self.assertEqual(sdg["status"], "proposal")
        self.assertTrue(isinstance(sdg["basis"], str) and sdg["basis"].strip())
        goals = sdg["goals"]
        self.assertEqual(goals, sorted(set(goals)))
        for goal in goals:
            self.assertTrue(type(goal) is int and 1 <= goal <= 17, goal)
        for target in sdg["targets"]:
            self.assertTrue(TARGET.fullmatch(target), target)
            self.assertIn(int(target.split(".")[0]), goals, target)
        for indicator in sdg["indicators"]:
            self.assertTrue(INDICATOR.fullmatch(indicator), indicator)
            self.assertIn(indicator.rsplit(".", 1)[0], sdg["targets"], indicator)
        if not goals:
            self.assertEqual((sdg["targets"], sdg["indicators"]), ([], []))

    def test_the_card_names_the_dataset_shape_it_was_built_for(self):
        derived = CONTRACT["derived_from"]
        self.assertTrue(isinstance(derived["shape"], str) and derived["shape"].strip())
        self.assertIsInstance(derived["kaggle_datasets"], list)
        for dataset in derived["kaggle_datasets"]:
            self.assertTrue(DATASET.fullmatch(dataset), dataset)


class ExampleTests(unittest.TestCase):
    def test_known_good_example_gives_its_expected_output(self):
        result = MODULE.run(copy.deepcopy(GOOD["input"]))
        self.assertEqual(canonical(result), canonical(GOOD["expected_output"]))
        self.assertEqual(kit_schema.validate(result, MODULE.OUTPUT_SCHEMA), [])

    def test_known_good_example_through_the_command_line(self):
        out = io.StringIO()
        code = MODULE.main([], io.StringIO(json.dumps(GOOD["input"])), out)
        self.assertEqual(code, 0)
        self.assertEqual(canonical(json.loads(out.getvalue())), canonical(GOOD["expected_output"]))

    def test_every_known_answer(self):
        self.assertGreaterEqual(len(ANSWERS), 3)
        for case in ANSWERS:
            result = MODULE.run(copy.deepcopy(case["input"]))
            self.assertEqual(canonical(result), canonical(case["expected_output"]), case["description"])
            self.assertEqual(kit_schema.validate(result, MODULE.OUTPUT_SCHEMA), [], case["description"])

    def test_known_wrong_example_is_refused_with_its_reason(self):
        with self.assertRaises(kit_schema.KitRefusal) as caught:
            MODULE.run(copy.deepcopy(WRONG["input"]))
        self.assertEqual(caught.exception.reason, WRONG["expected_refusal"]["reason"])

    def test_known_wrong_example_through_the_command_line(self):
        out = io.StringIO()
        code = MODULE.main([], io.StringIO(json.dumps(WRONG["input"])), out)
        self.assertEqual(code, 2)
        answer = json.loads(out.getvalue())
        self.assertEqual((answer["refused"], answer["reason"]), (True, WRONG["expected_refusal"]["reason"]))

    def test_a_missing_required_field_is_refused(self):
        required = MODULE.INPUT_SCHEMA.get("required", [])
        self.assertTrue(required)
        for name in required:
            broken = copy.deepcopy(GOOD["input"])
            broken.pop(name, None)
            with self.assertRaises(kit_schema.KitRefusal) as caught:
                MODULE.run(broken)
            self.assertEqual(caught.exception.reason, "input_invalid", name)

    def test_text_that_is_not_json_is_refused(self):
        out = io.StringIO()
        self.assertEqual(MODULE.main([], io.StringIO("{not json"), out), 2)
        self.assertEqual(json.loads(out.getvalue())["reason"], "input_not_json")

    def test_the_result_is_deterministic(self):
        first = canonical(MODULE.run(copy.deepcopy(GOOD["input"])))
        self.assertEqual(first, canonical(MODULE.run(copy.deepcopy(GOOD["input"]))))


class ValidatorTests(unittest.TestCase):
    SCHEMA = {"type": "object", "required": ["n", "when"], "additionalProperties": False,
              "properties": {"n": {"type": "integer", "minimum": 1}, "when": {"type": "string", "format": "date"},
                             "tag": {"enum": ["a", "b"]},
                             "values": {"type": "array", "items": {"type": "number"}, "maxItems": 2},
                             "at": {"type": "string", "format": "date-time"}}}

    def test_a_conforming_document_has_no_errors(self):
        self.assertEqual(kit_schema.validate({"n": 2, "when": "2026-10-09", "tag": "a", "values": [1, 2.5],
                                              "at": "2026-10-09T08:30:00Z"}, self.SCHEMA), [])

    def test_broken_values_are_refused(self):
        good = {"n": 2, "when": "2026-10-09"}
        for change in ({"n": 0}, {"n": True}, {"n": 1.5}, {"when": "2026-13-01"}, {"tag": "c"}, {"extra": 1},
                       {"values": [1, 2, 3]}, {"values": ["x"]}, {"at": "2026-10-09 08:30"}):
            self.assertTrue(kit_schema.validate({**good, **change}, self.SCHEMA), change)
        self.assertTrue(kit_schema.validate({"n": 2}, self.SCHEMA))

    def test_unsupported_schema_keywords_are_reported(self):
        self.assertTrue(kit_schema.schema_problems({"type": "object", "patternProperties": {}}))
        self.assertTrue(kit_schema.schema_problems({"type": "string", "format": "email"}))
        self.assertEqual(kit_schema.schema_problems(self.SCHEMA), [])


if __name__ == "__main__":
    unittest.main()
