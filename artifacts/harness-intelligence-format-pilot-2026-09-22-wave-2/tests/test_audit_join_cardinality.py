"""Known-good and known-wrong controls for the join-cardinality candidate."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "packages/audit-join-cardinality/scripts/audit_join_cardinality.py"
)


class JoinAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "left.csv").write_text("id,value\na,L1\nb,L2\n", encoding="utf-8")
        (self.root / "right.csv").write_text("id,value\na,R1\nb,R2\n", encoding="utf-8")

    def run_audit(self, *extra: str) -> tuple[int, dict]:
        command = [
            sys.executable,
            "-B",
            str(SCRIPT),
            "--approved-root",
            str(self.root),
            "--left-relative",
            "left.csv",
            "--right-relative",
            "right.csv",
            "--left-key",
            "id",
            "--right-key",
            "id",
            *extra,
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.stderr, "")
        return result.returncode, json.loads(result.stdout)

    def test_one_to_one_pass_and_no_key_leak(self) -> None:
        code, report = self.run_audit("--require-left-match", "--require-right-match")
        self.assertEqual(code, 0)
        self.assertEqual(report["projected_join_rows"], 2)
        self.assertEqual(report["status"], "pass")
        self.assertNotIn("L1", json.dumps(report))
        self.assertNotIn("R1", json.dumps(report))

    def test_known_wrong_many_to_many_expansion_fails_default(self) -> None:
        (self.root / "left.csv").write_text("id,value\na,L1\na,L2\n", encoding="utf-8")
        (self.root / "right.csv").write_text("id,value\na,R1\na,R2\n", encoding="utf-8")
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertEqual(report["projected_join_rows"], 4)
        self.assertIn("left_key_not_unique", report["failures"])
        self.assertIn("right_key_not_unique", report["failures"])

    def test_one_to_many_does_not_reject_right_duplicate(self) -> None:
        (self.root / "right.csv").write_text(
            "id,value\na,R1\na,R2\nb,R3\n", encoding="utf-8"
        )
        code, report = self.run_audit("--expect", "one-to-many")
        self.assertEqual(code, 0)
        self.assertEqual(report["projected_join_rows"], 3)

    def test_known_wrong_unmatched_left_requires_flag(self) -> None:
        (self.root / "right.csv").write_text("id,value\na,R1\n", encoding="utf-8")
        code, report = self.run_audit("--require-left-match")
        self.assertEqual(code, 1)
        self.assertEqual(report["left"]["unmatched_rows"], 1)
        self.assertIn("unmatched_left_rows", report["failures"])

    def test_known_wrong_blank_keys_never_join(self) -> None:
        (self.root / "left.csv").write_text("id,value\n,L1\n", encoding="utf-8")
        (self.root / "right.csv").write_text("id,value\n,R1\n", encoding="utf-8")
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertEqual(report["projected_join_rows"], 0)
        self.assertIn("blank_join_key", report["failures"])

    def test_known_wrong_whitespace_only_keys_are_blank(self) -> None:
        (self.root / "left.csv").write_text("id,value\n ,L1\n", encoding="utf-8")
        (self.root / "right.csv").write_text("id,value\n ,R1\n", encoding="utf-8")
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertEqual(report["left"]["blank_keys"], 1)
        self.assertEqual(report["right"]["blank_keys"], 1)
        self.assertEqual(report["projected_join_rows"], 0)

    def test_known_wrong_duplicate_header_fails(self) -> None:
        (self.root / "left.csv").write_text("id,id\na,b\n", encoding="utf-8")
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertEqual(report["failures"], ["empty_or_duplicate_header"])

    def test_known_wrong_ragged_record_fails(self) -> None:
        (self.root / "left.csv").write_text("id,value\na\n", encoding="utf-8")
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertEqual(report["failures"], ["field_count_mismatch"])

    def test_ancestor_symlink_refused(self) -> None:
        outside = self.root.parent / (self.root.name + "-outside")
        outside.mkdir()
        self.addCleanup(lambda: outside.rmdir())
        (outside / "external.csv").write_text("id,value\na,secret\n", encoding="utf-8")
        self.addCleanup(lambda: (outside / "external.csv").unlink())
        (self.root / "alias").symlink_to(outside, target_is_directory=True)
        code, report = self.run_audit("--left-relative", "alias/external.csv")
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "refused")

    def test_ceiling_cannot_be_raised(self) -> None:
        code, report = self.run_audit("--max-bytes", "20000001")
        self.assertEqual(code, 2)
        self.assertEqual(report["reason"], "max_bytes_outside_supported_ceiling")


if __name__ == "__main__":
    unittest.main()
