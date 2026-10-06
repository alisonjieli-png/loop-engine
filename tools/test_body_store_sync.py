"""A deferred body store write is made durable by flushing what it wrote, never the whole machine.

A store written with put(..., durable=False) is made durable by one later sync(). VolumeBodyStore.sync() calls
os.sync(), which flushes every file system of the machine; on the development machine a slow disk held test runs for
hours behind it (September 27, 2026). The three writers that defer (a catalogue release, a release bundle and the
licensed import store) now use ExactFlushVolumeBodyStore (src/loop_engine/core/service_runtime/catalogue_body_flush.py),
whose sync() flushes each object those writes created, then the folder that holds each name and the parent of any
folder they made, deepest first. VolumeBodyStore itself keeps its bytes, because native review catalogues pin
catalogue_packages.py. Each rule has a known-wrong control, the base store's os.sync() among them. Nothing here leaves
its temporary folder.
"""
from __future__ import annotations

import ast
import contextlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from loop_engine.core.service_runtime.catalogue_body_flush import ExactFlushVolumeBodyStore  # noqa: E402
from loop_engine.core.service_runtime.catalogue_packages import VolumeBodyStore, sha256_hex  # noqa: E402
from loop_engine.core.service_runtime.records import ServiceRuntimeError  # noqa: E402

REAL_OPEN, REAL_FSYNC = os.open, os.fsync
#: Where the rule below looks for body store writers: the package and the development tools, tests left out.
SCANNED = (ROOT / "src" / "loop_engine", ROOT / "tools")
#: These writers construct the adapter directly. Catalogue publication selects
#: it through the host factory and is exercised through that actual path below.
DEFERRING_WRITERS = ("src/loop_engine/core/service_runtime/catalogue_bundle.py", "tools/licensed_import/storage.py")


@contextlib.contextmanager
def recorded_flushes(fail=lambda path: False):
    """Every path os.fsync is called on while the block runs, in order. `fail` makes the flush of a path fail, and a
    call of os.sync() fails the test, because it would flush every file system of the machine."""
    opened, flushed = {}, []

    def opening(path, flags, *args, **kwargs):
        descriptor = REAL_OPEN(path, flags, *args, **kwargs)
        opened[descriptor] = os.fspath(path)
        return descriptor

    def flushing(descriptor):
        path = opened.get(descriptor, f"<descriptor {descriptor}>")
        if fail(path):
            raise OSError(5, "Input/output error", path)
        flushed.append(path)
        return REAL_FSYNC(descriptor)

    def whole_machine():
        raise AssertionError("os.sync() flushes every file system of the machine")

    with mock.patch.object(os, "open", opening), mock.patch.object(os, "fsync", flushing), \
            mock.patch.object(os, "sync", whole_machine, create=True):
        yield flushed


def deepest_first(paths):
    return sorted(paths, key=lambda path: (-path.count(os.sep), path))


def whole_machine_flush_problems(source: str, name: str) -> list:
    """A module that builds a write-enabled VolumeBodyStore and calls a sync() method would flush the whole machine."""
    tree = ast.parse(source, name)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    syncs = any(isinstance(node.func, ast.Attribute) and node.func.attr == "sync" and not node.args
                for node in calls)
    writers = [node.lineno for node in calls
               if isinstance(node.func, ast.Name) and node.func.id == "VolumeBodyStore"
               and any(keyword.arg == "writes_authorized"
                       and not (isinstance(keyword.value, ast.Constant) and keyword.value.value is False)
                       for keyword in node.keywords)]
    return [f"{name}:{line} builds a write-enabled VolumeBodyStore in a module that calls sync(); "
            "use ExactFlushVolumeBodyStore" for line in writers] if syncs else []


class ExactFlushTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix="body-store-sync-")
        self.root = Path(self.folder.name).resolve()
        self.store = ExactFlushVolumeBodyStore(str(self.root), writes_authorized=True)
        self.payloads = [b"first body\n", b"second body\n", b"third body\n"]

    def tearDown(self):
        self.folder.cleanup()

    def object_path(self, payload):
        return str(self.root / VolumeBodyStore.object_key(sha256_hex(payload)))

    def test_sync_flushes_each_written_object_then_its_folders_and_never_the_machine(self):
        with recorded_flushes() as flushed:
            for payload in self.payloads:
                self.store.put(payload, durable=False)
            self.assertEqual(flushed, [], "a deferred write flushed before sync()")
            self.store.sync()
        objects = sorted(self.object_path(payload) for payload in self.payloads)
        folders = {os.path.dirname(path) for path in objects} | {str(self.root / "sha256"), str(self.root)}
        self.assertEqual(flushed, objects + deepest_first(folders))
        self.assertTrue(all(path == str(self.root) or path.startswith(str(self.root) + os.sep) for path in flushed))
        reader = VolumeBodyStore(str(self.root))
        for payload in self.payloads:
            self.assertEqual(reader.read(sha256_hex(payload), len(payload)), payload)

    def test_a_second_sync_with_nothing_written_flushes_nothing(self):
        self.store.put(b"once\n", durable=False)
        with recorded_flushes() as flushed:
            self.store.sync()
            self.assertTrue(flushed)
            flushed.clear()
            self.store.sync()
        self.assertEqual(flushed, [])

    def test_an_object_already_present_is_not_flushed_again(self):
        self.store.put(b"present\n", durable=True)
        with recorded_flushes() as flushed:
            result = self.store.put(b"present\n", durable=False)
            self.store.sync()
        self.assertFalse(result["written"])
        self.assertEqual(flushed, [])

    def test_a_durable_write_flushes_its_bytes_then_every_folder_it_changed(self):
        with recorded_flushes() as flushed:
            self.store.put(b"durable\n", durable=True)
        folder = os.path.dirname(self.object_path(b"durable\n"))
        # The bytes are flushed through the temporary file whose hard link becomes the object.
        self.assertTrue(flushed[0].endswith(".partial"), flushed)
        self.assertEqual(flushed[1:], deepest_first({folder, str(self.root / "sha256"), str(self.root)}))
        # A second object in a new prefix folder changes that folder and sha256/, not the root.
        with recorded_flushes() as flushed:
            self.store.put(b"another durable body\n", durable=True)
        second = os.path.dirname(self.object_path(b"another durable body\n"))
        expected = {second} if second == folder else {second, str(self.root / "sha256")}
        self.assertEqual(flushed[1:], deepest_first(expected))

    def test_a_failed_flush_refuses_and_leaves_the_object_pending(self):
        self.store.put(b"pending\n", durable=False)
        target = self.object_path(b"pending\n")
        with recorded_flushes(fail=lambda path: path == target):
            with self.assertRaises(ServiceRuntimeError) as refused:
                self.store.sync()
        self.assertEqual(refused.exception.code, "body_store_write_failed")
        with recorded_flushes() as flushed:
            self.store.sync()
        self.assertEqual(flushed[0], target)

    def test_the_store_keeps_the_base_layout_rules_and_capabilities(self):
        base = VolumeBodyStore(str(self.root), writes_authorized=True)
        self.assertEqual(self.store.capabilities(), base.capabilities())
        with self.assertRaises(ServiceRuntimeError) as refused:
            ExactFlushVolumeBodyStore(str(self.root)).put(b"x")
        self.assertEqual(refused.exception.code, "body_store_writes_not_authorized")

    def test_known_wrong_the_base_store_flushes_the_whole_machine(self):
        base = VolumeBodyStore(str(self.root), writes_authorized=True)
        base.put(b"everything\n", durable=False)
        with recorded_flushes(), self.assertRaises(AssertionError):
            base.sync()

    def test_known_wrong_a_sync_that_skips_the_folders_is_found(self):
        class ObjectsOnly(ExactFlushVolumeBodyStore):
            def sync(self):
                with self._pending_lock:
                    for path in sorted(self._pending_objects):
                        descriptor = os.open(path, os.O_RDONLY)
                        try:
                            os.fsync(descriptor)
                        finally:
                            os.close(descriptor)
                    self._pending_objects.clear()
        store = ObjectsOnly(str(self.root), writes_authorized=True)
        with recorded_flushes() as flushed:
            store.put(self.payloads[0], durable=False)
            store.sync()
        self.assertNotEqual(flushed, [self.object_path(self.payloads[0])]
                            + deepest_first({os.path.dirname(self.object_path(self.payloads[0])),
                                             str(self.root / "sha256"), str(self.root)}))


class DeferringWriterTests(unittest.TestCase):
    def test_actual_catalogue_publication_flushes_its_destination(self):
        from loop_engine.core.service_runtime.catalogue_release_checks import Fixture
        with tempfile.TemporaryDirectory(prefix="publish-exact-flush-") as directory:
            case = Fixture(directory)
            payload = b"a new published body"
            target = str(case.root / "bodies" / VolumeBodyStore.object_key(sha256_hex(payload)))
            with recorded_flushes() as flushed:
                case.publish([case.line("one", payload.decode())])
            self.assertIn(target, flushed)
            changed = b"another published body"
            changed_target = str(case.root / "bodies" / VolumeBodyStore.object_key(sha256_hex(changed)))
            with mock.patch.object(ExactFlushVolumeBodyStore, "sync", return_value=None), recorded_flushes() as missing:
                case.publish([case.line("two", changed.decode())])
            self.assertNotIn(changed_target, missing, "removed-flush control must lose the publication durability predicate")

    def test_host_publication_factory_defers_and_flushes_only_its_written_paths(self):
        from loop_engine.core.service_runtime.catalogue_releases import CatalogueOperatorContext
        from loop_engine.core.service_runtime.records import ServiceRuntimeConfig
        from loop_engine.core.service_runtime.storage import ServiceCatalogBinding
        with tempfile.TemporaryDirectory(prefix="host-exact-flush-") as directory:
            root = Path(directory)
            binding = ServiceCatalogBinding(ServiceRuntimeConfig(str(root / "service.db"), writes_authorized=True))
            for ordinal, record in enumerate((None, {"record_type": "catalogue_body_store_engine/v1",
                                                     "engine": "service_volume_files"})):
                folder = root / str(ordinal)
                folder.mkdir()
                context = CatalogueOperatorContext(binding, str(folder), record)
                store = context.body_store(write=True)
                self.assertIsInstance(store, ExactFlushVolumeBodyStore)
                with recorded_flushes() as flushed:
                    stored = store.put(b"host deferred body", durable=False)
                    self.assertEqual(flushed, [])
                    store.sync()
                self.assertIn(str(folder / VolumeBodyStore.object_key(stored["digest"])), flushed)
                self.assertTrue(all(path == str(folder) or path.startswith(str(folder) + os.sep) for path in flushed))
                self.assertEqual(context.body_store().read(stored["digest"], stored["size_bytes"]), b"host deferred body")
            # Known-wrong control at the new factory boundary, not a substring
            # assertion that would forbid an otherwise valid storage adapter.
            with mock.patch("loop_engine.core.service_runtime.catalogue_body_flush.ExactFlushVolumeBodyStore",
                            VolumeBodyStore):
                wrong = CatalogueOperatorContext(binding, str(folder)).body_store(write=True)
                wrong.put(b"wrong host flush", durable=False)
                with recorded_flushes(), self.assertRaises(AssertionError):
                    wrong.sync()

    def test_no_module_builds_a_write_enabled_base_store_and_calls_sync(self):
        problems = []
        for folder in SCANNED:
            for path in sorted(folder.rglob("*.py")):
                relative = path.relative_to(ROOT).as_posix()
                if path.name.startswith("test_") or "__pycache__" in path.parts:
                    continue
                problems += whole_machine_flush_problems(path.read_text(encoding="utf-8"), relative)
        self.assertEqual(problems, [])

    def test_each_deferring_writer_builds_the_exact_flush_store_and_calls_sync(self):
        for name in DEFERRING_WRITERS:
            with self.subTest(writer=name):
                source = (ROOT / name).read_text(encoding="utf-8")
                self.assertIn("ExactFlushVolumeBodyStore(", source)
                self.assertIn(".sync()", source)

    def test_known_wrong_a_writer_back_on_the_base_store_is_found(self):
        name = "src/loop_engine/core/service_runtime/catalogue_bundle.py"
        source = (ROOT / name).read_text(encoding="utf-8")
        planted = source.replace("ExactFlushVolumeBodyStore(str((root", "VolumeBodyStore(str((root", 1)
        self.assertNotEqual(planted, source)
        self.assertEqual(len(whole_machine_flush_problems(planted, name)), 1)
        self.assertEqual(whole_machine_flush_problems(source, name), [])


if __name__ == "__main__":
    unittest.main()
