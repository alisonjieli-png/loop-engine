"""Immutable, bounded task and candidate packets for mechanism comparisons."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass

OPERATIONS = ("sum", "histogram", "stable_unique")
METHODS = ("streaming", "batch")
MAX_PACKET_BYTES = 262144


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def identifier(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,100}", value
    ):
        raise ValueError("invalid lab identifier")
    return value


@dataclass(frozen=True)
class TaskCase:
    case_id: str
    operation: str
    values: tuple[int, ...]

    def __post_init__(self):
        identifier(self.case_id)
        if self.operation not in OPERATIONS:
            raise ValueError("unknown operation")
        if (
            not isinstance(self.values, tuple)
            or len(self.values) > 4096
            or any(type(v) is not int or abs(v) > 10**9 for v in self.values)
        ):
            raise ValueError("values require at most 4096 bounded integers")

    def to_dict(self) -> dict:
        return {
            "record_type": "embodiment_task/v1",
            "case_id": self.case_id,
            "operation": self.operation,
            "values": list(self.values),
        }

    @classmethod
    def from_dict(cls, value: dict) -> TaskCase:
        if (
            not isinstance(value, dict)
            or set(value) != {"record_type", "case_id", "operation", "values"}
            or value["record_type"] != "embodiment_task/v1"
            or type(value["values"]) is not list
        ):
            raise ValueError("invalid task packet")
        return cls(value["case_id"], value["operation"], tuple(value["values"]))


@dataclass(frozen=True)
class WorkPacket:
    request_id: str
    task: TaskCase
    method: str = "streaming"

    def __post_init__(self):
        identifier(self.request_id)
        if not isinstance(self.task, TaskCase) or self.method not in METHODS:
            raise ValueError("invalid work packet")

    def to_dict(self) -> dict:
        return {
            "record_type": "embodiment_work/v1",
            "request_id": self.request_id,
            "task": self.task.to_dict(),
            "method": self.method,
            "task_digest": digest(self.task.to_dict()),
        }

    @classmethod
    def from_dict(cls, value: dict) -> WorkPacket:
        if (
            not isinstance(value, dict)
            or set(value)
            != {"record_type", "request_id", "task", "method", "task_digest"}
            or value["record_type"] != "embodiment_work/v1"
        ):
            raise ValueError("invalid work packet fields")
        task = TaskCase.from_dict(value["task"])
        if digest(task.to_dict()) != value["task_digest"]:
            raise ValueError("task digest mismatch")
        return cls(value["request_id"], task, value["method"])


@dataclass(frozen=True)
class RunPolicy:
    seconds: float = 60.0
    concurrency: int = 2

    def __post_init__(self):
        if (
            type(self.seconds) not in (int, float)
            or not math.isfinite(self.seconds)
            or not 0 < self.seconds <= 86400
        ):
            raise ValueError("seconds must be finite and in (0, 86400]")
        if type(self.concurrency) is not int or not 1 <= self.concurrency <= 16:
            raise ValueError("concurrency must be between 1 and 16")
