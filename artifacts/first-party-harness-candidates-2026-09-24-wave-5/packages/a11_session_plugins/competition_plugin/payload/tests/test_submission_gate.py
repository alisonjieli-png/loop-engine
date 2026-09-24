"""Tests for skills/pre-submission-gate/scripts/submission_gate.py, run together with experiment_note.py."""
from __future__ import annotations

import ast
import copy
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
GATE = ROOT / "skills" / "pre-submission-gate" / "scripts" / "submission_gate.py"
NOTE_SCRIPT = ROOT / "scripts" / "experiment_note.py"
EXAMPLE = ROOT / "examples" / "competition"
DRAFT = ROOT / "examples" / "experiment-note-draft.json"
LOG = Path(".baltor/state/competition-plugin/gate-decisions.jsonl")
BRIEF = Path(".baltor/competition/brief.json")
NOW = "2026-10-01T12:00:00Z"


def python(script: Path, arguments, payload: bytes = b"") -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", "-B", str(script), *arguments], input=payload, capture_output=True,
                          timeout=60, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")})


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SubmissionGateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name) / "work"
        shutil.copytree(EXAMPLE, self.root)
        self.submission = self.root / "submissions" / "exp-004.csv"
        self.submission.parent.mkdir()
        self.submission.write_text("row_id,units_sold\n1,4\n2,7\n", encoding="utf-8")
        draft = {**json.loads(DRAFT.read_text(encoding="utf-8")), "submission_file": "submissions/exp-004.csv"}
        recorded = python(NOTE_SCRIPT, ["--root", str(self.root)], json.dumps(draft).encode())
        self.assertEqual(recorded.returncode, 0, recorded.stdout)

    def tearDown(self):
        self.directory.cleanup()

    def gate(self, experiment="exp-004", submission="submissions/exp-004.csv", now=NOW):
        finished = python(GATE, ["--root", str(self.root), "--experiment", experiment, "--submission", submission,
                                 "--now", now])
        return finished.returncode, json.loads(finished.stdout)

    def failed(self, decision: dict) -> list[str]:
        return [row["check"] for row in decision["checks"] if not row["passed"]]

    def test_recorded_unchanged_file_is_ready_for_the_host(self):
        code, decision = self.gate()
        self.assertEqual((code, decision["decision"]), (0, "ready_for_host_upload"))
        self.assertEqual(self.failed(decision), [])
        self.assertIn("only the host uploads", decision["upload"])
        logged = [json.loads(line) for line in (self.root / LOG).read_text(encoding="utf-8").splitlines()]
        self.assertEqual([entry["decision"] for entry in logged], ["ready_for_host_upload"])

    def test_file_written_again_after_its_note_is_held(self):
        # Known-wrong case: the submission was regenerated after the note, so it is not the recorded file.
        self.submission.write_text("row_id,units_sold\n1,5\n2,7\n", encoding="utf-8")
        code, decision = self.gate()
        self.assertEqual((code, decision["decision"]), (1, "hold"))
        self.assertEqual(self.failed(decision), ["submission_unchanged"])

    def test_deadline_and_daily_limit_hold_the_gate(self):
        code, decision = self.gate(now="2026-11-01T00:00:00Z")
        self.assertEqual((code, self.failed(decision)), (1, ["deadline_not_passed"]))
        for _ in range(3):
            self.assertEqual(self.gate()[0], 0)
        code, decision = self.gate()
        self.assertEqual((code, self.failed(decision)), (1, ["daily_limit_not_reached"]))
        self.assertEqual(self.gate(now="2026-10-02T09:00:00Z")[0], 0)

    def test_unrecorded_experiment_and_note_without_file_are_held(self):
        code, decision = self.gate(experiment="exp-999")
        self.assertEqual(code, 1)
        self.assertIn("experiment_recorded", self.failed(decision))
        draft = {**json.loads(DRAFT.read_text(encoding="utf-8")), "experiment_id": "exp-005"}
        self.assertEqual(python(NOTE_SCRIPT, ["--root", str(self.root)], json.dumps(draft).encode()).returncode, 0)
        code, decision = self.gate(experiment="exp-005")
        self.assertEqual(self.failed(decision), ["submission_recorded_in_note", "submission_unchanged"])

    def test_changed_data_version_in_the_brief_holds_the_gate(self):
        brief = json.loads((self.root / BRIEF).read_text(encoding="utf-8"))
        brief["data_version"] = "v3"
        (self.root / BRIEF).write_text(json.dumps(brief), encoding="utf-8")
        code, decision = self.gate()
        self.assertEqual((code, self.failed(decision)), (1, ["data_version_current"]))

    def test_unusable_arguments_are_refused_without_a_decision(self):
        for experiment, submission, now, error in (
                ("EXP 4", "submissions/exp-004.csv", NOW, "experiment_id_invalid"),
                ("exp-004", "../exp-004.csv", NOW, "unsafe_path"),
                ("exp-004", "submissions/none.csv", NOW, "submission_missing"),
                ("exp-004", "submissions/exp-004.csv", "tomorrow", "now_invalid")):
            code, decision = self.gate(experiment, submission, now)
            self.assertEqual((code, decision["error"]), (2, error))
        self.assertFalse((self.root / LOG).exists())

    def test_submission_folder_linking_outside_the_root_is_refused(self):
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        shutil.copyfile(self.submission, Path(outside.name) / "exp-004.csv")
        os.symlink(outside.name, self.root / "linked")
        code, decision = self.gate(submission="linked/exp-004.csv")
        self.assertEqual((code, decision["error"]), (2, "path_leaves_root"))

    def test_gate_has_no_network_or_process_code(self):
        tree = ast.parse(GATE.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertFalse(imported & {"socket", "ssl", "http", "urllib", "subprocess", "ftplib", "smtplib", "asyncio"})

    def test_gate_and_hook_judge_briefs_the_same_way(self):
        gate = load(GATE, "gate_under_test")
        hook = load(ROOT / "scripts" / "brief_summary.py", "hook_under_test")
        valid = json.loads((EXAMPLE / BRIEF).read_text(encoding="utf-8"))
        changes = [("metric", {"name": "rmse", "direction": "lower"}), ("task_type", "guessing"),
                   ("validation", {"scheme": "kfold", "folds": 0}), ("daily_submission_limit", True),
                   ("deadline_utc", "2026-10-31"), ("submission_columns", ["row_id", "row_id"]),
                   ("rules", ["x" * 201]), ("extra_field", 1)]
        briefs = [valid] + [{**copy.deepcopy(valid), field: value} for field, value in changes]
        verdicts = []
        for brief in briefs:
            outcomes = []
            for module in (gate, hook):
                try:
                    module.check_brief(copy.deepcopy(brief))
                    outcomes.append("accepted")
                except module.Refused as error:
                    outcomes.append(error.code)
            self.assertEqual(outcomes[0], outcomes[1], brief)
            verdicts.append(outcomes[0])
        self.assertEqual(verdicts[0], "accepted")
        self.assertNotIn("accepted", verdicts[1:])


if __name__ == "__main__":
    unittest.main()
