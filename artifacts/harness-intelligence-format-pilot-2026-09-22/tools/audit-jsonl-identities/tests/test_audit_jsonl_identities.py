import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_jsonl_identities.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("audit_jsonl_identities", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class JsonlIdentityTests(unittest.TestCase):
    def check(self, body: str) -> dict:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "events.jsonl"
            source.write_text(body, encoding="utf-8")
            return MODULE.audit(folder, "events.jsonl", "event_id")

    def test_same_payload_with_different_key_order_is_identical_repeat(self):
        body = '{"event_id":"a","count":1}\n{"count":1,"event_id":"a"}\n'
        report = self.check(body)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["counts"]["identical_repeats"], 1)
        self.assertEqual(
            report["input_sha256"], hashlib.sha256(body.encode()).hexdigest()
        )

    def test_same_identity_with_changed_payload_fails(self):
        report = self.check('{"event_id":"a","count":1}\n{"event_id":"a","count":2}\n')
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["counts"]["conflicting_repeats"], 1)
        self.assertEqual(report["issue_examples"][0]["first_line"], 1)

    def test_duplicate_json_key_fails_before_identity_is_trusted(self):
        report = self.check('{"event_id":"a","event_id":"b"}\n')
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["distinct_identities"], 0)

    def test_missing_boolean_and_blank_ids_fail(self):
        report = self.check('{"value":1}\n{"event_id":true}\n{"event_id":""}\n')
        self.assertEqual(report["counts"]["invalid_records"], 3)

    def test_blank_line_and_nan_fail(self):
        report = self.check('{"event_id":1}\n\n{"event_id":2,"value":NaN}\n')
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["counts"]["invalid_records"], 2)

    def test_unicode_line_separator_inside_string_is_not_record_delimiter(self):
        report = self.check('{"event_id":"one","text":"a\u2028b"}\n')
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["line_count"], 1)

    def test_resource_limit_refuses_whole_input(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "events.jsonl"
            source.write_text('{"event_id":1}\n{"event_id":2}\n', encoding="utf-8")
            with self.assertRaises(MODULE.AuditInputError):
                MODULE.audit(folder, "events.jsonl", "event_id", max_records=1)

    def test_many_newlines_refuse_before_unbounded_record_allocation(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "events.jsonl"
            source.write_bytes(b"\n" * 1_000_000)
            with self.assertRaisesRegex(MODULE.AuditInputError, "max_records"):
                MODULE.audit(folder, "events.jsonl", "event_id", max_records=1_000)

    def test_empty_file_is_not_a_clean_event_stream(self):
        report = self.check("")
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["issue_examples"][0]["kind"], "empty_input")

    def test_cli_returns_failure_json_for_conflicting_payload(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "events.jsonl"
            source.write_text('{"event_id":1,"x":1}\n{"event_id":1,"x":2}\n')
            process = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    "--approved-root",
                    folder,
                    "--input-relative",
                    "events.jsonl",
                    "--id-field",
                    "event_id",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(process.returncode, 1)
            self.assertEqual(json.loads(process.stdout)["status"], "fail")

    def test_decimal_precision_difference_is_conflict(self):
        report = self.check(
            '{"event_id":"a","amount":9007199254740992.0}\n'
            '{"event_id":"a","amount":9007199254740993.0}\n'
        )
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["counts"]["conflicting_repeats"], 1)

    def test_large_exponent_has_deterministic_json_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "events.jsonl"
            source.write_text('{"event_id":"a","amount":1e999}\n', encoding="utf-8")
            process = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    "--approved-root",
                    folder,
                    "--input-relative",
                    "events.jsonl",
                    "--id-field",
                    "event_id",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(process.returncode, 0)
            self.assertEqual(json.loads(process.stdout)["status"], "pass")

    def test_extreme_exponent_returns_failure_json_without_traceback(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "events.jsonl"
            source.write_text(
                '{"event_id":"a","amount":1e99999999999999999999999999999999999}\n',
                encoding="utf-8",
            )
            process = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    "--approved-root",
                    folder,
                    "--input-relative",
                    "events.jsonl",
                    "--id-field",
                    "event_id",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=3,
            )
            self.assertEqual(process.returncode, 1)
            self.assertEqual(json.loads(process.stdout)["status"], "fail")
            self.assertEqual(process.stderr, "")

    def test_unpaired_surrogate_is_reported_without_traceback(self):
        report = self.check('{"event_id":"\\ud800"}\n')
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["issue_examples"][0]["kind"], "invalid_json_value")

    def test_ancestor_symlink_traversal_and_root_symlink_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            inside = base / "inside"
            outside = base / "outside"
            inside.mkdir()
            outside.mkdir()
            (outside / "private.jsonl").write_text('{"event_id":"secret"}\n')
            (inside / "alias").symlink_to(outside, target_is_directory=True)
            root_link = base / "root-link"
            root_link.symlink_to(inside, target_is_directory=True)
            for root, relative in (
                (inside, "alias/private.jsonl"),
                (inside, "../outside/private.jsonl"),
                (root_link, "event.jsonl"),
            ):
                with self.assertRaises(MODULE.ConfinedInputError):
                    MODULE.audit(root, relative, "event_id")

    def test_fifo_input_refuses_without_blocking(self):
        with tempfile.TemporaryDirectory() as folder:
            os.mkfifo(Path(folder) / "pipe.jsonl")
            process = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPT),
                    "--approved-root",
                    folder,
                    "--input-relative",
                    "pipe.jsonl",
                    "--id-field",
                    "event_id",
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
