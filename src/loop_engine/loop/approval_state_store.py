"""Durable compare-and-swap storage for native effect approval state.

This module owns one typed persistence boundary and one local JSON
implementation. It does not decide approvals or execute effects.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .effect_approval import PendingApprovalState

try:
    import fcntl as _fcntl
except ImportError:  # pragma: no cover
    _fcntl = None


APPROVAL_STATE_STORE_SCHEMA = "approval_state_store/v1"


class ApprovalStateStoreError(RuntimeError):
    """Base error for approval state persistence."""


class ApprovalStateNotFound(ApprovalStateStoreError, KeyError):
    """The requested approval state is absent."""


class ApprovalStateConflict(ApprovalStateStoreError):
    """A compare-and-swap request used stale or conflicting state."""


class ApprovalStateIntegrityError(ApprovalStateStoreError):
    """Stored state failed its digest or identity check."""


@runtime_checkable
class ApprovalStateStore(Protocol):
    """One revision-aware durable state authority."""

    def create(self, state: "PendingApprovalState") -> "PendingApprovalState": ...

    def load(self, request_id: str) -> "PendingApprovalState": ...

    def compare_and_swap(
            self, expected: "PendingApprovalState",
            replacement: "PendingApprovalState") -> "PendingApprovalState": ...


_PROCESS_LOCKS: dict[str, threading.RLock] = {}
_PROCESS_LOCKS_GUARD = threading.Lock()


class LocalJsonApprovalStateStore:
    """Atomic digest-addressed JSON state under one explicit local root."""

    def __init__(self, root: str):
        if not isinstance(root, str) or not root.strip():
            raise ValueError("approval state store needs an explicit root")
        self.root = Path(root).expanduser().resolve()
        self._objects = self.root / "objects"
        self._locks = self.root / "locks"
        self._objects.mkdir(parents=True, exist_ok=True)
        self._locks.mkdir(parents=True, exist_ok=True)
        self.process_locking_supported = _fcntl is not None

    def create(self, state: "PendingApprovalState") -> "PendingApprovalState":
        self._require_state(state)
        with self._locked(state.request.request_id):
            path = self._path(state.request.request_id)
            if path.exists():
                raise ApprovalStateConflict(
                    "approval request id already has durable state")
            self._write_unlocked(path, state)
        return state

    def load(self, request_id: str) -> "PendingApprovalState":
        self._require_request_id(request_id)
        with self._locked(request_id):
            return self._load_unlocked(request_id)

    def compare_and_swap(
            self, expected: "PendingApprovalState",
            replacement: "PendingApprovalState") -> "PendingApprovalState":
        self._require_state(expected)
        self._require_state(replacement)
        if expected.request.request_id != replacement.request.request_id:
            raise ApprovalStateConflict(
                "replacement targets a different approval request")
        if replacement.state_revision != expected.state_revision + 1:
            raise ApprovalStateConflict(
                "replacement must advance exactly one state revision")
        request_id = expected.request.request_id
        with self._locked(request_id):
            current = self._load_unlocked(request_id)
            if (current.state_revision != expected.state_revision
                    or not _same_state(current, expected)):
                raise ApprovalStateConflict(
                    "approval compare-and-swap used stale state")
            self._write_unlocked(self._path(request_id), replacement)
        return replacement

    def object_path(self, request_id: str) -> Path:
        """Return the digest-safe path for inspection and backup tooling."""
        return self._path(request_id)

    def _path(self, request_id: str) -> Path:
        digest = _request_id_digest(request_id)
        return self._objects / digest[:2] / f"{digest}.json"

    def _lock_path(self, request_id: str) -> Path:
        return self._locks / f"{_request_id_digest(request_id)}.lock"

    @contextmanager
    def _locked(self, request_id: str):
        key = str(self._lock_path(request_id))
        with _PROCESS_LOCKS_GUARD:
            local_lock = _PROCESS_LOCKS.setdefault(key, threading.RLock())
        with local_lock:
            descriptor = os.open(
                self._lock_path(request_id), os.O_CREAT | os.O_RDWR, 0o600)
            try:
                if _fcntl is not None:
                    _fcntl.flock(descriptor, _fcntl.LOCK_EX)
                yield
            finally:
                if _fcntl is not None:
                    _fcntl.flock(descriptor, _fcntl.LOCK_UN)
                os.close(descriptor)

    def _load_unlocked(self, request_id: str) -> "PendingApprovalState":
        path = self._path(request_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ApprovalStateNotFound(
                f"approval state {request_id!r} is unavailable") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ApprovalStateIntegrityError(
                "approval state is unreadable") from exc
        if not isinstance(payload, dict):
            raise ApprovalStateIntegrityError(
                "approval state envelope must be an object")
        if payload.get("record_type") != APPROVAL_STATE_STORE_SCHEMA:
            raise ApprovalStateIntegrityError(
                "approval state store schema is unsupported")
        if payload.get("request_id_digest") != _request_id_digest(request_id):
            raise ApprovalStateIntegrityError(
                "approval state filename identity does not match")
        state_body = payload.get("state")
        if not isinstance(state_body, dict):
            raise ApprovalStateIntegrityError(
                "approval state envelope has no state object")
        state_json = _canonical_json(state_body)
        if payload.get("state_digest") != _sha256(state_json.encode("utf-8")):
            raise ApprovalStateIntegrityError(
                "approval state content digest does not match")
        from .effect_approval import PendingApprovalState
        try:
            state = PendingApprovalState.from_dict(state_body)
        except (KeyError, TypeError, ValueError) as exc:
            raise ApprovalStateIntegrityError(
                "stored approval state failed validation") from exc
        if state.request.request_id != request_id:
            raise ApprovalStateIntegrityError(
                "stored approval request id does not match lookup")
        return state

    def _write_unlocked(self, path: Path,
                        state: "PendingApprovalState") -> None:
        state_body = state.to_dict()
        state_json = _canonical_json(state_body)
        payload = _canonical_json({
            "record_type": APPROVAL_STATE_STORE_SCHEMA,
            "request_id_digest": _request_id_digest(
                state.request.request_id),
            "state_digest": _sha256(state_json.encode("utf-8")),
            "state": state_body,
        }).encode("utf-8")
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.stem}.", dir=str(path.parent))
        try:
            os.chmod(temporary_name, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
            _fsync_directory(path.parent)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

    @staticmethod
    def _require_state(state: object) -> None:
        from .effect_approval import PendingApprovalState
        if not isinstance(state, PendingApprovalState):
            raise TypeError("approval state store needs PendingApprovalState")

    @staticmethod
    def _require_request_id(request_id: str) -> None:
        if not isinstance(request_id, str) or not request_id:
            raise ValueError("approval state lookup needs request_id")


def _request_id_digest(request_id: str) -> str:
    if not isinstance(request_id, str) or not request_id:
        raise ValueError("approval request id cannot be empty")
    return _sha256(request_id.encode("utf-8"))


def _same_state(left: "PendingApprovalState",
                right: "PendingApprovalState") -> bool:
    return _sha256(left.to_json().encode("utf-8")) == _sha256(
        right.to_json().encode("utf-8"))


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def self_test() -> dict:
    """Run durable restart, conflict, concurrency, and integrity checks."""
    from .approval_state_store_checks import run_checks
    return run_checks()
