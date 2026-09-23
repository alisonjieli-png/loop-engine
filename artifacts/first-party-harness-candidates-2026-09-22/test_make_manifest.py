"""Negative controls for exact-byte candidate inventory; no approval tests."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import make_manifest as subject

REVISION = "0" * 40


class CandidateManifestChecks(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        (self.root / "packages").mkdir()
        for group in subject.GROUPS:
            (self.root / "packages" / group).mkdir()
        (self.root / "review-notes").mkdir()
        self.skill = self.root / "packages" / "data" / "sample-method" / "SKILL.md"
        self.skill.parent.mkdir()
        self.skill.write_text(
            "---\nname: sample-method\ndescription: Check a sample method. Use for a sample task.\n---\n\n# Sample\n",
            encoding="utf-8",
        )
        self.note = self.root / "review-notes" / "sample-method.md"
        self.note.write_text("# Candidate review\n\nKnown-wrong example: skip a required check.\n", encoding="utf-8")
        for name, value in (
            ("ROOT", self.root),
            ("PACKAGES", self.root / "packages"),
            ("NOTES", self.root / "review-notes"),
            ("MANIFEST", self.root / "manifest.json"),
        ):
            substitution = patch.object(subject, name, value)
            substitution.start()
            self.addCleanup(substitution.stop)

    def test_render_binds_both_exact_files_without_approval(self) -> None:
        result = json.loads(subject.render(REVISION))
        self.assertEqual(result["package_count"], 1)
        self.assertEqual(result["approval_state"], "none")
        self.assertEqual(result["rights_state"], "pending_independent_review")
        self.assertEqual(result["effect_qualification"], "none")
        self.assertEqual(result["benefit_evidence"], "unmeasured")
        self.assertEqual(
            result["entries"][0]["package_sha256"],
            hashlib.sha256(self.skill.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            result["entries"][0]["review_note_sha256"],
            hashlib.sha256(self.note.read_bytes()).hexdigest(),
        )

    def test_missing_review_note_is_refused(self) -> None:
        self.note.unlink()
        with self.assertRaisesRegex(ValueError, "file missing"):
            subject.inventory()

    def test_symlinked_package_file_is_refused(self) -> None:
        outside = self.root / "outside.md"
        outside.write_text("outside", encoding="utf-8")
        self.skill.unlink()
        self.skill.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symlink"):
            subject.inventory()

    def test_duplicate_name_across_groups_is_refused(self) -> None:
        other = self.root / "packages" / "project" / "sample-method"
        other.mkdir()
        (other / "SKILL.md").write_bytes(self.skill.read_bytes())
        with self.assertRaisesRegex(ValueError, "duplicate logical package name"):
            subject.inventory()

    def test_extra_package_file_is_refused(self) -> None:
        (self.skill.parent / "surprise.txt").write_text("unexpected", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "only SKILL.md"):
            subject.inventory()

    def test_changed_bytes_make_the_frozen_manifest_fail_check(self) -> None:
        subject.MANIFEST.write_text(subject.render(REVISION), encoding="utf-8")
        self.skill.write_text(self.skill.read_text(encoding="utf-8") + "Changed.\n", encoding="utf-8")
        with (
            patch.object(sys, "argv", ["make_manifest.py", "--check"]),
            redirect_stderr(StringIO()),
            self.assertRaises(SystemExit) as failure,
        ):
            subject.main()
        self.assertEqual(failure.exception.code, 1)

    def test_cli_can_inventory_a_second_isolated_batch_root(self) -> None:
        other = self.root / "second"
        for group in subject.GROUPS:
            (other / "packages" / group).mkdir(parents=True)
        skill = other / "packages" / "data" / "other-method" / "SKILL.md"
        skill.parent.mkdir()
        skill.write_text(
            "---\nname: other-method\ndescription: Check another task. Use for a separate batch.\n---\n",
            encoding="utf-8",
        )
        note = other / "review-notes" / "other-method.md"
        note.parent.mkdir()
        note.write_text("# Candidate review\n\nKnown-wrong example: skip a required check.\n", encoding="utf-8")
        with (
            patch.object(sys, "argv", ["make_manifest.py", "--write", "--root", str(other),
                                       "--base-revision", REVISION]),
            redirect_stdout(StringIO()),
        ):
            self.assertEqual(subject.main(), 0)
        result = json.loads((other / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual([row["name"] for row in result["entries"]], ["other-method"])


if __name__ == "__main__":
    unittest.main()
