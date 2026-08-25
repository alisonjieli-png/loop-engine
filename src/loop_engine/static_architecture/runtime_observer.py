"""One typed observation service for safe runtime metadata.

Operational services emit small, schema-checked observations through this
interface. ``LedgerRuntimeObserver`` appends them to the existing Loop ledger;
it does not create another store or event vocabulary. Each raw kind maps into
the canonical event families owned by ``event_vocabulary``.

Event-specific allowlists reject raw prompts, content, tool payloads, paths,
secrets, approval tokens, and private spawned context before ledger recording.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol


_OBSERVATION_FIELDS = {
    "effect_approval_requested": frozenset({
        "request_id", "effect_class", "operation", "target_digest",
        "status", "state_revision", "schema_version",
    }),
    "effect_approval_decided": frozenset({
        "request_id", "effect_class", "operation", "target_digest",
        "status", "action", "state_revision", "schema_version",
    }),
    "context_artifact_stored": frozenset({
        "digest", "byte_count", "media_type", "artifact_kind",
        "estimated_tokens", "token_counter_id", "offloaded",
    }),
    "context_compaction_completed": frozenset({
        "raw_digest", "compacted_digest", "compacted_bytes",
        "omitted_bytes", "strategy", "loop_profile",
    }),
    "mcp_call_terminal": frozenset({
        "server_id", "tool_name", "status", "effect", "request_digest",
        "has_output_ref", "has_approval", "error_code",
    }),
    "skill_load_terminal": frozenset({
        "skill_id", "version", "lifecycle", "manifest_digest",
        "file_count", "status", "error_code",
    }),
}

_OBSERVATION_REQUIRED_FIELDS = {
    kind: fields for kind, fields in _OBSERVATION_FIELDS.items()
}

# The conformance scanner can verify a module-level literal map used by an
# event= subscript. Dynamic event strings are refused repository-wide.
_OBSERVATION_LEDGER_KINDS = {
    "effect_approval_requested": "effect_approval_requested",
    "effect_approval_decided": "effect_approval_decided",
    "context_artifact_stored": "context_artifact_stored",
    "context_compaction_completed": "context_compaction_completed",
    "mcp_call_terminal": "mcp_call_terminal",
    "skill_load_terminal": "skill_load_terminal",
}


class RuntimeObservationError(ValueError):
    """An observation attempted to leave its safe schema."""


@dataclass(frozen=True)
class RuntimeObservation:
    """One canonical raw event plus its display-safe metadata."""

    kind: str
    fields: Mapping[str, object]
    loop_id: str = ""

    def __post_init__(self):
        if self.kind not in _OBSERVATION_FIELDS:
            raise RuntimeObservationError(
                f"unknown runtime observation kind {self.kind!r}")
        values = dict(self.fields)
        unknown = set(values) - _OBSERVATION_FIELDS[self.kind]
        missing = _OBSERVATION_REQUIRED_FIELDS[self.kind] - set(values)
        if unknown:
            raise RuntimeObservationError(
                f"{self.kind} contains unsafe fields {sorted(unknown)!r}")
        if missing:
            raise RuntimeObservationError(
                f"{self.kind} misses required fields {sorted(missing)!r}")
        for key, value in values.items():
            if not isinstance(value, (str, int, float, bool, type(None))):
                raise RuntimeObservationError(
                    f"{self.kind}.{key} must be a safe scalar")
            if isinstance(value, str) and (len(value) > 256
                                           or "\n" in value
                                           or "\r" in value):
                raise RuntimeObservationError(
                    f"{self.kind}.{key} exceeds the safe text boundary")
            if (isinstance(value, (int, float))
                    and not isinstance(value, bool) and value < 0):
                raise RuntimeObservationError(
                    f"{self.kind}.{key} cannot be negative")
            if key.endswith("digest") and (
                    not isinstance(value, str) or len(value) != 64
                    or any(char not in "0123456789abcdef" for char in value)):
                raise RuntimeObservationError(
                    f"{self.kind}.{key} must be a SHA-256 value")
        status = str(values.get("status", ""))
        if (self.kind == "effect_approval_requested" and status != "pending"):
            raise RuntimeObservationError(
                "approval request observation must be pending")
        if (self.kind == "effect_approval_decided" and status != "decided"):
            raise RuntimeObservationError(
                "approval decision observation must be decided")
        if (self.kind == "mcp_call_terminal" and status not in (
                "completed", "failed", "refused", "approval_required",
                "unavailable")):
            raise RuntimeObservationError("unknown MCP terminal status")
        if (self.kind == "skill_load_terminal"
                and status not in ("completed", "failed")):
            raise RuntimeObservationError("unknown skill load status")
        object.__setattr__(self, "fields", values)


class RuntimeObserver(Protocol):
    """Small observer contract shared by operational services."""

    def emit(self, observation: RuntimeObservation) -> None: ...


class NullRuntimeObserver:
    """Default observer for callers that do not supply a run ledger."""

    def emit(self, observation: RuntimeObservation) -> None:
        return None


class LedgerRuntimeObserver:
    """Append safe observations to one existing Loop ledger."""

    def __init__(self, ledger, *, default_loop_id: str = ""):
        if ledger is None or not callable(getattr(ledger, "record", None)):
            raise RuntimeObservationError(
                "LedgerRuntimeObserver needs an object with record()")
        self.ledger = ledger
        self.default_loop_id = default_loop_id

    def emit(self, observation: RuntimeObservation) -> None:
        if not isinstance(observation, RuntimeObservation):
            raise RuntimeObservationError(
                "observer accepts RuntimeObservation objects only")
        self.ledger.record(
            loop_id=observation.loop_id or self.default_loop_id,
            event=_OBSERVATION_LEDGER_KINDS[observation.kind],
            **dict(observation.fields),
        )


@dataclass(frozen=True)
class RuntimeObservationServices:
    """Parent, ledger, and observer passed as one service object."""

    parent: object = None
    ledger: object = None
    observer: "RuntimeObserver | None" = None
    _resolved: RuntimeObserver = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        observer = self.observer
        if observer is None:
            ledger = self.ledger
            if ledger is None and self.parent is not None:
                ledger = getattr(self.parent, "ledger", None)
            observer = (LedgerRuntimeObserver(ledger) if ledger is not None
                        else NullRuntimeObserver())
        if not callable(getattr(observer, "emit", None)):
            raise RuntimeObservationError(
                "runtime observer needs an emit() method")
        object.__setattr__(self, "_resolved", observer)

    def emit(self, observation: RuntimeObservation) -> None:
        self._resolved.emit(observation)


def self_test() -> dict:
    """Verify allowlists, ledger reuse, and secret-shaped field refusal."""
    from ..loop.recursive_loop import LoopLedger

    tests = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    ledger = LoopLedger()
    services = RuntimeObservationServices(ledger=ledger)
    services.emit(RuntimeObservation(
        "context_artifact_stored",
        {"digest": "a" * 64, "byte_count": 12,
         "media_type": "text/plain", "artifact_kind": "raw_output",
         "estimated_tokens": 3, "token_counter_id": "fixture",
         "offloaded": False},
        loop_id="loop-observer"))
    check("safe_observation_reuses_the_existing_loop_ledger",
          len(ledger.events) == 1
          and ledger.events[0]["event"] == "context_artifact_stored"
          and ledger.events[0]["loop_id"] == "loop-observer")
    from .event_vocabulary import to_canonical_events
    canonical = to_canonical_events(ledger.events)
    check("safe_observation_uses_the_canonical_event_vocabulary",
          canonical[0]["type"] == "state.committed")

    unsafe_failed = False
    try:
        RuntimeObservation(
            "context_artifact_stored",
            {"digest": "a" * 64, "raw_content": "private"})
    except RuntimeObservationError:
        unsafe_failed = True
    check("event_specific_allowlists_refuse_raw_content_fields", unsafe_failed)

    unknown_failed = False
    try:
        RuntimeObservation("model_decided_anything", {})
    except RuntimeObservationError:
        unknown_failed = True
    check("an_unknown_observation_kind_fails_closed", unknown_failed)

    passed = sum(1 for test in tests if test["passed"])
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
