"""Tests for scripts/plan_tool.py. Effects: writes only inside temporary folders and starts python3 for the script.

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
SCRIPT = PAYLOAD / "scripts" / "plan_tool.py"
TABLE_PATH = "data/raw/customers.csv"
OUT_DIR = "work/cleaning-plan"
PLAN = OUT_DIR + "/cleaning_plan.json"
TABLE = ('customer_id,signup_date,country,plan,monthly_spend,notes\n'
         'C001,03/04/2025,NL,Basic,"1.234,50",\n'
         'C002,13/04/2025,DE,basic ,"99,00",n/a\n'
         'C003,2025-04-20,NA,Premium,"1.050,00",call back\n'
         'C004,21/04/2025,FR,PREMIUM,"12,5",\n'
         'C005,N/A,DE, Basic,"7,25",\n'
         'C006,30/04/2025,NL,Premium,"8,00",  vip  \n'
         'C007,02/05/2025,BE,basic,"15,75",\n'
         'C008,11/05/2025,DE,Premium,,\n')


def load_tool():
    spec = importlib.util.spec_from_file_location("plan_tool_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TOOL = load_tool()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class PlanToolTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        (self.root / "data" / "raw").mkdir(parents=True)
        (self.root / TABLE_PATH).write_text(TABLE, encoding="utf-8")
        self.example = read_json(PAYLOAD / "examples" / "output.json")

    def tearDown(self):
        self.directory.cleanup()

    def run_tool(self, *arguments):
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments, "--root", str(self.root)],
                                  capture_output=True, text=True, timeout=120)
        return finished.returncode, json.loads(finished.stdout)

    def draft(self):
        return self.run_tool("draft", "--table", TABLE_PATH, "--delimiter", "comma", "--max-rows", "50000",
                             "--out-dir", OUT_DIR)

    def check(self, *extra):
        return self.run_tool("check", "--table", TABLE_PATH, "--plan", PLAN, *extra)

    def write_plan(self, plan):
        (self.root / PLAN).write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    def rule(self, plan, rule_id):
        return next(rule for rule in plan["rules"] if rule["rule_id"] == rule_id)

    def draft_table(self, name, text):
        """Draft a plan for another small table and return the draft plan and its path."""
        (self.root / "data" / f"{name}.csv").write_text(text, encoding="utf-8")
        code, result = self.run_tool("draft", "--table", f"data/{name}.csv", "--delimiter", "comma", "--max-rows",
                                     "100", "--out-dir", f"work/{name}")
        self.assertEqual(code, 0, result)
        plan_path = self.root / "work" / name / "cleaning_plan.json"
        return read_json(plan_path), plan_path

    def check_table(self, name, plan, plan_path):
        plan_path.write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        return self.run_tool("check", "--table", f"data/{name}.csv", "--plan", f"work/{name}/cleaning_plan.json",
                             "--write-evidence")

    # Positive path ---------------------------------------------------------------------------

    def test_draft_suggests_the_rules_of_the_example(self):
        code, result = self.draft()
        self.assertEqual(code, 0, result)
        draft = read_json(self.root / PLAN)
        self.assertEqual(draft["table"], self.example["table"])
        self.assertEqual(draft["profile"], self.example["profile"])
        self.assertEqual([(r["rule_id"], r["column"], r["operation"]) for r in draft["rules"]],
                         [(r["rule_id"], r["column"], r["operation"]) for r in self.example["rules"]])
        self.assertTrue(all(r["status"] == "proposed" and r["reason"] == "" for r in draft["rules"]))
        self.assertEqual(self.rule(draft, "r2")["parameters"]["formats"], ["%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"])
        self.assertEqual(self.rule(draft, "r2")["evidence"]["would_hold"], 3)
        self.assertEqual(len(draft["questions"]), 1)

    def test_example_plan_passes_the_read_only_check(self):
        self.draft()
        (self.root / PLAN).write_bytes((PAYLOAD / "examples" / "output.json").read_bytes())
        code, result = self.check()
        self.assertEqual((code, result["status"], result["findings"]), (0, "pass", []), result)
        self.assertEqual(result["rules"], {"proposed": 7, "dropped": 1})

    def test_table_bytes_never_change(self):
        before = hashlib.sha256((self.root / TABLE_PATH).read_bytes()).hexdigest()
        self.draft()
        self.write_plan(self.example)
        self.check("--write-evidence")
        self.assertEqual(hashlib.sha256((self.root / TABLE_PATH).read_bytes()).hexdigest(), before)

    def test_semicolon_table_with_byte_order_mark(self):
        (self.root / "data" / "semi.csv").write_bytes(b"\xef\xbb\xbfcode;amount\nA; 1,5\nB;2,25\n")
        code, result = self.run_tool("draft", "--table", "data/semi.csv", "--delimiter", "semicolon", "--max-rows", "10",
                                     "--out-dir", "work/semi")
        self.assertEqual(code, 0, result)
        plan = read_json(self.root / "work" / "semi" / "cleaning_plan.json")
        self.assertEqual(plan["table"]["columns"], ["code", "amount"])
        parse = [rule for rule in plan["rules"] if rule["operation"] == "parse_number"]
        self.assertEqual(parse[0]["parameters"], {"decimal_separator": ",", "thousands_separator": "."})

    # Known-wrong cases -------------------------------------------------------------------------

    def test_untouched_draft_fails_until_reasons_are_written(self):
        self.draft()
        code, result = self.check()
        self.assertEqual(code, 1)
        self.assertTrue(any("write a reason" in finding for finding in result["findings"]))

    def test_hand_typed_evidence_is_caught_and_recounted(self):
        self.draft()
        wrong = json.loads(json.dumps(self.example))
        self.rule(wrong, "r6")["evidence"]["would_change"] = 5
        self.write_plan(wrong)
        code, result = self.check()
        self.assertEqual(code, 1)
        self.assertTrue(any("r6: evidence differs" in finding for finding in result["findings"]))
        code, result = self.check("--write-evidence")
        self.assertEqual((code, result["status"]), (0, "pass"), result)
        self.assertEqual(self.rule(read_json(self.root / PLAN), "r6")["evidence"]["would_change"], 7)

    def test_plan_step_cannot_approve_a_rule(self):
        self.draft()
        wrong = json.loads(json.dumps(self.example))
        self.rule(wrong, "r4")["status"] = "approved"
        self.write_plan(wrong)
        code, result = self.check()
        self.assertEqual(code, 1)
        self.assertTrue(any("approval belongs to a reviewer" in finding for finding in result["findings"]))

    def test_deleting_a_suggestion_is_caught(self):
        self.draft()
        wrong = json.loads(json.dumps(self.example))
        wrong["rules"] = [rule for rule in wrong["rules"] if rule["rule_id"] != "r3"]
        self.write_plan(wrong)
        code, result = self.check()
        self.assertEqual(code, 1)
        self.assertTrue(any("missing_tokens_to_empty for column 'country'" in finding for finding in result["findings"]))

    def test_parse_rule_before_missing_tokens_is_caught(self):
        self.draft()
        wrong = json.loads(json.dumps(self.example))
        wrong["rules"][0], wrong["rules"][1] = wrong["rules"][1], wrong["rules"][0]
        self.write_plan(wrong)
        code, result = self.check("--write-evidence")
        self.assertEqual(code, 1)
        self.assertTrue(any("order its rules" in finding for finding in result["findings"]))

    def test_zero_padded_codes_get_a_question_instead_of_a_number_rule(self):
        (self.root / "data" / "shops.csv").write_text("shop,postal_code,visits\nA,01234,5\nB,00501,7\nC,12345,9\n"
                                                      "D,02110,3\n", encoding="utf-8")
        code, result = self.run_tool("draft", "--table", "data/shops.csv", "--delimiter", "comma", "--max-rows", "10",
                                     "--out-dir", "work/shops")
        self.assertEqual(code, 0, result)
        plan_path = self.root / "work" / "shops" / "cleaning_plan.json"
        plan = read_json(plan_path)
        self.assertEqual(plan["rules"], [])
        self.assertEqual(len(plan["questions"]), 1, plan["questions"])
        self.assertIn("'postal_code': 3 values such as '01234' start with 0", plan["questions"][0])
        plan["rules"].append({"rule_id": "r1", "column": "postal_code", "operation": "parse_number",
                              "parameters": {"decimal_separator": ".", "thousands_separator": ""},
                              "status": "proposed", "reason": "The export stores these codes as plain counts.",
                              "evidence": {}})
        plan_path.write_text(json.dumps(plan, indent=1) + "\n", encoding="utf-8")
        code, result = self.run_tool("check", "--table", "data/shops.csv", "--plan", "work/shops/cleaning_plan.json",
                                     "--write-evidence")
        self.assertEqual((code, result["status"]), (0, "pass"), result)
        self.assertTrue(any(warning.startswith("rule r1 would drop a leading 0 from 3 of 4 profiled cells")
                            for warning in result["warnings"]), result)

    def test_dates_that_read_two_ways_get_a_rule_and_a_question(self):
        mostly_iso = "id,visit\n" + "".join(f"{day},2024-03-{day:02d}\n" for day in range(1, 19)) \
            + "19,03/04/2024\n20,05/06/2024\n"
        plan, plan_path = self.draft_table("visits", mostly_iso)
        self.assertEqual([(rule["operation"], rule["parameters"]) for rule in plan["rules"]],
                         [("parse_date", {"formats": ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]})])
        self.assertEqual((plan["rules"][0]["evidence"]["would_change"], plan["rules"][0]["evidence"]["would_hold"]),
                         (0, 2))
        self.assertEqual(len(plan["questions"]), 1, plan["questions"])
        self.assertIn("2 values such as '03/04/2024' read as different dates", plan["questions"][0])
        code, result = self.check_table("visits", plan, plan_path)
        self.assertEqual(code, 1, result)
        plan["rules"][0]["reason"] = "The visit column holds dates, and two of them need a person to pick the order."
        code, result = self.check_table("visits", plan, plan_path)
        self.assertEqual((code, result["status"]), (0, "pass"), result)
        only_ambiguous, _path = self.draft_table("orders", "id,ordered\n1,01/02/2024\n2,03/04/2024\n3,05/06/2024\n"
                                                           "4,07/08/2024\n")
        self.assertEqual([rule["operation"] for rule in only_ambiguous["rules"]], ["parse_date"])
        self.assertEqual(only_ambiguous["rules"][0]["evidence"]["would_hold"], 4)
        self.assertEqual(len(only_ambiguous["questions"]), 1, only_ambiguous["questions"])

    def test_evidence_counts_what_the_application_step_would_change(self):
        # The first date is trimmed and then held, so the application step leaves that cell unchanged.
        plan, _path = self.draft_table("chain", "id,d,city\n1,  03/04/2025 ,Paris\n2, 13/04/2025,paris\n"
                                                "3,14/04/2025,PARIS\n4,15/04/2025,Lyon\n5,16/04/2025,lyon\n")
        counted = {(rule["column"], rule["operation"]): (rule["evidence"]["would_change"],
                                                         rule["evidence"]["would_hold"]) for rule in plan["rules"]}
        self.assertEqual(counted[("d", "trim_whitespace")], (1, 0))
        self.assertEqual(counted[("d", "parse_date")], (4, 1))
        self.assertEqual(counted[("city", "map_values")], (3, 0))
        trim = next(rule for rule in plan["rules"] if rule["operation"] == "trim_whitespace")
        self.assertEqual(trim["evidence"]["change_examples"], [[" 13/04/2025", "13/04/2025"]])

    def test_tied_spellings_prefer_the_usual_written_form(self):
        plan, _path = self.draft_table("cities", "id,city\n1,Paris\n2,paris\n3,PARIS\n4,Lyon\n5,lyon\n")
        mapping = plan["rules"][0]["parameters"]["mapping"]
        self.assertEqual(mapping, {"PARIS": "Paris", "paris": "Paris", "lyon": "Lyon"})

    def test_mapping_target_may_only_change_to_another_spelling(self):
        plan, plan_path = self.draft_table("cities", "id,city\n1,Paris\n2,paris\n3,PARIS\n4,Lyon\n5,lyon\n")
        plan["rules"][0]["reason"] = "City names are labels, so letter case carries no meaning here."
        plan["rules"][0]["parameters"]["mapping"] = {"Paris": "PARIS", "paris": "PARIS", "lyon": "Lyon"}
        code, result = self.check_table("cities", plan, plan_path)
        self.assertEqual((code, result["status"]), (0, "pass"), result)
        plan["rules"][0]["parameters"]["mapping"] = {"paris": "London", "lyon": "Lyon"}
        code, result = self.check_table("cities", plan, plan_path)
        self.assertEqual(code, 1, result)
        self.assertTrue(any("only in letter case" in finding for finding in result["findings"]), result)

    def test_broken_json_edit_is_a_finding_to_fix(self):
        self.draft()
        plan_path = self.root / PLAN
        text = plan_path.read_text(encoding="utf-8")
        broken = text.replace('"status": "proposed",', '"status": "proposed"', 1)
        self.assertNotEqual(broken, text)
        plan_path.write_text(broken, encoding="utf-8")
        code, result = self.check("--write-evidence")
        self.assertEqual((code, result["status"]), (1, "fail"), result)
        self.assertTrue(any("not strict JSON" in finding and "line" in finding for finding in result["findings"]),
                        result)
        self.assertEqual(plan_path.read_text(encoding="utf-8"), broken)
        plan_path.write_text(text, encoding="utf-8")
        code, result = self.check()
        self.assertEqual(code, 1, result)
        self.assertFalse(any("not strict JSON" in finding for finding in result["findings"]), result)

    def test_profile_of_another_version_is_refused(self):
        self.draft()
        profile_path = self.root / OUT_DIR / "table_profile.json"
        profile = read_json(profile_path)
        self.assertEqual(profile["record_type"], "table_profile/v2")
        profile["record_type"] = "table_profile/v1"
        profile_path.write_text(json.dumps(profile, indent=1) + "\n", encoding="utf-8")
        plan = json.loads(json.dumps(self.example))
        plan["profile"]["sha256"] = hashlib.sha256(profile_path.read_bytes()).hexdigest()
        self.write_plan(plan)
        code, result = self.check()
        self.assertEqual((code, result["status"]), (2, "refused"), result)
        self.assertIn("another version of this step wrote it", result["reason"])

    def test_table_changed_after_the_draft_is_refused(self):
        self.draft()
        self.write_plan(self.example)
        with open(self.root / TABLE_PATH, "a", encoding="utf-8") as stream:
            stream.write("C009,01/06/2025,NL,Basic,\"3,00\",\n")
        code, result = self.check()
        self.assertEqual((code, result["status"]), (2, "refused"))
        self.assertIn("changed after the draft", result["reason"])

    def test_draft_refuses_ragged_rows_escapes_and_overwrites(self):
        (self.root / "data" / "ragged.csv").write_text("a,b\n1,2\n3\n", encoding="utf-8")
        code, result = self.run_tool("draft", "--table", "data/ragged.csv", "--delimiter", "comma", "--max-rows", "10",
                                     "--out-dir", "work/ragged")
        self.assertEqual(code, 2)
        self.assertIn("data row 2 has 1 fields", result["reason"])
        code, result = self.run_tool("draft", "--table", "../outside.csv", "--delimiter", "comma", "--max-rows", "10",
                                     "--out-dir", "work/x")
        self.assertEqual(code, 2)
        self.assertEqual(self.draft()[0], 0)
        code, result = self.draft()
        self.assertEqual(code, 2)
        self.assertIn("never overwrites", result["reason"])

    # Operations --------------------------------------------------------------------------------

    def test_operations_hold_what_they_cannot_read(self):
        self.assertEqual(TOOL.parse_number("1.234,50", ",", "."), "1234.50")
        self.assertEqual(TOOL.parse_number("-0,5", ",", ""), "-0.5")
        self.assertEqual(TOOL.parse_number("1\u00a0234,5", ",", " "), "1234.5")
        self.assertEqual(TOOL.parse_number("12\u202f345", ".", " "), "12345")
        self.assertEqual(TOOL.parse_number("0012", ".", ""), "12")
        for text, decimal, thousands in (("12,34", ".", ","), ("1.5", ",", "."), ("1e3", ".", ""), ("inf", ".", "")):
            with self.assertRaises(TOOL.Hold):
                TOOL.parse_number(text, decimal, thousands)
        self.assertEqual(TOOL.parse_date("13/04/2025", ["%d/%m/%Y", "%m/%d/%Y"]), "2025-04-13")
        with self.assertRaises(TOOL.Hold) as held:
            TOOL.parse_date("03/04/2025", ["%d/%m/%Y", "%m/%d/%Y"])
        self.assertEqual(held.exception.reason, "formats_disagree")
        self.assertTrue(TOOL.date_format_problem("%H:%M"))
        self.assertEqual(TOOL.date_format_problem("%d %b %Y"), "")

    # Contracts and entry files -----------------------------------------------------------------

    def test_examples_follow_the_contracts(self):
        input_schema = read_json(PAYLOAD / "contracts" / "input.schema.json")
        output_schema = read_json(PAYLOAD / "contracts" / "output.schema.json")
        self.assertEqual(TOOL.schema_errors(read_json(PAYLOAD / "examples" / "input.json"), input_schema), [])
        self.assertEqual(TOOL.schema_errors(self.example, output_schema), [])
        unsafe = {"table_path": "data/x.csv; touch y", "output_dir": "../out", "max_rows": 10, "delimiter": "comma"}
        self.assertEqual(len(TOOL.schema_errors(unsafe, input_schema)), 2)
        approved = json.loads(json.dumps(self.example))
        approved["rules"][0]["status"] = "approved"
        self.assertTrue(TOOL.schema_errors(approved, output_schema))

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
        # The first action starts python3, so the typed record names the process effect through its marker.
        self.assertEqual(task["effects"], ["reads_fs", "writes_fs", "{{PROCESS_EFFECT}}"])
        self.assertEqual(task["dependency_ids"], [])
        for named in re.findall(r"\.baltor/step/scripts/([a-z_]+\.py)", agents.decode("utf-8")):
            self.assertTrue((PAYLOAD / "scripts" / named).is_file(), named)


if __name__ == "__main__":
    unittest.main()
