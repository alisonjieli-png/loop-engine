"""Negative controls for occupation-source identity and obvious copying."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import check_source_refs as subject


class SourceReferenceChecks(unittest.TestCase):
    def test_current_batch_has_pinned_references(self) -> None:
        self.assertEqual(subject.check(), (20, 21))

    def test_supported_source_note_forms_preserve_code_id_pairing(self) -> None:
        self.assertEqual(
            subject._source_references("- Source: `15-1252.00 / 21669`"),
            [("15-1252.00", "21669")],
        )
        self.assertEqual(
            subject._source_references("- Source: task ID `21825`, occupation `15-2051.00`"),
            [("15-2051.00", "21825")],
        )

    def test_invented_task_id_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "notes"
            shutil.copytree(subject.NOTES, copied)
            note = copied / "audit-sampling-frame-coverage.md"
            note.write_text(note.read_text(encoding="utf-8").replace("`21825`", "`999999`", 1),
                            encoding="utf-8")
            with (
                patch.object(subject, "NOTES", copied),
                self.assertRaisesRegex(ValueError, "unknown source task ID"),
            ):
                subject.check()

    def test_complete_source_statement_in_skill_is_refused(self) -> None:
        source = json.loads(subject.OPPORTUNITIES.read_text(encoding="utf-8"))
        statement = next(row["source_task_text"] for row in source["task_references"]
                         if row["occupation_code"] == "15-2051.00" and row["task_id"] == "21825")
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "packages"
            shutil.copytree(subject.PACKAGES, copied)
            skill = copied / "data" / "audit-sampling-frame-coverage" / "SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8") + "\n" + statement + "\n",
                             encoding="utf-8")
            with (
                patch.object(subject, "PACKAGES", copied),
                self.assertRaisesRegex(ValueError, "complete source task statement copied"),
            ):
                subject.check()


if __name__ == "__main__":
    unittest.main()
