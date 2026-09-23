"""Known-good and known-wrong controls for text encoding screening."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "packages/audit-text-encoding/scripts/audit_text_encoding.py"
)


class TextAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "notes.txt"

    def run_audit(self, *extra: str) -> tuple[int, dict]:
        command = [
            sys.executable,
            "-B",
            str(SCRIPT),
            "--approved-root",
            str(self.root),
            "--input-relative",
            "notes.txt",
            *extra,
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.stderr, "")
        return result.returncode, json.loads(result.stdout)

    def test_valid_utf8_reports_structure_without_content(self) -> None:
        self.source.write_text("alpha\nbeta \n", encoding="utf-8")
        code, report = self.run_audit()
        self.assertEqual(code, 0)
        self.assertEqual(report["physical_lines"], 2)
        self.assertEqual(report["lines_with_trailing_whitespace"], 1)
        self.assertNotIn("alpha", json.dumps(report))

    def test_known_wrong_invalid_utf8_fails(self) -> None:
        self.source.write_bytes(b"hello\xff")
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertEqual(report["failures"], ["invalid_utf8"])

    def test_known_wrong_mixed_newline_fails(self) -> None:
        self.source.write_bytes(b"first\r\nsecond\n")
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn("mixed_newline_styles", report["failures"])
        self.assertEqual(report["newline_counts"]["crlf"], 1)
        self.assertEqual(report["newline_counts"]["lf"], 1)

    def test_known_wrong_nul_fails(self) -> None:
        self.source.write_bytes(b"good\x00bad")
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn("nul_character", report["failures"])

    def test_known_wrong_oversized_line_fails(self) -> None:
        self.source.write_text("123456\n", encoding="utf-8")
        code, report = self.run_audit("--max-line-chars", "5")
        self.assertEqual(code, 1)
        self.assertEqual(report["lines_over_limit"], 1)

    def test_bom_is_reported_without_failure(self) -> None:
        self.source.write_bytes(b"\xef\xbb\xbfhello\r\n")
        code, report = self.run_audit()
        self.assertEqual(code, 0)
        self.assertTrue(report["utf8_bom"])

    def test_symlink_refused(self) -> None:
        outside = self.root.parent / (self.root.name + "-outside.txt")
        outside.write_text("private", encoding="utf-8")
        self.addCleanup(outside.unlink)
        self.source.symlink_to(outside)
        code, report = self.run_audit()
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "refused")

    def test_ceiling_cannot_be_raised(self) -> None:
        code, report = self.run_audit("--max-bytes", "20000001")
        self.assertEqual(code, 2)
        self.assertEqual(report["reason"], "max_bytes_outside_supported_ceiling")


if __name__ == "__main__":
    unittest.main()
