"""Content-addressed quarantine for fetched outside bytes.

Fetched bytes land here before any other stage reads them. Each file is
named by the SHA-256 digest of its content, written once with exclusive
creation and left read-only, and nothing in this component executes or
imports a quarantined file. Writing the same bytes twice is a no-op, and a
file whose bytes no longer hash to its name is refused when read. The
quarantine is local evidence for independent review, not a store of served
material, and it lives outside the repository.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .record_rules import LibraryRecordError, bytes_digest, digest_value


@dataclass(frozen=True)
class QuarantineEntry:
    digest: str
    size_bytes: int


class Quarantine:
    """One folder of read-only files named by their own digest."""

    def __init__(self, folder: Path) -> None:
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        if self.folder.is_symlink() or not self.folder.is_dir():
            raise LibraryRecordError("unsafe_quarantine", "the quarantine must be a real folder")

    def _path(self, digest: str) -> Path:
        digest_value(digest, "quarantine digest")
        return self.folder / digest[:2] / digest

    def put(self, data: bytes) -> QuarantineEntry:
        digest = bytes_digest(data)
        path = self._path(digest)
        path.parent.mkdir(exist_ok=True)
        if path.exists():
            if path.is_symlink() or bytes_digest(path.read_bytes()) != digest:
                raise LibraryRecordError("quarantine_corrupted", f"{digest} does not hold its own bytes")
            return QuarantineEntry(digest, len(data))
        temporary = path.with_name(digest + ".partial")
        with temporary.open("xb") as stream:
            stream.write(data)
        os.chmod(temporary, 0o400)
        os.replace(temporary, path)
        return QuarantineEntry(digest, len(data))

    def get(self, digest: str) -> bytes:
        path = self._path(digest)
        if path.is_symlink() or not path.is_file():
            raise LibraryRecordError("quarantine_missing", f"{digest} is not in quarantine")
        data = path.read_bytes()
        if bytes_digest(data) != digest:
            raise LibraryRecordError("quarantine_corrupted", f"{digest} does not hold its own bytes")
        return data

    def has(self, digest: str) -> bool:
        return self._path(digest).is_file()
