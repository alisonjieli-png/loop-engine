"""Durable, fail-closed approval objects for effects requested by Loops.

An approval pauses one exact effect and resumes only with its opaque token.
This module records authority through verifier Loops; it executes no effect.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Callable, TypeVar

if TYPE_CHECKING:
    from .approval_state_store import ApprovalStateStore
    from .recursive_loop import Loop
    from ..core.runtime_observer import (
        RuntimeObservationServices)


_T = TypeVar("_T")
_APPROVAL_OPERATION_PORTS = {
    "create_effect_approval": ("approval_request", "approval_checkpoint"),
    "restore_effect_approval": ("approval_state", "approval_state"),
    "restore_serialized_effect_approval": ("serialized_approval_state",
                                            "approval_state"),
    "read_effect_approval": ("approval_request_id", "approval_state"),
    "serialize_effect_approval": ("approval_request_id",
                                  "serialized_approval_state"),
    "decide_effect_approval": ("pending_approval_decision",
                               "decided_approval_state"),
    "consume_effect_approval": ("approved_effect_execution",
                                "consumed_approval_state"),
}

class EffectClass(str, Enum):
    """Known effect boundaries. Any value outside this enum fails closed."""

    LOCAL_READ = "local_read"
    LOCAL_WRITE = "local_write"
    COMMAND_EXECUTION = "command_execution"
    NETWORK_READ = "network_read"
    NETWORK_WRITE = "network_write"
    EXTERNAL_MESSAGE = "external_message"
    EXTERNAL_SUBMISSION = "external_submission"
    MONEY_SPEND = "money_spend"
    SECRET_ACCESS = "secret_access"
    DATA_DELETION = "data_deletion"
    DEPLOYMENT = "deployment"


class ApprovalAction(str, Enum):
    APPROVE = "approve"
    EDIT = "edit"
    REJECT = "reject"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    DECIDED = "decided"
    CONSUMED = "consumed"


EFFECT_APPROVAL_SCHEMA_VERSION = "effect_approval/v2"
SUPPORTED_EFFECT_APPROVAL_SCHEMAS = (
    "effect_approval/v1", EFFECT_APPROVAL_SCHEMA_VERSION)


@dataclass(frozen=True)
class EffectSpec:
    """One bounded effect with a plain target and string parameters."""

    effect_class: EffectClass
    operation: str
    target: str
    parameters: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        if not isinstance(self.effect_class, EffectClass):
            raise TypeError("effect_class must be a known EffectClass")
        if not self.operation.strip():
            raise ValueError("an effect needs an operation")
        if not self.target.strip():
            raise ValueError("an effect needs an exact target")
        keys = [key for key, _value in self.parameters]
        if len(keys) != len(set(keys)):
            raise ValueError("effect parameter keys must be unique")
        if any(not key for key in keys):
            raise ValueError("effect parameter keys cannot be empty")

    def to_dict(self) -> dict:
        return {
            "effect_class": self.effect_class.value,
            "operation": self.operation,
            "target": self.target,
            "parameters": {key: value for key, value in self.parameters},
        }

    @classmethod
    def from_dict(cls, value: dict) -> "EffectSpec":
        # Enum construction is deliberate. An unknown value raises rather than
        # being converted into a generic or less restrictive effect.
        effect_class = EffectClass(str(value["effect_class"]))
        parameters = value.get("parameters", {})
        if not isinstance(parameters, dict):
            raise TypeError("effect parameters must be an object")
        return cls(
            effect_class=effect_class,
            operation=str(value["operation"]),
            target=str(value["target"]),
            parameters=tuple(sorted(
                (str(key), str(item)) for key, item in parameters.items())),
        )


@dataclass(frozen=True)
class ApprovalRequest:
    """The exact effect and reason presented to a reviewer."""

    request_id: str
    loop_id: str
    effect: EffectSpec
    reason: str
    requested_by: str = "loop"
    created_at: str = ""

    def __post_init__(self):
        if not self.request_id or not self.loop_id:
            raise ValueError("approval request needs request_id and loop_id")
        if not self.reason.strip():
            raise ValueError("approval request needs a plain reason")

    @classmethod
    def create(cls, loop_id: str, effect: EffectSpec, reason: str, *,
               requested_by: str = "loop", created_at: str = ""
               ) -> "ApprovalRequest":
        request_id = f"approval_{secrets.token_hex(16)}"
        return cls(
            request_id=request_id,
            loop_id=loop_id,
            effect=effect,
            reason=reason,
            requested_by=requested_by,
            created_at=created_at,
        )

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "loop_id": self.loop_id,
            "effect": self.effect.to_dict(),
            "reason": self.reason,
            "requested_by": self.requested_by,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, value: dict) -> "ApprovalRequest":
        return cls(
            request_id=str(value["request_id"]),
            loop_id=str(value["loop_id"]),
            effect=EffectSpec.from_dict(value["effect"]),
            reason=str(value["reason"]),
            requested_by=str(value.get("requested_by", "loop")),
            created_at=str(value.get("created_at", "")),
        )


@dataclass(frozen=True)
class ApprovalDecision:
    """A reviewer decision tied to one approval request."""

    request_id: str
    action: ApprovalAction
    decided_by: str
    reason: str = ""
    edited_effect: "EffectSpec | None" = None
    decided_at: str = ""

    def __post_init__(self):
        if not self.request_id or not self.decided_by:
            raise ValueError("approval decision needs request_id and decided_by")
        if not isinstance(self.action, ApprovalAction):
            raise TypeError("action must be a known ApprovalAction")
        if self.action is ApprovalAction.EDIT and self.edited_effect is None:
            raise ValueError("an edit decision needs edited_effect")
        if self.action is not ApprovalAction.EDIT and self.edited_effect is not None:
            raise ValueError("only an edit decision can carry edited_effect")

    @classmethod
    def approve(cls, request_id: str, decided_by: str, *, reason: str = "",
                decided_at: str = "") -> "ApprovalDecision":
        return cls(request_id, ApprovalAction.APPROVE, decided_by,
                   reason=reason, decided_at=decided_at)

    @classmethod
    def edit(cls, request_id: str, decided_by: str, effect: EffectSpec, *,
             reason: str = "", decided_at: str = "") -> "ApprovalDecision":
        return cls(request_id, ApprovalAction.EDIT, decided_by, reason=reason,
                   edited_effect=effect, decided_at=decided_at)

    @classmethod
    def reject(cls, request_id: str, decided_by: str, *, reason: str,
               decided_at: str = "") -> "ApprovalDecision":
        return cls(request_id, ApprovalAction.REJECT, decided_by,
                   reason=reason, decided_at=decided_at)

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "action": self.action.value,
            "decided_by": self.decided_by,
            "reason": self.reason,
            "edited_effect": (
                self.edited_effect.to_dict() if self.edited_effect else None),
            "decided_at": self.decided_at,
        }

    @classmethod
    def from_dict(cls, value: dict) -> "ApprovalDecision":
        edited = value.get("edited_effect")
        return cls(
            request_id=str(value["request_id"]),
            action=ApprovalAction(str(value["action"])),
            decided_by=str(value["decided_by"]),
            reason=str(value.get("reason", "")),
            edited_effect=EffectSpec.from_dict(edited) if edited else None,
            decided_at=str(value.get("decided_at", "")),
        )


@dataclass(frozen=True)
class PendingApprovalState:
    """Serializable approval state. The plain resume token is not stored."""

    request: ApprovalRequest
    request_digest: str
    resume_token_digest: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    decision: "ApprovalDecision | None" = None
    schema_version: str = EFFECT_APPROVAL_SCHEMA_VERSION
    state_revision: int = 0

    def __post_init__(self):
        for name, digest in (
                ("request_digest", self.request_digest),
                ("resume_token_digest", self.resume_token_digest)):
            if (len(digest) != 64 or any(
                    char not in "0123456789abcdef" for char in digest)):
                raise ValueError(f"{name} must be a SHA-256 value")
        if not hmac.compare_digest(
                self.request_digest, _request_digest(self.request)):
            raise ValueError("serialized approval request failed integrity validation")
        if self.schema_version not in SUPPORTED_EFFECT_APPROVAL_SCHEMAS:
            raise ValueError("unsupported effect approval schema version")
        if self.status is ApprovalStatus.PENDING and self.decision is not None:
            raise ValueError("pending approval cannot already have a decision")
        if (self.status in (ApprovalStatus.DECIDED, ApprovalStatus.CONSUMED)
                and self.decision is None):
            raise ValueError("decided or consumed approval needs its decision")
        if (self.status is ApprovalStatus.CONSUMED
                and self.schema_version != EFFECT_APPROVAL_SCHEMA_VERSION):
            raise ValueError("consumed approval state requires schema version 2")
        expected_revision = {
            ApprovalStatus.PENDING: 0,
            ApprovalStatus.DECIDED: 1,
            ApprovalStatus.CONSUMED: 2,
        }[self.status]
        if self.state_revision != expected_revision:
            raise ValueError(
                f"{self.status.value} approval needs state_revision "
                f"{expected_revision}")
        if self.decision and self.decision.request_id != self.request.request_id:
            raise ValueError("approval decision does not match its request")

    def to_dict(self) -> dict:
        return {
            "request": self.request.to_dict(),
            "request_digest": self.request_digest,
            "resume_token_digest": self.resume_token_digest,
            "status": self.status.value,
            "decision": self.decision.to_dict() if self.decision else None,
            "schema_version": self.schema_version,
            "state_revision": self.state_revision,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, value: dict) -> "PendingApprovalState":
        decision = value.get("decision")
        return cls(
            request=ApprovalRequest.from_dict(value["request"]),
            request_digest=str(value["request_digest"]),
            resume_token_digest=str(value["resume_token_digest"]),
            status=ApprovalStatus(str(value.get("status", "pending"))),
            decision=ApprovalDecision.from_dict(decision) if decision else None,
            schema_version=str(value.get("schema_version", "")),
            state_revision=int(value.get("state_revision", -1)),
        )

    @classmethod
    def from_json(cls, value: str) -> "PendingApprovalState":
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise TypeError("serialized approval state must be an object")
        return cls.from_dict(parsed)

    def resume(self, resume_token: str,
               decision: ApprovalDecision) -> "PendingApprovalState":
        """Apply one decision only when the request and token match exactly."""
        if self.status is not ApprovalStatus.PENDING:
            raise RuntimeError("an approval can be resumed only once")
        supplied_digest = _token_digest(resume_token)
        if not hmac.compare_digest(supplied_digest, self.resume_token_digest):
            raise PermissionError("the approval resume token does not match")
        if decision.request_id != self.request.request_id:
            raise ValueError("approval decision targets a different request")
        return PendingApprovalState(
            request=self.request,
            request_digest=self.request_digest,
            resume_token_digest=self.resume_token_digest,
            status=ApprovalStatus.DECIDED,
            decision=decision,
            schema_version=self.schema_version,
            state_revision=1,
        )

    def authorized_effect(self) -> "EffectSpec | None":
        """Return decided unused authority, or None when it cannot execute."""
        if self.status is not ApprovalStatus.DECIDED or self.decision is None:
            return None
        if self.decision.action is ApprovalAction.REJECT:
            return None
        if self.decision.action is ApprovalAction.EDIT:
            return self.decision.edited_effect
        return self.request.effect

    def consume(self, request_id: str,
                expected_effect: EffectSpec) -> "PendingApprovalState":
        """Consume exact decided authority once before an effect boundary."""
        if self.status is ApprovalStatus.CONSUMED:
            raise RuntimeError("approval authority was already consumed")
        if self.status is not ApprovalStatus.DECIDED:
            raise PermissionError("approval authority is not decided")
        if request_id != self.request.request_id:
            raise PermissionError("approval request id does not match")
        authorized = self.authorized_effect()
        if authorized is None:
            raise PermissionError("approval decision authorizes no effect")
        if not hmac.compare_digest(
                _effect_digest(authorized), _effect_digest(expected_effect)):
            raise PermissionError("approved effect does not match execution")
        return PendingApprovalState(
            request=self.request,
            request_digest=self.request_digest,
            resume_token_digest=self.resume_token_digest,
            status=ApprovalStatus.CONSUMED,
            decision=self.decision,
            schema_version=EFFECT_APPROVAL_SCHEMA_VERSION,
            state_revision=2,
        )


@dataclass(frozen=True)
class ApprovalCheckpoint:
    """A pending state plus the one plain token needed to resume it."""

    pending: PendingApprovalState
    resume_token: str

    def __post_init__(self):
        if not hmac.compare_digest(
                _token_digest(self.resume_token),
                self.pending.resume_token_digest):
            raise ValueError("checkpoint token does not match pending state")

    @classmethod
    def create(cls, request: ApprovalRequest) -> "ApprovalCheckpoint":
        token = f"resume_{secrets.token_urlsafe(32)}"
        pending = PendingApprovalState(
            request=request,
            request_digest=_request_digest(request),
            resume_token_digest=_token_digest(token),
        )
        return cls(pending=pending, resume_token=token)


@dataclass
class EffectApprovalService:
    """Own approval state through one verifier Loop per public operation."""

    runtime: "RuntimeObservationServices" = field(
        default_factory=lambda: _runtime_services())
    store: "ApprovalStateStore | None" = None
    _states: dict[str, PendingApprovalState] = field(
        default_factory=dict, init=False, repr=False)
    _lock: threading.RLock = field(
        default_factory=threading.RLock, init=False, repr=False,
        compare=False)

    def __post_init__(self) -> None:
        from ..core.runtime_observer import (
            RuntimeObservationServices)
        if not isinstance(self.runtime, RuntimeObservationServices):
            raise TypeError("runtime must be RuntimeObservationServices")
        if self.store is not None:
            from .approval_state_store import ApprovalStateStore
            if not isinstance(self.store, ApprovalStateStore):
                raise TypeError("store must implement ApprovalStateStore")

    def create(self, request: ApprovalRequest) -> ApprovalCheckpoint:
        return self._run_operation(
            "create_effect_approval",
            lambda loop: self._create_core(request, loop.loop_id))

    def _create_core(
            self, request: ApprovalRequest,
            operation_loop_id: str) -> ApprovalCheckpoint:
        with self._lock:
            if request.request_id in self._states:
                raise RuntimeError("approval request id is already registered")
            checkpoint = ApprovalCheckpoint.create(request)
            if self.store is not None:
                self.store.create(checkpoint.pending)
            self._states[request.request_id] = checkpoint.pending
        self.runtime.emit(_approval_observation(
            "effect_approval_requested", checkpoint.pending,
            loop_id=operation_loop_id))
        return checkpoint

    def restore(self, state: PendingApprovalState) -> PendingApprovalState:
        """Restore one validated serialized state without allowing rollback."""
        return self._run_operation(
            "restore_effect_approval", lambda _loop: self._restore_core(state))

    def _restore_core(
            self, state: PendingApprovalState) -> PendingApprovalState:
        if not isinstance(state, PendingApprovalState):
            raise TypeError("restore needs a PendingApprovalState")
        with self._lock:
            request_id = state.request.request_id
            existing = self._canonical_or_none(request_id)
            if existing is not None and existing != state:
                raise RuntimeError("approval state conflicts with current state")
            if existing is None and self.store is not None:
                self.store.create(state)
            self._states[request_id] = state
        return state

    def restore_json(self, value: str) -> PendingApprovalState:
        return self._run_operation(
            "restore_serialized_effect_approval",
            lambda _loop: self._restore_core(
                PendingApprovalState.from_json(value)))

    def state(self, request_id: str) -> PendingApprovalState:
        return self._run_operation(
            "read_effect_approval",
            lambda _loop: self._state_core(request_id))

    def _state_core(self, request_id: str) -> PendingApprovalState:
        with self._lock:
            if self.store is not None:
                state = self.store.load(request_id)
                self._states[request_id] = state
                return state
            try:
                return self._states[request_id]
            except KeyError as exc:
                raise KeyError(
                    f"unknown approval request {request_id!r}") from exc

    def serialize(self, request_id: str) -> str:
        return self._run_operation(
            "serialize_effect_approval",
            lambda _loop: self._state_core(request_id).to_json())

    def resume(self, pending: PendingApprovalState, resume_token: str,
               decision: ApprovalDecision) -> PendingApprovalState:
        return self._run_operation(
            "decide_effect_approval",
            lambda loop: self._resume_core(
                pending, resume_token, decision, loop.loop_id))

    def _resume_core(
            self, pending: PendingApprovalState, resume_token: str,
            decision: ApprovalDecision,
            operation_loop_id: str) -> PendingApprovalState:
        with self._lock:
            current = self._canonical_or_none(pending.request.request_id)
            if current is None:
                current = self._restore_core(pending)
            if current != pending:
                raise RuntimeError("cannot decide a stale approval state")
            resolved = current.resume(resume_token, decision)
            if self.store is not None:
                self.store.compare_and_swap(current, resolved)
            self._states[pending.request.request_id] = resolved
        self.runtime.emit(_approval_observation(
            "effect_approval_decided", resolved,
            loop_id=operation_loop_id))
        return resolved

    def consume(self, request_id: str,
                expected_effect: EffectSpec) -> PendingApprovalState:
        """Atomically replace decided state with one-use consumed state."""
        return self._run_operation(
            "consume_effect_approval",
            lambda _loop: self._consume_core(request_id, expected_effect))

    def _consume_core(
            self, request_id: str,
            expected_effect: EffectSpec) -> PendingApprovalState:
        with self._lock:
            current = self._state_core(request_id)
            consumed = current.consume(request_id, expected_effect)
            if self.store is not None:
                self.store.compare_and_swap(current, consumed)
            self._states[request_id] = consumed
            return consumed

    def _run_operation(
            self, operation: str,
            action: Callable[["Loop"], _T]) -> _T:
        """Run one private state transition inside one canonical Loop."""
        from .service_loop_envelope import (
            ServiceLoopSpec, run_service_operation)
        input_role, output_role = _APPROVAL_OPERATION_PORTS[operation]
        return run_service_operation(self.runtime, ServiceLoopSpec(
            operation=operation, profile_id="practitioner.verifier",
            input_role=input_role, output_role=output_role,
            effects=_approval_operation_effects(
                operation, self.store is not None),
            objective=f"verify approval operation: {operation}",
            failure_kind="approval_operation_failed"), action)

    def _canonical_or_none(
            self, request_id: str) -> "PendingApprovalState | None":
        if self.store is None:
            return self._states.get(request_id)
        from .approval_state_store import ApprovalStateNotFound
        try:
            return self.store.load(request_id)
        except ApprovalStateNotFound:
            return None


def _token_digest(token: str) -> str:
    if not token:
        raise ValueError("resume token cannot be empty")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _request_digest(request: ApprovalRequest) -> str:
    canonical = json.dumps(
        request.to_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _effect_digest(effect: EffectSpec) -> str:
    canonical = json.dumps(
        effect.to_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _approval_operation_effects(
        operation: str, has_store: bool) -> tuple[str, ...]:
    if not has_store:
        return ("pure",)
    if operation in ("read_effect_approval", "serialize_effect_approval"):
        return ("reads_fs",)
    return ("reads_fs", "writes_fs")


def _runtime_services():
    from ..core.runtime_observer import (
        RuntimeObservationServices)
    return RuntimeObservationServices()


def _approval_observation(kind: str, state: PendingApprovalState, *,
                          loop_id: str = ""):
    from ..core.runtime_observer import RuntimeObservation
    effect = state.request.effect
    if (state.decision is not None
            and state.decision.edited_effect is not None):
        effect = state.decision.edited_effect
    fields = {
        "request_id": state.request.request_id,
        "effect_class": effect.effect_class.value,
        "operation": effect.operation,
        "target_digest": hashlib.sha256(
            effect.target.encode("utf-8")).hexdigest(),
        "status": state.status.value,
        "state_revision": state.state_revision,
        "schema_version": state.schema_version,
    }
    if state.decision is not None:
        fields["action"] = state.decision.action.value
    return RuntimeObservation(
        kind, fields, loop_id=loop_id or state.request.loop_id)


def self_test() -> dict:
    """Exercise serialization, exact resume, editing, and fail-closed parsing."""
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    original_effect = EffectSpec(
        EffectClass.NETWORK_WRITE,
        "post",
        "https://example.test/jobs",
        (("content_digest", "abc123"),),
    )
    request = ApprovalRequest(
        request_id="approval_test_1",
        loop_id="loop_42",
        effect=original_effect,
        reason="Send one reviewed job payload.",
        requested_by="practitioner",
    )
    from ..core.runtime_observer import (
        RuntimeObservationServices)
    from .recursive_loop import LoopLedger
    ledger = LoopLedger()
    service = EffectApprovalService(RuntimeObservationServices(ledger=ledger))
    checkpoint = service.create(request)
    restored = PendingApprovalState.from_json(checkpoint.pending.to_json())
    check(
        "pending_approval_round_trips_without_serializing_the_plain_token",
        restored == checkpoint.pending
        and checkpoint.resume_token not in checkpoint.pending.to_json(),
        "durable state retains only the token digest",
    )
    changed_state = json.loads(checkpoint.pending.to_json())
    changed_state["request"]["effect"]["target"] = "https://other.test/jobs"
    changed_request_failed = False
    try:
        PendingApprovalState.from_dict(changed_state)
    except ValueError:
        changed_request_failed = True
    check(
        "a_changed_serialized_request_fails_its_content_binding",
        changed_request_failed,
        "the request digest binds the paused effect to its durable state",
    )
    unknown_version = json.loads(checkpoint.pending.to_json())
    unknown_version["schema_version"] = "effect_approval/v99"
    unknown_version_failed = False
    try:
        PendingApprovalState.from_dict(unknown_version)
    except ValueError:
        unknown_version_failed = True
    check(
        "an_unknown_approval_schema_version_fails_closed",
        unknown_version_failed,
        "resume requires a compatible durable-state contract",
    )
    wrong_token_failed = False
    try:
        restored.resume(
            "resume_wrong",
            ApprovalDecision.approve(request.request_id, "reviewer"),
        )
    except PermissionError:
        wrong_token_failed = True
    check(
        "approval_refuses_a_nonmatching_resume_token",
        wrong_token_failed,
        "the serialized pause cannot be resumed with a substitute token",
    )
    approved = service.resume(
        restored,
        checkpoint.resume_token,
        ApprovalDecision.approve(request.request_id, "reviewer"),
    )
    check(
        "approve_authorizes_only_the_original_effect",
        approved.authorized_effect() == original_effect
        and approved.state_revision == 1,
        "approval resolves to the exact effect shown to the reviewer",
    )
    check(
        "approval_service_emits_safe_requested_and_decided_events",
        [event["event"] for event in ledger.events
         if event["event"].startswith("effect_approval_")] == [
             "effect_approval_requested", "effect_approval_decided"]
        and all("target" not in event and "resume_token" not in event
                for event in ledger.events)
        and next(event for event in ledger.events if event["event"]
                 == "effect_approval_decided")["action"] == "approve",
        "the existing Loop ledger receives identity and lifecycle only",
    )
    restored_service = EffectApprovalService(
        RuntimeObservationServices(ledger=LoopLedger()))
    restored_service.restore_json(approved.to_json())
    changed_effect_failed = False
    try:
        restored_service.consume(request.request_id, EffectSpec(
            EffectClass.NETWORK_WRITE,
            "post",
            "https://example.test/other",
            (("content_digest", "abc123"),),
        ))
    except PermissionError:
        changed_effect_failed = True
    consumed = restored_service.consume(request.request_id, original_effect)
    consumed_round_trip = PendingApprovalState.from_json(consumed.to_json())
    replay_failed = False
    replay_service = EffectApprovalService(
        RuntimeObservationServices(ledger=LoopLedger()))
    replay_service.restore(consumed_round_trip)
    try:
        replay_service.consume(request.request_id, original_effect)
    except RuntimeError:
        replay_failed = True
    check(
        "exact_authority_survives_restore_and_is_consumed_once",
        changed_effect_failed
        and consumed.status is ApprovalStatus.CONSUMED
        and consumed.state_revision == 2
        and consumed.authorized_effect() is None
        and replay_failed,
        "changed effects fail and serialized consumed state cannot execute again",
    )
    edited_effect = EffectSpec(
        EffectClass.NETWORK_WRITE,
        "post",
        "https://example.test/drafts",
        (("content_digest", "abc123"),),
    )
    edited = restored.resume(
        checkpoint.resume_token,
        ApprovalDecision.edit(
            request.request_id,
            "reviewer",
            edited_effect,
            reason="Stage a draft instead of publishing.",
        ),
    )
    check(
        "edit_authorizes_the_reviewed_replacement_not_the_original",
        edited.authorized_effect() == edited_effect
        and edited.authorized_effect() != original_effect,
        "edited authority cannot be mistaken for the original request",
    )
    rejected = restored.resume(
        checkpoint.resume_token,
        ApprovalDecision.reject(
            request.request_id,
            "reviewer",
            reason="External write is not authorized.",
        ),
    )
    second_resume_failed = False
    try:
        rejected.resume(
            checkpoint.resume_token,
            ApprovalDecision.approve(request.request_id, "reviewer"),
        )
    except RuntimeError:
        second_resume_failed = True
    check(
        "rejection_authorizes_nothing_and_a_decision_cannot_be_replayed",
        rejected.authorized_effect() is None and second_resume_failed,
        "rejection is terminal for this approval request",
    )
    unknown_failed = False
    unknown = original_effect.to_dict()
    unknown["effect_class"] = "anything_the_model_wants"
    try:
        EffectSpec.from_dict(unknown)
    except ValueError:
        unknown_failed = True
    check(
        "unknown_effect_classes_fail_closed_during_deserialization",
        unknown_failed,
        "an unrecognized effect never falls into a permissive default class",
    )
    passed = sum(1 for item in results if item["passed"])
    return {
        "suite": "effect_approval",
        "total": len(results),
        "passed": passed,
        "all_passed": passed == len(results),
        "tests": results,
        "failed": [item for item in results if not item["passed"]],
        "results": results,
    }

if __name__ == "__main__":
    print(json.dumps(self_test(), indent=2))
