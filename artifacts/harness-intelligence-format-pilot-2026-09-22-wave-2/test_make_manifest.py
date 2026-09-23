"""Mutant controls for exact package-tree binding."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "wave2_manifest", ROOT / "make_manifest.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "batch"
        shutil.copytree(ROOT, self.root)

    def test_current_tree_contains_all_three_complete_packages(self) -> None:
        manifest = MODULE.build_manifest(self.root)
        self.assertEqual(manifest["logical_packages"], 3)
        self.assertEqual(manifest["physical_delivery_paths"], 9)
        self.assertEqual(manifest["distinct_delivery_body_digests"], 7)
        self.assertEqual(set(manifest["package_trees"]), MODULE.PACKAGE_IDS)

    def test_known_wrong_missing_script_refused(self) -> None:
        (self.root / "packages/audit-zip-package/scripts/audit_zip_package.py").unlink()
        with self.assertRaisesRegex(ValueError, "candidate_tree_mismatch"):
            MODULE.build_manifest(self.root)

    def test_known_wrong_unlisted_file_refused(self) -> None:
        (self.root / "packages/audit-zip-package/scripts/unreviewed.py").write_text(
            "print('extra')\n"
        )
        with self.assertRaisesRegex(ValueError, "candidate_tree_mismatch"):
            MODULE.build_manifest(self.root)

    def test_known_wrong_symlink_refused(self) -> None:
        (self.root / "packages/audit-zip-package/scripts/linked.py").symlink_to(
            "audit_zip_package.py"
        )
        with self.assertRaisesRegex(ValueError, "symlink_in_candidate_tree"):
            MODULE.build_manifest(self.root)

    def test_known_wrong_reused_helper_divergence_refused(self) -> None:
        with (self.root / "packages/audit-zip-package/scripts/confined_input.py").open(
            "a"
        ) as handle:
            handle.write("\n# changed\n")
        with self.assertRaisesRegex(ValueError, "reused_helper_bytes_diverged"):
            MODULE.build_manifest(self.root)

    def test_known_wrong_historical_failed_manifest_rewrite_refused(self) -> None:
        historical = self.root / "manifest-initial-failed-2026-09-22.json"
        historical.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "historical_failed_manifest_changed"):
            MODULE.build_manifest(self.root)

    def test_known_wrong_historical_overcount_manifest_rewrite_refused(self) -> None:
        historical = self.root / "manifest-successor-overcount-2026-09-22.json"
        historical.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(
            ValueError, "historical_overcount_manifest_changed"
        ):
            MODULE.build_manifest(self.root)

    def test_known_wrong_edited_script_invalidates_saved_manifest(self) -> None:
        check = [
            sys.executable,
            "-B",
            str(self.root / "make_manifest.py"),
            "--root",
            str(self.root),
            "--check",
        ]
        baseline = subprocess.run(check, capture_output=True, text=True, check=False)
        self.assertEqual(baseline.returncode, 0, baseline.stderr)
        script = (
            self.root / "packages/audit-text-encoding/scripts/audit_text_encoding.py"
        )
        with script.open("a", encoding="utf-8") as handle:
            handle.write("\n# changed after inventory\n")
        result = subprocess.run(check, capture_output=True, text=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("manifest_mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()
