"""Tests for skills/write-step-result/scripts/write_result.py. Every write happens in a temporary copy of the example workspace."""
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
SCRIPT = ROOT / "skills" / "write-step-result" / "scripts" / "write_result.py"
WORKSPACE = ROOT / "examples" / "workspace"
RESULTS = Path(".baltor/state/portable-step-packet-plugin/results/newest-release")
GOOD = {"version": "2.4.1", "release_date": "2026-09-18", "change_count": 3}


def write(root: Path, value=None, raw: bytes | None = None) -> tuple[int, dict]:
    payload = raw if raw is not None else json.dumps(value).encode("utf-8")
    finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--root", str(root)], input=payload,
                              capture_output=True, timeout=60, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")})
    return finished.returncode, json.loads(finished.stdout)


def load():
    spec = importlib.util.spec_from_file_location("write_result_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WriteResultTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        shutil.copytree(WORKSPACE / ".baltor", self.root / ".baltor")

    def tearDown(self):
        self.directory.cleanup()

    def results(self) -> list[str]:
        folder = self.root / RESULTS
        return sorted(os.listdir(folder)) if folder.is_dir() else []

    def test_good_result_is_written_as_001_then_002_and_never_replaced(self):
        code, answer = write(self.root, GOOD)
        self.assertEqual(code, 0, answer)
        self.assertEqual((answer["written"], answer["sequence"]), (True, 1))
        self.assertEqual(answer["path"], f"{RESULTS.as_posix()}/result-001.json")
        first = (self.root / answer["path"]).read_bytes()
        self.assertEqual(answer["sha256"], hashlib.sha256(first).hexdigest())
        record = json.loads(first)
        task = (self.root / ".baltor" / "step" / "task.json").read_bytes()
        self.assertEqual(record["record_type"], "portable_step_result/v1")
        self.assertEqual((record["node_id"], record["task_sha256"]), ("newest-release", hashlib.sha256(task).hexdigest()))
        self.assertEqual((record["result"], record["checked"]), (GOOD, "required_fields_and_top_level_types"))
        code, answer = write(self.root, {**GOOD, "change_count": 4})
        self.assertEqual((code, answer["sequence"]), (0, 2))
        self.assertEqual((self.root / RESULTS / "result-001.json").read_bytes(), first)

    def test_known_wrong_result_is_refused_and_nothing_is_written(self):
        # Known-wrong case: a result with an invented field name and none of the required fields.
        code, answer = write(self.root, {"release": "2.4.1"})
        self.assertEqual(code, 1)
        self.assertFalse(answer["written"])
        self.assertEqual(answer["problems"], ["missing_required_field: version", "missing_required_field: release_date",
                                              "missing_required_field: change_count", "unknown_field: release"])
        self.assertEqual(self.results(), [])

    def test_top_level_types_are_checked(self):
        code, answer = write(self.root, {**GOOD, "change_count": "3"})
        self.assertEqual((code, answer["problems"]), (1, ["field_type_differs: change_count (expected integer)"]))
        code, answer = write(self.root, {**GOOD, "change_count": True})
        self.assertEqual(code, 1, "a boolean is not an integer")
        code, answer = write(self.root, {**GOOD, "change_count": 3.0})
        self.assertEqual(code, 0, "3.0 is an integer in JSON Schema 2020-12")
        code, answer = write(self.root, [GOOD])
        self.assertEqual((code, answer["problems"]), (1, ["result_type_differs: expected object"]))

    def test_secret_shaped_text_is_refused_without_echo(self):
        # The key-shaped value is assembled at run time so that no file at rest holds one.
        shaped = "sk-" + "Q7" * 12
        code, answer = write(self.root, {**GOOD, "version": shaped})
        self.assertEqual(code, 1)
        self.assertIn("secret_shaped_text", answer["problems"])
        self.assertNotIn(shaped, json.dumps(answer))
        self.assertEqual(self.results(), [])

    def test_without_an_output_schema_any_result_is_kept(self):
        (self.root / ".baltor" / "step" / "contracts" / "output.schema.json").unlink()
        code, answer = write(self.root, ["free", "form"])
        self.assertEqual((code, answer["checked"]), (0, "no_output_schema"))

    def test_existing_result_file_is_never_overwritten(self):
        (self.root / RESULTS).mkdir(parents=True)
        (self.root / RESULTS / "result-001.json").write_text("kept\n", encoding="utf-8")
        code, answer = write(self.root, GOOD)
        self.assertEqual((code, answer["sequence"]), (0, 2))
        self.assertEqual((self.root / RESULTS / "result-001.json").read_text(encoding="utf-8"), "kept\n")

    def test_too_many_results_stop_the_writer(self):
        (self.root / RESULTS).mkdir(parents=True)
        (self.root / RESULTS / "result-999.json").write_text("{}\n", encoding="utf-8")
        code, answer = write(self.root, GOOD)
        self.assertEqual((code, answer["problems"]), (1, ["too_many_results: 999"]))

    def test_results_folder_link_leaving_the_root_is_refused(self):
        with tempfile.TemporaryDirectory() as outside:
            state = self.root / ".baltor" / "state" / "portable-step-packet-plugin"
            state.mkdir(parents=True)
            os.symlink(outside, state / "results")
            code, answer = write(self.root, GOOD)
            self.assertEqual((code, answer["error"]), (2, "path_leaves_root"))
            self.assertEqual(os.listdir(outside), [])

    def test_unreadable_input_and_unsafe_tasks_are_refused(self):
        self.assertEqual(write(self.root, raw=b"{not json")[1]["error"], "invalid_json")
        self.assertEqual(write(self.root, raw=b'{"a": 1, "a": 2}')[1]["error"], "duplicate_key")
        code, answer = write(self.root, raw=b"[" + b"1," * (200 * 1024) + b"1]")
        self.assertEqual((code, answer["error"]), (2, "result_too_large"))
        task = self.root / ".baltor" / "step" / "task.json"
        task.write_text(json.dumps({"record_type": "node_assignment/v3", "node_id": "../escape"}), encoding="utf-8")
        code, answer = write(self.root, GOOD)
        self.assertEqual((code, answer["error"]), (2, "task_node_id_unsafe"))
        self.assertFalse((self.root / ".baltor" / "state").exists())

    def test_check_function_reports_every_problem_at_the_top_level_only(self):
        module = load()
        schema = json.loads((WORKSPACE / ".baltor" / "step" / "contracts" / "output.schema.json").read_text())
        problems, checked = module.check_result({"version": "2.4.1", "release_date": 20260918, "extra": 1}, schema)
        self.assertEqual(problems, ["missing_required_field: change_count", "unknown_field: extra",
                                    "field_type_differs: release_date (expected string)"])
        self.assertEqual(checked, "required_fields_and_top_level_types")
        problems, _checked = module.check_result({**GOOD, "version": "not a version"}, schema)
        self.assertEqual(problems, [], "patterns and deeper rules are left to the host's acceptance check")


if __name__ == "__main__":
    unittest.main()
