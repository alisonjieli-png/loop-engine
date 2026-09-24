"""Tests for scripts/brief_tool.py. Effects: writes only inside temporary folders and starts python3 for the script.

Run from the payload root: python3 -I -B -m unittest discover -s tests -p 'test_*.py' -v
The competition pages below are synthetic and were written for these tests.
"""
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent.parent
SCRIPT = PAYLOAD / "scripts" / "brief_tool.py"
BRIEF = "work/brief/competition_brief.json"
ARGUMENTS = ["--pages", "competition/pages", "--data", "competition/data", "--brief", BRIEF]
PAGES = {
    "overview.md": ("# Synthetic Renewal Challenge\n\nThis practice competition uses synthetic data written for tests. "
                    "The goal is to estimate how likely each customer is to renew a yearly plan.\n\n## Key dates\n\n"
                    "Entries close on 2026-11-30 at 23:59 UTC.\n\n## Rules\n\n"
                    "A team can send at most 5 entries in one calendar day. Using data from outside this competition "
                    "is prohibited.\n"),
    "data.md": ("# Files and columns\n\nThree files come with this competition:\n\n- train.csv holds the labelled "
                "customers. Its column renewed is 1 when the customer renewed and 0 when the customer left.\n"
                "- test.csv holds the customers to score and has no renewed column.\n"
                "- sample_submission.csv shows the layout that every entry must follow.\n\n"
                "Every row is one customer, and the column customer_id names that customer. The column region gives "
                "the customer's sales area.\n"),
    "evaluation.md": ("# Scoring\n\nEntries are ranked by the area under the ROC curve (AUC) between the predicted "
                      "values and the true renewed labels. A higher AUC is better.\n\n## Entry file\n\n"
                      "An entry holds one row per customer_id in test.csv and two columns: customer_id, then renewed. "
                      "The renewed column holds a probability from 0 to 1 that the customer renews. Start the file "
                      "with a header row, as in this example:\n\n    customer_id,renewed\n    T001,0.5\n    T002,0.5\n"),
}
DATA = {
    "train.csv": ("customer_id,tenure_months,monthly_spend,renewed,region\nC001,12,20.5,1,north\n"
                  "C002,3,35.0,0,south\nC003,30,18.0,1,east\n"),
    "test.csv": "customer_id,tenure_months,monthly_spend,region\nT001,8,22.0,north\nT002,1,50.0,east\n",
    "sample_submission.csv": "customer_id,renewed\nT001,0.5\nT002,0.5\n",
}
# A second synthetic competition with two target columns, for the multi-target cases.
TWO_TARGET_PAGES = {
    "brief.md": ("# Synthetic Account Outcomes\n\nFor each account, predict both churned and upgraded; each is 1 or 0.\n"
                 "Rows are identified by account_id. The files are train.csv, test.csv and sample.csv.\n"),
}
TWO_TARGET_DATA = {
    "train.csv": "account_id,seats,churned,upgraded\nA1,3,1,0\nA2,9,0,1\nA3,4,0,0\nA4,7,1,1\n",
    "test.csv": "account_id,seats\nB1,5\nB2,2\n",
    "sample.csv": "account_id,churned,upgraded\nB1,0.5,0.5\nB2,0.5,0.5\n",
}


def load_tool():
    spec = importlib.util.spec_from_file_location("brief_tool_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TOOL = load_tool()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class BriefToolTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        for folder, files in (("competition/pages", PAGES), ("competition/data", DATA),
                              ("accounts/pages", TWO_TARGET_PAGES), ("accounts/data", TWO_TARGET_DATA)):
            (self.root / folder).mkdir(parents=True)
            for name, text in files.items():
                (self.root / folder / name).write_text(text, encoding="utf-8")
        self.example = read_json(PAYLOAD / "examples" / "output.json")

    def tearDown(self):
        self.directory.cleanup()

    def run_tool(self, command, *arguments):
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), command, *arguments,
                                   "--root", str(self.root)], capture_output=True, text=True, timeout=120)
        return finished.returncode, json.loads(finished.stdout)

    def check_brief(self, brief):
        (self.root / BRIEF).write_text(json.dumps(brief, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        return self.run_tool("check", *ARGUMENTS)

    def edited(self, fact, value=None, quote=None, page=None):
        brief = json.loads(json.dumps(self.example))
        entry = brief["facts"][fact]
        if value is not None:
            entry["value"] = value
        if quote is not None:
            entry["source"]["quote"] = quote
        if page is not None:
            entry["source"]["file"] = page
        return brief

    def findings(self, brief):
        code, result = self.check_brief(brief)
        self.assertEqual(code, 1, result)
        return " | ".join(result["findings"])

    def passing_warnings(self, brief):
        code, result = self.check_brief(brief)
        self.assertEqual((code, result["status"]), (0, "pass"), result)
        return " | ".join(result["warnings"])

    def two_target_brief(self, name, target_columns, target_type):
        arguments = ["--pages", "accounts/pages", "--data", "accounts/data", "--brief", f"work/{name}.json"]
        code, _result = self.run_tool("start", *arguments)
        self.assertEqual(code, 0)
        brief = read_json(self.root / "work" / f"{name}.json")
        targets = {"file": "brief.md", "quote": "For each account, predict both churned and upgraded; each is 1 or 0."}
        files = {"file": "brief.md", "quote": "The files are train.csv, test.csv and sample.csv."}
        filled = {"target_columns": (target_columns, targets), "target_type": (target_type, targets),
                  "prediction_columns": (["churned", "upgraded"], targets),
                  "id_column": ("account_id", {"file": "brief.md", "quote": "Rows are identified by account_id."}),
                  "train_file": ("train.csv", files), "test_file": ("test.csv", files),
                  "sample_submission_file": ("sample.csv", files)}
        for fact, (value, source) in filled.items():
            brief["facts"][fact] = {"value": value, "source": source}
        brief["unknowns"] = [{"fact": fact, "question": f"What does the page say about {fact}?"}
                             for fact, entry in brief["facts"].items() if entry["value"] is None]
        (self.root / "work" / f"{name}.json").write_text(json.dumps(brief), encoding="utf-8")
        return self.run_tool("check", *arguments)

    # Positive path ---------------------------------------------------------------------------

    def test_start_writes_an_empty_skeleton_with_headers(self):
        code, result = self.run_tool("start", *ARGUMENTS)
        self.assertEqual((code, result["status"]), (0, "started"), result)
        skeleton = read_json(self.root / BRIEF)
        self.assertEqual(skeleton["record_type"], "competition_brief/v2")
        self.assertEqual(skeleton["pages"], self.example["pages"])
        self.assertEqual(skeleton["data_files"], self.example["data_files"])
        self.assertTrue(all(fact == {"value": None, "source": None} for fact in skeleton["facts"].values()))
        train = next(entry for entry in result["data_files"] if entry["file"] == "train.csv")
        self.assertEqual(train["header"][-1], "region")

    def test_example_brief_passes_the_check(self):
        self.run_tool("start", *ARGUMENTS)
        (self.root / BRIEF).write_bytes((PAYLOAD / "examples" / "output.json").read_bytes())
        code, result = self.run_tool("check", *ARGUMENTS)
        self.assertEqual((code, result["status"], result["findings"], result["warnings"]), (0, "pass", [], []), result)
        self.assertEqual((result["facts_filled"], result["unknowns"]), (14, 1))

    def test_several_target_columns_are_recorded_and_checked(self):
        code, result = self.two_target_brief("both", ["churned", "upgraded"], "multilabel")
        self.assertEqual((code, result["status"]), (0, "pass"), result)
        code, result = self.two_target_brief("feature", ["churned", "seats"], "multilabel")
        self.assertEqual(code, 1, result)
        found = " | ".join(result["findings"])
        self.assertIn("target_columns: 'seats' is also a column of the test file", found)
        self.assertIn("target_type: multilabel target columns hold at most two values each", found)

    # Known-wrong cases -------------------------------------------------------------------------

    def test_untouched_skeleton_fails(self):
        self.run_tool("start", *ARGUMENTS)
        code, result = self.run_tool("check", *ARGUMENTS)
        self.assertEqual(code, 1)
        self.assertEqual(len(result["findings"]), 15)

    def test_last_column_taken_as_target_is_caught(self):
        self.run_tool("start", *ARGUMENTS)
        wrong = self.edited("target_columns", value=["region"],
                            quote="The column region gives the customer's sales area.")
        self.assertIn("also a column of the test file", self.findings(wrong))

    def test_paraphrased_quote_is_caught(self):
        self.run_tool("start", *ARGUMENTS)
        wrong = self.edited("metric", quote="Entries are ranked by AUC between the predictions and the true labels.")
        self.assertIn("metric: the quote is not found word for word", self.findings(wrong))

    def test_a_quote_that_is_not_found_points_to_the_page_sentence(self):
        self.run_tool("start", *ARGUMENTS)
        paraphrased = self.edited("metric", quote="Entries are ranked by AUC between the predictions and the true labels.")
        self.assertIn('metric: the quote is not found word for word in evaluation.md; the closest sentence there is '
                      '"Entries are ranked by the area under the ROC curve (AUC) between the predicted values and the '
                      'true renewed labels."', self.findings(paraphrased))
        moved = self.edited("deadline", page="data.md")
        self.assertIn("deadline: the quote is not found word for word in data.md, but it is in overview.md; set "
                      "source.file to overview.md", self.findings(moved))
        unrelated = self.edited("task", quote="Bring your own snacks to the kickoff meeting.")
        self.assertIn("task: the quote is not found word for word in overview.md; no sentence there is close, so "
                      "read the page again", self.findings(unrelated))

    def test_wrong_metric_and_direction_are_caught(self):
        self.run_tool("start", *ARGUMENTS)
        self.assertIn("does not name the metric rmse", self.findings(self.edited("metric", value="rmse")))
        self.assertIn("scored with maximize", self.findings(self.edited("metric_direction", value="minimize")))

    def test_prediction_columns_must_match_the_sample_submission(self):
        self.run_tool("start", *ARGUMENTS)
        wrong = self.edited("prediction_columns", value=["renewed", "probability"])
        self.assertIn("not columns of the sample submission", self.findings(wrong))

    def test_guessed_fact_and_misplaced_question_are_caught(self):
        self.run_tool("start", *ARGUMENTS)
        guessed = json.loads(json.dumps(self.example))
        guessed["unknowns"] = []
        self.assertIn("team_size_limit: no value and no question", self.findings(guessed))
        doubled = json.loads(json.dumps(self.example))
        doubled["unknowns"].append({"fact": "metric", "question": "Is the metric really AUC?"})
        self.assertIn("metric: has a value, so remove it from unknowns", self.findings(doubled))
        wrong_count = self.edited("daily_submission_limit", value=6)
        self.assertIn("does not state the number 6", self.findings(wrong_count))

    def test_choice_values_that_contradict_the_data_or_the_quote_are_caught(self):
        self.run_tool("start", *ARGUMENTS)
        self.assertIn("target_type: 'renewed' holds only the two values", self.findings(self.edited("target_type",
                                                                                                    value="regression")))
        self.assertIn("target_type: multiclass needs more than two", self.findings(self.edited("target_type",
                                                                                               value="multiclass")))
        self.assertIn("prediction_value_type: the sample submission holds '0.5' in 'renewed'",
                      self.findings(self.edited("prediction_value_type", value="class_label")))
        self.assertIn("external_data_allowed: the quote says 'prohibited'",
                      self.findings(self.edited("external_data_allowed", value="yes")))
        invented = self.edited("deadline", value="2027-01-15 12:00 UTC")
        self.assertIn("deadline: the quote does not contain 2027, 1, 15, 12, 0 from the value", self.findings(invented))
        partial = self.edited("deadline", quote="Entries close on")
        self.assertIn("deadline: the quote does not contain 2026, 11, 30, 23, 59 from the value", self.findings(partial))

    def test_deadline_numbers_may_use_month_names(self):
        self.assertEqual(TOOL.deadline_missing("2026-11-30 23:59 UTC", "Entries close on November 30, 2026 at 23:59 UTC."),
                         [])
        self.assertEqual(TOOL.deadline_missing("30 Nov 2026", "Entries close on 2026-11-30 at 23:59 UTC."), [])
        self.assertEqual(TOOL.deadline_missing("2026-12-30", "Entries close on 2026-11-30 at 23:59 UTC."), ["12"])

    def test_wording_that_may_not_fit_a_value_is_a_warning(self):
        self.run_tool("start", *ARGUMENTS)
        real_number = self.edited("prediction_value_type", value="real_number")
        self.assertIn("prediction_value_type: the quote mentions a probability", self.passing_warnings(real_number))
        unlimited = self.edited("external_data_allowed",
                                quote="This practice competition uses synthetic data written for tests.")
        self.assertIn("external_data_allowed: the quote does not say that outside data is limited",
                      self.passing_warnings(unlimited))

    def test_broken_json_edit_is_a_finding_to_fix(self):
        self.run_tool("start", *ARGUMENTS)
        brief_path = self.root / BRIEF
        text = json.dumps(self.example, indent=1, ensure_ascii=False) + "\n"
        broken = text.replace('"value": "binary",', '"value": "binary"', 1)
        self.assertNotEqual(broken, text)
        brief_path.write_text(broken, encoding="utf-8")
        code, result = self.run_tool("check", *ARGUMENTS)
        self.assertEqual((code, result["status"]), (1, "fail"), result)
        self.assertTrue(any("not strict JSON" in finding and "line" in finding for finding in result["findings"]),
                        result)
        self.assertEqual(brief_path.read_text(encoding="utf-8"), broken)
        brief_path.write_text(text, encoding="utf-8")
        self.assertEqual(self.run_tool("check", *ARGUMENTS)[0], 0)

    def test_changed_page_after_start_is_caught(self):
        self.run_tool("start", *ARGUMENTS)
        with open(self.root / "competition" / "pages" / "overview.md", "a", encoding="utf-8") as stream:
            stream.write("\nTeams may have at most 3 members.\n")
        (self.root / BRIEF).write_bytes((PAYLOAD / "examples" / "output.json").read_bytes())
        code, result = self.run_tool("check", *ARGUMENTS)
        self.assertEqual(code, 1)
        self.assertIn("no longer matches the files", " ".join(result["findings"]))

    def test_start_refuses_overwrite_escape_and_missing_pages(self):
        self.assertEqual(self.run_tool("start", *ARGUMENTS)[0], 0)
        code, result = self.run_tool("start", *ARGUMENTS)
        self.assertEqual(code, 2)
        self.assertIn("never overwrites", result["reason"])
        code, _result = self.run_tool("start", "--pages", "../pages", "--data", "competition/data", "--brief", "x.json")
        self.assertEqual(code, 2)
        (self.root / "empty").mkdir()
        code, result = self.run_tool("start", "--pages", "empty", "--data", "competition/data", "--brief", "y.json")
        self.assertEqual(code, 2)
        self.assertIn("no .md or .txt page", result["reason"])

    def test_quote_matching_ignores_only_formatting(self):
        self.assertEqual(TOOL.normalize("the  `renewed` column"), "the renewed column")
        self.assertEqual(TOOL.normalize("“A” and ‘b’"), "\"A\" and 'b'")
        self.assertTrue(TOOL.mentions_count("up to five entries", 5))
        self.assertFalse(TOOL.mentions_count("up to 15 entries", 5))

    # Contracts and entry files -----------------------------------------------------------------

    def test_examples_follow_the_contracts(self):
        contracts = PAYLOAD / "contracts"
        self.assertEqual(TOOL.schema_errors(read_json(PAYLOAD / "examples" / "input.json"),
                                            read_json(contracts / "input.schema.json")), [])
        self.assertEqual(TOOL.schema_errors(self.example, read_json(contracts / "output.schema.json")), [])
        wrong = self.edited("target_type", value="yes")
        self.assertTrue(TOOL.schema_errors(wrong, read_json(contracts / "output.schema.json")))
        single = self.edited("target_columns", value="renewed")
        self.assertTrue(TOOL.schema_errors(single, read_json(contracts / "output.schema.json")))

    def test_entry_files_agree(self):
        agents = (PAYLOAD / "AGENTS.md").read_bytes()
        self.assertEqual((PAYLOAD / "GEMINI.md").read_bytes(), agents)
        self.assertEqual((PAYLOAD / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n")
        markers = set(re.findall(r"\{\{([A-Z][A-Z0-9_]*)\}\}", agents.decode("utf-8")))
        properties = read_json(PAYLOAD / "contracts" / "input.schema.json")["properties"]
        self.assertEqual(markers, {name.upper() for name in properties})
        task = read_json(PAYLOAD / "contracts" / "task.json")
        task_markers = set(re.findall(r"\{\{([A-Z][A-Z0-9_]*)\}\}", (PAYLOAD / "contracts" / "task.json").read_text()))
        self.assertEqual(task_markers, {"STEP_ID", "HARNESS_STYLE", "PROCESS_EFFECT"})
        # Both commands start python3, so the typed record names the process effect through its marker.
        self.assertEqual(task["effects"], ["reads_fs", "writes_fs", "{{PROCESS_EFFECT}}"])
        self.assertEqual(task["output_contract_refs"], ["competition_brief/v2"])
        for named in re.findall(r"\.baltor/step/scripts/([a-z_]+\.py)", agents.decode("utf-8")):
            self.assertTrue((PAYLOAD / "scripts" / named).is_file(), named)


if __name__ == "__main__":
    unittest.main()
