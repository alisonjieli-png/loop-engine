"""Spawned-Loop execution and Runtime Memory ports for typed delegation.

The public ports expose Spawned Loop identity, relationship, configuration facts,
safe counters, bounded run/cancel operations, and an explicitly injected
Runtime Memory service. They never expose the internal Loop, spawning Loop,
goal, or ledger.

This is a Python API boundary, not a security sandbox. Untrusted executor code
still requires process isolation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .loop_role import LoopRelationship, LoopRoleIdentity
from .recursive_loop import Loop, StepOutcome


class SpawnedLoopRuntimePortError(RuntimeError):
    """A Spawned Loop runtime port call violated its typed boundary."""


@dataclass(frozen=True)
class SpawnedLoopRuntimeConfigFacts:
    """Immutable Spawned Loop facts safe for an executor to inspect."""

    framework: str
    logical_kind: str
    replay_guarantee: str
    allowable_modes: tuple[str, ...]
    preferred_modes: tuple[str, ...]
    delegated_modes: tuple[str, ...]
    power: str
    llm_thinking_power: str
    max_depth: "int | None"
    exit_condition: str
    success_confidence_min: float
    steps: tuple[str, ...]

    @classmethod
    def from_loop(cls, spawned_loop: Loop) -> "SpawnedLoopRuntimeConfigFacts":
        config = spawned_loop.config
        return cls(
            framework=config.framework,
            logical_kind=config.logical_kind,
            replay_guarantee=config.replay_guarantee,
            allowable_modes=tuple(config.allowable_modes),
            preferred_modes=tuple(config.preferred_modes),
            delegated_modes=tuple(config.delegated_modes),
            power=config.power,
            llm_thinking_power=config.llm_thinking_power,
            max_depth=config.max_depth,
            exit_condition=config.exit_condition,
            success_confidence_min=config.success_confidence_min,
            steps=tuple(spawned_loop.steps()),
        )


@dataclass(frozen=True)
class SpawnedLoopRuntimeCounters:
    """Safe execution counters with no event history or state objects."""

    steps_run: int
    model_calls: int
    spawned: int
    attempts: int
    accepted_successes: int
    mode_counts: tuple[tuple[str, int], ...]
    terminal: bool
    terminal_code: str


@dataclass(frozen=True)
class SpawnedLoopRuntimeOutcome:
    """Safe value returned after running a Spawned Loop through its port."""

    loop_id: str
    output: str
    confidence: float
    stopped: str
    exit_condition: str
    accepted: bool
    counters: SpawnedLoopRuntimeCounters


@dataclass(frozen=True)
class SpawnedStepRequest:
    """One Spawned Loop step without the internal callback argument."""

    loop_id: str
    step: str
    context_items: tuple[tuple[str, Any], ...]
    counters: SpawnedLoopRuntimeCounters

    def context(self) -> dict[str, Any]:
        """Return a copy of the Spawned Loop's accumulated step context."""
        return dict(self.context_items)


class SpawnedStepHandler(Protocol):
    """Resolve one step through the public Spawned Loop contract."""

    def __call__(self, request: SpawnedStepRequest) -> StepOutcome: ...


class RuntimeMemoryService(Protocol):
    """Explicit service required when a Spawned Loop may share Runtime Memory."""

    def write(self, note: str, *, loop_id: str, topic: str = "general",
              refs: tuple = ()) -> Any: ...

    def read(self, *, topic: "str | None" = None, since: int = 0,
             loop_id: str = "") -> Any: ...

    def search(self, query: str) -> Any: ...


class SpawnedLoopRuntimeMemoryPort:
    """Bind an explicit Runtime Memory service to one Spawned Loop identity."""

    __slots__ = ("__loop_id", "__service")

    def __init__(self, service: RuntimeMemoryService, loop_id: str) -> None:
        required = ("write", "read", "search")
        if any(not callable(getattr(service, name, None)) for name in required):
            raise SpawnedLoopRuntimePortError(
                "Runtime Memory service must implement write, read, and search")
        self.__service = service
        self.__loop_id = loop_id

    @property
    def loop_id(self) -> str:
        return self.__loop_id

    def write(self, note: str, *, topic: str = "general",
              refs: tuple = ()) -> Any:
        return self.__service.write(
            note, loop_id=self.__loop_id, topic=topic, refs=tuple(refs))

    def read(self, *, topic: "str | None" = None, since: int = 0) -> Any:
        return self.__service.read(
            topic=topic, since=since, loop_id=self.__loop_id)

    def search(self, query: str) -> Any:
        return self.__service.search(query)

    def __repr__(self) -> str:
        return f"SpawnedLoopRuntimeMemoryPort(loop_id={self.__loop_id!r})"


class SpawnedLoopRuntimePort:
    """Bounded run/cancel port over one private spawned Loop."""

    __slots__ = ("__loop", "__max_iterations")

    def __init__(self, spawned_loop: Loop, *,
                 max_iterations: "int | None") -> None:
        if not isinstance(spawned_loop, Loop) or spawned_loop.parent is None:
            raise SpawnedLoopRuntimePortError(
                "a runtime port needs an internally owned Spawned Loop")
        if (max_iterations is not None
                and (not isinstance(max_iterations, int)
                     or isinstance(max_iterations, bool)
                     or max_iterations < 1)):
            raise SpawnedLoopRuntimePortError(
                "max_iterations must be positive when provided")
        self.__loop = spawned_loop
        self.__max_iterations = max_iterations

    @property
    def loop_id(self) -> str:
        return self.__loop.loop_id

    @property
    def identity(self) -> LoopRoleIdentity:
        return self.__loop.identity

    @property
    def relationship(self) -> LoopRelationship:
        return self.__loop.relationship

    @property
    def config(self) -> SpawnedLoopRuntimeConfigFacts:
        return SpawnedLoopRuntimeConfigFacts.from_loop(self.__loop)

    @property
    def is_terminal(self) -> bool:
        return self.__loop.is_terminal

    @property
    def counters(self) -> SpawnedLoopRuntimeCounters:
        if getattr(self.__loop, "_it", None) is None:
            return SpawnedLoopRuntimeCounters(
                steps_run=0, model_calls=0, spawned=0, attempts=0,
                accepted_successes=0, mode_counts=(), terminal=False,
                terminal_code="")
        result = self.__loop.result()
        return SpawnedLoopRuntimeCounters(
            steps_run=result.steps_run,
            model_calls=result.model_calls,
            spawned=result.spawned,
            attempts=result.attempts,
            accepted_successes=result.accepted_successes,
            mode_counts=tuple(sorted(result.mode_counts.items())),
            terminal=self.__loop.is_terminal,
            terminal_code=(result.terminal_code
                           if self.__loop.is_terminal else ""),
        )

    def run(self, *, handler: "SpawnedStepHandler | None" = None,
            max_steps: "int | None" = None) -> SpawnedLoopRuntimeOutcome:
        selected_max = self.__max_iterations if max_steps is None else max_steps
        if (selected_max is not None and (
                not isinstance(selected_max, int)
                or isinstance(selected_max, bool) or selected_max < 1
                or (self.__max_iterations is not None
                    and selected_max > self.__max_iterations))):
            raise SpawnedLoopRuntimePortError(
                "max_steps must be positive and within the spawned budget")

        adapted = None
        if handler is not None:
            if not callable(handler):
                raise SpawnedLoopRuntimePortError(
                    "spawned step handler must be callable")

            def adapted(
                    _spawned_loop: Loop, step: str,
                    context: dict) -> StepOutcome:
                outcome = handler(SpawnedStepRequest(
                    loop_id=self.loop_id,
                    step=step,
                    context_items=tuple(context.items()),
                    counters=self.counters,
                ))
                if not isinstance(outcome, StepOutcome):
                    raise SpawnedLoopRuntimePortError(
                        "spawned step handler must return StepOutcome")
                return outcome

        result = self.__loop.run(handler=adapted, max_steps=selected_max)
        return SpawnedLoopRuntimeOutcome(
            loop_id=result.loop_id,
            output=result.output,
            confidence=result.confidence,
            stopped=result.stopped,
            exit_condition=result.exit_condition,
            accepted=result.accepted,
            counters=self.counters,
        )

    def cancel(self, reason: str = "canceled by spawned executor") \
            -> SpawnedLoopRuntimeCounters:
        if not isinstance(reason, str) or not reason.strip():
            raise SpawnedLoopRuntimePortError(
                "cancellation needs a non-empty reason")
        if not self.__loop.is_terminal:
            self.__loop.cancel(reason)
        return self.counters

    def __repr__(self) -> str:
        return (
            f"SpawnedLoopRuntimePort(loop_id={self.loop_id!r}, "
            f"terminal={self.is_terminal!r})")


class DeterministicSpawnedExecutor:
    """Run one deterministic Spawned Loop through its public runtime port."""

    def __call__(self, request):
        from .delegation_runtime import (
            SpawnedLoopResult,
            SpawnedTaskStatus,
            DelegationError,
            LoopPortValue,
        )
        if request.spec.mode != "deterministic":
            raise DelegationError(
                "the default executor accepts deterministic Spawned Loops only")
        if len(request.spec.contract.output_roles) != 1:
            raise DelegationError(
                "the default executor needs one output role; inject an "
                "executor for structured multi-output work")
        result = request.runtime.run(
            max_steps=request.spec.budget.max_iterations)
        status = (SpawnedTaskStatus.SUCCEEDED if result.accepted
                  else SpawnedTaskStatus.FAILED)
        output = ()
        error_code = ""
        error = ""
        if status == SpawnedTaskStatus.SUCCEEDED:
            output = (LoopPortValue(
                request.spec.contract.output_roles[0], result.output),)
        else:
            error_code = result.counters.terminal_code
            error = "the spawned Loop did not reach its accepted outcome"
        summary = ""
        if request.spec.context.summary_return:
            summary = (
                f"Spawned Loop completed {result.counters.steps_run} step(s) "
                f"with terminal code {result.counters.terminal_code}.")
        return SpawnedLoopResult(
            task_id=request.task_id,
            status=status,
            outputs=output,
            summary=summary,
            terminal_code=result.counters.terminal_code,
            steps_run=result.counters.steps_run,
            model_calls=result.counters.model_calls,
            error_code=error_code,
            error=error,
        )
