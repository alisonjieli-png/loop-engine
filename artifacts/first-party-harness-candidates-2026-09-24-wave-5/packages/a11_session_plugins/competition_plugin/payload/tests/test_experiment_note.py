"""Tests for scripts/experiment_note.py."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "experiment_note.py"
EXAMPLE = ROOT / "examples" / "competition"
DRAFT = ROOT / "examples" / "experiment-note-draft.json"
NOTES = Path(".baltor/state/competition-plugin/experiments.jsonl")


def note(root: Path, draft=None, raw: bytes | None = None) -> subprocess.CompletedProcess:
    payload = raw if raw is not None else json.dumps(draft).encode()
    return subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), "--root", str(root)], input=payload,
                          capture_output=True, timeout=60, env={"PATH": os.environ.get("PATH", "/usr/bin:/bin")})


class ExperimentNoteTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name) / "work"
        shutil.copytree(EXAMPLE, self.root)
        self.draft = json.loads(DRAFT.read_text(encoding="utf-8"))

    def tearDown(self):
        self.directory.cleanup()

    def lines(self) -> list[dict]:
        path = self.root / NOTES
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []

    def test_example_draft_is_recorded_with_computed_mean_and_spread(self):
        finished = note(self.root, self.draft)
        self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
        answer = json.loads(finished.stdout)
        scores = self.draft["fold_scores"]
        self.assertAlmostEqual(answer["cv_mean"], statistics.fmean(scores))
        self.assertAlmostEqual(answer["cv_std"], statistics.pstdev(scores))
        self.assertEqual((answer["fold_count"], answer["notes_total"], answer["direction"]), (5, 1, "minimize"))
        stored = self.lines()
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["record_type"], "experiment_note/v1")
        self.assertRegex(stored[0]["recorded_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_a_claimed_mean_is_refused(self):
        # Known-wrong case: the model sends its own rounded or invented mean.
        finished = note(self.root, {**self.draft, "cv_mean": 11.9})
        self.assertEqual(finished.returncode, 2)
        self.assertIn("the script computes cv_mean", json.loads(finished.stdout)["problems"][0])
        self.assertEqual(self.lines(), [])

    def test_brief_mismatches_are_refused_and_nothing_is_written(self):
        cases = {"metric_differs_from_brief": {"metric": "mae"},
                 "fold_count_differs_from_brief": {"fold_scores": [12.4, 12.9, 12.1, 13.0]},
                 "data_version_differs_from_brief": {"data_version": "v1"}}
        for failure, change in cases.items():
            finished = note(self.root, {**self.draft, **change})
            self.assertEqual(finished.returncode, 1, failure)
            self.assertEqual(json.loads(finished.stdout)["failures"], [failure])
        self.assertEqual(self.lines(), [])

    def test_an_experiment_id_is_recorded_once(self):
        self.assertEqual(note(self.root, self.draft).returncode, 0)
        finished = note(self.root, {**self.draft, "seed": 99})
        self.assertEqual(finished.returncode, 1)
        self.assertEqual(json.loads(finished.stdout)["failures"], ["experiment_id_already_recorded"])
        self.assertEqual(len(self.lines()), 1)

    def test_submission_file_digest_is_recorded(self):
        submission = self.root / "submissions" / "exp-004.csv"
        submission.parent.mkdir()
        submission.write_text("row_id,units_sold\n1,4\n2,7\n", encoding="utf-8")
        finished = note(self.root, {**self.draft, "submission_file": "submissions/exp-004.csv"})
        self.assertEqual(finished.returncode, 0, finished.stdout)
        self.assertEqual(json.loads(finished.stdout)["submission_sha256"], hashlib.sha256(submission.read_bytes()).hexdigest())

    def test_missing_or_unsafe_submission_files_are_refused(self):
        finished = note(self.root, {**self.draft, "submission_file": "submissions/none.csv"})
        self.assertEqual(json.loads(finished.stdout)["failures"], ["submission_file_missing"])
        finished = note(self.root, {**self.draft, "submission_file": "../outside.csv"})
        self.assertEqual(json.loads(finished.stdout)["failures"], ["submission_file_path_unsafe"])

    def test_unusable_numbers_are_refused(self):
        finished = note(self.root, raw=DRAFT.read_bytes().replace(b"12.41", b"NaN"))
        self.assertEqual((finished.returncode, json.loads(finished.stdout)["error"]), (2, "nonstandard_number"))
        finished = note(self.root, {**self.draft, "fold_scores": [True, 12.0, 12.0, 12.0, 12.0]})
        self.assertEqual(finished.returncode, 2)
        finished = note(self.root, {**self.draft, "seed": 1.5})
        self.assertEqual(finished.returncode, 2)

    def test_missing_brief_is_refused(self):
        (self.root / ".baltor" / "competition" / "brief.json").unlink()
        finished = note(self.root, self.draft)
        self.assertEqual((finished.returncode, json.loads(finished.stdout)["error"]), (2, "brief_missing"))


if __name__ == "__main__":
    unittest.main()
