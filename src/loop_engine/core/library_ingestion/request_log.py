"""Every network request of an ingestion run, recorded, counted and bounded.

library_network_request/v1 records one request: the transport, the host,
the target, the method (always GET), the status, the byte count and digest
of the body, the time it took, the outcome and the provider's remaining
request allowance when the provider reports one. No header other than the
allowance and its reset time is kept, and no credential ever reaches a
record, because the transports never hold one.

RequestBudget is the declared ceiling of one run. A request beyond the
ceiling is refused before it is sent. When a provider's allowance runs low,
the budget pauses until the reported reset, but only up to a declared total
pause; a longer wait stops the run cleanly instead of waiting without end.
Every pause is recorded with its length and reason.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from .record_rules import bytes_digest, canonical_digest, now_utc

NETWORK_REQUEST_RECORD_TYPE = "library_network_request/v1"
PAUSE_RECORD_TYPE = "library_request_pause/v1"
TRANSPORTS = ("gh_api", "https_get")
OUTCOMES = ("ok", "not_found", "http_error", "transport_error", "rate_limited")


class RequestCeilingReached(RuntimeError):
    """The run's declared request ceiling would be exceeded; nothing was sent."""


class PauseExceedsBound(RuntimeError):
    """Waiting for the provider's allowance would exceed the declared total pause."""


@dataclass
class RequestBudget:
    """The ceiling of one run: requests, the allowance reserve and the total pause."""

    maximum_requests: int
    maximum_pause_seconds: float = 900.0
    reserve: int = 200
    used: int = 0
    paused_seconds: float = 0.0
    pauses: list = field(default_factory=list)
    sleep: object = time.sleep
    clock: object = time.time

    def admit(self) -> None:
        if self.used >= self.maximum_requests:
            raise RequestCeilingReached(f"the run's ceiling of {self.maximum_requests} requests is reached")
        self.used += 1

    def respect_allowance(self, remaining: "int | None", reset_epoch: "int | None", provider: str) -> None:
        """Pause until the reset when fewer than the reserve remain, within the declared bound."""
        if remaining is None or remaining > self.reserve:
            return
        wait = max(0.0, float(reset_epoch or 0) - float(self.clock())) + 1.0
        self.pause(wait, f"{provider} allowance at {remaining}, reserve {self.reserve}")

    def pause(self, seconds: float, reason: str) -> None:
        if self.paused_seconds + seconds > self.maximum_pause_seconds:
            self.pauses.append({"record_type": PAUSE_RECORD_TYPE, "seconds": round(seconds, 3),
                                "reason": reason, "taken": False, "at": now_utc()})
            raise PauseExceedsBound(f"a pause of {seconds:.0f} seconds would exceed the declared total "
                                    f"of {self.maximum_pause_seconds:.0f} seconds")
        self.pauses.append({"record_type": PAUSE_RECORD_TYPE, "seconds": round(seconds, 3),
                            "reason": reason, "taken": True, "at": now_utc()})
        self.paused_seconds += seconds
        self.sleep(seconds)


@dataclass(frozen=True)
class RequestObservation:
    """What one transport saw of one request: where it went, what came back and how long it took.

    The body is kept only to measure its size and digest; the log never
    writes it. No header, and so no credential, has a place here.
    """

    transport: str
    host: str
    target: str
    status: "int | None"
    body: "bytes | None"
    started_at: str
    elapsed_ms: float
    outcome: str
    allowance_remaining: "int | None" = None
    error_class: str = ""

    def __post_init__(self) -> None:
        if self.transport not in TRANSPORTS or self.outcome not in OUTCOMES:
            raise ValueError(f"a request observation names a transport from {TRANSPORTS} and an outcome "
                             f"from {OUTCOMES}")


class RequestLog:
    """Keeps every request record in order, and appends it to a file when one is given."""

    def __init__(self, path: "Path | None" = None) -> None:
        self.path = path
        self.records: list = []

    def record(self, observation: RequestObservation) -> dict:
        body = observation.body
        row = {"record_type": NETWORK_REQUEST_RECORD_TYPE, "sequence": len(self.records) + 1,
               "transport": observation.transport, "host": observation.host,
               "target": observation.target[:512], "method": "GET", "status": observation.status,
               "bytes": None if body is None else len(body),
               "body_digest": None if body is None else bytes_digest(body),
               "started_at": observation.started_at, "elapsed_ms": round(observation.elapsed_ms, 1),
               "outcome": observation.outcome, "allowance_remaining": observation.allowance_remaining,
               "error_class": observation.error_class}
        row["request_digest"] = canonical_digest(row)
        self.records.append(row)
        if self.path is not None:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row, sort_keys=True) + "\n")
        return row

    def summary(self) -> dict:
        outcomes: dict = {}
        for row in self.records:
            key = f"{row['transport']}:{row['outcome']}"
            outcomes[key] = outcomes.get(key, 0) + 1
        return {"requests": len(self.records), "by_outcome": outcomes,
                "bytes": sum(row["bytes"] or 0 for row in self.records)}
