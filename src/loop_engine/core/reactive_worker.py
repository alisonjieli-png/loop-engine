"""Execute claimed reactive activations as exact canonical Loops.

Owns local asynchronous placement after the durable scheduler grants a lease.
It does not define another runtime, scheduler, provider, or output authority.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..code_nodes.solution_graph import LoopDefinitionRegistry
from ..loop.loop_definition import LoopDefinitionRef, LoopStartRequest
from ..loop.loop_role import LoopRelationship
from ..loop.effect_approval import (
    ApprovalDecision, ApprovalRequest, ApprovalStatus, EffectApprovalService,
    EffectClass, EffectSpec)
from ..loop.reactive_activation import (
    ActivationClaimRequest, ActivationHistoryDisposition, ActivationHistoryRef,
    ActivationRecord, ActivationStartRequest, ActivationStatus,
    ActivationTerminalRequest, ReactiveSeriesDefinition, TriggerEnvelope)
from ..loop.recursive_loop import Loop, LoopLedger, StepOutcome, terminal_code
from .reactive_scheduler import (
    ActivationClaimResult, ReactiveSchedulerError, SQLiteReactiveScheduler)


class ReactiveWorkerError(RuntimeError):
    """A claimed activation could not run through the canonical Loop."""


ReactiveStepHandler = Callable[[Loop, str, TriggerEnvelope], StepOutcome]


@dataclass(frozen=True)
class ReactiveHistoryPolicy:
    """Host-owned history root and exact write review; no implicit writes.

    A required root must already exist and remain host-managed. Approval is
    requested for one immutable attempt bundle, including its native record.
    Reading that configured root does not grant authority to replay effects.
    """

    required: bool = False
    root: str = ""
    authorize: Callable[[ApprovalRequest], ApprovalDecision] | None = field(
        default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if type(self.required) is not bool:
            raise ReactiveWorkerError("history required must be a Boolean")
        if not self.required:
            if self.root or self.authorize is not None:
                raise ReactiveWorkerError(
                    "non-persistent history policy cannot carry write authority")
        elif not callable(self.authorize):
            raise ReactiveWorkerError(
                "required history needs an exact host approval callback")
        else:
            _history_path(self.root)


def _history_path(root: str, *parts: str, require_exists: bool = True) -> Path:
    """Refuse traversal, symlinks, and hidden root creation in the owned store."""
    if (not isinstance(root, str) or not root or not Path(root).is_absolute()
            or Path(root) == Path(Path(root).anchor) or ".." in Path(root).parts
            or any(not part or Path(part).is_absolute()
                   or ".." in Path(part).parts for part in parts)):
        raise ReactiveWorkerError("history path needs a confined explicit root")
    base = Path(root)
    path = base.joinpath(*parts)
    for entry in (path, *path.parents):
        if entry.is_symlink():
            raise ReactiveWorkerError("history paths cannot cross a symlink")
    if not base.is_dir():
        raise ReactiveWorkerError("history root must already be a directory")
    if require_exists and not path.exists():
        raise ReactiveWorkerError("referenced history path is missing")
    return path


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False).encode("utf-8")).hexdigest()


def _attempt_binding(request: ReactiveExecutionRequest, loop_id: str,
                     run_id: str) -> dict:
    activation = request.claim.activation
    return {
        "record_type": "reactive_history_binding/v1", "run_id": run_id,
        "activation_id": activation.activation_id, "attempt": activation.attempt,
        "fencing_token": activation.fencing_token, "loop_id": loop_id,
        "definition_ref": activation.loop_definition_ref.to_dict(),
        "input_ref": activation.input_ref.to_dict(),
        "series_digest": request.series.content_digest,
        "trigger_digest": _digest(request.trigger.to_dict()),
    }


def _reference_binding(reference: ActivationHistoryRef) -> dict:
    body = reference.to_dict()
    return {"record_type": "reactive_history_binding/v1", **{
        key: body[key] for key in (
            "run_id", "activation_id", "attempt", "fencing_token", "loop_id",
            "definition_ref", "input_ref", "series_digest", "trigger_digest")}}


def _history_effect(root: str, binding: dict, head: str,
                    count: int, code: str) -> EffectSpec:
    target = _history_path(root, binding["run_id"], require_exists=False)
    return EffectSpec(EffectClass.LOCAL_WRITE, "persist_reactive_run_history",
        str(target), (("history_identity_digest", _digest({
            "binding": binding, "head_digest": head, "event_count": count,
            "terminal_code": code})), ("head_digest", head),
            ("event_count", str(count))))


@dataclass(frozen=True)
class ReactiveHandlerBinding:
    """One exact Loop definition bound to its installed step handler."""

    definition_ref: LoopDefinitionRef
    handler: ReactiveStepHandler = field(repr=False, compare=False)
    history_policy: ReactiveHistoryPolicy = field(default_factory=ReactiveHistoryPolicy)

    def __post_init__(self) -> None:
        if not isinstance(self.definition_ref, LoopDefinitionRef):
            raise ReactiveWorkerError(
                "reactive handler requires an exact LoopDefinitionRef")
        if not callable(self.handler):
            raise ReactiveWorkerError("reactive handler must be callable")
        if not isinstance(self.history_policy, ReactiveHistoryPolicy):
            raise ReactiveWorkerError("reactive handler needs a typed history policy")


@dataclass(frozen=True)
class ReactiveExecutionRequest:
    """Exact series, trigger, and claim passed to one Loop executor."""

    series: ReactiveSeriesDefinition
    trigger: TriggerEnvelope
    claim: ActivationClaimResult


@dataclass(frozen=True)
class CanonicalActivationResult:
    """Terminal canonical Loop evidence for one activation."""

    activation_id: str
    loop_id: str
    terminal_code: str
    definition_ref: LoopDefinitionRef
    elapsed_seconds: float
    ledger: LoopLedger = field(repr=False, compare=False)
    history_ref: ActivationHistoryRef | None = None
    history_disposition: ActivationHistoryDisposition = (
        ActivationHistoryDisposition.NOT_PERSISTED)
    history_error_code: str = ""


class CanonicalReactiveExecutor:
    """Resolve one exact definition and run one Starting Loop."""

    def __init__(self, registry: LoopDefinitionRegistry, runtime_context,
                 bindings: tuple[ReactiveHandlerBinding, ...]) -> None:
        if not isinstance(registry, LoopDefinitionRegistry):
            raise ReactiveWorkerError(
                "canonical reactive executor needs LoopDefinitionRegistry")
        handlers = tuple(bindings)
        if (not handlers
                or any(not isinstance(item, ReactiveHandlerBinding)
                       for item in handlers)
                or len({item.definition_ref for item in handlers})
                != len(handlers)):
            raise ReactiveWorkerError(
                "canonical reactive executor needs unique typed bindings")
        self._registry = registry
        self._runtime_context = runtime_context
        self._bindings = {item.definition_ref: item for item in handlers}
        self._ledgers: dict[str, LoopLedger] = {}

    def execute(self, request: ReactiveExecutionRequest) \
            -> CanonicalActivationResult:
        if not isinstance(request, ReactiveExecutionRequest):
            raise ReactiveWorkerError(
                "execute requires ReactiveExecutionRequest")
        reference = request.claim.activation.loop_definition_ref
        if reference != request.series.loop_definition_ref:
            raise ReactiveWorkerError(
                "activation and series definition references differ")
        definition = self._registry.resolve(reference)
        binding = self._bindings.get(reference)
        if binding is None:
            raise ReactiveWorkerError(
                "no installed handler matches the exact Loop definition")
        activation = request.claim.activation
        if (request.trigger.activation_id != activation.activation_id
                or request.trigger.trigger_id != activation.trigger_id
                or request.trigger.series_id != request.series.series_id
                or activation.series_id != request.series.series_id
                or request.trigger.input_ref != activation.input_ref
                or request.claim.lease.activation_id != activation.activation_id
                or request.claim.lease.fencing_token != activation.fencing_token
                or request.claim.lease.lease_id != activation.lease_id):
            raise ReactiveWorkerError("activation source or claim identity changed")
        run_id = "reactive-" + _digest({
            "activation_id": activation.activation_id,
            "attempt": activation.attempt, "fencing_token": activation.fencing_token,
            "definition_ref": reference.to_dict(),
            "input_ref": activation.input_ref.to_dict()})
        ledger = LoopLedger(id_namespace=run_id)
        loop = Loop(LoopStartRequest(
            request.series.goal, definition, LoopRelationship.starting(),
            self._runtime_context, ledger))
        started = time.monotonic()
        history_binding = _attempt_binding(request, loop.loop_id, run_id)
        ledger.record(loop_id=loop.loop_id, event="custom",
                      reactive_activation_binding=history_binding)

        def bound(active: Loop, step: str, _state: dict) -> StepOutcome:
            outcome = binding.handler(active, step, request.trigger)
            if not isinstance(outcome, StepOutcome):
                raise ReactiveWorkerError(
                    "reactive step handler must return StepOutcome")
            return outcome

        steps = loop.steps()
        if not steps:
            raise ReactiveWorkerError(
                "reactive executor requires a finite installed step profile")
        try:
            result = loop.run(handler=bound, max_steps=len(steps) + 1)
        except Exception:
            # The canonical runtime records handler exceptions before propagating
            # them. Preserve that failed terminal history instead of losing it at
            # the worker boundary. A nonterminal error still remains unknown.
            if not loop.is_terminal or loop.result().terminal_code == "ACCEPTED":
                raise
            result = loop.result()
        if not loop.is_terminal or result.loop_id != loop.loop_id:
            raise ReactiveWorkerError(
                "reactive activation Loop did not terminate honestly")
        self._ledgers[request.claim.activation.activation_id] = ledger
        history_ref = None
        disposition = ActivationHistoryDisposition.NOT_PERSISTED
        history_error = ""
        if binding.history_policy.required:
            try:
                history_ref = self._persist_history(
                    binding.history_policy, history_binding, ledger,
                    result.terminal_code, request.series, request.trigger)
                disposition = ActivationHistoryDisposition.PERSISTED
            except Exception as exc:
                disposition = ActivationHistoryDisposition.PERSISTENCE_FAILED
                history_error = type(exc).__name__.upper()
        elapsed = time.monotonic() - started
        return CanonicalActivationResult(
            request.claim.activation.activation_id, loop.loop_id,
            result.terminal_code, definition.ref, round(elapsed, 6), ledger,
            history_ref, disposition, history_error)

    def history_required(self, reference: LoopDefinitionRef) -> bool:
        binding = self._bindings.get(reference)
        return bool(binding and binding.history_policy.required)

    def _persist_history(self, policy: ReactiveHistoryPolicy, binding: dict,
                         ledger: LoopLedger, code: str,
                         series: ReactiveSeriesDefinition,
                         trigger: TriggerEnvelope) -> ActivationHistoryRef:
        from ..loop.approval_state_store import LocalJsonApprovalStateStore
        from ..loop.service_loop_envelope import ServiceLoopSpec, run_service_operation
        from .run_history import RunHistory
        from .runtime_observer import RuntimeObservationServices

        from ..loop.intelligence_loops import serve_historical_intelligence
        history = serve_historical_intelligence("Reactive terminal history projection", lambda:
            RunHistory.from_ledger(ledger.events, run_id=binding["run_id"]))["value"]
        if not isinstance(history, RunHistory):
            raise ReactiveWorkerError("reactive history could not be projected")
        head = history.commit()
        effect = _history_effect(policy.root, binding, head,
                                 len(history.event_log), code)
        # A separate bookkeeping ledger keeps approval out of the history
        # whose exact head it approves. Its consumed record stays in the bundle.
        runtime = RuntimeObservationServices(ledger=LoopLedger())
        approvals = EffectApprovalService(runtime)
        request = ApprovalRequest.create(binding["loop_id"], effect,
            "Persist this exact terminal reactive history and its approval record.",
            requested_by="reactive_history_policy")
        pending = approvals.create(request)
        decision = policy.authorize(request)
        if not isinstance(decision, ApprovalDecision):
            raise ReactiveWorkerError("history host must return ApprovalDecision")
        approvals.resume(pending.pending, pending.resume_token, decision)
        consumed = approvals.consume(request.request_id, effect)

        def persist(_active: Loop) -> ActivationHistoryRef:
            target = _history_path(policy.root, binding["run_id"], require_exists=False)
            if target.exists():
                raise ReactiveWorkerError("attempt history already exists; replay is refused")
            history.save(policy.root)
            store_root = _history_path(policy.root, binding["run_id"], "approval",
                                       require_exists=False)
            durable = EffectApprovalService(runtime,
                LocalJsonApprovalStateStore(str(store_root)))
            durable.restore(consumed)
            reference = ActivationHistoryRef(
                binding["run_id"], head, len(history.event_log),
                binding["activation_id"], binding["attempt"], binding["fencing_token"],
                binding["loop_id"], LoopDefinitionRef.from_dict(binding["definition_ref"]),
                trigger.input_ref, binding["series_digest"], binding["trigger_digest"],
                code, request.request_id,
                hashlib.sha256(consumed.to_json().encode("utf-8")).hexdigest())
            self._read_verified_history(reference, policy, series, trigger)
            return reference

        return run_service_operation(runtime, ServiceLoopSpec(
            "persist_reactive_run_history", "practitioner.code_execution",
            "terminal_loop_history", "activation_history_ref/v1",
            ("reads_fs", "writes_fs"), "Persist one exactly authorized reactive history.",
            "reactive_history_persistence_failed"), persist)

    def _read_verified_history(self, reference: ActivationHistoryRef,
                               policy: ReactiveHistoryPolicy,
                               series: ReactiveSeriesDefinition,
                               trigger: TriggerEnvelope):
        from ..loop.approval_state_store import LocalJsonApprovalStateStore
        from ..loop.intelligence_loops import serve_historical_intelligence
        from .run_history import RunHistory

        if (not policy.required or reference.definition_ref != series.loop_definition_ref
                or reference.series_digest != series.content_digest
                or reference.trigger_digest != _digest(trigger.to_dict())
                or reference.input_ref != trigger.input_ref
                or reference.activation_id != trigger.activation_id):
            raise ReactiveWorkerError("history source identity or current binding changed")
        self._registry.resolve(reference.definition_ref)

        for name in ("manifest.json", "events.jsonl"):
            _history_path(policy.root, reference.run_id, name)

        def read(history):
            expected = _reference_binding(reference)
            records = history.event_log
            identities = [event for event in records if
                          event.detail.get("reactive_activation_binding") is not None]
            terminals = [event for event in records if event.event_type == "terminal"
                         and event.loop_id == reference.loop_id]
            initialized = [event for event in records if event.event_type == "loop_init"
                           and event.loop_id == reference.loop_id]
            if (history._committed is not True or not records
                    or len(records) != reference.event_count
                    or records[-1].event_digest != reference.head_digest
                    or any(event.run_id != reference.run_id for event in records)
                    or len(identities) != 1
                    or identities[0].loop_id != reference.loop_id
                    or identities[0].detail["reactive_activation_binding"] != expected
                    or len(terminals) != 1 or terminal_code(
                        terminals[0].detail.get("reason", "")) != reference.terminal_code
                    or not initialized
                    or any(event.detail.get("loop_definition_digest") !=
                           reference.definition_ref.content_digest for event in initialized)):
                raise ReactiveWorkerError("history does not bind the exact committed attempt")
            store_root = _history_path(policy.root, reference.run_id, "approval")
            for directory in ("objects", "locks"):
                _history_path(policy.root, reference.run_id, "approval", directory)
            store = LocalJsonApprovalStateStore(str(store_root))
            object_path = store.object_path(reference.approval_request_id)
            _history_path(policy.root, str(object_path.relative_to(Path(policy.root))))
            lock_name = hashlib.sha256(reference.approval_request_id.encode("utf-8")).hexdigest()
            _history_path(policy.root, reference.run_id, "approval", "locks", lock_name + ".lock")
            record = store.load(reference.approval_request_id)
            if (record.status is not ApprovalStatus.CONSUMED
                    or hashlib.sha256(record.to_json().encode("utf-8")).hexdigest()
                    != reference.approval_record_digest
                    or record.request.loop_id != reference.loop_id
                    or record.request.effect.to_dict() != _history_effect(policy.root, expected,
                        reference.head_digest, reference.event_count, reference.terminal_code).to_dict()):
                raise ReactiveWorkerError("history approval record no longer matches")
            return history

        history = serve_historical_intelligence(
            "reactive-history:" + reference.run_id,
            lambda: read(RunHistory.load(policy.root, reference.run_id)))["value"]
        if not isinstance(history, RunHistory):
            raise ReactiveWorkerError("reactive history could not be read and verified")
        return history

    def load_verified_history(self, activation: ActivationRecord, *,
                              series: ReactiveSeriesDefinition,
                              trigger: TriggerEnvelope):
        """Recheck saved bytes and exact source records; never replay an effect."""
        if (not isinstance(activation, ActivationRecord)
                or activation.history_disposition is not ActivationHistoryDisposition.PERSISTED
                or activation.history_ref is None):
            raise ReactiveWorkerError("activation has no persisted history reference")
        binding = self._bindings.get(activation.loop_definition_ref)
        if binding is None:
            raise ReactiveWorkerError("exact history binding is unavailable")
        return self._read_verified_history(
            activation.history_ref, binding.history_policy, series, trigger)

    def ledger_for(self, activation_id: str) -> LoopLedger:
        ledger = self._ledgers.get(activation_id)
        if ledger is None:
            raise ReactiveWorkerError(
                "activation ledger is unavailable in this worker")
        return ledger


@dataclass(frozen=True)
class ReactiveWorkerRequest:
    """One bounded asynchronous claim and execution attempt."""

    claim: ActivationClaimRequest
    started_at: str
    terminal_at: str


@dataclass(frozen=True)
class ReactiveWorkerOutcome:
    """One worker result, including a no-work outcome without a fake Loop."""

    worker_id: str
    claimed: bool
    activation_id: str = ""
    loop_id: str = ""
    terminal_code: str = ""
    error_code: str = ""
    elapsed_seconds: float = 0.0


class AsyncReactiveWorker:
    """Claim work, execute canonical Loops in threads, and commit by fence."""

    def __init__(self, scheduler: SQLiteReactiveScheduler,
                 executor: CanonicalReactiveExecutor) -> None:
        if not isinstance(scheduler, SQLiteReactiveScheduler):
            raise ReactiveWorkerError(
                "async reactive worker needs SQLiteReactiveScheduler")
        if not isinstance(executor, CanonicalReactiveExecutor):
            raise ReactiveWorkerError(
                "async reactive worker needs CanonicalReactiveExecutor")
        self._scheduler = scheduler
        self._executor = executor

    async def run_once(self, request: ReactiveWorkerRequest) \
            -> ReactiveWorkerOutcome:
        if not isinstance(request, ReactiveWorkerRequest):
            raise ReactiveWorkerError(
                "run_once requires ReactiveWorkerRequest")
        claim = self._scheduler.claim(request.claim)
        if claim is None:
            return ReactiveWorkerOutcome(request.claim.worker_id, False)
        activation = claim.activation
        self._scheduler.start(ActivationStartRequest(
            activation.activation_id, claim.lease.lease_id,
            claim.lease.fencing_token, request.started_at))
        series = self._scheduler.get_series(activation.series_id)
        trigger = self._scheduler.get_trigger(activation.trigger_id)
        if series is None or trigger is None:
            raise ReactiveWorkerError(
                "claimed activation lost its series or trigger")
        try:
            result = await asyncio.to_thread(
                self._executor.execute,
                ReactiveExecutionRequest(series, trigger, claim))
            if result.history_disposition is ActivationHistoryDisposition.PERSISTENCE_FAILED:
                status, error_code = ActivationStatus.FAILED, "HISTORY_PERSISTENCE_FAILED"
            elif result.terminal_code == "ACCEPTED":
                status, error_code = ActivationStatus.COMPLETED, ""
            elif result.terminal_code == "CANCELED":
                status, error_code = ActivationStatus.CANCELED, ""
            else:
                status, error_code = ActivationStatus.FAILED, result.terminal_code
            self._scheduler.terminal(ActivationTerminalRequest(
                activation.activation_id, claim.lease.lease_id,
                claim.lease.fencing_token, status, request.terminal_at,
                result.loop_id, result.terminal_code, error_code,
                history_ref=result.history_ref,
                history_disposition=result.history_disposition))
            return ReactiveWorkerOutcome(
                request.claim.worker_id, True, activation.activation_id,
                result.loop_id, result.terminal_code, error_code,
                result.elapsed_seconds)
        except Exception as exc:
            error_code = type(exc).__name__.upper()
            try:
                self._scheduler.terminal(ActivationTerminalRequest(
                    activation.activation_id, claim.lease.lease_id,
                    claim.lease.fencing_token, ActivationStatus.FAILED,
                    request.terminal_at, failure_code=error_code,
                    history_disposition=(ActivationHistoryDisposition.UNAVAILABLE
                        if self._executor.history_required(activation.loop_definition_ref)
                        else ActivationHistoryDisposition.NOT_PERSISTED)))
            except ReactiveSchedulerError:
                pass
            return ReactiveWorkerOutcome(
                request.claim.worker_id, True, activation.activation_id,
                error_code=error_code)

    async def run_many(
            self, requests: tuple[ReactiveWorkerRequest, ...]
            ) -> tuple[ReactiveWorkerOutcome, ...]:
        if any(not isinstance(item, ReactiveWorkerRequest)
               for item in requests):
            raise ReactiveWorkerError(
                "run_many requires ReactiveWorkerRequest records")
        return tuple(await asyncio.gather(*(
            self.run_once(item) for item in requests)))


__all__ = (
    "AsyncReactiveWorker", "CanonicalActivationResult",
    "CanonicalReactiveExecutor", "ReactiveExecutionRequest",
    "ReactiveHandlerBinding", "ReactiveHistoryPolicy", "ReactiveWorkerError", "ReactiveWorkerOutcome",
    "ReactiveWorkerRequest",
)
