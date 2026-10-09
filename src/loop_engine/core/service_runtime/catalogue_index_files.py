"""File integrity and scoped durability for the existing disk search-index engine.

These helpers operate only on the index builder's owned paths. They are not
a separate engine or runtime. Closed data files and the marker are flushed
before directory entries and atomic rename; the final parent flush precedes
successful completion. The caller preserves built bytes and reports failure
if any durability operation fails. No machine-wide sync is used.
"""
from __future__ import annotations

import hashlib
import os
import stat


def file_digest(path):
    """Hash the file bytes with bounded reads; retain the index's existing digest format."""
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sync_index_path(path, *, directory=False):
    """Flush one owned regular file or directory; unsupported durability is an error."""
    if path.is_symlink():
        raise OSError("an index durability target is a symlink")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_DIRECTORY", 0) if directory else getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    try:
        mode = os.fstat(descriptor).st_mode
        if not (stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode)):
            raise OSError("an index durability target has the wrong file type")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def build_parent_chain(target):
    """Name the target parent through its closest existing ancestor before mkdir."""
    parents = [target.parent]
    while not parents[-1].exists():
        parents.append(parents[-1].parent)
    return parents


def commit_index_files(partial, target, names, marker_file, parents):
    """Flush completed files and parent entries, rename, then flush the target parent."""
    for name in names:
        sync_index_path(partial / name)
    sync_index_path(partial / marker_file)
    sync_index_path(partial, directory=True)
    for parent in parents:
        sync_index_path(parent, directory=True)
    os.rename(partial, target)
    sync_index_path(target.parent, directory=True)
