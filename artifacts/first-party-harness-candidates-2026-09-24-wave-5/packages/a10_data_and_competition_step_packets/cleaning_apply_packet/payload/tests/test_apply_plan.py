"""Tests for scripts/apply_plan.py. Effects: writes only inside temporary folders and starts python3 for the script.

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
SCRIPT = PAYLOAD / "scripts" / "apply_plan.py"
TABLE_PATH = "data/raw/customers.csv"
PLAN_PATH = "work/cleaning-plan/cleaning_plan.json"
OUT_DIR = "work/cleaned"
TABLE = ('customer_id,signup_date,country,plan,monthly_spend,notes\n'
         'C001,03/04/2025,NL,Basic,"1.234,50",\n'
         'C002,13/04/2025,DE,basic ,"99,00",n/a\n'
         'C003,2025-04-20,NA,Premium,"1.050,00",call back\n'
         'C004,21/04/2025,FR,PREMIUM,"12,5",\n'
         'C005,N/A,DE, Basic,"7,25",\n'
         'C006,30/04/2025,NL,Premium,"8,00",  vip  \n'
         'C007,02/05/2025,BE,basic,"15,75",\n'
         'C008,11/05/2025,DE,Premium,,\n')


# A cell that is trimmed and then held: the plan step's evidence counts no trim change for it.
CHAIN_TABLE = ("id,d,city\n1,  03/04/2025 ,Paris\n2, 13/04/2025,paris\n3,14/04/2025,PARIS\n4,15/04/2025,Lyon\n"
               "5,16/04/2025,lyon\n")
# Evidence (would_change, would_hold) that the cleaning plan step records for these rules on CHAIN_TABLE.
CHAIN_EVIDENCE = {"r1": (1, 0), "r2": (4, 1), "r3": (3, 0)}


def load_tool():
    spec = importlib.util.spec_from_file_location("apply_plan_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TOOL = load_tool()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_lines(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]


class ApplyPlanTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        (self.root / "data" / "raw").mkdir(parents=True)
        (self.root / "work" / "cleaning-plan").mkdir(parents=True)
        (self.root / TABLE_PATH).write_text(TABLE, encoding="utf-8")
        self.plan = read_json(PAYLOAD / "examples" / "approved_plan.json")
        (self.root / PLAN_PATH).write_bytes((PAYLOAD / "examples" / "approved_plan.json").read_bytes())

    def tearDown(self):
        self.directory.cleanup()

    def apply(self, *extra):
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--table", TABLE_PATH, "--plan", PLAN_PATH,
                                   "--out-dir", OUT_DIR, *extra, "--root", str(self.root)],
                                  capture_output=True, text=True, timeout=120)
        return finished.returncode, json.loads(finished.stdout)

    def write_plan(self, plan):
        (self.root / PLAN_PATH).write_text(json.dumps(plan, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    def rule(self, plan, rule_id):
        return next(rule for rule in plan["rules"] if rule["rule_id"] == rule_id)

    # Positive path ---------------------------------------------------------------------------

    def test_check_only_writes_nothing(self):
        code, result = self.apply("--check-only")
        self.assertEqual((code, result["status"]), (0, "ready"), result)
        self.assertEqual(result["will_apply"], ["r1", "r2", "r4", "r5", "r6", "r7"])
        self.assertEqual(result["not_applied"], {"r3": "dropped", "r8": "rejected"})
        self.assertFalse((self.root / OUT_DIR).exists())

    def test_summary_equals_the_example(self):
        code, result = self.apply()
        self.assertEqual(code, 0, result)
        self.assertEqual(result, read_json(PAYLOAD / "examples" / "output.json"))
        self.assertEqual(read_json(self.root / OUT_DIR / "apply_summary.json"), result)

    def test_change_log_and_hold_list_name_each_cell(self):
        self.apply()
        changes = read_lines(self.root / OUT_DIR / "changes.jsonl")
        holds = read_lines(self.root / OUT_DIR / "holds.jsonl")
        self.assertIn({"row": 2, "column": "plan", "before": "basic ", "after": "Basic", "rules": ["r4", "r5"]}, changes)
        self.assertIn({"row": 5, "column": "signup_date", "before": "N/A", "after": "", "rules": ["r1"]}, changes)
        self.assertEqual([(hold["row"], hold["value"], hold["reason"]) for hold in holds],
                         [(1, "03/04/2025", "formats_disagree"), (7, "02/05/2025", "formats_disagree"),
                          (8, "11/05/2025", "formats_disagree")])
        copy = (self.root / OUT_DIR / "cleaned.csv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(copy[1], "C001,03/04/2025,NL,Basic,1234.50,")
        self.assertEqual(copy[3], "C003,2025-04-20,NA,Premium,1050.00,call back")
        self.assertEqual(copy[2].split(",")[-1], "n/a")

    def test_counts_equal_the_plan_evidence_when_every_proposed_rule_is_approved(self):
        plan = json.loads(json.dumps(self.plan))
        self.rule(plan, "r8")["status"] = "approved"
        self.write_plan(plan)
        code, result = self.apply()
        self.assertEqual(code, 0, result)
        applied = result["plan"]["applied_rules"]
        self.assertEqual(applied, ["r1", "r2", "r4", "r5", "r6", "r7", "r8"])
        self.assertEqual({rule_id: (counts["changed"], counts["held"]) for rule_id, counts in result["rule_counts"].items()},
                         {rule_id: (self.rule(plan, rule_id)["evidence"]["would_change"],
                                    self.rule(plan, rule_id)["evidence"]["would_hold"]) for rule_id in applied})

    def test_a_trimmed_then_held_cell_counts_only_as_held(self):
        (self.root / "data" / "chain.csv").write_text(CHAIN_TABLE, encoding="utf-8")
        reviewed = {"status": "approved", "reviewed_by": "data-steward-01", "reason": "Synthetic chain case.",
                    "evidence": {}}
        plan = {"record_type": "cleaning_plan/v1",
                "table": {"path": "data/chain.csv", "sha256": hashlib.sha256(CHAIN_TABLE.encode("utf-8")).hexdigest(),
                          "delimiter": "comma", "columns": ["id", "d", "city"], "rows_profiled": 5, "row_cap": 100,
                          "row_cap_reached": False},
                "profile": {"path": "work/chain-plan/table_profile.json", "sha256": "0" * 64},
                "rules": [{"rule_id": "r1", "column": "d", "operation": "trim_whitespace", "parameters": {}, **reviewed},
                          {"rule_id": "r2", "column": "d", "operation": "parse_date",
                           "parameters": {"formats": ["%d/%m/%Y", "%m/%d/%Y"]}, **reviewed},
                          {"rule_id": "r3", "column": "city", "operation": "map_values",
                           "parameters": {"mapping": {"PARIS": "Paris", "paris": "Paris", "lyon": "Lyon"},
                                          "unmapped": "keep"}, **reviewed}],
                "questions": []}
        (self.root / "work" / "chain-plan").mkdir(parents=True)
        (self.root / "work" / "chain-plan" / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--table", "data/chain.csv", "--plan",
                                   "work/chain-plan/plan.json", "--out-dir", "work/chain-out", "--root", str(self.root)],
                                  capture_output=True, text=True, timeout=120)
        result = json.loads(finished.stdout)
        self.assertEqual(finished.returncode, 0, result)
        self.assertEqual({rule_id: (counts["changed"], counts["held"]) for rule_id, counts in result["rule_counts"].items()},
                         CHAIN_EVIDENCE)
        holds = read_lines(self.root / "work" / "chain-out" / "holds.jsonl")
        self.assertEqual(holds, [{"row": 1, "column": "d", "value": "  03/04/2025 ", "rule": "r2",
                                  "reason": "formats_disagree"}])

    def test_source_bytes_never_change(self):
        before = hashlib.sha256((self.root / TABLE_PATH).read_bytes()).hexdigest()
        self.apply()
        self.assertEqual(hashlib.sha256((self.root / TABLE_PATH).read_bytes()).hexdigest(), before)

    # Known-wrong cases -------------------------------------------------------------------------

    def test_unfinished_review_is_refused(self):
        wrong = json.loads(json.dumps(self.plan))
        self.rule(wrong, "r8")["status"] = "proposed"
        self.write_plan(wrong)
        code, result = self.apply("--check-only")
        self.assertEqual(code, 2)
        self.assertIn("still proposed", result["reason"])

    def test_approval_without_reviewer_is_refused(self):
        wrong = json.loads(json.dumps(self.plan))
        del self.rule(wrong, "r6")["reviewed_by"]
        self.write_plan(wrong)
        code, result = self.apply("--check-only")
        self.assertEqual(code, 2)
        self.assertIn("names no reviewer", result["reason"])

    def test_plan_without_approved_rules_is_refused(self):
        wrong = json.loads(json.dumps(self.plan))
        for rule in wrong["rules"]:
            if rule["status"] == "approved":
                rule["status"] = "rejected"
        self.write_plan(wrong)
        code, result = self.apply()
        self.assertEqual(code, 2)
        self.assertIn("no rule is approved", result["reason"])

    def test_table_changed_after_planning_is_refused(self):
        with open(self.root / TABLE_PATH, "a", encoding="utf-8") as stream:
            stream.write("C009,01/06/2025,NL,Basic,\"3,00\",\n")
        code, result = self.apply()
        self.assertEqual(code, 2)
        self.assertIn("changed after the plan was made", result["reason"])
        self.assertFalse((self.root / OUT_DIR).exists())

    def test_existing_output_is_never_overwritten(self):
        self.assertEqual(self.apply()[0], 0)
        code, result = self.apply()
        self.assertEqual(code, 2)
        self.assertIn("never overwrites", result["reason"])

    def test_paths_outside_the_workspace_are_refused(self):
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--table", "../customers.csv", "--plan",
                                   PLAN_PATH, "--out-dir", OUT_DIR, "--root", str(self.root)],
                                  capture_output=True, text=True, timeout=60)
        self.assertEqual(finished.returncode, 2)

    def test_self_check_catches_an_unlogged_edit(self):
        self.apply()
        copy_path = self.root / OUT_DIR / "cleaned.csv"
        header = TABLE.splitlines()[0].split(",")
        good = TOOL.self_check(TABLE, copy_path, self.root / OUT_DIR / "changes.jsonl", ",", header)
        self.assertTrue(all(good.values()), good)
        tampered = self.root / "tampered.csv"
        tampered.write_text(copy_path.read_text(encoding="utf-8").replace("C003,2025-04-20,NA", "C003,2025-04-20,"),
                            encoding="utf-8")
        result = TOOL.self_check(TABLE, tampered, self.root / OUT_DIR / "changes.jsonl", ",", header)
        self.assertFalse(result["every_difference_logged"])
        wrong_log = self.root / "wrong.jsonl"
        wrong_log.write_text((self.root / OUT_DIR / "changes.jsonl").read_text().replace('"after": "99.00"',
                                                                                         '"after": "99"'))
        self.assertFalse(TOOL.self_check(TABLE, copy_path, wrong_log, ",", header)["log_matches_cells"])

    def test_operations_match_the_plan_step(self):
        self.assertEqual(TOOL.parse_number("1\u00a0234,5", ",", " "), "1234.5")
        self.assertEqual(TOOL.parse_number("12\u202f345", ".", " "), "12345")
        with self.assertRaises(TOOL.Hold):
            TOOL.parse_number("12,34", ".", ",")
        with self.assertRaises(TOOL.Hold) as held:
            TOOL.parse_date("03/04/2025", ["%d/%m/%Y", "%m/%d/%Y"])
        self.assertEqual(held.exception.reason, "formats_disagree")

    # Contracts and entry files -----------------------------------------------------------------

    def test_examples_follow_the_contracts(self):
        contracts = PAYLOAD / "contracts"
        self.assertEqual(TOOL.schema_errors(read_json(PAYLOAD / "examples" / "input.json"),
                                            read_json(contracts / "input.schema.json")), [])
        self.assertEqual(TOOL.schema_errors(self.plan, read_json(contracts / "plan.schema.json")), [])
        self.assertEqual(TOOL.schema_errors(read_json(PAYLOAD / "examples" / "output.json"),
                                            read_json(contracts / "output.schema.json")), [])
        failed = read_json(PAYLOAD / "examples" / "output.json")
        failed["checks"]["source_unchanged"] = False
        self.assertTrue(TOOL.schema_errors(failed, read_json(contracts / "output.schema.json")))

    def test_entry_files_agree(self):
        agents = (PAYLOAD / "AGENTS.md").read_bytes()
        self.assertEqual((PAYLOAD / "GEMINI.md").read_bytes(), agents)
        self.assertEqual((PAYLOAD / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n")
        markers = set(re.findall(r"\{\{([A-Z][A-Z0-9_]*)\}\}", agents.decode("utf-8")))
        properties = read_json(PAYLOAD / "contracts" / "input.schema.json")["properties"]
        self.assertEqual(markers, {name.upper() for name in properties})
        task = read_json(PAYLOAD / "contracts" / "task.json")
        task_markers = set(re.findall(r"\{\{([A-Z][A-Z0-9_]*)\}\}", (PAYLOAD / "contracts" / "task.json").read_text()))
        self.assertEqual(task_markers, {"STEP_ID", "HARNESS_STYLE", "PROCESS_EFFECT", "PLAN_STEP_ID"})
        # The first action starts python3, and the step consumes the plan step's output.
        self.assertEqual(task["effects"], ["reads_fs", "writes_fs", "{{PROCESS_EFFECT}}"])
        self.assertEqual(task["dependency_ids"], ["{{PLAN_STEP_ID}}"])
        for named in re.findall(r"\.baltor/step/scripts/([a-z_]+\.py)", agents.decode("utf-8")):
            self.assertTrue((PAYLOAD / "scripts" / named).is_file(), named)


if __name__ == "__main__":
    unittest.main()
