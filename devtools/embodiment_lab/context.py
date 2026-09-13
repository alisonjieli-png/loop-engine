"""Host-owned grants and observations for one independently launched experiment."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from .contracts import RunPolicy, WorkPacket
from .storage import ResultRecorder


@dataclass
class ExperimentContext:
    root: Path
    policy: RunPolicy
    recorder: ResultRecorder
    started: float = field(default_factory=time.monotonic)
    rows: list[dict] = field(default_factory=list)

    def remaining(self) -> float:
        seconds = self.policy.seconds - (time.monotonic() - self.started)
        if seconds <= 0:
            raise TimeoutError("experiment deadline exhausted")
        return seconds

    def accept(self, packet: WorkPacket, result: dict) -> dict:
        verdict = self.recorder.record(packet, result)
        row = {
            "request_id": packet.request_id,
            "case_id": packet.task.case_id,
            "method": packet.method,
            "accepted": verdict["accepted"],
            "reason": verdict["reason"],
            "pid": result.get("pid"),
            "loop_id": result.get("loop_id"),
            "model_calls": result.get("model_calls"),
            "seconds_since_start": time.monotonic() - self.started,
            "portfolio_version": verdict.get("portfolio_version"),
        }
        self.rows.append(row)
        return row

    def failure(self, packet: WorkPacket, error: Exception) -> dict:
        row = {
            "request_id": packet.request_id,
            "case_id": packet.task.case_id,
            "method": packet.method,
            "accepted": False,
            "reason": type(error).__name__ + ": " + str(error)[:200],
            "pid": None,
            "loop_id": None,
            "model_calls": None,
            "seconds_since_start": time.monotonic() - self.started,
        }
        self.rows.append(row)
        return row
