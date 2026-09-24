"""Tests for scripts/train_baseline.py. Effects: writes only inside temporary folders and starts python3 for the script.

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
SCRIPT = PAYLOAD / "scripts" / "train_baseline.py"
EXAMPLE_INPUT = json.loads((PAYLOAD / "examples" / "input.json").read_text(encoding="utf-8"))
REGIONS = ("north", "south", "east")


def load_tool():
    spec = importlib.util.spec_from_file_location("train_baseline_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TOOL = load_tool()


def renewal_files(leak: bool = False) -> dict:
    """Deterministic synthetic customers; renewal depends on tenure. The test file lists columns in another order."""
    train = ["customer_id,tenure_months,monthly_spend,region,renewed" + (",renewal_flag" if leak else "")]
    folds = ["customer_id,fold"]
    for index in range(40):
        tenure, spend, region = (index * 7) % 37 + 1, 10 + (index * 13) % 50, REGIONS[index % 3]
        renewed = 1 if tenure + (index * 13) % 17 - 8 + (index % 3) * 3 > 20 else 0
        train.append(f"C{index:03d},{tenure},{spend},{region},{renewed}" + (f",{renewed}" if leak else ""))
        folds.append(f"C{index:03d},{index % 4}")
    test = ["customer_id,region,tenure_months,monthly_spend" + (",renewal_flag" if leak else "")]
    for index in range(12):
        tenure, spend, region = (index * 11) % 36 + 1, 12 + (index * 17) % 45, REGIONS[index % 3]
        test.append(f"T{index:03d},{region},{tenure},{spend}" + (",1" if leak else ""))
    return {"competition/data/train.csv": "\n".join(train) + "\n", "competition/data/test.csv": "\n".join(test) + "\n",
            "work/folds/folds.csv": "\n".join(folds) + "\n"}


def sales_files() -> dict:
    """Deterministic synthetic regression data: sales grow with two numeric columns."""
    train, folds, test = ["shop_id,area,staff,sales"], ["shop_id,fold"], ["shop_id,area,staff"]
    for index in range(30):
        area, staff = 20 + (index * 9) % 61, 1 + (index * 5) % 7
        sales = 3 * area + 11 * staff + (index % 4) * 2
        train.append(f"S{index:02d},{area},{staff},{sales}")
        folds.append(f"S{index:02d},{index % 3}")
    for index in range(6):
        test.append(f"Q{index:02d},{25 + index * 8},{1 + index}")
    return {"data/train.csv": "\n".join(train) + "\n", "data/test.csv": "\n".join(test) + "\n",
            "data/folds.csv": "\n".join(folds) + "\n"}


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


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.write(renewal_files())

    def tearDown(self):
        self.directory.cleanup()

    def write(self, files):
        for relative, text in files.items():
            (self.root / relative).parent.mkdir(parents=True, exist_ok=True)
            (self.root / relative).write_text(text, encoding="utf-8")

    def run_tool(self, **changes):
        values = {**EXAMPLE_INPUT, **changes}
        arguments = ["--train", values["train_path"], "--test", values["test_path"], "--folds", values["folds_path"],
                     "--id-column", values["id_column"], "--target-column", values["target_column"],
                     "--task-type", values["task_type"], "--metric", values["metric"], "--baseline", values["baseline"],
                     "--features", values["features"], "--run-id", values["run_id"], "--out-dir", values["output_dir"],
                     "--ledger", values["ledger_path"]]
        if values.get("check_only"):
            arguments.append("--check-only")
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments, "--root", str(self.root)],
                                  capture_output=True, text=True, timeout=300)
        return finished.returncode, json.loads(finished.stdout)

    def refused(self, fragment, **changes):
        code, result = self.run_tool(**changes)
        self.assertEqual(code, 2, result)
        self.assertIn(fragment, result["reason"])

    # Positive path ---------------------------------------------------------------------------

    def test_check_only_writes_nothing(self):
        code, result = self.run_tool(check_only=True)
        self.assertEqual((code, result["status"]), (0, "ready"), result)
        self.assertEqual(result["folds"], [0, 1, 2, 3])
        self.assertFalse((self.root / "work" / "experiments").exists())

    def test_record_equals_the_example_and_ends_the_ledger(self):
        code, result = self.run_tool()
        self.assertEqual((code, result["status"]), (0, "recorded"), result)
        self.assertEqual(result["record"], read_json(PAYLOAD / "examples" / "output.json"))
        ledger = (self.root / EXAMPLE_INPUT["ledger_path"]).read_text(encoding="utf-8").splitlines()
        self.assertEqual(json.loads(ledger[-1]), result["record"])
        for entry in result["record"]["outputs"].values():
            data = (self.root / entry["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"])
        self.assertEqual(result["record"]["script"]["sha256"], hashlib.sha256(SCRIPT.read_bytes()).hexdigest())

    def test_the_constant_reference_and_flags(self):
        code, result = self.run_tool(baseline="group_mean", features="region", metric="log_loss", run_id="gm-01")
        self.assertEqual(code, 0, result)
        record = result["record"]
        self.assertEqual(record["flags"], ["worse_than_constant"])
        self.assertGreater(record["mean_score"], record["reference_constant"]["mean_score"])
        code, result = self.run_tool(baseline="constant", features="none", metric="accuracy", run_id="const-01")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["record"]["fold_scores"], result["record"]["reference_constant"]["fold_scores"])

    def test_regression_with_rmse_and_rmsle(self):
        self.write(sales_files())
        shared = {"train_path": "data/train.csv", "test_path": "data/test.csv", "folds_path": "data/folds.csv",
                  "id_column": "shop_id", "target_column": "sales", "task_type": "regression"}
        code, result = self.run_tool(**shared, metric="rmse", baseline="ridge", features="area,staff", run_id="r-01")
        self.assertEqual(code, 0, result)
        record = result["record"]
        self.assertLess(record["mean_score"], record["reference_constant"]["mean_score"] / 10)
        self.assertEqual(record["flags"], [])
        code, result = self.run_tool(**shared, metric="rmsle", baseline="group_mean", features="staff", run_id="r-02")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["record"]["model"]["target_transform"], "log1p")
        predictions = (self.root / result["record"]["outputs"]["test_predictions"]["path"]).read_text().splitlines()[1:]
        self.assertTrue(all(float(line.split(",")[1]) >= 0 for line in predictions))

    # Known-wrong cases -------------------------------------------------------------------------

    def test_leaked_target_is_flagged(self):
        self.write(renewal_files(leak=True))
        code, result = self.run_tool(features="tenure_months,renewal_flag", run_id="leak-01")
        self.assertEqual(code, 0, result)
        self.assertIn("suspiciously_perfect", result["record"]["flags"])

    def test_fold_file_must_cover_every_training_id(self):
        folds = renewal_files()["work/folds/folds.csv"].splitlines()
        (self.root / "work" / "folds" / "folds.csv").write_text("\n".join(folds[:-1]) + "\n", encoding="utf-8")
        self.refused("must cover exactly the training ids")

    def test_run_id_already_in_the_ledger_is_refused(self):
        self.assertEqual(self.run_tool()[0], 0)
        self.refused("already in the ledger")

    def test_ledger_that_is_not_utf8_is_refused(self):
        ledger = self.root / EXAMPLE_INPUT["ledger_path"]
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_bytes(b'{"run_id": "older-\xff-run"}\n')
        self.refused("is not UTF-8 text")
        self.assertEqual(ledger.read_bytes(), b'{"run_id": "older-\xff-run"}\n')

    def test_mismatched_inputs_are_refused(self):
        self.refused("does not fit a regression task", task_type="regression")
        self.refused("takes 0 to 0 feature columns", baseline="constant")
        self.refused("holds the target column", test_path="competition/data/train.csv")
        self.refused("must stay inside the workspace root", train_path="../train.csv")
        self.refused("is not a number", features="tenure_months,region")

    def test_numbers_too_large_to_compute_are_refused_as_json(self):
        files = sales_files()
        rows = files["data/train.csv"].splitlines()
        rows[3] = rows[3].rsplit(",", 1)[0] + ",1e200"
        files["data/train.csv"] = "\n".join(rows) + "\n"
        self.write(files)
        shared = {"train_path": "data/train.csv", "test_path": "data/test.csv", "folds_path": "data/folds.csv",
                  "id_column": "shop_id", "target_column": "sales", "task_type": "regression"}
        for baseline, features in (("ridge", "area,staff"), ("constant", "none")):
            self.refused("extreme values", **shared, metric="rmse", baseline=baseline, features=features,
                         run_id=f"big-{baseline}")
        self.assertFalse((self.root / "work" / "experiments").exists())

    def test_prediction_that_is_not_finite_is_refused(self):
        files = sales_files()
        files["data/test.csv"] = files["data/test.csv"].replace("Q00,25,", "Q00,1e308,", 1)
        self.assertIn("Q00,1e308,", files["data/test.csv"])
        self.write(files)
        self.refused("not a finite number", train_path="data/train.csv", test_path="data/test.csv",
                     folds_path="data/folds.csv", id_column="shop_id", target_column="sales", task_type="regression",
                     metric="rmse", baseline="ridge", features="area,staff", run_id="inf-01")
        self.assertFalse((self.root / "work" / "experiments").exists())

    def test_number_and_fold_text_that_is_not_plain_ascii_is_refused(self):
        # str.isdigit() accepts a superscript two and Arabic-Indic digits; float() accepts 7_1 and full-width digits.
        folds = renewal_files()["work/folds/folds.csv"]
        for fold in ("\u00b2", "\u0663"):
            self.write({"work/folds/folds.csv": folds.replace("C000,0", f"C000,{fold}", 1)})
            self.refused("fold file row 1: the fold is a whole number", check_only=True)
        shared = {"train_path": "data/train.csv", "test_path": "data/test.csv", "folds_path": "data/folds.csv",
                  "id_column": "shop_id", "target_column": "sales", "task_type": "regression", "metric": "rmse"}
        for old, new, baseline, features in (("S00,20,1,71", "S00,20,1,7_1", "constant", "none"),
                                             ("S01,29,6,155", "S01,2_9,6,155", "ridge", "area,staff"),
                                             ("S01,29,6,155", "S01,\uff12\uff19,6,155", "ridge", "area,staff")):
            files = sales_files()
            self.assertIn(old, files["data/train.csv"])
            files["data/train.csv"] = files["data/train.csv"].replace(old, new, 1)
            self.write(files)
            self.refused("is not a number written with plain ASCII digits", **shared, baseline=baseline,
                         features=features, run_id=f"spelled-{baseline}")
        self.assertFalse((self.root / "work" / "experiments").exists())

    def test_single_class_fold_is_refused_for_auc(self):
        rows = renewal_files()["competition/data/train.csv"].splitlines()[1:]
        folds = ["customer_id,fold"] + [f"{line.split(',')[0]},{line.split(',')[4]}" for line in rows]
        (self.root / "work" / "folds" / "folds.csv").write_text("\n".join(folds) + "\n", encoding="utf-8")
        self.refused("holds one class only")

    def test_metric_units(self):
        self.assertEqual(TOOL.auc([0, 1, 0, 1], [0.5, 0.5, 0.5, 0.5]), 0.5)
        self.assertEqual(TOOL.auc([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]), 1.0)
        self.assertAlmostEqual(TOOL.score("rmse", [1.0, 3.0], [2.0, 2.0]), 1.0)
        self.assertAlmostEqual(TOOL.score("accuracy", [1.0, 0.0], [0.7, 0.6]), 0.5)
        self.assertTrue(TOOL.worse("auc", 0.6, 0.7))
        self.assertTrue(TOOL.worse("rmse", 2.0, 1.0))

    # Contracts and entry files -----------------------------------------------------------------

    def test_examples_follow_the_contracts(self):
        contracts = PAYLOAD / "contracts"
        self.assertEqual(schema_errors(EXAMPLE_INPUT, read_json(contracts / "input.schema.json")), [])
        self.assertEqual(schema_errors(read_json(PAYLOAD / "examples" / "output.json"),
                                       read_json(contracts / "output.schema.json")), [])
        unsafe = {**EXAMPLE_INPUT, "features": "a,b;touch x", "run_id": "../x"}
        self.assertEqual(len(schema_errors(unsafe, read_json(contracts / "input.schema.json"))), 2)

    def test_entry_files_agree(self):
        agents = (PAYLOAD / "AGENTS.md").read_bytes()
        self.assertEqual((PAYLOAD / "GEMINI.md").read_bytes(), agents)
        self.assertEqual((PAYLOAD / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n")
        markers = set(re.findall(r"\{\{([A-Z][A-Z0-9_]*)\}\}", agents.decode("utf-8")))
        properties = read_json(PAYLOAD / "contracts" / "input.schema.json")["properties"]
        self.assertEqual(markers, {name.upper() for name in properties})
        task = read_json(PAYLOAD / "contracts" / "task.json")
        task_markers = set(re.findall(r"\{\{([A-Z][A-Z0-9_]*)\}\}", (PAYLOAD / "contracts" / "task.json").read_text()))
        self.assertEqual(task_markers, {"STEP_ID", "HARNESS_STYLE", "PROCESS_EFFECT", "BRIEF_STEP_ID", "FOLDS_STEP_ID"})
        # The step starts python3, and it consumes the brief's values and the fold file.
        self.assertEqual(task["effects"], ["reads_fs", "writes_fs", "{{PROCESS_EFFECT}}"])
        self.assertEqual(task["dependency_ids"], ["{{BRIEF_STEP_ID}}", "{{FOLDS_STEP_ID}}"])
        for named in re.findall(r"\.baltor/step/scripts/([a-z_]+\.py)", agents.decode("utf-8")):
            self.assertTrue((PAYLOAD / "scripts" / named).is_file(), named)


if __name__ == "__main__":
    unittest.main()
