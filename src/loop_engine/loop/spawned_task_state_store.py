"""Durable compare-and-swap storage for Spawned Loop task checkpoints.

The store persists lifecycle metadata only. It never owns a Loop, executor,
coroutine, workspace, or provider. Active saved work is interpreted by
``SpawnedTaskManager`` and can only restore as interrupted work.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from .spawned_task_checkpoint import SpawnedTaskCheckpoint

try:
    import fcntl as _fcntl
except ImportError:  # pragma: no cover
    _fcntl = None


SPAWNED_TASK_STATE_STORE_SCHEMA = "spawned_task_state_store/v1"


class SpawnedTaskStateStoreError(RuntimeError):
    """Base error for Spawned task persistence."""


class SpawnedTaskStateNotFound(SpawnedTaskStateStoreError, KeyError):
    """No saved task matches the requested owner and task identity."""


class SpawnedTaskStateConflict(SpawnedTaskStateStoreError):
    """A create or compare-and-swap request used conflicting state."""


class SpawnedTaskStateIntegrityError(SpawnedTaskStateStoreError):
    """Saved state failed schema, identity, or digest validation."""


@dataclass(frozen=True)
class SpawnedTaskServices:
    """Optional services shared by one Spawned task manager."""

    runtime_memory: object = None
    context_artifacts: object = None
    state_store: "SpawnedTaskStateStore | None" = None

    def __post_init__(self) -> None:
        if self.runtime_memory is not None and any(not callable(getattr(
                self.runtime_memory, name, None))
                for name in ("write", "read", "search")):
            raise TypeError(
                "runtime_memory must implement write, read, and search")
        if self.context_artifacts is not None:
            from ..core.context_artifacts import ContextArtifactManager
            if not isinstance(self.context_artifacts, ContextArtifactManager):
                raise TypeError(
                    "context_artifacts must be a ContextArtifactManager")
        if (self.state_store is not None
                and not isinstance(self.state_store, SpawnedTaskStateStore)):
            raise TypeError("state_store must implement SpawnedTaskStateStore")

    @classmethod
    def compose(cls, services: "SpawnedTaskServices | None" = None, *,
                runtime_memory=None, context_artifacts=None
                ) -> "SpawnedTaskServices":
        if services is not None and (runtime_memory is not None
                                     or context_artifacts is not None):
            raise TypeError(
                "services cannot be combined with legacy service arguments")
        if services is not None:
            if not isinstance(services, cls):
                raise TypeError("services must be SpawnedTaskServices")
            return services
        return cls(runtime_memory, context_artifacts)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class StoredSpawnedTaskState:
    """One revisioned, digest-bound checkpoint owned by one Loop ID."""

    owner_loop_id: str
    checkpoint: SpawnedTaskCheckpoint
    store_revision: int = 0
    record_digest: str = ""
    schema_version: str = SPAWNED_TASK_STATE_STORE_SCHEMA

    def __post_init__(self) -> None:
        if not isinstance(self.owner_loop_id, str) or not self.owner_loop_id:
            raise SpawnedTaskStateIntegrityError(
                "stored Spawned task needs an owner Loop ID")
        if not isinstance(self.checkpoint, SpawnedTaskCheckpoint):
            raise SpawnedTaskStateIntegrityError(
                "stored Spawned task needs a typed checkpoint")
        if (not isinstance(self.store_revision, int)
                or isinstance(self.store_revision, bool)
                or self.store_revision < 0):
            raise SpawnedTaskStateIntegrityError(
                "store_revision must be a non-negative integer")
        if self.schema_version != SPAWNED_TASK_STATE_STORE_SCHEMA:
            raise SpawnedTaskStateIntegrityError(
                "unsupported Spawned task store schema")
        relationship = self.checkpoint.relationship
        if relationship.spawned_by_loop_id != self.owner_loop_id:
            raise SpawnedTaskStateIntegrityError(
                "checkpoint relationship does not name the owning Loop")
        prefix = self.owner_loop_id + ".spawned-task."
        if not str(self.checkpoint.task_id).startswith(prefix):
            raise SpawnedTaskStateIntegrityError(
                "checkpoint task ID does not belong to the owning Loop")
        digest = _sha256(_canonical_json(self._body()).encode("utf-8"))
        if self.record_digest and self.record_digest != digest:
            raise SpawnedTaskStateIntegrityError(
                "Spawned task state record digest does not match")
        object.__setattr__(self, "record_digest", digest)

    def _body(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "owner_loop_id": self.owner_loop_id,
            "owner_loop_id_digest": _sha256(
                self.owner_loop_id.encode("utf-8")),
            "task_id_digest": _sha256(
                str(self.checkpoint.task_id).encode("utf-8")),
            "store_revision": self.store_revision,
            "checkpoint": self.checkpoint.to_dict(),
        }

    def to_dict(self) -> dict:
        return {**self._body(), "record_digest": self.record_digest}

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, value: dict) -> "StoredSpawnedTaskState":
        expected = {"schema_version", "owner_loop_id",
                    "owner_loop_id_digest", "task_id_digest",
                    "store_revision", "checkpoint", "record_digest"}
        if not isinstance(value, dict) or set(value) != expected:
            raise SpawnedTaskStateIntegrityError(
                "Spawned task state record has an invalid shape")
        owner = str(value["owner_loop_id"])
        checkpoint = SpawnedTaskCheckpoint.from_dict(value["checkpoint"])
        if value["owner_loop_id_digest"] != _sha256(owner.encode("utf-8")):
            raise SpawnedTaskStateIntegrityError("owner Loop digest mismatch")
        if value["task_id_digest"] != _sha256(
                str(checkpoint.task_id).encode("utf-8")):
            raise SpawnedTaskStateIntegrityError("Spawned task digest mismatch")
        return cls(
            owner, checkpoint, value["store_revision"],
            str(value["record_digest"]), str(value["schema_version"]))

    @classmethod
    def from_json(cls, value: str) -> "StoredSpawnedTaskState":
        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise SpawnedTaskStateIntegrityError(
                "Spawned task state is not valid JSON") from exc
        return cls.from_dict(parsed)


@runtime_checkable
class SpawnedTaskStateStore(Protocol):
    """One revision-aware persistence boundary for Spawned task metadata."""

    def create(self, owner_loop_id: str, checkpoint: SpawnedTaskCheckpoint
               ) -> StoredSpawnedTaskState: ...

    def load(self, owner_loop_id: str, task_id: str
             ) -> StoredSpawnedTaskState: ...

    def load_owner(self, owner_loop_id: str
                   ) -> tuple[StoredSpawnedTaskState, ...]: ...

    def compare_and_swap(
            self, expected: StoredSpawnedTaskState,
            replacement: SpawnedTaskCheckpoint) -> StoredSpawnedTaskState: ...


_THREAD_LOCKS: dict[str, threading.RLock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


class LocalJsonSpawnedTaskStateStore:
    """Atomic local JSON storage beneath one explicit run-scoped root."""

    def __init__(self, root: str):
        if not isinstance(root, str) or not root.strip():
            raise ValueError("Spawned task state store needs an explicit root")
        self.root = Path(root).expanduser().resolve()
        self._owners = self.root / "owners"
        self._locks = self.root / "locks"
        self._owners.mkdir(parents=True, exist_ok=True)
        self._locks.mkdir(parents=True, exist_ok=True)
        self.process_locking_supported = _fcntl is not None

    def create(self, owner_loop_id: str, checkpoint: SpawnedTaskCheckpoint
               ) -> StoredSpawnedTaskState:
        state = StoredSpawnedTaskState(owner_loop_id, checkpoint)
        with self._locked(owner_loop_id, str(checkpoint.task_id)):
            path = self._path(owner_loop_id, str(checkpoint.task_id))
            if path.exists():
                raise SpawnedTaskStateConflict(
                    "Spawned task already has durable state")
            self._write_unlocked(path, state)
        return state

    def load(self, owner_loop_id: str, task_id: str
             ) -> StoredSpawnedTaskState:
        self._require_identity(owner_loop_id, task_id)
        with self._locked(owner_loop_id, task_id):
            return self._load_unlocked(owner_loop_id, task_id)

    def load_owner(self, owner_loop_id: str
                   ) -> tuple[StoredSpawnedTaskState, ...]:
        if not isinstance(owner_loop_id, str) or not owner_loop_id:
            raise ValueError("load_owner needs an owner Loop ID")
        directory = self._owner_directory(owner_loop_id)
        if not directory.exists():
            return ()
        states = []
        for path in directory.glob("*.json"):
            try:
                state = StoredSpawnedTaskState.from_json(
                    path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise SpawnedTaskStateIntegrityError(
                    f"saved Spawned task {path.name!r} is unreadable") from exc
            if state.owner_loop_id != owner_loop_id:
                raise SpawnedTaskStateIntegrityError(
                    "owner directory contains another Loop's task")
            if path != self._path(owner_loop_id, str(state.checkpoint.task_id)):
                raise SpawnedTaskStateIntegrityError(
                    "saved Spawned task filename identity does not match")
            states.append(state)
        return tuple(sorted(states, key=_task_order))

    def compare_and_swap(
            self, expected: StoredSpawnedTaskState,
            replacement: SpawnedTaskCheckpoint) -> StoredSpawnedTaskState:
        if not isinstance(expected, StoredSpawnedTaskState):
            raise TypeError("expected must be StoredSpawnedTaskState")
        if not isinstance(replacement, SpawnedTaskCheckpoint):
            raise TypeError("replacement must be SpawnedTaskCheckpoint")
        if replacement.task_id != expected.checkpoint.task_id:
            raise SpawnedTaskStateConflict(
                "replacement targets another Spawned task")
        next_state = StoredSpawnedTaskState(
            expected.owner_loop_id, replacement,
            expected.store_revision + 1)
        with self._locked(
                expected.owner_loop_id, str(replacement.task_id)):
            current = self._load_unlocked(
                expected.owner_loop_id, str(replacement.task_id))
            if (current.store_revision != expected.store_revision
                    or current.record_digest != expected.record_digest):
                raise SpawnedTaskStateConflict(
                    "Spawned task compare-and-swap used stale state")
            if current.checkpoint.checkpoint_digest == replacement.checkpoint_digest:
                raise SpawnedTaskStateConflict(
                    "replacement checkpoint did not change")
            self._write_unlocked(
                self._path(expected.owner_loop_id, str(replacement.task_id)),
                next_state)
        return next_state

    def object_path(self, owner_loop_id: str, task_id: str) -> Path:
        """Return the digest-only state path for backup and inspection."""
        self._require_identity(owner_loop_id, task_id)
        return self._path(owner_loop_id, task_id)

    def _owner_directory(self, owner_loop_id: str) -> Path:
        digest = _sha256(owner_loop_id.encode("utf-8"))
        return self._owners / digest[:2] / digest

    def _path(self, owner_loop_id: str, task_id: str) -> Path:
        return self._owner_directory(owner_loop_id) / (
            _sha256(task_id.encode("utf-8")) + ".json")

    def _lock_path(self, owner_loop_id: str, task_id: str) -> Path:
        digest = _sha256(f"{owner_loop_id}\0{task_id}".encode("utf-8"))
        return self._locks / f"{digest}.lock"

    @contextmanager
    def _locked(self, owner_loop_id: str, task_id: str):
        lock_path = self._lock_path(owner_loop_id, task_id)
        key = str(lock_path)
        with _THREAD_LOCKS_GUARD:
            local = _THREAD_LOCKS.setdefault(key, threading.RLock())
        with local:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
            try:
                if _fcntl is not None:
                    _fcntl.flock(descriptor, _fcntl.LOCK_EX)
                yield
            finally:
                if _fcntl is not None:
                    _fcntl.flock(descriptor, _fcntl.LOCK_UN)
                os.close(descriptor)

    def _load_unlocked(
            self, owner_loop_id: str, task_id: str) -> StoredSpawnedTaskState:
        path = self._path(owner_loop_id, task_id)
        try:
            state = StoredSpawnedTaskState.from_json(
                path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise SpawnedTaskStateNotFound(
                f"Spawned task {task_id!r} is unavailable") from exc
        except (OSError, ValueError) as exc:
            raise SpawnedTaskStateIntegrityError(
                "saved Spawned task failed validation") from exc
        if (state.owner_loop_id != owner_loop_id
                or str(state.checkpoint.task_id) != task_id):
            raise SpawnedTaskStateIntegrityError(
                "saved Spawned task identity does not match lookup")
        return state

    def _write_unlocked(
            self, path: Path, state: StoredSpawnedTaskState) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.stem}.", dir=str(path.parent))
        try:
            os.chmod(temporary_name, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(state.to_json().encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
            _fsync_directory(path.parent)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

    @staticmethod
    def _require_identity(owner_loop_id: str, task_id: str) -> None:
        if (not isinstance(owner_loop_id, str) or not owner_loop_id
                or not isinstance(task_id, str) or not task_id):
            raise ValueError("Spawned task lookup needs owner and task IDs")


def _task_order(state: StoredSpawnedTaskState) -> tuple[int, str]:
    value = str(state.checkpoint.task_id)
    match = re.search(r"\.spawned-task\.(\d+)$", value)
    return (int(match.group(1)) if match else 2 ** 63, value)


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def self_test() -> dict:
    """Run durability, integrity, CAS, loading, and manager integration checks."""
    from .spawned_task_state_store_checks import run_checks
    return run_checks()
