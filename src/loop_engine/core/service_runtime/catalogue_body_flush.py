"""The volume body store for writers: it flushes exactly the files and folders its own deferred writes changed.

Kind: engine variant behind the catalogue body store edge (catalogue_body_store/v1), with the storage layout, write
rules and capabilities of VolumeBodyStore unchanged. The three processes that write many bodies and flush once use
it: a catalogue release (catalogue_releases.py), a release bundle (catalogue_bundle.py) and the licensed import store
(tools/licensed_import/storage.py). VolumeBodyStore.sync() calls os.sync(), which flushes every file system of the
machine; on the development machine a slow disk held test runs for hours behind it (September 27, 2026). This store
records what each write with durable=False created, and its sync() flushes exactly those objects and then the
folders whose entries they changed, deepest first.

It is a module of its own, not a change to VolumeBodyStore, because catalogue_packages.py is a cited source of native
review catalogues whose reader refuses a cited file once its bytes change: the committed native calibration controls,
which every review of original packages loads, and candidate catalogues waiting for review. The flush moves into
VolumeBodyStore once those citations are anchored to a dedicated source.
"""
from __future__ import annotations

import os
import threading

from .catalogue_packages import VolumeBodyStore, sha256_hex
from .records import ServiceRuntimeError


class ExactFlushVolumeBodyStore(VolumeBodyStore):
    """VolumeBodyStore whose sync() flushes what this store's own deferred writes created, never the whole machine."""

    def __init__(self, root, **options):
        super().__init__(root, **options)
        self._pending_lock = threading.Lock()
        self._pending_objects = set()
        self._pending_folders = set()

    def _object_folders(self, payload):
        """The folders on the way to the object these bytes would be stored as, outermost first."""
        if not isinstance(payload, bytes):
            return []
        parts = self.object_key(sha256_hex(payload)).split("/")
        return [os.path.join(str(self.root), *parts[:depth]) for depth in range(1, len(parts))]

    def put(self, payload, *, expected_digest=None, durable=True):
        """Store bytes once under their digest, as VolumeBodyStore does, and note what the write changed.

        A durable write also flushes the parent of any folder it made, so a new prefix folder is durable too. A
        deferred write is recorded for the next sync(). An object that was already present was not written here and
        is not recorded.
        """
        folders = self._object_folders(payload)
        absent = [folder for folder in folders if not os.path.lexists(folder)]
        result = super().put(payload, expected_digest=expected_digest, durable=durable)
        if not result["written"]:
            return result
        holder = folders[-1]
        changed = {holder, *(os.path.dirname(folder) for folder in absent)}
        if durable:
            # The base write flushed the object's bytes and the folder that holds its name.
            for folder in _deepest_first(changed - {holder}):
                _sync_folder(folder)
        else:
            with self._pending_lock:
                self._pending_objects.add(os.path.join(holder, result["digest"]))
                self._pending_folders.update(changed)
        return result

    def sync(self):
        """Make every object written with durable=False durable before anything refers to it.

        Each recorded object is flushed, then each recorded folder, deepest first. An object that cannot be flushed
        refuses with body_store_write_failed and stays recorded, so a later sync() tries it again.
        """
        with self._pending_lock:
            objects = sorted(self._pending_objects)
            folders = _deepest_first(self._pending_folders)
        for path in objects:
            _sync_file(path)
        for folder in folders:
            _sync_folder(folder)
        with self._pending_lock:
            self._pending_objects.difference_update(objects)
            self._pending_folders.difference_update(folders)


def _deepest_first(folders):
    """Folders in the order to flush them: a folder before the folder that holds it."""
    return sorted(folders, key=lambda path: (-path.count(os.sep), path))


def _sync_file(path):
    """Flush one stored object to disk; an object that cannot be flushed is not durable, so it refuses."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        raise ServiceRuntimeError("body_store_write_failed",
                                  "a stored object could not be opened to flush it to disk") from None
    try:
        os.fsync(descriptor)
    except OSError:
        raise ServiceRuntimeError("body_store_write_failed", "a stored object could not be flushed to disk") from None
    finally:
        os.close(descriptor)


def _sync_folder(folder):
    """Flush one folder's entries as VolumeBodyStore does; a file system that cannot flush a folder is left as it is."""
    try:
        descriptor = os.open(folder, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)
