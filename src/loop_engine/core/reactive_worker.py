"""Execute claimed reactive activations as exact canonical Loops.

Owns local asynchronous placement after the durable scheduler grants a lease.
It does not define another runtime, scheduler, provider, or output authority.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Callable

from ..code_nodes.solution_graph import LoopDefinitionRegistry
from ..loop.loop_definition import LoopDefinitionRef, LoopStartRequest
from ..loop.loop_role import LoopRelationship
from ..loop.reactive_activation import (
    ActivationClaimRequest, ActivationStartRequest, ActivationStatus,
    ActivationTerminalRequest, ReactiveSeriesDefinition, TriggerEnvelope)
from ..loop.recursive_loop import Loop, LoopLedger, StepOutcome
from .reactive_scheduler import (
    ActivationClaimResult, ReactiveSchedulerError, SQLiteReactiveScheduler)


class ReactiveWorkerError(RuntimeError):
    """A claimed activation could not run through the canonical Loop."""


ReactiveStepHandler = Callable[[Loop, str, TriggerEnvelope], StepOutcome]


@dataclass(frozen=True)
class ReactiveHandlerBinding:
    """One exact Loop definition bound to its installed step handler."""

    definition_ref: LoopDefinitionRef
    handler: ReactiveStepHandler = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.definition_ref, LoopDefinitionRef):
            raise ReactiveWorkerError(
                "reactive handler requires an exact LoopDefinitionRef")
        if not callable(self.handler):
            raise ReactiveWorkerError("reactive handler must be callable")


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
        self._handlers = {item.definition_ref: item.handler for item in handlers}
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
        handler = self._handlers.get(reference)
        if handler is None:
            raise ReactiveWorkerError(
                "no installed handler matches the exact Loop definition")
        ledger = LoopLedger(id_namespace=request.claim.activation.activation_id)
        loop = Loop(LoopStartRequest(
            request.series.goal, definition, LoopRelationship.starting(),
            self._runtime_context, ledger))
        started = time.monotonic()

        def bound(active: Loop, step: str, _state: dict) -> StepOutcome:
            outcome = handler(active, step, request.trigger)
            if not isinstance(outcome, StepOutcome):
                raise ReactiveWorkerError(
                    "reactive step handler must return StepOutcome")
            return outcome

        steps = loop.steps()
        if not steps:
            raise ReactiveWorkerError(
                "reactive executor requires a finite installed step profile")
        result = loop.run(handler=bound, max_steps=len(steps) + 1)
        if not loop.is_terminal or result.loop_id != loop.loop_id:
            raise ReactiveWorkerError(
                "reactive activation Loop did not terminate honestly")
        elapsed = time.monotonic() - started
        self._ledgers[request.claim.activation.activation_id] = ledger
        return CanonicalActivationResult(
            request.claim.activation.activation_id, loop.loop_id,
            result.terminal_code, definition.ref, round(elapsed, 6), ledger)

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
            self._scheduler.terminal(ActivationTerminalRequest(
                activation.activation_id, claim.lease.lease_id,
                claim.lease.fencing_token, ActivationStatus.COMPLETED,
                request.terminal_at, result.loop_id, result.terminal_code))
            return ReactiveWorkerOutcome(
                request.claim.worker_id, True, activation.activation_id,
                result.loop_id, result.terminal_code, "",
                result.elapsed_seconds)
        except Exception as exc:
            error_code = type(exc).__name__.upper()
            try:
                self._scheduler.terminal(ActivationTerminalRequest(
                    activation.activation_id, claim.lease.lease_id,
                    claim.lease.fencing_token, ActivationStatus.FAILED,
                    request.terminal_at, failure_code=error_code))
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
    "ReactiveHandlerBinding", "ReactiveWorkerError", "ReactiveWorkerOutcome",
    "ReactiveWorkerRequest",
)
