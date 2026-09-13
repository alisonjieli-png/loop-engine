"""Reference mirroring must exclude ambient state and refuse hostile archives."""

import hashlib
import io
import json
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

from embodiment_lab.reference_sources import prepare, snapshot
from embodiment_lab.storage import write_new


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="embodiment-reference-test-")
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_committed_source_is_mirrored_without_dirty_or_runtime_data(self):
        source = self.root / "source"
        source.mkdir()

        def git(*args):
            return subprocess.run(
                ["git", *args], cwd=source, capture_output=True, text=True, check=True
            )

        git("init", "-q")
        git("config", "user.email", "fixture@example.invalid")
        git("config", "user.name", "Reference fixture")
        (source / "keep.py").write_text("COMMITTED = True\n")
        (source / ".env").write_text("EXAMPLE=fixture-only\n")
        (source / "state.db").write_text("fixture runtime state")
        git("add", "keep.py", ".env", "state.db")
        git("commit", "-qm", "fixture")
        (source / "keep.py").write_text("DIRTY = True\n")
        manifest = snapshot(source, self.root / "snapshot")
        self.assertFalse(manifest["dirty_work_included"])
        self.assertIn("keep.py", manifest["dirty_state_at_snapshot"])
        self.assertEqual([f["path"] for f in manifest["files"]], ["keep.py"])
        prepared = prepare(self.root / "snapshot", self.root / "prepared")
        self.assertFalse(prepared["executed"])
        self.assertEqual(
            (self.root / "prepared/keep.py").read_text(), "COMMITTED = True\n"
        )
        self.assertFalse((self.root / "prepared/.env").exists())
        with self.assertRaises(FileExistsError):
            prepare(self.root / "snapshot", self.root / "prepared")

    def make_archive(self, name, symlink=False):
        reference = self.root / "reference"
        reference.mkdir()
        archive = reference / "source.tar.gz"
        with tarfile.open(archive, "w:gz") as stream:
            member = tarfile.TarInfo(name)
            body = b"fixture"
            if symlink:
                member.type, member.linkname = tarfile.SYMTYPE, "../../escape"
                stream.addfile(member)
            else:
                member.size = len(body)
                stream.addfile(member, io.BytesIO(body))
        write_new(
            reference / "provenance.json",
            {
                "record_type": "embodiment_reference_source/v1",
                "archive": "source.tar.gz",
                "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "revision": None,
                "files": [
                    {
                        "path": name,
                        "bytes": 7,
                        "sha256": hashlib.sha256(b"fixture").hexdigest(),
                    }
                ],
            },
        )
        return reference

    def test_traversal_refused_before_output_directory_exists(self):
        reference = self.make_archive("../escape")
        with self.assertRaises(ValueError):
            prepare(reference, self.root / "out")
        self.assertFalse((self.root / "out").exists())
        self.assertFalse((self.root / "escape").exists())

    def test_symlink_member_refused_before_extraction(self):
        reference = self.make_archive("link", True)
        with self.assertRaises(ValueError):
            prepare(reference, self.root / "out")
        self.assertFalse((self.root / "out").exists())

    def test_archive_or_member_drift_refused(self):
        reference = self.make_archive("good.py")
        path = reference / "provenance.json"
        manifest = json.loads(path.read_text())
        manifest["files"][0]["sha256"] = "0" * 64
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "digest"):
            prepare(reference, self.root / "out")
        self.assertFalse((self.root / "out").exists())

    def test_foreign_source_cannot_be_prepared_inside_product_tree(self):
        reference = self.make_archive("good.py")
        repository = Path(__file__).resolve().parents[3]
        with self.assertRaisesRegex(ValueError, "outside Loop Engine"):
            prepare(reference, repository / "embodiments/should-not-exist")
        self.assertFalse((repository / "embodiments/should-not-exist").exists())
