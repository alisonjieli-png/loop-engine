"""Passive v2 records and local checkpoint I/O for overnight_queue.

This is the existing operator queue's state boundary, not an execution engine
or a managed-record registry. The solver and run_checkpoint retain ownership of
task execution and surviving artifacts. Like fly_reconcile_remote, reservations
are fsynced before dispatch and unresolved attempts cannot be replayed.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import tempfile

STATE_VERSION = "overnight_queue_state/v2"
STATE_FILENAME = "overnight-queue.json"
LOCK_FILENAME = ".overnight-queue.lock"
MAX_RECORD_BYTES = 4 * 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_TASK_BYTES = 4 * 1024 * 1024


class QueueRefusal(ValueError):
    """Bounded operator error code; raw task and provider text is not a code."""


def require(condition, code):
    if not condition:
        raise QueueRefusal(code)


def integer(value, *, minimum=0):
    return type(value) is int and value >= minimum


def number(value, *, minimum=0):
    try:
        return type(value) in (int, float) and math.isfinite(value) and value >= minimum
    except OverflowError:
        return False


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def bytes_digest(raw):
    return hashlib.sha256(raw).hexdigest()


def exact_fields(value, names):
    require(type(value) is dict and set(value) == set(names), "state_fields_invalid")


def parse(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, "duplicate_record_key")
            value[key] = item
        return value
    try:
        return json.loads(raw, object_pairs_hook=unique,
                          parse_constant=lambda _value: require(False, "nonfinite_record"))
    except (UnicodeError, ValueError, RecursionError) as error:
        if isinstance(error, QueueRefusal):
            raise
        raise QueueRefusal("record_invalid_json") from None


def plain_path(path):
    path = Path(path).expanduser().absolute()
    require(path.resolve() == path, "symlink_or_parent_path_refused")
    return path


def read_bytes(path, maximum=MAX_RECORD_BYTES):
    path = plain_path(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as handle:
            require(stat.S_ISREG(os.fstat(handle.fileno()).st_mode), "record_not_regular")
            raw = handle.read(maximum + 1)
        require(len(raw) <= maximum, "record_too_large")
        return raw
    except OSError:
        raise QueueRefusal("record_unavailable") from None


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save_state(path, state):
    """Atomic replacement plus file and parent-directory durability under the lock."""
    validate_state(state)
    path = plain_path(path)
    raw = encode(state)
    require(len(raw) <= MAX_RECORD_BYTES, "state_too_large")
    fd, temporary = tempfile.mkstemp(prefix=".overnight-pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def queue_lock(root):
    """Local POSIX single writer; the caller passes this descriptor to its child.

    Close, never LOCK_UN: the child's inherited open-file description must keep
    the lock when its parent is interrupted. This is not a distributed lock.
    """
    root = plain_path(root)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(root.is_dir(), "runs_root_not_directory")
    fd = os.open(root / LOCK_FILENAME, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == os.getuid(),
                "queue_lock_not_owned_regular_file")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise QueueRefusal("queue_writer_active") from None
        yield fd
    finally:
        os.close(fd)


@dataclass(frozen=True)
class QueueLimits:
    max_calls_per_task: int
    queue_call_budget: int
    max_passes: int
    task_timeout: float
    grace_seconds: float
    queue_timeout: float

    def __post_init__(self):
        require(all(integer(value, minimum=1) for value in (
            self.max_calls_per_task, self.queue_call_budget, self.max_passes)), "positive_call_limits_required")
        require(all(number(value, minimum=0.001) for value in (
            self.task_timeout, self.queue_timeout)) and number(self.grace_seconds), "wall_limits_invalid")


@dataclass(frozen=True)
class QueueBinding:
    manifest: str
    manifest_sha256: str
    tasks: tuple
    runs_root: str
    workspace_root: str
    python: str
    execution_cwd: str
    limits: QueueLimits
    record_type: str = "overnight_queue_binding/v2"

    def to_dict(self):
        value = asdict(self)
        value["tasks"] = list(value["tasks"])
        return value


def validate_binding(value):
    exact_fields(value, ("record_type", "manifest", "manifest_sha256", "tasks", "runs_root",
                         "workspace_root", "python", "execution_cwd", "limits"))
    require(value["record_type"] == "overnight_queue_binding/v2", "binding_version_unsupported")
    for key in ("manifest", "runs_root", "workspace_root", "python", "execution_cwd"):
        require(type(value[key]) is str and Path(value[key]).is_absolute(), "binding_path_invalid")
    require(type(value["manifest_sha256"]) is str and len(value["manifest_sha256"]) == 64
            and all(ch in "0123456789abcdef" for ch in value["manifest_sha256"]), "binding_digest_invalid")
    exact_fields(value["limits"], QueueLimits.__dataclass_fields__)
    QueueLimits(**value["limits"])
    tasks = value["tasks"]
    require(type(tasks) is list and tasks, "tasks_required")
    seen = set()
    for task in tasks:
        exact_fields(task, ("path", "sha256", "size_bytes"))
        require(type(task["path"]) is str and Path(task["path"]).is_absolute() and task["path"] not in seen,
                "duplicate_or_invalid_task")
        require(type(task["sha256"]) is str and len(task["sha256"]) == 64
                and all(ch in "0123456789abcdef" for ch in task["sha256"])
                and integer(task["size_bytes"], minimum=1) and task["size_bytes"] <= MAX_TASK_BYTES,
                "task_binding_invalid")
        seen.add(task["path"])


def new_state(binding, now):
    value = binding.to_dict()
    state = {"record_type": STATE_VERSION, "binding": value, "binding_sha256": digest(value),
             "created_at": now, "deadline": now + binding.limits.queue_timeout,
             "updated_at": now, "revision": 1, "attempts": []}
    validate_state(state)
    return state


def calls_allocated(state):
    """Conservative authority consumed, not a claim of provider-reported usage."""
    return sum(attempt["allocation"] for attempt in state["attempts"])


def validate_state(state, binding=None):
    require(type(state) is dict and state.get("record_type") == STATE_VERSION, "state_version_unsupported")
    exact_fields(state, ("record_type", "binding", "binding_sha256", "created_at", "deadline", "updated_at",
                         "revision", "attempts"))
    validate_binding(state["binding"])
    require(state["binding_sha256"] == digest(state["binding"]), "state_binding_digest_mismatch")
    if binding is not None:
        require(state["binding"] == binding.to_dict(), "queue_binding_changed")
    require(integer(state["revision"], minimum=1), "state_revision_invalid")
    require(all(number(state[key]) for key in ("created_at", "deadline", "updated_at")), "state_time_invalid")
    require(state["created_at"] <= state["updated_at"]
            and state["deadline"] == state["created_at"] + state["binding"]["limits"]["queue_timeout"],
            "state_deadline_changed")
    require(type(state["attempts"]) is list, "attempts_invalid")
    tasks = state["binding"]["tasks"]
    last = {}
    for index, attempt in enumerate(state["attempts"], 1):
        exact_fields(attempt, ("id", "task_index", "allocation", "reserved_at", "status", "outcome", "reconciliation"))
        task_index = attempt["task_index"]
        require(integer(task_index) and task_index < len(tasks), "attempt_task_invalid")
        require(attempt["id"] == f"attempt-{index:06d}" and integer(attempt["allocation"], minimum=1)
                and attempt["allocation"] <= state["binding"]["limits"]["max_calls_per_task"], "attempt_allocation_invalid")
        require(number(attempt["reserved_at"]) and state["created_at"] <= attempt["reserved_at"] <= state["updated_at"],
                "attempt_time_invalid")
        previous = last.get(task_index)
        require(previous is None or (previous["status"] == "reconciled"
                and previous["reconciliation"]["action"] == "retry"), "unreconciled_task_replay")
        require(not any(row["status"] in ("reserved", "unknown") for row in state["attempts"][:index - 1]),
                "unreconciled_queue_continuation")
        require(attempt["status"] in ("reserved", "finished", "unknown", "reconciled"), "attempt_status_invalid")
        outcome = attempt["outcome"]
        require(outcome is None or type(outcome) is dict, "attempt_outcome_invalid")
        if outcome is not None:
            exact_fields(outcome, ("exit", "ended", "seconds", "summary", "observed_model_calls"))
            require((outcome["exit"] is None or type(outcome["exit"]) is int)
                    and type(outcome["ended"]) is str and number(outcome["seconds"])
                    and type(outcome["summary"]) is dict and outcome["observed_model_calls"] is None,
                    "attempt_outcome_invalid")
        require(attempt["status"] != "reserved" or outcome is None, "reservation_has_outcome")
        require(attempt["status"] != "finished" or (outcome is not None and outcome["exit"] == 0
                and outcome["ended"] == "finished"), "finished_outcome_invalid")
        reconciliation = attempt["reconciliation"]
        require((attempt["status"] == "reconciled") == (reconciliation is not None), "reconciliation_state_invalid")
        if reconciliation is not None:
            validate_reconciliation(reconciliation, state, attempt)
        last[task_index] = attempt
    require(calls_allocated(state) <= state["binding"]["limits"]["queue_call_budget"], "queue_allocation_exceeded")


def load_state(path, binding=None):
    """Missing, malformed and historical records never imply a fresh allowance."""
    state = parse(read_bytes(path))
    validate_state(state, binding)
    return state


def validate_reconciliation(value, state, attempt):
    exact_fields(value, ("record_type", "binding_sha256", "attempt_id", "action", "external_outcome",
                         "evidence_path", "evidence_sha256", "operator_confirmation"))
    require(value["record_type"] == "overnight_queue_reconciliation/v1"
            and value["binding_sha256"] == state["binding_sha256"] and value["attempt_id"] == attempt["id"],
            "reconciliation_binding_mismatch")
    require(value["action"] in ("retire", "retry") and value["external_outcome"] in (
        "not_dispatched", "effects_reconciled"), "reconciliation_disposition_invalid")
    require(value["operator_confirmation"] == "checked_external_effects_and_child_quiescence",
            "reconciliation_confirmation_required")
    require(type(value["evidence_path"]) is str and Path(value["evidence_path"]).is_absolute()
            and type(value["evidence_sha256"]) is str and len(value["evidence_sha256"]) == 64
            and all(ch in "0123456789abcdef" for ch in value["evidence_sha256"]), "reconciliation_evidence_invalid")
