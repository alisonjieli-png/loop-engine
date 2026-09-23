"""Bytes an earlier run already fetched at a pinned commit, reused only when they are the very blob.

A file at an exact commit never changes, so a rerun need not ask GitHub for
it again. PinnedBlobCache indexes the quarantine of earlier run folders by
git blob identity, and the provenance those runs recorded for each item by
repository, commit and path. The source engine asks the cache only with the
blob identity that the tree it read in this run names, and the cache hands
back bytes only after hashing them again: a file whose bytes changed on
disk, or whose identity is not the one asked for, is never returned, and
the engine fetches it instead. Reused item facts are the facts of the fetch
that produced the bytes (its response digest, request digest and time), so
the provenance stays exact. The cache sends nothing and writes nothing.
"""
from __future__ import annotations

import json
from pathlib import Path

from .candidates import read_candidate_batch
from .provenance import GITHUB_ORIGIN
from .record_rules import LibraryRecordError, bytes_digest, git_blob_identity

#: The provenance fields of one fetch that a reused item carries unchanged.
FETCH_FACTS = ("source_digest", "source_size_bytes", "git_blob_sha", "fetch_digest", "fetched_at",
               "request_digest")


class PinnedBlobCache:
    """Earlier runs' verified bytes by git blob identity, and their item fetch facts by path."""

    def __init__(self) -> None:
        self._files: dict = {}
        self._facts: dict = {}
        self.folders: list = []
        self.hits = 0
        self.refused = 0
        self.skipped = 0

    @classmethod
    def from_run_folders(cls, folders) -> "PinnedBlobCache":
        cache = cls()
        for folder in folders:
            cache.add_run_folder(Path(folder))
        return cache

    def add_run_folder(self, folder: Path) -> None:
        quarantine = folder / "quarantine"
        if not quarantine.is_dir() or quarantine.is_symlink():
            raise LibraryRecordError("unsafe_quarantine", f"{folder} holds no quarantine folder")
        for path in sorted(quarantine.glob("??/*")):
            if path.is_file() and not path.is_symlink() and len(path.name) == 64:
                data = path.read_bytes()
                if bytes_digest(data) == path.name:
                    self._files.setdefault(git_blob_identity(data), path)
                else:
                    # Bytes that no longer hash to their own name are not evidence of anything.
                    self.skipped += 1
        for path in sorted((folder / "batches").glob("*.json")):
            batch = read_candidate_batch(json.loads(path.read_text(encoding="utf-8")))
            for candidate in batch["candidates"]:
                record = candidate["provenance"]
                if record["origin"] == GITHUB_ORIGIN:
                    key = (record["repository"], record["immutable_revision"], record["path"])
                    self._facts.setdefault(key, {field: record[field] for field in FETCH_FACTS})
        self.folders.append(str(folder))

    def blob(self, blob_sha: str) -> "bytes | None":
        """The bytes of this git blob, hashed again now; None when the cache does not hold them."""
        path = self._files.get(blob_sha)
        if path is None:
            return None
        try:
            data = path.read_bytes()
        except OSError:
            data = b""
        if git_blob_identity(data) != blob_sha or bytes_digest(data) != path.name:
            self.refused += 1
            return None
        self.hits += 1
        return data

    def item(self, repository: str, commit: str, path: str, blob_sha: str):
        """(bytes, fetch facts) of an item fetched before at this exact commit and blob, or None."""
        facts = self._facts.get((repository, commit, path))
        if facts is None or facts["git_blob_sha"] != blob_sha:
            return None
        data = self.blob(blob_sha)
        if data is None or bytes_digest(data) != facts["source_digest"]:
            return None
        return data, dict(facts)

    def describe(self) -> dict:
        return {"folders": list(self.folders), "blobs": len(self._files), "items": len(self._facts),
                "hits": self.hits, "refused": self.refused, "skipped": self.skipped}
