"""Tests for scripts/step_status.py. Read-only: they use the shipped example packet and text held in memory."""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "step_status.py"
CHECKER = ROOT / "scripts" / "check_step_packet.py"
PACKET = ROOT / "examples" / "packet"
WRITE_NAMES = {"write_text", "write_bytes", "mkdir", "makedirs", "unlink", "rmdir", "rmtree", "rename", "replace",
               "touch", "symlink_to", "copyfile", "copytree", "remove", "chmod", "utime"}


def run(*arguments: str) -> tuple[int, dict]:
    finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--root", str(PACKET), *arguments],
                              capture_output=True, text=True, timeout=60,
                              env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")})
    return finished.returncode, json.loads(finished.stdout)


def load_status_module():
    spec = importlib.util.spec_from_file_location("status_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StepStatusTests(unittest.TestCase):
    def test_example_card_names_step_output_and_handoff(self):
        code, status = run()
        self.assertEqual(code, 0, status)
        step = status["step"]
        self.assertEqual((step["node_id"], step["kind"], step["mode"]), ("list-failing-tests", "reason", "deterministic"))
        self.assertIs(step["model_calls_authorized"], False)
        self.assertEqual(step["effects"], ["reads_fs"])
        self.assertEqual(status["output"]["required_fields"], ["failing_tests"])
        self.assertEqual(status["output"]["type"], "object")
        self.assertEqual(status["output"]["contract_refs"], ["failing_tests/v1"])
        self.assertEqual(len(status["handoff"]), 3)
        self.assertTrue(status["packet"]["passed"])
        self.assertTrue(status["next_action"].startswith("Work only on step.objective"))

    def test_packet_that_is_not_the_expected_one_turns_the_card_into_a_stop(self):
        # Known-wrong case: the host digest from the first message does not match the packet on disk.
        code, status = run("--expect-content-sha256", "1" * 64)
        self.assertEqual(code, 1)
        self.assertEqual(status["packet"]["failures"], ["not_the_expected_packet"])
        self.assertTrue(status["next_action"].startswith("Stop."))
        self.assertEqual(status["step"]["node_id"], "list-failing-tests", "the card still shows what the step was")

    def test_missing_manifest_is_a_failed_packet_not_a_crash(self):
        code, status = run("--manifest", ".baltor/step/none.json")
        self.assertEqual((code, status["packet"]["failures"]), (1, ["manifest_missing"]))

    def test_missing_or_unsafe_step_folder_is_refused(self):
        self.assertEqual(run("--step-dir", ".baltor/none"), (2, {"error": "step_dir_missing", "detail": ".baltor/none"}))
        self.assertEqual(run("--step-dir", "../packet")[1]["error"], "step_dir_unsafe")

    def test_handoff_items_come_only_from_their_section(self):
        module = load_status_module()
        text = ("# Checklist\n- [ ] outside any section\n## Before work\n- [x] packet checked\n"
                "## Before handoff\n- [ ] result written\n* [X] names in log order\nSome prose.\n"
                "## Notes\n- [ ] not a handoff item\n")
        self.assertEqual(module.handoff_items(text), ["result written", "names in log order"])
        self.assertEqual(module.handoff_items("## Before handoff\n"), [])

    def test_long_objective_is_shortened(self):
        module = load_status_module()
        shortened = module.shorten("word " * 200, module.MAX_OBJECTIVE_CHARS)
        self.assertEqual(len(shortened), module.MAX_OBJECTIVE_CHARS)
        self.assertTrue(shortened.endswith("..."))
        self.assertIsNone(module.shorten(7, 10))

    def test_both_scripts_contain_no_writing_calls(self):
        for script in (SCRIPT, CHECKER):
            tree = ast.parse(script.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
                    self.assertNotIn(name, WRITE_NAMES, f"{script.name} line {node.lineno}")
                    if name == "open" and len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                        self.assertNotRegex(node.args[1].value, "[wax+]", f"{script.name} line {node.lineno}")
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module]
                    for name in names:
                        self.assertNotIn(str(name).split(".")[0], {"subprocess", "socket", "urllib", "http", "shutil"},
                                         f"{script.name} imports {name}")


if __name__ == "__main__":
    unittest.main()
