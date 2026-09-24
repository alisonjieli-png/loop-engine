"""Tests for scripts/step_packet_check.py. Effects: writes packet files only inside temporary folders and starts the script with the running Python; no network."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent
SCRIPT = PACKAGE / "scripts" / "step_packet_check.py"
# Assembled at run time so that no file of the package holds an unfilled marker.
MARKER = "{" * 2 + "TICKET_PATH" + "}" * 2

TASK = {"record_type": "node_assignment/v3", "node_id": "sort-ticket-7", "kind": "reason",
        "objective": "Decide whether ticket ABC-7 can be worked tonight.",
        "output_contract_refs": ["ticket_decision/v1"], "dependency_ids": [], "required_capabilities": [],
        "effects": ["reads_fs", "writes_fs"], "harness_style": "codex", "model_calls_authorized": True,
        "mode": "non_deterministic"}
CONTEXT = """# Sort one ticket: context

## Objective

Decide whether ticket ABC-7 can be worked tonight.

## Relevant context

The queue runs without a person present.

## Current state

Nothing has changed yet.

## Contracts and input

The ticket is in tickets/ABC-7.md.

## Acceptance

- The decision is go or hold.
- Every hold names one question.
"""
CHECKLIST = """# Checklist

## Before work

- [ ] The ticket file exists.

## Before handoff

- [ ] The decision file matches the output schema.
- [x] No other file changed.
"""
ENTRY = """# Sort one ticket

## First action

Open the ticket file tickets/ABC-7.md once from start to end.

## Steps

1. List every acceptance statement.
"""


class StepPacketCheck(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.step = self.root / ".baltor" / "step"
        self.step.mkdir(parents=True)
        self.write(".baltor/step/task.json", json.dumps(TASK, indent=1) + "\n")
        self.write(".baltor/step/node_context.md", CONTEXT)
        self.write(".baltor/step/checklist.md", CHECKLIST)
        self.write("AGENTS.md", ENTRY)

    def tearDown(self):
        self.folder.cleanup()

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def run_check(self, *arguments):
        finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--root", str(self.root), *arguments],
                                  capture_output=True, text=True, timeout=60)
        return finished.returncode, json.loads(finished.stdout)

    def test_complete_packet_is_ready(self):
        status, answer = self.run_check()
        self.assertEqual((status, answer["result"]), (0, "ready"), answer)
        self.assertEqual(answer["objective"], TASK["objective"])
        self.assertEqual(answer["first_action"], "Open the ticket file tickets/ABC-7.md once from start to end.")
        self.assertEqual(answer["first_action_source"], "AGENTS.md")
        self.assertEqual(answer["acceptance"], ["The decision is go or hold.", "Every hold names one question."])
        self.assertEqual(answer["before_work"], ["The ticket file exists."])
        self.assertEqual(answer["before_handoff"], ["The decision file matches the output schema.",
                                                    "No other file changed."])
        self.assertEqual((answer["kind"], answer["model_calls_authorized"]), ("reason", True))
        self.assertEqual(answer["instruction_markers"], [])
        self.assertEqual(answer["unchecked_files"], [])

    def test_ready_answer_tells_the_model_to_do_the_before_work_items_first(self):
        """Known-wrong case: the answer lists before_work items, but nothing tells the model to do them."""
        status, answer = self.run_check()
        self.assertEqual(status, 0)
        self.assertLess(answer["next"].index("before_work"), answer["next"].index("first_action"))

    def test_marker_in_an_input_file_is_refused(self):
        self.write(".baltor/step/input.json", json.dumps({"ticket_path": MARKER}) + "\n")
        status, answer = self.run_check()
        self.assertEqual((status, answer["reason"]), (1, "unrendered_step_input"))
        self.assertEqual(answer["detail"]["files"], [".baltor/step/input.json"])

    def test_binary_and_large_input_files_are_listed_not_refused(self):
        """Known-wrong case: an attachment the host placed in the packet folder blocked the whole step."""
        (self.step / "inputs").mkdir()
        (self.step / "inputs" / "scan.png").write_bytes(bytes(range(256)) * 4)
        (self.step / "inputs" / "rows.csv").write_text("id,value\n" + "1,2\n" * 80000, encoding="utf-8")
        status, answer = self.run_check()
        self.assertEqual((status, answer["result"]), (0, "ready"), answer)
        self.assertEqual({item["path"]: item["reason"] for item in answer["unchecked_files"]},
                         {".baltor/step/inputs/rows.csv": "larger than 262144 bytes",
                          ".baltor/step/inputs/scan.png": "not UTF-8 text"})

    def test_context_file_that_is_not_text_is_refused(self):
        (self.step / "node_context.md").write_bytes(b"## Objective\n\xff\xfe\n")
        status, answer = self.run_check()
        self.assertEqual((status, answer["reason"]), (2, "packet_file_not_text"))

    def test_unfilled_marker_in_the_packet_is_refused(self):
        """Known-wrong case: the host left a marker in node_context.md."""
        self.write(".baltor/step/node_context.md", CONTEXT.replace("tickets/ABC-7.md", MARKER))
        status, answer = self.run_check()
        self.assertEqual((status, answer["reason"]), (1, "unrendered_step_input"))
        self.assertEqual(answer["detail"]["files"], [".baltor/step/node_context.md"])

    def test_marker_in_a_root_instruction_file_is_reported_not_refused(self):
        self.write("AGENTS.md", ENTRY + "\nTemplates in this project look like " + MARKER + ".\n")
        status, answer = self.run_check()
        self.assertEqual(status, 0)
        self.assertEqual(answer["instruction_markers"], ["AGENTS.md"])
        self.assertIn("unrendered_step_input", answer["next"])

    def test_first_action_in_the_context_file_comes_first(self):
        self.write(".baltor/step/node_context.md", CONTEXT + "\n## First actions\n\n1. Read the ticket.\n2. Sort it.\n")
        status, answer = self.run_check()
        self.assertEqual((answer["first_action"], answer["first_action_source"]),
                         ("Read the ticket.", ".baltor/step/node_context.md"))

    def test_gemini_file_is_used_when_there_is_no_agents_file(self):
        (self.root / "AGENTS.md").rename(self.root / "GEMINI.md")
        status, answer = self.run_check()
        self.assertEqual((status, answer["first_action_source"]), (0, "GEMINI.md"))

    def test_claude_file_linked_to_agents_file_is_accepted(self):
        os.symlink("AGENTS.md", self.root / "CLAUDE.md")
        status, answer = self.run_check()
        self.assertEqual(status, 0)

    def test_missing_first_action_is_refused(self):
        self.write("AGENTS.md", "# Sort one ticket\n\n## Steps\n\n1. Work.\n")
        status, answer = self.run_check()
        self.assertEqual((status, answer["reason"]), (1, "first_action_missing"))

    def test_wrong_task_record_is_refused(self):
        for change in ({"record_type": "node_assignment/v2"}, {"model_calls_authorized": "false"},
                       {"kind": "write"}, {"mode": "fast"}, {"effects": ["pure", "reads_fs"]},
                       {"effects": ["reads_fs", "reads_fs"]}, {"effects": ["Reads FS"]},
                       {"node_id": "../x"}, {"extra": 1}):
            record = dict(TASK)
            record.update(change)
            self.write(".baltor/step/task.json", json.dumps(record) + "\n")
            status, answer = self.run_check()
            self.assertEqual((status, answer["reason"]), (1, "task_record_invalid"), change)

    def test_duplicate_key_in_the_task_record_is_refused(self):
        self.write(".baltor/step/task.json", '{"kind": "reason", "kind": "build"}\n')
        status, answer = self.run_check()
        self.assertEqual((status, answer["reason"]), (2, "task_record_unreadable"))

    def test_context_without_acceptance_is_refused(self):
        self.write(".baltor/step/node_context.md", CONTEXT.split("## Acceptance")[0])
        status, answer = self.run_check()
        self.assertEqual((status, answer["reason"]), (1, "node_context_incomplete"))

    def test_missing_packet_is_refused(self):
        (self.step / "task.json").unlink()
        status, answer = self.run_check()
        self.assertEqual((status, answer["reason"]), (2, "packet_file_missing"))
        status, answer = self.run_check("--step-dir", "no/such/folder")
        self.assertEqual((status, answer["reason"]), (2, "packet_missing"))

    def test_links_and_paths_that_leave_the_workspace_are_refused(self):
        with tempfile.TemporaryDirectory() as other:
            os.symlink(other, self.root / ".baltor" / "elsewhere")
            status, answer = self.run_check("--step-dir", ".baltor/elsewhere")
            self.assertEqual((status, answer["reason"]), (2, "unsafe_packet_path"))
        status, answer = self.run_check("--step-dir", "../step")
        self.assertEqual((status, answer["reason"]), (2, "unsafe_packet_path"))

    def test_instruction_section_names_this_script(self):
        text = (PACKAGE / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("python3 -I -B .baltor/focused-step-packet-rules/scripts/step_packet_check.py", text)
        self.assertEqual((PACKAGE / "GEMINI.md").read_bytes(), (PACKAGE / "AGENTS.md").read_bytes())
        self.assertEqual((PACKAGE / "CLAUDE.md").read_text(encoding="utf-8"), "@AGENTS.md\n")
        self.assertNotIn("## First action", text.splitlines())

    def test_section_reads_the_packet_before_it_runs_anything(self):
        """Known-wrong case: the section made the model start a process before it had read its effects."""
        rules = [line for line in (PACKAGE / "AGENTS.md").read_text(encoding="utf-8").splitlines()
                 if line[:1].isdigit()]
        self.assertIn(".baltor/step/task.json", rules[0])
        self.assertNotIn("python3", rules[0])
        command = [line for line in rules if "step_packet_check.py" in line]
        self.assertEqual(len(command), 1)
        self.assertIn("ends in `_process`", command[0])
        self.assertIn("Before work", "\n".join(rules))


if __name__ == "__main__":
    unittest.main()
