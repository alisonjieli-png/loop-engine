"""Passive trigger, series, activation, and lease contracts.

The records describe durable reactive work.  They never execute a task or
become graph vertices.  A claimed activation must still start the canonical
``Loop`` runtime with the exact ``LoopDefinitionRef`` recorded here.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum

from .atomic_primitives import LoopValueRef
from .loop_definition import LoopDefinitionRef
from .reactive_contracts import (
    ReactiveContractError, ReactiveLoopProfile, TriggerKind, _digest,
    _enum, _identity, _names, _timestamp)


class ActivationStatus(str, Enum):
    ADMITTED = "admitted"
    LEASED = "leased"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    DEAD_LETTER = "dead_letter"

    @property
    def terminal(self) -> bool:
        return self in {
            ActivationStatus.COMPLETED, ActivationStatus.FAILED,
            ActivationStatus.CANCELED, ActivationStatus.DEAD_LETTER,
        }


def _canonical(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _content_id(prefix: str, value: object) -> str:
    digest = hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()
    return f"{prefix}.{digest[:24]}"


@dataclass(frozen=True)
class ReactiveSeriesDefinition:
    """Stable ongoing responsibility implemented by finite Loop activations."""

    series_id: str
    goal: str
    loop_definition_ref: LoopDefinitionRef
    reactive_profile_id: str
    reactive_profile_version: str
    reactive_profile_digest: str
    input_contract_ref: str
    output_port_refs: tuple[str, ...]
    maximum_attempts_per_trigger: int
    maximum_active_activations: int

    def __post_init__(self) -> None:
        _identity("series_id", self.series_id)
        if not isinstance(self.goal, str) or not self.goal.strip():
            raise ReactiveContractError("reactive series requires a goal")
        if not isinstance(self.loop_definition_ref, LoopDefinitionRef):
            raise ReactiveContractError(
                "reactive series requires an exact LoopDefinitionRef")
        _identity("reactive_profile_id", self.reactive_profile_id)
        if not isinstance(self.reactive_profile_version, str) \
                or not self.reactive_profile_version.strip():
            raise ReactiveContractError(
                "reactive series requires a profile version")
        _digest("reactive_profile_digest", self.reactive_profile_digest)
        if not isinstance(self.input_contract_ref, str) \
                or not self.input_contract_ref.strip():
            raise ReactiveContractError(
                "reactive series requires an input contract")
        outputs = _names("output_port_refs", self.output_port_refs)
        if not outputs:
            raise ReactiveContractError(
                "reactive series requires at least one output port")
        object.__setattr__(self, "output_port_refs", outputs)
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 1
               for value in (self.maximum_attempts_per_trigger,
                             self.maximum_active_activations)):
            raise ReactiveContractError(
                "reactive series limits must be positive integers")

    def validate_profile(self, profile: ReactiveLoopProfile) -> None:
        if (not isinstance(profile, ReactiveLoopProfile)
                or profile.profile_id != self.reactive_profile_id
                or profile.version != self.reactive_profile_version
                or profile.content_digest != self.reactive_profile_digest):
            raise ReactiveContractError(
                "reactive series profile identity does not match")
        available = {port.port_id for port in profile.output_ports}
        if not set(self.output_port_refs) <= available:
            raise ReactiveContractError(
                "reactive series names an output absent from its profile")

    @property
    def content_digest(self) -> str:
        return hashlib.sha256(_canonical(self.to_dict()).encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "record_type": "reactive_series_definition/v1",
            "series_id": self.series_id, "goal": self.goal,
            "loop_definition_ref": self.loop_definition_ref.to_dict(),
            "reactive_profile_id": self.reactive_profile_id,
            "reactive_profile_version": self.reactive_profile_version,
            "reactive_profile_digest": self.reactive_profile_digest,
            "input_contract_ref": self.input_contract_ref,
            "output_port_refs": list(self.output_port_refs),
            "maximum_attempts_per_trigger": self.maximum_attempts_per_trigger,
            "maximum_active_activations": self.maximum_active_activations,
        }

    @classmethod
    def from_dict(cls, value: dict) -> "ReactiveSeriesDefinition":
        expected = {
            "record_type", "series_id", "goal", "loop_definition_ref",
            "reactive_profile_id", "reactive_profile_version",
            "reactive_profile_digest", "input_contract_ref",
            "output_port_refs", "maximum_attempts_per_trigger",
            "maximum_active_activations",
        }
        if (not isinstance(value, dict) or set(value) != expected
                or value.get("record_type")
                != "reactive_series_definition/v1"):
            raise ReactiveContractError(
                "reactive series definition has an invalid shape")
        body = dict(value)
        body.pop("record_type")
        body["loop_definition_ref"] = LoopDefinitionRef.from_dict(
            body["loop_definition_ref"])
        body["output_port_refs"] = tuple(body["output_port_refs"])
        return cls(**body)


@dataclass(frozen=True)
class TriggerEnvelope:
    """One versioned information delta requesting series activation."""

    trigger_id: str
    series_id: str
    trigger_kind: TriggerKind | str
    subject_ref: str
    input_ref: LoopValueRef
    source_loop_id: str
    source_event_time: str
    received_at: str
    deduplication_key: str
    information_delta: float
    priority: int = 0
    deadline: str = ""
    correlation_id: str = ""
    causation_id: str = ""

    def __post_init__(self) -> None:
        for label, value in (
                ("trigger_id", self.trigger_id),
                ("series_id", self.series_id),
                ("subject_ref", self.subject_ref),
                ("source_loop_id", self.source_loop_id),
                ("deduplication_key", self.deduplication_key)):
            _identity(label, value)
        if not isinstance(self.input_ref, LoopValueRef):
            raise ReactiveContractError(
                "trigger input must use an exact LoopValueRef")
        object.__setattr__(
            self, "trigger_kind", _enum(
                self.trigger_kind, TriggerKind, "trigger kind"))
        _timestamp("source_event_time", self.source_event_time)
        _timestamp("received_at", self.received_at)
        _timestamp("deadline", self.deadline, optional=True)
        if (not isinstance(self.information_delta, (int, float))
                or isinstance(self.information_delta, bool)
                or not 0.0 <= float(self.information_delta) <= 1.0):
            raise ReactiveContractError(
                "trigger information_delta must be between zero and one")
        object.__setattr__(
            self, "information_delta", float(self.information_delta))
        if (not isinstance(self.priority, int)
                or isinstance(self.priority, bool)
                or not -100 <= self.priority <= 100):
            raise ReactiveContractError(
                "trigger priority must be an integer from -100 through 100")
        for label, value in (("correlation_id", self.correlation_id),
                             ("causation_id", self.causation_id)):
            if value:
                _identity(label, value)

    @property
    def activation_id(self) -> str:
        return _content_id("activation", {
            "series_id": self.series_id,
            "deduplication_key": self.deduplication_key,
            "input_ref": self.input_ref.to_dict(),
        })

    def to_dict(self) -> dict:
        return {
            "record_type": "trigger_envelope/v1",
            "trigger_id": self.trigger_id, "series_id": self.series_id,
            "trigger_kind": self.trigger_kind.value,
            "subject_ref": self.subject_ref,
            "input_ref": self.input_ref.to_dict(),
            "source_loop_id": self.source_loop_id,
            "source_event_time": self.source_event_time,
            "received_at": self.received_at,
            "deduplication_key": self.deduplication_key,
            "information_delta": self.information_delta,
            "priority": self.priority, "deadline": self.deadline,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
        }

    @classmethod
    def from_dict(cls, value: dict) -> "TriggerEnvelope":
        expected = {
            "record_type", "trigger_id", "series_id", "trigger_kind",
            "subject_ref", "input_ref", "source_loop_id",
            "source_event_time", "received_at", "deduplication_key",
            "information_delta", "priority", "deadline", "correlation_id",
            "causation_id",
        }
        if (not isinstance(value, dict) or set(value) != expected
                or value.get("record_type") != "trigger_envelope/v1"):
            raise ReactiveContractError("trigger envelope has an invalid shape")
        body = dict(value)
        body.pop("record_type")
        body["input_ref"] = LoopValueRef.from_dict(body["input_ref"])
        return cls(**body)


@dataclass(frozen=True)
class ActivationRecord:
    """Current durable projection of one finite activation lifecycle."""

    activation_id: str
    series_id: str
    trigger_id: str
    input_ref: LoopValueRef
    loop_definition_ref: LoopDefinitionRef
    status: ActivationStatus | str
    revision: int
    attempt: int
    fencing_token: int
    requested_at: str
    lease_id: str = ""
    worker_id: str = ""
    loop_id: str = ""
    started_at: str = ""
    terminal_at: str = ""
    terminal_code: str = ""
    failure_code: str = ""
    candidate_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for label, value in (("activation_id", self.activation_id),
                             ("series_id", self.series_id),
                             ("trigger_id", self.trigger_id)):
            _identity(label, value)
        if not isinstance(self.input_ref, LoopValueRef) \
                or not isinstance(self.loop_definition_ref, LoopDefinitionRef):
            raise ReactiveContractError(
                "activation requires exact input and definition references")
        object.__setattr__(
            self, "status", _enum(
                self.status, ActivationStatus, "activation status"))
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 0
               for value in (self.revision, self.attempt,
                             self.fencing_token)):
            raise ReactiveContractError(
                "activation counters must be non-negative integers")
        _timestamp("requested_at", self.requested_at)
        _timestamp("started_at", self.started_at, optional=True)
        _timestamp("terminal_at", self.terminal_at, optional=True)
        object.__setattr__(
            self, "candidate_refs", _names(
                "candidate_refs", self.candidate_refs))
        if self.status.terminal and not self.terminal_at:
            raise ReactiveContractError(
                "terminal activation requires terminal_at")
        if self.status is ActivationStatus.COMPLETED \
                and (not self.loop_id or not self.terminal_code):
            raise ReactiveContractError(
                "completed activation requires Loop and terminal identity")

    def to_dict(self) -> dict:
        return {
            "record_type": "activation_record/v1",
            "activation_id": self.activation_id,
            "series_id": self.series_id, "trigger_id": self.trigger_id,
            "input_ref": self.input_ref.to_dict(),
            "loop_definition_ref": self.loop_definition_ref.to_dict(),
            "status": self.status.value, "revision": self.revision,
            "attempt": self.attempt, "fencing_token": self.fencing_token,
            "requested_at": self.requested_at, "lease_id": self.lease_id,
            "worker_id": self.worker_id, "loop_id": self.loop_id,
            "started_at": self.started_at, "terminal_at": self.terminal_at,
            "terminal_code": self.terminal_code,
            "failure_code": self.failure_code,
            "candidate_refs": list(self.candidate_refs),
        }

    @classmethod
    def from_dict(cls, value: dict) -> "ActivationRecord":
        expected = {
            "record_type", "activation_id", "series_id", "trigger_id",
            "input_ref", "loop_definition_ref", "status", "revision",
            "attempt", "fencing_token", "requested_at", "lease_id",
            "worker_id", "loop_id", "started_at", "terminal_at",
            "terminal_code", "failure_code", "candidate_refs",
        }
        if (not isinstance(value, dict) or set(value) != expected
                or value.get("record_type") != "activation_record/v1"):
            raise ReactiveContractError("activation record has an invalid shape")
        body = dict(value)
        body.pop("record_type")
        body["input_ref"] = LoopValueRef.from_dict(body["input_ref"])
        body["loop_definition_ref"] = LoopDefinitionRef.from_dict(
            body["loop_definition_ref"])
        body["candidate_refs"] = tuple(body["candidate_refs"])
        return cls(**body)


@dataclass(frozen=True)
class WorkLease:
    """Exclusive expiring claim over one activation revision."""

    lease_id: str
    activation_id: str
    worker_id: str
    fencing_token: int
    acquired_at: str
    heartbeat_at: str
    expires_at: str

    def __post_init__(self) -> None:
        for label, value in (("lease_id", self.lease_id),
                             ("activation_id", self.activation_id),
                             ("worker_id", self.worker_id)):
            _identity(label, value)
        if (not isinstance(self.fencing_token, int)
                or isinstance(self.fencing_token, bool)
                or self.fencing_token < 1):
            raise ReactiveContractError(
                "lease fencing token must be a positive integer")
        for label, value in (("acquired_at", self.acquired_at),
                             ("heartbeat_at", self.heartbeat_at),
                             ("expires_at", self.expires_at)):
            _timestamp(label, value)

    def to_dict(self) -> dict:
        return {
            "record_type": "work_lease/v1", "lease_id": self.lease_id,
            "activation_id": self.activation_id, "worker_id": self.worker_id,
            "fencing_token": self.fencing_token,
            "acquired_at": self.acquired_at,
            "heartbeat_at": self.heartbeat_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, value: dict) -> "WorkLease":
        expected = {
            "record_type", "lease_id", "activation_id", "worker_id",
            "fencing_token", "acquired_at", "heartbeat_at", "expires_at",
        }
        if (not isinstance(value, dict) or set(value) != expected
                or value.get("record_type") != "work_lease/v1"):
            raise ReactiveContractError("work lease has an invalid shape")
        body = dict(value)
        body.pop("record_type")
        return cls(**body)


@dataclass(frozen=True)
class ActivationClaimRequest:
    """One worker request to claim the next eligible activation."""

    worker_id: str
    as_of: str
    lease_seconds: float
    series_id: str = ""

    def __post_init__(self) -> None:
        _identity("worker_id", self.worker_id)
        _timestamp("as_of", self.as_of)
        if (not isinstance(self.lease_seconds, (int, float))
                or isinstance(self.lease_seconds, bool)
                or self.lease_seconds <= 0):
            raise ReactiveContractError("lease_seconds must be positive")
        if self.series_id:
            _identity("series_id", self.series_id)


@dataclass(frozen=True)
class ActivationStartRequest:
    activation_id: str
    lease_id: str
    fencing_token: int
    started_at: str

    def __post_init__(self) -> None:
        _identity("activation_id", self.activation_id)
        _identity("lease_id", self.lease_id)
        if (not isinstance(self.fencing_token, int)
                or isinstance(self.fencing_token, bool)
                or self.fencing_token < 1):
            raise ReactiveContractError(
                "activation start fencing token must be positive")
        _timestamp("started_at", self.started_at)


@dataclass(frozen=True)
class LeaseHeartbeatRequest:
    """Extend only the current fenced lease with an explicit new deadline."""

    activation_id: str
    lease_id: str
    fencing_token: int
    heartbeat_at: str
    expires_at: str

    def __post_init__(self) -> None:
        _identity("activation_id", self.activation_id)
        _identity("lease_id", self.lease_id)
        if (not isinstance(self.fencing_token, int)
                or isinstance(self.fencing_token, bool)
                or self.fencing_token < 1):
            raise ReactiveContractError(
                "heartbeat fencing token must be positive")
        _timestamp("heartbeat_at", self.heartbeat_at)
        _timestamp("expires_at", self.expires_at)


@dataclass(frozen=True)
class ActivationTerminalRequest:
    """Terminal result committed only by the current fenced worker."""

    activation_id: str
    lease_id: str
    fencing_token: int
    status: ActivationStatus | str
    terminal_at: str
    loop_id: str = ""
    terminal_code: str = ""
    failure_code: str = ""
    candidate_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for label, value in (("activation_id", self.activation_id),
                             ("lease_id", self.lease_id)):
            _identity(label, value)
        if (not isinstance(self.fencing_token, int)
                or isinstance(self.fencing_token, bool)
                or self.fencing_token < 1):
            raise ReactiveContractError(
                "terminal fencing token must be positive")
        object.__setattr__(
            self, "status", _enum(
                self.status, ActivationStatus, "terminal status"))
        if not self.status.terminal:
            raise ReactiveContractError(
                "activation terminal request needs a terminal status")
        _timestamp("terminal_at", self.terminal_at)
        object.__setattr__(
            self, "candidate_refs", _names(
                "candidate_refs", self.candidate_refs))
        if self.status is ActivationStatus.COMPLETED \
                and (not self.loop_id or not self.terminal_code):
            raise ReactiveContractError(
                "completed activation needs Loop and terminal identity")
        if self.status in {ActivationStatus.FAILED,
                           ActivationStatus.DEAD_LETTER} \
                and not self.failure_code:
            raise ReactiveContractError(
                "failed activation needs a failure code")


__all__ = (
    "ActivationClaimRequest", "ActivationRecord", "ActivationStartRequest",
    "ActivationStatus", "ActivationTerminalRequest", "LeaseHeartbeatRequest",
    "ReactiveSeriesDefinition", "TriggerEnvelope", "WorkLease",
)
