"""Known-wrong controls for the pinned source check."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import check_source_refs as subject


class SourceReferenceChecks(unittest.TestCase):
    def test_current_batch_has_exact_references(self) -> None:
        self.assertEqual(subject.check(), (12, 12))

    def test_invented_task_id_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "notes"
            shutil.copytree(subject.NOTES, copied)
            note = copied / "allocate-scarce-stock-by-promised-service.md"
            note.write_text(note.read_text(encoding="utf-8").replace("task ID `8934`", "task ID `999999`", 1), encoding="utf-8")
            with patch.object(subject, "NOTES", copied), self.assertRaisesRegex(ValueError, "unknown source task ID"):
                subject.check()

    def test_duplicate_source_id_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "notes"
            shutil.copytree(subject.NOTES, copied)
            note = copied / "compare-distribution-paths-with-failure-costs.md"
            note.write_text(note.read_text(encoding="utf-8").replace("task ID `8949`", "task ID `8934`", 1), encoding="utf-8")
            with patch.object(subject, "NOTES", copied), self.assertRaisesRegex(ValueError, "duplicate source task ID"):
                subject.check()

    def test_copied_source_phrase_is_refused(self) -> None:
        source = json.loads(subject.OPPORTUNITIES.read_text(encoding="utf-8"))
        statement = next(row["source_task_text"] for row in source["task_references"]
                         if row["occupation_code"] == "13-1081.00" and row["task_id"] == "8934")
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "packages"
            shutil.copytree(subject.PACKAGES, copied)
            skill = copied / "data" / "allocate-scarce-stock-by-promised-service" / "SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8") + "\n" + statement + "\n", encoding="utf-8")
            with patch.object(subject, "PACKAGES", copied), self.assertRaisesRegex(ValueError, "source span copied"):
                subject.check()


if __name__ == "__main__":
    unittest.main()
