"""Tests for scripts/assemble_submission.py. Effects: writes only inside temporary folders and starts python3 for the script.

Run from the payload root: python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v
"""
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent.parent
SCRIPT = PAYLOAD / "scripts" / "assemble_submission.py"
EXAMPLE_INPUT = json.loads((PAYLOAD / "examples" / "input.json").read_text(encoding="utf-8"))
SAMPLE = "customer_id,renewed\nT003,0.5\nT001,0.5\nT002,0.5\nT004,0.5\n"
TEST_DATA = ("customer_id,region,tenure_months,monthly_spend\nT001,north,12,20\nT002,south,3,40\nT003,east,30,15\n"
             "T004,north,8,25\n")
PREDICTIONS = "customer_id,prediction\nT001,0.81\nT002,0.12\nT003,0.9\nT004,0.5\n"
PREDICTIONS_PATH = "work/experiments/baseline-ridge-01.test.csv"
TEST_PATH = "competition/data/test.csv"


def load_tool():
    spec = importlib.util.spec_from_file_location("assemble_submission_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TOOL = load_tool()


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ledger_line(run_id: str, predictions: str = PREDICTIONS, test: str = TEST_DATA, flags=(), **changes) -> str:
    record = {"record_type": "experiment_record/v1", "run_id": run_id, "step": "baseline_training",
              "metric": {"name": "auc", "direction": "maximize"}, "fold_scores": [1.0, 0.96, 0.9166666667, 0.8333333333],
              "mean_score": 0.9275, "flags": list(flags),
              "outputs": {"test_predictions": {"path": PREDICTIONS_PATH, "sha256": digest(predictions), "rows": 4}},
              "data": {"test": {"path": TEST_PATH, "sha256": digest(test), "rows": 4}}}
    record.update(changes)
    return json.dumps(record) + "\n"


SCHEMA_KEYWORDS = frozenset(("$schema", "$id", "$comment", "title", "description", "$defs", "$ref", "type",
                             "properties", "required", "additionalProperties", "items", "minItems", "maxItems",
                             "uniqueItems", "enum", "const", "minimum", "maximum", "minLength", "maxLength", "pattern"))
TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def schema_errors(value, schema, root=None, where="$"):
    """The JSON Schema subset these contracts use; an unknown keyword raises instead of passing."""
    root = schema if root is None else root
    if set(schema) - SCHEMA_KEYWORDS:
        raise ValueError(f"unsupported schema keywords {sorted(set(schema) - SCHEMA_KEYWORDS)}")
    if "$ref" in schema:
        return schema_errors(value, root["$defs"][schema["$ref"].split("/")[-1]], root, where)
    names = [schema["type"]] if isinstance(schema.get("type"), str) else schema.get("type", [])

    def fits(name):
        if name == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if name == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        return isinstance(value, TYPES[name])

    if names and not any(fits(name) for name in names):
        return [f"{where}: expected {names}"]
    errors = []
    if "const" in schema and (value != schema["const"] or type(value) is not type(schema["const"])):
        errors.append(f"{where}: const")
    if "enum" in schema and not any(value == item and type(value) is type(item) for item in schema["enum"]):
        errors.append(f"{where}: enum")
    if isinstance(value, str) and "pattern" in schema and not re.search(schema["pattern"], value):
        errors.append(f"{where}: pattern")
    if isinstance(value, str) and not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", len(value)):
        errors.append(f"{where}: length")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value < schema.get("minimum", value) or value > schema.get("maximum", value):
            errors.append(f"{where}: range")
    if isinstance(value, list):
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", len(value)):
            errors.append(f"{where}: item count")
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            errors.append(f"{where}: repeated items")
        for index, item in enumerate(value):
            errors += schema_errors(item, schema.get("items", {}), root, f"{where}[{index}]")
    if isinstance(value, dict):
        errors += [f"{where}: missing {name}" for name in schema.get("required", []) if name not in value]
        extra = schema.get("additionalProperties", True)
        for name, item in value.items():
            if name in schema.get("properties", {}):
                errors += schema_errors(item, schema["properties"][name], root, f"{where}.{name}")
            elif extra is False:
                errors.append(f"{where}: unexpected {name}")
            elif isinstance(extra, dict):
                errors += schema_errors(item, extra, root, f"{where}.{name}")
    return errors


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.write({EXAMPLE_INPUT["sample_submission_path"]: SAMPLE, TEST_PATH: TEST_DATA, PREDICTIONS_PATH: PREDICTIONS,
                    EXAMPLE_INPUT["ledger_path"]: ledger_line("baseline-constant-01") + ledger_line("baseline-ridge-01")})

    def tearDown(self):
        self.directory.cleanup()

    def write(self, files):
        for relative, text in files.items():
            (self.root / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.root / relative).write_text(text, encoding="utf-8")

    def run_tool(self, check_only=False, **changes):
        values = {**EXAMPLE_INPUT, **changes}
        arguments = ["--sample", values["sample_submission_path"], "--ledger", values["ledger_path"],
                     "--run-id", values["run_id"], "--id-column", values["id_column"],
                     "--value-type", values["value_type"], "--out-dir", values["output_dir"]]
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments,
                                   *(["--check-only"] if check_only else []), "--root", str(self.root)],
                                  capture_output=True, text=True, timeout=120)
        return finished.returncode, json.loads(finished.stdout)

    def refused(self, fragment, **changes):
        code, result = self.run_tool(**changes)
        self.assertEqual(code, 2, result)
        self.assertIn(fragment, result["reason"])
        self.assertFalse((self.root / "work" / "submissions").exists())

    # Positive path ---------------------------------------------------------------------------

    def test_check_only_writes_nothing(self):
        code, result = self.run_tool(check_only=True)
        self.assertEqual((code, result["status"]), (0, "ready"), result)
        self.assertEqual((result["prediction_column"], result["rows"], result["ledger_line"]), ("renewed", 4, 2))
        self.assertFalse((self.root / "work" / "submissions").exists())

    def test_record_equals_the_example_and_keeps_sample_order(self):
        code, result = self.run_tool()
        self.assertEqual(code, 0, result)
        self.assertEqual(result, read_json(PAYLOAD / "examples" / "output.json"))
        submission = (self.root / result["submission"]["path"]).read_text(encoding="utf-8")
        self.assertEqual(submission, "customer_id,renewed\nT003,0.9\nT001,0.81\nT002,0.12\nT004,0.5\n")
        self.assertEqual(read_json(self.root / "work" / "submissions" / "baseline-ridge-01.submission_record.json"),
                         result)

    def test_binary_labels_use_one_half_as_the_threshold(self):
        code, result = self.run_tool(value_type="binary_label")
        self.assertEqual(code, 0, result)
        submission = (self.root / result["submission"]["path"]).read_text(encoding="utf-8")
        self.assertEqual(submission, "customer_id,renewed\nT003,1\nT001,1\nT002,0\nT004,1\n")

    def test_run_flags_are_carried_into_the_record(self):
        self.write({EXAMPLE_INPUT["ledger_path"]: ledger_line("baseline-ridge-01", flags=["suspiciously_perfect"])})
        code, result = self.run_tool()
        self.assertEqual(code, 0, result)
        self.assertEqual(result["run_flags"], ["suspiciously_perfect"])

    # Known-wrong cases -------------------------------------------------------------------------

    def test_unknown_or_repeated_run_is_refused(self):
        self.refused("is not in the ledger", run_id="baseline-ridge-02")
        self.write({EXAMPLE_INPUT["ledger_path"]: ledger_line("baseline-ridge-01") * 2})
        self.refused("appears 2 times")

    def test_ledger_that_is_not_utf8_is_refused(self):
        ledger = self.root / EXAMPLE_INPUT["ledger_path"]
        ledger.write_bytes(ledger.read_bytes().replace(b'"baseline_training"', b'"baseline_\xff_training"', 1))
        self.refused("ledger line 1 is not UTF-8 text")

    def test_changed_predictions_or_test_data_are_refused(self):
        self.write({PREDICTIONS_PATH: PREDICTIONS.replace("0.81", "0.82")})
        self.refused("changed after the run was recorded")
        self.write({PREDICTIONS_PATH: PREDICTIONS, TEST_PATH: TEST_DATA + "T005,east,2,30\n"})
        self.refused("predictions may not fit it")

    def test_ids_that_differ_from_the_sample_are_refused(self):
        short = "customer_id,prediction\nT001,0.81\nT002,0.12\nT003,0.9\n"
        self.write({PREDICTIONS_PATH: short, EXAMPLE_INPUT["ledger_path"]: ledger_line("baseline-ridge-01", short)})
        self.refused("missing ['T004']")

    def test_probability_outside_zero_to_one_is_refused(self):
        wrong = PREDICTIONS.replace("0.9", "1.2")
        self.write({PREDICTIONS_PATH: wrong, EXAMPLE_INPUT["ledger_path"]: ledger_line("baseline-ridge-01", wrong)})
        self.refused("outside 0 to 1")
        code, result = self.run_tool(value_type="real_number")
        self.assertEqual(code, 0, result)

    def test_number_text_that_is_not_plain_decimal_is_refused(self):
        grouped = PREDICTIONS.replace("0.81", "0.8_1")
        self.write({PREDICTIONS_PATH: grouped, EXAMPLE_INPUT["ledger_path"]: ledger_line("baseline-ridge-01", grouped)})
        self.refused("not a plain decimal number")
        self.refused("not a plain decimal number", value_type="real_number")
        other_digits = PREDICTIONS.replace("0.12", "٠.١٢")
        self.write({PREDICTIONS_PATH: other_digits,
                    EXAMPLE_INPUT["ledger_path"]: ledger_line("baseline-ridge-01", other_digits)})
        self.refused("not a plain decimal number", value_type="real_number")
        header = ["customer_id", "renewed"]
        self.assertFalse(TOOL.verify(b"customer_id,renewed\nT003,1_0\n", header, ["T003"], 0, 1,
                                     "real_number")["values_valid"])
        self.assertTrue(TOOL.verify(b"customer_id,renewed\nT003,1e-06\n", header, ["T003"], 0, 1,
                                    "probability")["values_valid"])

    def test_ledger_fields_of_the_wrong_type_are_refused(self):
        # These fields are copied into the record, so a wrong type would break contracts/output.schema.json.
        for field, value in (("flags", "suspiciously_perfect"), ("metric", "auc"), ("fold_scores", "high"),
                             ("fold_scores", [0.9, "0.8"]), ("mean_score", "0.9"), ("mean_score", True),
                             ("flags", [1])):
            self.write({EXAMPLE_INPUT["ledger_path"]: ledger_line("baseline-ridge-01", **{field: value})})
            self.refused(f"ledger line 1: {field} ")
        self.write({EXAMPLE_INPUT["ledger_path"]: ledger_line("baseline-ridge-01", metric=None, fold_scores=None,
                                                              mean_score=None)})
        code, result = self.run_tool()
        self.assertEqual(code, 0, result)
        self.assertEqual(schema_errors(result, read_json(PAYLOAD / "contracts" / "output.schema.json")), [])
        self.assertEqual(result["cross_validation"], {"metric": None, "fold_scores": None, "mean_score": None})

    def test_sample_with_several_prediction_columns_is_refused(self):
        self.write({EXAMPLE_INPUT["sample_submission_path"]: "customer_id,a,b\nT001,0,0\n"})
        self.refused("one id column and one prediction column only")

    def test_existing_output_is_never_overwritten(self):
        self.assertEqual(self.run_tool()[0], 0)
        code, result = self.run_tool()
        self.assertEqual(code, 2)
        self.assertIn("never overwrites", result["reason"])

    def test_self_check_catches_a_wrong_order(self):
        header = ["customer_id", "renewed"]
        good = TOOL.verify(b"customer_id,renewed\nT003,0.9\nT001,0.81\n", header, ["T003", "T001"], 0, 1, "probability")
        self.assertTrue(all(good.values()))
        wrong = TOOL.verify(b"customer_id,renewed\nT001,0.81\nT003,0.9\n", header, ["T003", "T001"], 0, 1, "probability")
        self.assertFalse(wrong["ids_match_sample_order"])
        self.assertFalse(TOOL.verify(b"customer_id,renewed\nT003,1.5\n", header, ["T003"], 0, 1,
                                     "probability")["values_valid"])

    # Contracts and entry files -----------------------------------------------------------------

    def test_examples_follow_the_contracts(self):
        contracts = PAYLOAD / "contracts"
        self.assertEqual(schema_errors(EXAMPLE_INPUT, read_json(contracts / "input.schema.json")), [])
        example = read_json(PAYLOAD / "examples" / "output.json")
        self.assertEqual(schema_errors(example, read_json(contracts / "output.schema.json")), [])
        example["upload"] = "uploaded"
        self.assertTrue(schema_errors(example, read_json(contracts / "output.schema.json")))

    def test_entry_files_agree(self):
        agents = (PAYLOAD / "AGENTS.md").read_bytes()
        self.assertEqual((PAYLOAD / "GEMINI.md").read_bytes(), agents)
        self.assertEqual((PAYLOAD / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n")
        markers = set(re.findall(r"\{\{([A-Z][A-Z0-9_]*)\}\}", agents.decode("utf-8")))
        properties = read_json(PAYLOAD / "contracts" / "input.schema.json")["properties"]
        self.assertEqual(markers, {name.upper() for name in properties})
        task = read_json(PAYLOAD / "contracts" / "task.json")
        task_markers = set(re.findall(r"\{\{([A-Z][A-Z0-9_]*)\}\}", (PAYLOAD / "contracts" / "task.json").read_text()))
        self.assertEqual(task_markers, {"STEP_ID", "HARNESS_STYLE", "PROCESS_EFFECT", "BRIEF_STEP_ID", "RUN_STEP_ID"})
        # The step starts python3, and it consumes the brief's values and one recorded run.
        self.assertEqual(task["effects"], ["reads_fs", "writes_fs", "{{PROCESS_EFFECT}}"])
        self.assertEqual(task["dependency_ids"], ["{{BRIEF_STEP_ID}}", "{{RUN_STEP_ID}}"])
        for named in re.findall(r"\.baltor/step/scripts/([a-z_]+\.py)", agents.decode("utf-8")):
            self.assertTrue((PAYLOAD / "scripts" / named).is_file(), named)


if __name__ == "__main__":
    unittest.main()
