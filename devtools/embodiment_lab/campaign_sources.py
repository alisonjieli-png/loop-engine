"""Content identities for the declared inputs of an experiment.

These passive records are persisted by CampaignProjection. They do not copy
source bodies or create another artifact store. Host preparation freezes the
records; a trial checks them again before and after using its source inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat

from loop_engine.core.adaptive_practitioner_source import _open_source

from .systematic_records import digest


class SourceIdentityError(ValueError):
    """Declared source contents cannot be frozen or no longer match."""


@dataclass(frozen=True)
class TaskSourceSnapshot:
    """Portable content identities, never source content or execution authority."""

    roots: tuple[str, ...]
    entries: tuple[tuple[str, str, int, str], ...]
    version: str = "1.0.0"

    def __post_init__(self):
        if self.version != "1.0.0":
            raise SourceIdentityError("unsupported source snapshot version")
        roots = tuple(self.roots)
        entries = tuple(tuple(item) for item in self.entries)
        paths = []
        for path, kind, size, value in entries:
            if (not isinstance(path, str) or not path
                    or Path(path).is_absolute() or ".." in Path(path).parts):
                raise SourceIdentityError("source identity needs a confined relative path")
            if kind not in ("file", "directory") or type(size) is not int or size < 0:
                raise SourceIdentityError("invalid source identity kind or byte count")
            if (not isinstance(value, str) or len(value) != 64
                    or any(character not in "0123456789abcdef" for character in value)):
                raise SourceIdentityError("source identity needs an exact content digest")
            paths.append(path)
        if len(set(paths)) != len(paths) or tuple(sorted(entries)) != entries:
            raise SourceIdentityError("source identities must be unique and sorted")
        if (tuple(sorted(set(roots))) != roots
                or any(root not in paths for root in roots)):
            raise SourceIdentityError("declared source roots must be present and unique")
        object.__setattr__(self, "roots", roots)
        object.__setattr__(self, "entries", entries)

    def to_dict(self):
        return {"record_type": "task_source_snapshot/v1", "version": self.version,
                "roots": list(self.roots), "entries": [list(item) for item in self.entries]}

    @property
    def content_digest(self):
        return digest(self.to_dict())

    @classmethod
    def from_dict(cls, value):
        if (not isinstance(value, dict)
                or set(value) != {"record_type", "version", "roots", "entries"}
                or value["record_type"] != "task_source_snapshot/v1"):
            raise SourceIdentityError("invalid source snapshot record")
        return cls(tuple(value["roots"]), tuple(value["entries"]), value["version"])


def _stable_file_identity(path, cache):
    with os.fdopen(_open_source(path), "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise SourceIdentityError("declared input is not a regular file")
        key = (before.st_dev, before.st_ino, before.st_size,
               before.st_mtime_ns, before.st_ctime_ns)
        value = cache.get(key) if cache is not None else None
        if value is None:
            hasher = hashlib.sha256()
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(block)
            value = hasher.hexdigest()
        after = os.fstat(stream.fileno())
        current = path.stat(follow_symlinks=False)
        identity = lambda item: (item.st_dev, item.st_ino, item.st_size,
                                 item.st_mtime_ns, item.st_ctime_ns)
        if key != identity(after) or key != identity(current):
            raise SourceIdentityError("declared input changed while it was being read")
        if cache is not None:
            cache[key] = value
        return before.st_size, value


def snapshot_task_sources(task_directory, task_root, *, cache=None):
    """Hash all declared inputs, including directory membership and hidden files.

    A declared root may resolve to another location inside the admitted task
    database. Nested symbolic links and special files refuse. The cache is
    optional and belongs only to one host preparation operation.
    """
    task_root = Path(task_root).resolve(strict=True)
    task_directory = Path(task_directory).resolve(strict=True)
    if not task_directory.is_relative_to(task_root):
        raise SourceIdentityError("task directory escapes the admitted database")
    descriptor = task_directory / "task.json"
    with os.fdopen(_open_source(descriptor), "r") as source:
        declaration = json.load(source)
    paths = [descriptor, task_directory / "task.md"]
    for relative in declaration.get("attachments", ()):
        candidate = (task_directory / relative).resolve(strict=True)
        if not candidate.is_relative_to(task_directory):
            raise SourceIdentityError("attachment escapes its task directory")
        paths.append(candidate)
    if declaration.get("data_path"):
        paths.append((task_directory / declaration["data_path"]).resolve(strict=True))
    records = {}
    roots = set()

    def visit(path):
        relative = path.relative_to(task_root).as_posix()
        if relative in records:
            return
        info = path.stat(follow_symlinks=False)
        if stat.S_ISLNK(info.st_mode):
            raise SourceIdentityError("nested source symbolic links are not admitted")
        if stat.S_ISDIR(info.st_mode):
            descriptor = _open_source(path, directory=True)
            try:
                names = sorted(os.listdir(descriptor))
                records[relative] = (relative, "directory", 0, digest(names))
                for name in names:
                    visit(path / name)
                if names != sorted(os.listdir(descriptor)):
                    raise SourceIdentityError("source directory membership changed during inspection")
            finally:
                os.close(descriptor)
        elif stat.S_ISREG(info.st_mode):
            size, value = _stable_file_identity(path, cache)
            records[relative] = (relative, "file", size, value)
        else:
            raise SourceIdentityError("special files are not admitted as experiment input")

    for path in paths:
        if not path.is_relative_to(task_root):
            raise SourceIdentityError("source escapes the admitted task database")
        roots.add(path.relative_to(task_root).as_posix())
        visit(path)
    return TaskSourceSnapshot(tuple(sorted(roots)), tuple(sorted(records.values())))


def verify_task_sources(task_directory, task_root, expected):
    if not isinstance(expected, TaskSourceSnapshot):
        raise TypeError("source verification needs a typed snapshot")
    observed = snapshot_task_sources(task_directory, task_root)
    if observed != expected:
        raise SourceIdentityError("frozen task source contents changed")
    return observed
