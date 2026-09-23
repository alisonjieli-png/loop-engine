"""Known-good and known-wrong controls for ZIP metadata screening."""

from __future__ import annotations

import json
import resource
import stat
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "packages/audit-zip-package/scripts/audit_zip_package.py"
)


class ZipAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "bundle.zip"

    def run_audit(self, *extra: str) -> tuple[int, dict]:
        command = [
            sys.executable,
            "-B",
            str(SCRIPT),
            "--approved-root",
            str(self.root),
            "--input-relative",
            "bundle.zip",
            *extra,
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.stderr, "")
        return result.returncode, json.loads(result.stdout)

    def test_safe_archive_passes_without_extraction(self) -> None:
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("docs/", "")
            archive.writestr("docs/readme.txt", "hello")
        code, report = self.run_audit()
        self.assertEqual(code, 0)
        self.assertEqual(report["entries"], 2)
        self.assertFalse((self.root / "docs").exists())

    def test_distinct_unicode_and_nested_regular_entries_pass(self) -> None:
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("docs/caf\u00e9.txt", "one")
            archive.writestr("docs/notes.txt", "two")
        code, report = self.run_audit()
        self.assertEqual(code, 0)
        self.assertTrue(report["metadata_complete"])

    def test_known_wrong_traversal_fails_without_echoing_name(self) -> None:
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("../secret.txt", "hidden")
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn("unsafe_entry_path", report["issue_counts"])
        self.assertNotIn("secret.txt", json.dumps(report))

    def test_known_wrong_duplicate_entry_fails(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.archive, "w") as archive:
                archive.writestr("same.txt", "one")
                archive.writestr("same.txt", "two")
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn("duplicate_entry_path", report["issue_counts"])

    def test_known_wrong_casefold_equivalent_names_fail(self) -> None:
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("Readme.txt", "one")
            archive.writestr("README.txt", "two")
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn("portable_path_collision", report["issue_counts"])

    def test_known_wrong_unicode_equivalent_names_fail(self) -> None:
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("caf\u00e9.txt", "one")
            archive.writestr("cafe\u0301.txt", "two")
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn("portable_path_collision", report["issue_counts"])

    def test_known_wrong_trailing_dot_alias_fails(self) -> None:
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("report.txt", "one")
            archive.writestr("report.txt.", "two")
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn("unsafe_entry_path", report["issue_counts"])

    def test_known_wrong_reserved_device_name_fails(self) -> None:
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("CON", "device")
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn("unsafe_entry_path", report["issue_counts"])

    def test_known_wrong_nested_portable_unsafe_names_fail(self) -> None:
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("dir/foo:ads", "alternate stream")
            archive.writestr("dir/CON.txt", "device")
            archive.writestr("dir/aux", "device")
            archive.writestr("dir/file.txt ", "alias")
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertGreaterEqual(report["issue_counts"].get("unsafe_entry_path", 0), 4)

    def test_known_wrong_symlink_entry_fails(self) -> None:
        link = zipfile.ZipInfo("link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr(link, "../outside")
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn("symbolic_link_entry", report["issue_counts"])

    def test_known_wrong_special_files_and_privileged_mode_fail(self) -> None:
        with zipfile.ZipFile(self.archive, "w") as archive:
            for name, mode in (
                ("fifo", stat.S_IFIFO | 0o644),
                ("character-device", stat.S_IFCHR | 0o666),
                ("setuid-file", stat.S_IFREG | stat.S_ISUID | 0o755),
            ):
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = mode << 16
                archive.writestr(info, b"")
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertGreaterEqual(
            report["issue_counts"].get("unsupported_special_file_entry", 0), 2
        )
        self.assertGreaterEqual(
            report["issue_counts"].get("privileged_mode_entry", 0), 1
        )

    def test_known_wrong_expansion_fails(self) -> None:
        with zipfile.ZipFile(
            self.archive, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            archive.writestr("repeated.txt", "x" * 50_000)
        code, report = self.run_audit("--max-expanded-bytes", "1000")
        self.assertEqual(code, 1)
        self.assertIn("expanded_size_exceeds_ceiling", report["issue_counts"])

    def test_known_wrong_entry_ceiling_does_not_report_partial_expansion(self) -> None:
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("one.txt", "1")
            archive.writestr("two.txt", "2")
            archive.writestr("three.txt", "3")
        code, report = self.run_audit("--max-entries", "2")
        self.assertEqual(code, 1)
        self.assertEqual(report["entries"], 3)
        self.assertIn("entry_count_exceeds_ceiling", report["issue_counts"])
        self.assertFalse(report["metadata_complete"])
        self.assertIsNone(report["claimed_expanded_bytes"])

    def test_known_wrong_large_entry_directory_returns_json_under_memory_cap(
        self,
    ) -> None:
        with zipfile.ZipFile(self.archive, "w") as archive:
            for index in range(130_000):
                archive.writestr(f"entry-{index:06d}", b"")
        self.assertLess(self.archive.stat().st_size, 20_000_000)

        def limit_address_space() -> None:
            ceiling = 96 * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (ceiling, ceiling))

        command = [
            sys.executable,
            "-B",
            str(SCRIPT),
            "--approved-root",
            str(self.root),
            "--input-relative",
            "bundle.zip",
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            preexec_fn=limit_address_space,
        )
        self.assertEqual(result.stderr, "")
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report["status"], "refused")
        self.assertEqual(report["reason"], "entry_signature_prefilter_ambiguous")
        self.assertIsNone(report["entries"])
        self.assertFalse(report["metadata_complete"])

    def test_known_wrong_signature_bytes_in_payload_are_unknown_not_invalid(
        self,
    ) -> None:
        with zipfile.ZipFile(
            self.archive, "w", compression=zipfile.ZIP_STORED
        ) as archive:
            archive.writestr("payload.bin", b"PK\x01\x02" * 5_001)
        code, report = self.run_audit()
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "refused")
        self.assertEqual(report["reason"], "entry_signature_prefilter_ambiguous")
        self.assertIsNone(report["entries"])

    def test_known_wrong_deep_paths_return_before_timeout(self) -> None:
        with zipfile.ZipFile(self.archive, "w") as archive:
            for index in range(500):
                archive.writestr(("a/" * 5_000) + str(index), b"")
        self.assertLess(self.archive.stat().st_size, 20_000_000)
        command = [
            sys.executable,
            "-B",
            str(SCRIPT),
            "--approved-root",
            str(self.root),
            "--input-relative",
            "bundle.zip",
        ]
        result = subprocess.run(
            command, capture_output=True, text=True, check=False, timeout=5
        )
        self.assertEqual(result.stderr, "")
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("entry_path_depth_exceeds_ceiling", report["issue_counts"])

    def test_known_wrong_file_parent_collision_fails(self) -> None:
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("a", "file")
            archive.writestr("a/b.txt", "child")
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn("file_used_as_parent", report["issue_counts"])

    def test_invalid_archive_fails(self) -> None:
        self.archive.write_bytes(b"not an archive")
        code, report = self.run_audit()
        self.assertEqual(code, 1)
        self.assertIn("invalid_zip", report["issue_counts"])

    def test_symlink_to_outside_refused(self) -> None:
        outside = self.root.parent / (self.root.name + "-outside.zip")
        outside.write_bytes(b"outside")
        self.addCleanup(outside.unlink)
        self.archive.symlink_to(outside)
        code, report = self.run_audit()
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "refused")

    def test_ceiling_cannot_be_raised(self) -> None:
        code, report = self.run_audit("--max-entries", "5001")
        self.assertEqual(code, 2)
        self.assertEqual(report["reason"], "max_entries_outside_supported_ceiling")


if __name__ == "__main__":
    unittest.main()
