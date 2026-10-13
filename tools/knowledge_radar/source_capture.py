"""Bounded local input for the radar's offline source parsers; no network I/O."""
from __future__ import annotations

import os
from pathlib import Path
import stat

from knowledge_radar.feed_profile_files import _open_directory


def read_capture(path: Path, maximum_bytes: int) -> bytes:
    """Read one regular capture without following symlinks or blocking on a FIFO."""
    path = Path(path).absolute()
    parent_fd = _open_directory(path.parent)
    try:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
        with os.fdopen(descriptor, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise ValueError('source_capture_regular_file_required')
            if info.st_size > maximum_bytes:
                raise ValueError('source_capture_byte_limit')
            body = stream.read(maximum_bytes + 1)
            if len(body) > maximum_bytes:
                raise ValueError('source_capture_byte_limit')
            return body
    finally:
        os.close(parent_fd)
