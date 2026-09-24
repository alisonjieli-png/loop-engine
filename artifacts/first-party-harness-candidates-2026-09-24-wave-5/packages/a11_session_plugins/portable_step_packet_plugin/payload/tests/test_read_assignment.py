"""Tests for skills/read-step-assignment/scripts/read_assignment.py. Writes happen only in temporary folders."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "read-step-assignment" / "scripts" / "read_assignment.py"
WORKSPACE = ROOT / "examples" / "workspace"


def run(*arguments: str) -> tuple[int, dict]:
    finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments], capture_output=True, text=True,
                              timeout=60, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")})
    return finished.returncode, json.loads(finished.stdout)


def load():
    spec = importlib.util.spec_from_file_location("read_assignment_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReadAssignmentTests(unittest.TestCase):
    def test_example_card_names_task_output_and_results(self):
        code, card = run("--root", str(WORKSPACE))
        self.assertEqual(code, 0, card)
        self.assertEqual(card["record_type"], "portable_step_assignment/v1")
        self.assertEqual((card["task"]["node_id"], card["task"]["kind"]), ("newest-release", "reason"))
        self.assertIs(card["task"]["model_calls_authorized"], False)
        self.assertEqual(card["output"]["required_fields"], ["version", "release_date", "change_count"])
        self.assertIs(card["output"]["extra_fields_allowed"], False)
        names = [row["name"] for row in card["files"]]
        self.assertEqual(sorted(names), ["checklist.md", "contracts/output.schema.json", "node_context.md", "task.json"])
        task_bytes = (WORKSPACE / ".baltor" / "step" / "task.json").read_bytes()
        self.assertEqual(card["task_sha256"], hashlib.sha256(task_bytes).hexdigest())
        self.assertEqual(card["results"], {"folder": ".baltor/state/portable-step-packet-plugin/results/newest-release",
                                           "count": 0, "latest": None})

    def test_one_packet_file_is_read_as_text(self):
        code, answer = run("--root", str(WORKSPACE), "--file", "node_context.md")
        self.assertEqual(code, 0, answer)
        data = (WORKSPACE / ".baltor" / "step" / "node_context.md").read_bytes()
        self.assertEqual(answer["text"], data.decode("utf-8"))
        self.assertEqual((answer["size_bytes"], answer["sha256"]), (len(data), hashlib.sha256(data).hexdigest()))

    def test_names_outside_the_step_folder_are_refused(self):
        for name, error in (("../../CHANGELOG.md", "unsafe_path"), ("/etc/hostname", "unsafe_path"),
                            ("a\\b.md", "unsafe_path"), ("missing.md", "file_missing")):
            code, answer = run("--root", str(WORKSPACE), "--file", name)
            self.assertEqual((code, answer["error"]), (2, error), name)

    def test_a_name_that_is_not_text_is_refused_before_any_path_is_built(self):
        module = load()
        for name in (7, None, ["node_context.md"]):
            with self.assertRaises(module.Refused) as caught:
                module.read_step_file(WORKSPACE, name)
            self.assertEqual(caught.exception.code, "unsafe_path")

    def test_missing_step_folder_is_refused_with_the_root_named(self):
        code, answer = run("--root", str(ROOT / "examples"))
        self.assertEqual((code, answer["error"]), (2, "step_folder_missing"))
        self.assertIn(str(ROOT / "examples"), answer["detail"])

    def test_root_is_found_from_a_placed_script_path(self):
        module = load()
        placed = Path("/work/.baltor/plugins/portable-step-packet-plugin/skills/read-step-assignment/scripts/x.py")
        self.assertEqual(module.default_root(placed, Path("/elsewhere")), Path("/work"))
        self.assertEqual(module.default_root(Path("/opt/plugin/skills/s/scripts/x.py"), Path("/cwd")), Path("/cwd"))

    def test_output_card_without_a_schema_allows_any_fields(self):
        module = load()
        self.assertEqual(module.output_card(None), {"schema": None, "type": None, "required_fields": [],
                                                    "extra_fields_allowed": True})
        card = module.output_card({"type": "object", "required": ["a", 7], "additionalProperties": False})
        self.assertEqual((card["required_fields"], card["extra_fields_allowed"]), (["a"], False))

    def test_unsupported_or_unsafe_tasks_are_refused(self):
        cases = ({"record_type": "node_assignment/v2", "node_id": "n"}, "task_record_type_unsupported"), \
                ({"record_type": "node_assignment/v3", "node_id": "../x"}, "task_node_id_unsafe"), \
                ([1, 2], "task_record_type_unsupported")
        for task, error in cases:
            with tempfile.TemporaryDirectory() as directory:
                step = Path(directory) / ".baltor" / "step"
                step.mkdir(parents=True)
                (step / "task.json").write_text(json.dumps(task), encoding="utf-8")
                code, answer = run("--root", directory)
            self.assertEqual((code, answer["error"]), (2, error))

    def test_linked_task_and_binary_files_are_not_read(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            shutil.copytree(WORKSPACE / ".baltor", root / ".baltor")
            (root / ".baltor" / "step" / "blob.bin").write_bytes(b"\xff\xfe\x00\x01")
            code, answer = run("--root", directory, "--file", "blob.bin")
            self.assertEqual((code, answer["error"]), (2, "not_text"))
            (Path(outside) / "secret.md").write_text("outside the workspace\n", encoding="utf-8")
            os.symlink(Path(outside) / "secret.md", root / ".baltor" / "step" / "leak.md")
            code, answer = run("--root", directory, "--file", "leak.md")
            self.assertEqual((code, answer["error"]), (2, "path_leaves_root"))
            code, card = run("--root", directory)
            self.assertIn({"name": "leak.md", "readable": False}, card["files"])
            (root / "notes.md").write_text("a workspace file outside the packet\n", encoding="utf-8")
            os.symlink(root, root / ".baltor" / "step" / "linked")
            code, answer = run("--root", directory, "--file", "linked/notes.md")
            self.assertEqual((code, answer["error"]), (2, "path_leaves_step_folder"))
            task = root / ".baltor" / "step" / "task.json"
            task.rename(root / "task-copy.json")
            os.symlink(root / "task-copy.json", task)
            code, answer = run("--root", directory)
            self.assertEqual((code, answer["error"]), (2, "task_missing"))


if __name__ == "__main__":
    unittest.main()
