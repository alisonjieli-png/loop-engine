"""Index publication flushes only its own files and directories, with explicit failures."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

from loop_engine.core.service_runtime import catalogue_disk_index as index
from loop_engine.core.service_runtime import catalogue_index_files as index_files
from loop_engine.core.service_runtime.catalogue_index_checks import _entries, _schema
from loop_engine.core.service_runtime.records import ServiceRuntimeError


@contextlib.contextmanager
def recorded_io(*, fail_flush=None, fail_rename=False):
    """Record actual scoped flushes and reject a global flush before it reaches the kernel."""
    original_open, original_close = os.open, os.close
    original_fsync, original_rename = os.fsync, os.rename
    descriptors, events = {}, []
    flush_count = 0

    def opening(path, flags, *args, **kwargs):
        descriptor = original_open(path, flags, *args, **kwargs)
        descriptors[descriptor] = Path(path)
        return descriptor

    def closing(descriptor):
        descriptors.pop(descriptor, None)
        return original_close(descriptor)

    def flushing(descriptor):
        nonlocal flush_count
        flush_count += 1
        path = descriptors[descriptor]
        kind = "directory" if stat.S_ISDIR(os.fstat(descriptor).st_mode) else "file"
        events.append(("flush", kind, path))
        if flush_count == fail_flush:
            raise OSError("injected scoped flush failure")
        return original_fsync(descriptor)

    def renaming(source, target):
        events.append(("rename", Path(source), Path(target)))
        if fail_rename:
            raise OSError("injected atomic rename failure")
        return original_rename(source, target)

    with mock.patch.object(os, "open", opening), mock.patch.object(os, "close", closing), \
            mock.patch.object(os, "fsync", flushing), mock.patch.object(os, "rename", renaming), \
            mock.patch.object(os, "sync", side_effect=AssertionError("global sync forbidden"), create=True):
        yield events


class IndexDurabilityTests(unittest.TestCase):
    def test_build_never_flushes_the_whole_machine(self):
        with tempfile.TemporaryDirectory() as temporary, recorded_io() as events:
            target = Path(temporary) / "index"
            self.assertEqual(index.build_disk_index(target, _entries(3), _schema()), target)
            self.assertTrue(any(event[0] == "flush" for event in events))

    def assert_complete_order(self, events, target, anchor):
        marker = json.loads((target / index.MARKER_FILE).read_text())
        rename = next(event for event in events if event[0] == "rename")
        partial = rename[1]
        expected = [("flush", "file", partial / name) for name in sorted(marker["files"])]
        expected.append(("flush", "file", partial / index.MARKER_FILE))
        expected.append(("flush", "directory", partial))
        parent = target.parent
        while True:
            expected.append(("flush", "directory", parent))
            if parent == anchor:
                break
            parent = parent.parent
        expected.extend([("rename", partial, target), ("flush", "directory", target.parent)])
        self.assertEqual(events, expected)
        self.assertFalse(partial.exists())
        self.assertEqual(index.DiskIndex(target, verify_files=True).size, 3)
        self.assertEqual(marker["entries"], 3)
        for name, expected_digest in marker["files"].items():
            self.assertEqual(hashlib.sha256((target / name).read_bytes()).hexdigest(), expected_digest)

    def test_every_file_marker_and_new_parent_is_flushed_in_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            anchor = Path(temporary)
            target = anchor / "first" / "second" / "index"
            with recorded_io() as events:
                index.build_disk_index(target, _entries(3), _schema())
            self.assert_complete_order(events, target, anchor)

    def test_database_commit_and_close_precede_durability(self):
        original_connect = index.sqlite3.connect
        original_sync = index_files.sync_index_path
        database_events = []

        class Connection:
            def __init__(self, *args, **kwargs):
                self.connection = original_connect(*args, **kwargs)

            def __getattr__(self, name):
                return getattr(self.connection, name)

            def commit(self):
                self.connection.commit()
                database_events.append("committed")

            def close(self):
                self.connection.close()
                database_events.append("closed")

        def after_close(path, **kwargs):
            self.assertEqual(database_events, ["committed", "closed"])
            return original_sync(path, **kwargs)

        with tempfile.TemporaryDirectory() as temporary, recorded_io(), \
                mock.patch.object(index.sqlite3, "connect", Connection), \
                mock.patch.object(index_files, "sync_index_path", after_close):
            index.build_disk_index(Path(temporary) / "index", _entries(3), _schema())
        self.assertEqual(database_events, ["committed", "closed"])

    def test_an_existing_parent_stops_the_ancestor_flush_walk(self):
        with tempfile.TemporaryDirectory() as temporary:
            anchor = Path(temporary) / "existing"
            anchor.mkdir()
            target = anchor / "index"
            with recorded_io() as events:
                index.build_disk_index(target, _entries(3), _schema())
            self.assert_complete_order(events, target, anchor)

    def test_every_failed_flush_refuses_completion_and_keeps_built_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "first" / "second" / "index"
            with recorded_io() as events:
                index.build_disk_index(target, _entries(3), _schema())
            flushes = sum(event[0] == "flush" for event in events)
        for failure in range(1, flushes + 1):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary) / "first" / "second" / "index"
                with recorded_io(fail_flush=failure) as events, self.assertRaises(ServiceRuntimeError) as caught:
                    index.build_disk_index(target, _entries(3), _schema())
                self.assertEqual(caught.exception.code, "search_index_unavailable")
                self.assertIn("retained", str(caught.exception))
                renamed = any(event[0] == "rename" for event in events)
                self.assertEqual(target.exists(), renamed)
                partials = list(target.parent.glob(".index.partial-*"))
                self.assertEqual(len(partials), 0 if renamed else 1)
                retained = target if renamed else partials[0]
                marker = json.loads((retained / index.MARKER_FILE).read_text())
                for name, expected in marker["files"].items():
                    self.assertEqual(hashlib.sha256((retained / name).read_bytes()).hexdigest(), expected)
                self.assertEqual(sum(event[0] == "flush" for event in events), failure)

    def test_failed_rename_keeps_the_flushed_partial_and_does_not_flush_a_published_parent(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "index"
            with recorded_io(fail_rename=True) as events, self.assertRaises(ServiceRuntimeError):
                index.build_disk_index(target, _entries(3), _schema())
            self.assertFalse(target.exists())
            self.assertEqual(events[-1][0], "rename")
            partials = list(target.parent.glob(".index.partial-*"))
            self.assertEqual(len(partials), 1)
            self.assertTrue((partials[0] / index.MARKER_FILE).is_file())

    def test_missing_durability_and_directory_only_durability_are_detected(self):
        original = index_files.sync_index_path

        def files_only(path, *, directory=False):
            if not directory:
                original(path)

        def directories_only(path, *, directory=False):
            if directory:
                original(path, directory=True)

        for wrong in (lambda path, **kwargs: None, files_only, directories_only):
            result = unittest.TestResult()
            with mock.patch.object(index_files, "sync_index_path", wrong):
                type(self)("test_every_file_marker_and_new_parent_is_flushed_in_order").run(result)
            self.assertEqual(len(result.failures), 1)
            self.assertEqual(result.errors, [])

    def test_existing_and_symlink_targets_are_refused_before_effects(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            existing = root / "existing"
            existing.mkdir()
            dangling = root / "dangling"
            dangling.symlink_to(root / "missing", target_is_directory=True)
            for target in (existing, dangling, Path("relative-index")):
                with self.subTest(target=target), recorded_io() as events, self.assertRaises(ServiceRuntimeError):
                    index.build_disk_index(target, _entries(3), _schema())
                self.assertEqual(events, [])
            self.assertTrue(dangling.is_symlink())
            self.assertFalse((root / "missing").exists())

    def test_flush_refuses_symlinks_and_the_wrong_object_type(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            file = root / "file"
            file.write_bytes(b"unchanged")
            link = root / "link"
            link.symlink_to(file)
            for path, directory in ((link, False), (file, True), (root, False)):
                with self.subTest(path=path, directory=directory), recorded_io() as events, self.assertRaises(OSError):
                    index_files.sync_index_path(path, directory=directory)
                self.assertEqual(events, [])
            self.assertEqual(file.read_bytes(), b"unchanged")


if __name__ == "__main__":
    unittest.main()
