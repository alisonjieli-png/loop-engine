import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "inventory_file_digests.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("inventory_file_digests", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InventoryTests(unittest.TestCase):
    def test_stable_paths_exact_digests_and_same_content_group(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "z.txt").write_bytes(b"same")
            (root / "nested").mkdir()
            (root / "nested" / "a.bin").write_bytes(b"same")
            report = MODULE.inventory(root)
            self.assertEqual(
                [item["path"] for item in report["files"]], ["nested/a.bin", "z.txt"]
            )
            self.assertEqual(
                report["files"][0]["sha256"], hashlib.sha256(b"same").hexdigest()
            )
            self.assertEqual(report["same_digest_groups"], [["nested/a.bin", "z.txt"]])

    def test_changed_content_changes_digest(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source.txt"
            source.write_bytes(b"first")
            first = MODULE.inventory(root)["files"][0]["sha256"]
            source.write_bytes(b"second")
            second = MODULE.inventory(root)["files"][0]["sha256"]
            self.assertNotEqual(first, second)

    def test_symlinked_file_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "real").write_bytes(b"data")
            (root / "link").symlink_to(root / "real")
            with self.assertRaisesRegex(
                MODULE.InventoryInputError, "symlink_or_non_regular"
            ):
                MODULE.inventory(root)

    def test_symlinked_directory_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "real").mkdir()
            (root / "link").symlink_to(root / "real", target_is_directory=True)
            with self.assertRaisesRegex(
                MODULE.InventoryInputError, "symlink_or_non_regular"
            ):
                MODULE.inventory(root)

    def test_file_and_byte_limits_refuse(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "a").write_bytes(b"12")
            (root / "b").write_bytes(b"34")
            with self.assertRaisesRegex(MODULE.InventoryInputError, "max_files"):
                MODULE.inventory(root, max_files=1)
            with self.assertRaisesRegex(MODULE.InventoryInputError, "max_total_bytes"):
                MODULE.inventory(root, max_total_bytes=3)

    def test_root_symlink_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            real = root / "real"
            real.mkdir()
            link = root / "link"
            link.symlink_to(real, target_is_directory=True)
            with self.assertRaises(MODULE.InventoryInputError):
                MODULE.inventory(link)

    def test_deep_empty_tree_refused_without_recursion_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            current = root
            for _ in range(MODULE.MAX_DEPTH + 1):
                current = current / "d"
                current.mkdir()
            with self.assertRaisesRegex(MODULE.InventoryInputError, "max_depth"):
                MODULE.inventory(root)

    def test_cli_returns_refusal_json_for_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "real").write_bytes(b"data")
            (root / "link").symlink_to(root / "real")
            process = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), "--approved-root", str(root)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(process.returncode, 2)
            self.assertEqual(json.loads(process.stdout)["status"], "refused")

    def test_ancestor_symlink_and_traversal_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            inside = base / "inside"
            outside = base / "outside"
            inside.mkdir()
            outside.mkdir()
            (outside / "child").mkdir()
            (inside / "alias").symlink_to(outside, target_is_directory=True)
            for relative in ("alias/child", "../outside/child"):
                with self.assertRaises(MODULE.InventoryInputError):
                    MODULE.inventory(inside, relative)

    def test_directory_entry_cap_refuses_before_unbounded_sort(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("a", "b", "c"):
                (root / name).mkdir()
            with (
                patch.object(MODULE, "MAX_ENTRIES", 2),
                self.assertRaisesRegex(MODULE.InventoryInputError, "max_entries"),
            ):
                MODULE.inventory(root)

    def test_regular_to_fifo_swap_refuses_without_blocking(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            os.mkfifo(root / "pipe")
            (root / "sample").write_bytes(b"sample")
            probe = """\
import importlib.util, json, os, sys
from pathlib import Path
from unittest.mock import patch
script=Path(sys.argv[1]); root=Path(sys.argv[2])
sys.path.insert(0, str(script.parent))
spec=importlib.util.spec_from_file_location('inventory_probe',script)
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
real_stat=os.stat; regular=real_stat(root/'sample')
def stale_stat(path,*args,**kwargs):
    if path=='pipe' and kwargs.get('dir_fd') is not None: return regular
    return real_stat(path,*args,**kwargs)
with patch.object(module.os,'stat',side_effect=stale_stat):
    try: module.inventory(root)
    except module.InventoryInputError as error:
        print(json.dumps({'status':'refused','reason':str(error)}))
        sys.exit(0)
sys.exit(1)
"""
            process = subprocess.run(
                [sys.executable, "-B", "-c", probe, str(SCRIPT), folder],
                capture_output=True,
                text=True,
                check=False,
                timeout=3,
            )
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(json.loads(process.stdout)["status"], "refused")


if __name__ == "__main__":
    unittest.main()
