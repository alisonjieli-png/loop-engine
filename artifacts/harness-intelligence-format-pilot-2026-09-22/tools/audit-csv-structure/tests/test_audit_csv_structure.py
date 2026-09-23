import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_csv_structure.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("audit_csv_structure", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CsvAuditTests(unittest.TestCase):
    def check(
        self, body: bytes, delimiter: str = ",", header_mode: str = "present"
    ) -> dict:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "table.csv"
            source.write_bytes(body)
            return MODULE.audit(folder, "table.csv", delimiter, header_mode=header_mode)

    def test_quoted_delimiter_and_multiline_value_are_valid(self):
        body = b'id,note\n1,"a,b"\n2,"two\nlines"\n'
        report = self.check(body)
        self.assertEqual((report["status"], report["data_rows"]), ("pass", 2))
        self.assertEqual(report["input_sha256"], hashlib.sha256(body).hexdigest())

    def test_wrong_row_width_is_rejected(self):
        report = self.check(b"id,value\n1,2\n3\n")
        self.assertIn(
            "row_width_mismatch", [x["kind"] for x in report["issue_examples"]]
        )

    def test_duplicate_and_blank_headers_are_rejected(self):
        report = self.check(b" ID ,id, \n1,2,3\n")
        self.assertEqual(report["status"], "fail")
        self.assertEqual(
            {x["kind"] for x in report["issue_examples"]},
            {"duplicate_header_name", "blank_header_name"},
        )

    def test_malformed_quote_is_rejected(self):
        report = self.check(b'id,note\n1,"unterminated\n')
        self.assertIn("malformed_csv", [x["kind"] for x in report["issue_examples"]])

    def test_bom_and_tab_delimiter(self):
        report = self.check(b"\xef\xbb\xbfid\tvalue\n1\t2\n", "\t")
        self.assertEqual(report["header"], ["id", "value"])
        self.assertEqual(report["status"], "pass")

    def test_symlink_leaf_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "real.csv"
            link = Path(folder) / "link.csv"
            target.write_text("id\n1\n", encoding="utf-8")
            link.symlink_to(target)
            with self.assertRaises(MODULE.ConfinedInputError):
                MODULE.audit(folder, "link.csv", header_mode="present")

    def test_byte_limit_refuses_whole_input(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "table.csv"
            source.write_bytes(b"id\n1\n")
            with self.assertRaisesRegex(MODULE.AuditInputError, "max_bytes"):
                MODULE.audit(folder, "table.csv", max_bytes=4, header_mode="present")

    def test_cli_returns_failure_json_for_known_wrong_row(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "table.csv"
            source.write_bytes(b"id,value\n1\n")
            process = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    "--approved-root",
                    folder,
                    "--input-relative",
                    "table.csv",
                    "--header-mode",
                    "present",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(process.returncode, 1)
            self.assertEqual(json.loads(process.stdout)["status"], "fail")

    def test_headerless_default_never_prints_private_first_row(self):
        private = b"secret-customer,private-value\n"
        report = self.check(private, header_mode="absent")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(
            (report["header"], report["column_count"], report["data_rows"]), ([], 2, 1)
        )
        self.assertNotIn("secret-customer", json.dumps(report))

    def test_large_valid_quoted_field_is_not_mislabeled_malformed(self):
        body = b'id,note\n1,"' + b"x" * 131_073 + b'"\n'
        report = self.check(body)
        self.assertEqual(report["status"], "pass")

    def test_ancestor_symlink_and_traversal_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            inside = base / "inside"
            outside = base / "outside"
            inside.mkdir()
            outside.mkdir()
            (outside / "private.csv").write_text("secret\n", encoding="utf-8")
            (inside / "alias").symlink_to(outside, target_is_directory=True)
            for relative in ("alias/private.csv", "../outside/private.csv"):
                with self.assertRaises(MODULE.ConfinedInputError):
                    MODULE.audit(inside, relative, header_mode="present")

    def test_approved_root_symlink_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            inside = base / "inside"
            inside.mkdir()
            (inside / "table.csv").write_text("id\n1\n", encoding="utf-8")
            link = base / "root-link"
            link.symlink_to(inside, target_is_directory=True)
            with self.assertRaises(MODULE.ConfinedInputError):
                MODULE.audit(link, "table.csv", header_mode="present")

    def test_fifo_input_refuses_without_blocking(self):
        with tempfile.TemporaryDirectory() as folder:
            os.mkfifo(Path(folder) / "pipe.csv")
            process = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    "--approved-root",
                    folder,
                    "--input-relative",
                    "pipe.csv",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=3,
            )
            self.assertEqual(process.returncode, 2)
            self.assertEqual(json.loads(process.stdout)["status"], "refused")


if __name__ == "__main__":
    unittest.main()
