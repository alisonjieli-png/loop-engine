"""Negative controls for mixed-format candidate file inventory."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import make_format_manifest as subject


class MixedFormatManifestChecks(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        for group in subject.GROUPS:
            (self.root / group).mkdir()
        self.script = self.root / "tools" / "check.py"
        self.script.write_text("print('candidate')\n", encoding="utf-8")
        (self.root / "context" / "AGENTS.md").write_text("# Candidate brief\n", encoding="utf-8")
        (self.root / "connections" / "opencode.json").write_text("{}\n", encoding="utf-8")

    def test_non_markdown_files_are_counted_and_hashed(self) -> None:
        record = json.loads(subject.render("0" * 40, self.root))
        self.assertEqual(record["physical_file_count"], 3)
        self.assertEqual(record["approval_state"], "none")
        self.assertEqual(record["effect_qualification"], "none")
        script = next(row for row in record["entries"] if row["path"] == "tools/check.py")
        self.assertEqual(script["sha256"], hashlib.sha256(self.script.read_bytes()).hexdigest())

    def test_changed_bytes_no_longer_match_saved_manifest(self) -> None:
        frozen = subject.render("0" * 40, self.root)
        self.script.write_text("print('changed')\n", encoding="utf-8")
        self.assertNotEqual(frozen, subject.render("0" * 40, self.root))

    def test_symlinked_file_is_refused(self) -> None:
        outside = self.root / "outside.txt"
        outside.write_text("external", encoding="utf-8")
        self.script.unlink()
        self.script.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symlinked"):
            subject.inventory(self.root)

    def test_generated_python_cache_is_refused(self) -> None:
        cache = self.root / "tools" / "__pycache__"
        cache.mkdir()
        (cache / "check.cpython-314.pyc").write_bytes(b"compiled")
        with self.assertRaisesRegex(ValueError, "generated, runtime"):
            subject.inventory(self.root)


if __name__ == "__main__":
    unittest.main()
