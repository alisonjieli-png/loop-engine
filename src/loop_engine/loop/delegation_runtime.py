"""Typed spawned-task controls around the existing :class:`Loop` runtime.

Every accepted task uses ``parent.spawn()``. Existing depth, authority, ledger,
and closure rules remain authoritative. Executors receive a Spawned Loop-only
runtime port, must terminate that Loop, and must return its exact output roles.
"""

from __future__ import annotations

import asyncio
import inspect
import re
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Awaitable, Protocol, TYPE_CHECKING

from ..static_architecture.facets import EFFECTS
from .spawned_runtime_port import (DeterministicSpawnedExecutor,
    RuntimeMemoryService, SpawnedLoopRuntimeMemoryPort, SpawnedLoopRuntimePort)
from .spawned_task_checkpoint import SpawnedTaskLifecycleMixin
from .loop_contract import LoopContract
from .loop_profile_catalog import LoopProfileRef
from .loop_profile_ontology import identity_for_profile, resolve_profile
from .loop_role import LoopRelationship, LoopRoleIdentity
from .loop_templates import TEMPLATE_LIBRARY, config_from_template
from .recursive_loop import (MODEL_THINKING_POWER_LEVELS, MODES, Loop, LoopConfig)

if TYPE_CHECKING:  # pragma: no cover
    from ..static_architecture.context_artifacts import ContextArtifactManager


class DelegationError(RuntimeError):
    """A spawned task request or lifecycle transition failed closed."""

class SpawnedTaskStatus(str, Enum):
    """Closed spawned-task lifecycle states."""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    INTERRUPTED = "interrupted"

    @property
    def terminal(self) -> bool:
        return self in {
            SpawnedTaskStatus.SUCCEEDED,
            SpawnedTaskStatus.FAILED,
            SpawnedTaskStatus.CANCELED,
            SpawnedTaskStatus.INTERRUPTED,
        }


class SpawnedReturnDestination(str, Enum):
    """Closed destinations for a Spawned Loop's public return value."""
    PARENT_CONTEXT = "parent_context"
    SHARED_RUNTIME_MEMORY = "shared_runtime_memory"
    CALLER = "caller"


@dataclass(frozen=True)
class SpawnedTaskId:
    """Validated identifier for one dynamically created spawned task."""

    value: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", self.value):
            raise DelegationError(
                "a spawned task id must use letters, numbers, dot, underscore, "
                "colon, or hyphen")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class LoopPortValue:
    """One value bound to one versioned Loop contract role."""

    role: str
    value: Any

    def __post_init__(self) -> None:
        if not isinstance(self.role, str) or not self.role.strip():
            raise DelegationError("a LoopPortValue needs a non-empty role")


@dataclass(frozen=True)
class ContextVisibilityPolicy:
    """What spawning context a Spawned Loop can see and may return.

    The default shares no spawning-Loop references or Runtime Memory. Spawned
    Loop history and raw tool output remain private in every policy.
    """

    fresh: bool = True
    selected_refs: tuple[str, ...] = ()
    shared_runtime_memory: bool = False
    summary_return: bool = True

    def __post_init__(self) -> None:
        for name in ("fresh", "shared_runtime_memory", "summary_return"):
            if not isinstance(getattr(self, name), bool):
                raise DelegationError(f"{name} must be a boolean")
        refs = tuple(self.selected_refs)
        if (any(not isinstance(ref, str) or not ref.strip() for ref in refs)
                or len(refs) != len(set(refs))):
            raise DelegationError(
                "selected_refs must contain unique non-empty references")
        object.__setattr__(self, "selected_refs", refs)


@dataclass(frozen=True)
class DelegationBudget:
    """Hard result ceilings for one Spawned Loop."""

    max_iterations: int = 10
    max_model_calls: int = 0
    max_output_bytes: int = 1_000_000
    max_updates: int = 20
    wall_time_seconds: "float | None" = None

    def __post_init__(self) -> None:
        if any(not isinstance(value, int) or isinstance(value, bool) for value in (
                self.max_iterations, self.max_model_calls,
                self.max_output_bytes, self.max_updates)):
            raise DelegationError("delegation budget values must be integers")
        if self.max_iterations < 1:
            raise DelegationError("max_iterations must be positive")
        if self.max_model_calls < 0:
            raise DelegationError("max_model_calls cannot be negative")
        if self.max_output_bytes < 1:
            raise DelegationError("max_output_bytes must be positive")
        if self.max_updates < 0:
            raise DelegationError("max_updates cannot be negative")
        if (self.wall_time_seconds is not None
                and (not isinstance(self.wall_time_seconds, (int, float))
                     or isinstance(self.wall_time_seconds, bool)
                     or not 0 < float(self.wall_time_seconds) < float("inf"))):
            raise DelegationError("wall_time_seconds must be positive when set")


@dataclass(frozen=True)
class DelegationConstraints:
    """Profile fields, capabilities, and effects the Spawned Loop may use."""

    available_fields: tuple[str, ...] = ()
    capability_refs: tuple[str, ...] = ()
    allowed_effects: tuple[str, ...] = ("pure",)

    def __post_init__(self) -> None:
        for name in ("available_fields", "capability_refs",
                     "allowed_effects"):
            values = tuple(getattr(self, name))
            if (any(not isinstance(value, str) or not value.strip()
                    for value in values)
                    or len(values) != len(set(values))):
                raise DelegationError(
                    f"{name} must contain unique non-empty strings")
            object.__setattr__(self, name, values)
        unknown = [effect for effect in self.allowed_effects
                   if effect not in EFFECTS]
        if unknown:
            raise DelegationError(
                f"allowed_effects contains unknown values {unknown!r}")
        if ("pure" in self.allowed_effects
                and len(self.allowed_effects) > 1):
            raise DelegationError("pure cannot be combined with other effects")


@dataclass(frozen=True)
class DelegationSpec:
    """One complete, typed request to start a Spawned Loop."""

    goal: str
    profile: LoopProfileRef
    contract: LoopContract
    inputs: tuple[LoopPortValue, ...] = ()
    mode: str = "deterministic"
    budget: DelegationBudget = field(default_factory=DelegationBudget)
    context: ContextVisibilityPolicy = field(
        default_factory=ContextVisibilityPolicy)
    workspace_policy_ref: str = ""
    return_destination: SpawnedReturnDestination = (
        SpawnedReturnDestination.PARENT_CONTEXT)
    constraints: DelegationConstraints = field(
        default_factory=DelegationConstraints)
    delegated_modes: tuple[str, ...] = ()
    llm_thinking_power: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.goal, str) or not self.goal.strip():
            raise DelegationError("a DelegationSpec needs a goal")
        if not isinstance(self.profile, LoopProfileRef):
            raise DelegationError("profile must be a LoopProfileRef")
        if not isinstance(self.contract, LoopContract):
            raise DelegationError("contract must be a LoopContract")
        if not isinstance(self.budget, DelegationBudget):
            raise DelegationError("budget must be a DelegationBudget")
        if not isinstance(self.context, ContextVisibilityPolicy):
            raise DelegationError("context must be a ContextVisibilityPolicy")
        if not isinstance(self.constraints, DelegationConstraints):
            raise DelegationError("constraints must be DelegationConstraints")
        values = tuple(self.inputs)
        if any(not isinstance(value, LoopPortValue) for value in values):
            raise DelegationError("inputs must contain LoopPortValue objects")
        roles = tuple(value.role for value in values)
        if len(roles) != len(set(roles)):
            raise DelegationError("input roles cannot be repeated")
        missing = [role for role in self.contract.input_roles
                   if role not in roles]
        extra = [role for role in roles
                 if role not in self.contract.input_roles]
        if missing or extra:
            raise DelegationError(
                f"inputs do not match the LoopContract; missing {missing!r}; "
                f"unexpected {extra!r}")
        object.__setattr__(self, "inputs", values)
        if self.mode not in MODES:
            raise DelegationError(f"mode must be one of {MODES}")
        delegated_modes = tuple(self.delegated_modes)
        if any(mode not in MODES for mode in delegated_modes):
            raise DelegationError(f"delegated_modes must use {MODES}")
        object.__setattr__(self, "delegated_modes", delegated_modes)
        if (not isinstance(self.workspace_policy_ref, str)
                or (self.workspace_policy_ref
                    and not self.workspace_policy_ref.strip())):
            raise DelegationError(
                "workspace_policy_ref must be empty or a non-empty string")
        destination = self.return_destination
        if not isinstance(destination, SpawnedReturnDestination):
            try:
                destination = SpawnedReturnDestination(destination)
            except (TypeError, ValueError) as exc:
                raise DelegationError(
                    "return_destination is not recognized") from exc
            object.__setattr__(self, "return_destination", destination)
        if (destination == SpawnedReturnDestination.SHARED_RUNTIME_MEMORY
                and not self.context.shared_runtime_memory):
            raise DelegationError(
                "a shared_runtime_memory return needs explicit Runtime "
                "Memory sharing")
        if (self.llm_thinking_power
                and self.llm_thinking_power
                not in MODEL_THINKING_POWER_LEVELS):
            raise DelegationError(
                "llm_thinking_power must be small, medium, high, max, or "
                "specialized")
        if self.mode == "deterministic" and self.llm_thinking_power:
            raise DelegationError(
                "a deterministic Spawned Loop cannot request LLM thinking power")
        if (self.mode == "non_deterministic"
                and self.budget.max_model_calls < 1):
            raise DelegationError(
                "a non_deterministic Spawned Loop needs a positive model-call "
                "budget")


@dataclass(frozen=True)
class SpawnedTaskUpdate:
    """Typed information added while a Spawned Loop is still running."""

    inputs: tuple[LoopPortValue, ...] = ()
    instruction: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.instruction, str):
            raise DelegationError("update instruction must be a string")
        values = tuple(self.inputs)
        if any(not isinstance(value, LoopPortValue) for value in values):
            raise DelegationError(
                "update inputs must contain LoopPortValue objects")
        roles = [value.role for value in values]
        if len(roles) != len(set(roles)):
            raise DelegationError("update input roles cannot repeat")
        if not values and not self.instruction.strip():
            raise DelegationError("an update needs inputs or an instruction")
        object.__setattr__(self, "inputs", values)


class SpawnedTaskControl:
    """Read-only lifecycle signals available to an injected executor."""

    def __init__(self) -> None:
        self._updates: list[SpawnedTaskUpdate] = []
        self._cancel_requested = False

    @property
    def cancel_requested(self) -> bool:
        return self._cancel_requested

    def updates(self) -> tuple[SpawnedTaskUpdate, ...]:
        return tuple(self._updates)

    def _add_update(self, update: SpawnedTaskUpdate) -> None:
        self._updates.append(update)

    def _request_cancel(self) -> None:
        self._cancel_requested = True


@dataclass(frozen=True)
class SpawnedExecutionRequest:
    """Public Spawned Loop-only request passed to an injected executor."""

    task_id: SpawnedTaskId
    runtime: SpawnedLoopRuntimePort
    spec: DelegationSpec
    control: SpawnedTaskControl
    runtime_memory: SpawnedLoopRuntimeMemoryPort | None = None


@dataclass(frozen=True)
class SpawnedLoopResult:
    """Typed return with no Loop, history, messages, or raw tool output."""

    task_id: SpawnedTaskId
    status: SpawnedTaskStatus
    outputs: tuple[LoopPortValue, ...] = ()
    summary: str = ""
    terminal_code: str = ""
    steps_run: int = 0
    model_calls: int = 0
    error_code: str = ""
    error: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, SpawnedTaskId):
            raise DelegationError("result.task_id must be a SpawnedTaskId")
        status = self.status
        if not isinstance(status, SpawnedTaskStatus):
            try:
                status = SpawnedTaskStatus(status)
            except (TypeError, ValueError) as exc:
                raise DelegationError("result status is not recognized") from exc
            object.__setattr__(self, "status", status)
        if not status.terminal:
            raise DelegationError("SpawnedLoopResult status must be terminal")
        values = tuple(self.outputs)
        if any(not isinstance(value, LoopPortValue) for value in values):
            raise DelegationError(
                "result outputs must contain LoopPortValue objects")
        roles = [value.role for value in values]
        if len(roles) != len(set(roles)):
            raise DelegationError("result output roles cannot repeat")
        object.__setattr__(self, "outputs", values)
        for name in ("summary", "terminal_code", "error_code", "error"):
            if not isinstance(getattr(self, name), str):
                raise DelegationError(f"result {name} must be a string")
        if any(not isinstance(value, int) or isinstance(value, bool)
               for value in (self.steps_run, self.model_calls)):
            raise DelegationError("result counters must be integers")
        if self.steps_run < 0 or self.model_calls < 0:
            raise DelegationError("result counters cannot be negative")
        if status == SpawnedTaskStatus.SUCCEEDED and (self.error_code or self.error):
            raise DelegationError(
                "a successful spawned result cannot carry an error")
        if status != SpawnedTaskStatus.SUCCEEDED and not self.error_code:
            raise DelegationError(
                "a failed or canceled spawned result needs an error_code")
@dataclass(frozen=True)
class SpawnedTaskSnapshot:
    """Safe lifecycle view returned by status and list operations."""

    task_id: SpawnedTaskId
    status: SpawnedTaskStatus
    goal: str
    profile: LoopProfileRef
    identity: LoopRoleIdentity
    relationship: LoopRelationship
    updates: int = 0
    result: SpawnedLoopResult | None = None


@dataclass(frozen=True)
class SpawnedTaskManagerLimits:
    """Bounded task counts for one parent manager."""

    max_active: int = 8
    max_total: int = 100

    def __post_init__(self) -> None:
        if any(not isinstance(value, int) or isinstance(value, bool)
               for value in (self.max_active, self.max_total)):
            raise DelegationError("manager limits must be integers")
        if self.max_active < 1 or self.max_total < 1:
            raise DelegationError("manager limits must be positive")
        if self.max_active > self.max_total:
            raise DelegationError("max_active cannot exceed max_total")


class SpawnedExecutor(Protocol):
    """Callable boundary for synchronous or asynchronous spawned execution."""
    def __call__(self, request: SpawnedExecutionRequest
                 ) -> SpawnedLoopResult | Awaitable[SpawnedLoopResult]:
        ...


@dataclass
class _SpawnedTaskRecord:
    task_id: SpawnedTaskId
    spec: DelegationSpec
    spawned_loop: Loop | None
    runtime: SpawnedLoopRuntimePort | None
    control: SpawnedTaskControl
    identity: LoopRoleIdentity
    relationship: LoopRelationship
    status: SpawnedTaskStatus = SpawnedTaskStatus.QUEUED
    result: SpawnedLoopResult | None = None
    async_task: asyncio.Task | None = None


class SpawnedTaskManager(SpawnedTaskLifecycleMixin):
    """Manage bounded spawned tasks for one spawning Loop."""

    def __init__(self, parent: Loop, executor: SpawnedExecutor | None = None,
                 limits: SpawnedTaskManagerLimits | None = None, *,
                 runtime_memory: RuntimeMemoryService | None = None,
                 context_artifacts: "ContextArtifactManager | None" = None) -> None:
        if not isinstance(parent, Loop):
            raise DelegationError("parent must be a Loop")
        self._parent = parent
        self._executor = executor or DeterministicSpawnedExecutor()
        self._limits = limits or SpawnedTaskManagerLimits()
        if runtime_memory is not None and any(not callable(getattr(
                runtime_memory, name, None))
                for name in ("write", "read", "search")):
            raise DelegationError(
                "runtime_memory must implement write, read, and search")
        if context_artifacts is not None:
            from ..static_architecture.context_artifacts import ContextArtifactManager
            if not isinstance(context_artifacts, ContextArtifactManager):
                raise DelegationError(
                    "context_artifacts must be a ContextArtifactManager")
        self._runtime_memory = runtime_memory
        self._context_artifacts = context_artifacts
        self._records: dict[SpawnedTaskId, _SpawnedTaskRecord] = {}
        self._counter = 0

    def start(self, spec: DelegationSpec) -> SpawnedTaskId:
        """Start one synchronous spawned executor and return its task ID."""
        if self._executor_is_async():
            raise DelegationError(
                "this executor is asynchronous; use start_async()")
        record = self._prepare(spec)
        try:
            value = self._executor(self._request(record))
            if inspect.isawaitable(value):
                close = getattr(value, "close", None)
                if callable(close):
                    close()
                raise DelegationError(
                    "executor returned an awaitable; use start_async()")
            self._finish(record, value)
        except Exception as exc:
            self._fail(record, "EXECUTOR_FAILED", str(exc))
        return record.task_id

    async def start_async(self, spec: DelegationSpec) -> SpawnedTaskId:
        """Schedule an asynchronous spawned executor and return its task ID."""
        if not self._executor_is_async():
            raise DelegationError(
                "this executor is synchronous; use start()")
        record = self._prepare(spec)
        record.async_task = asyncio.create_task(self._execute_async(record))
        await asyncio.sleep(0)
        return record.task_id

    def status(self, task_id: SpawnedTaskId) -> SpawnedTaskSnapshot:
        """Return a safe snapshot without Spawned Loop internals."""
        return self._snapshot(self._record(task_id))

    def update(self, task_id: SpawnedTaskId,
               update: SpawnedTaskUpdate) -> SpawnedTaskSnapshot:
        """Add typed information to a running spawned task."""
        record = self._record(task_id)
        if record.status.terminal:
            raise DelegationError("a terminal spawned task cannot be updated")
        if len(record.control.updates()) >= record.spec.budget.max_updates:
            raise DelegationError("the spawned update budget is exhausted")
        unexpected = [value.role for value in update.inputs
                      if value.role not in record.spec.contract.input_roles]
        if unexpected:
            raise DelegationError(
                f"update roles are outside the input contract {unexpected!r}")
        record.control._add_update(update)
        self._parent.ledger.record(
            loop_id=self._parent.loop_id,
            event="custom",
            custom_kind="spawned_task_updated",
            spawned_task_id=str(task_id),
            input_roles=tuple(value.role for value in update.inputs),
            has_instruction=bool(update.instruction.strip()),
        )
        return self._snapshot(record)

    def cancel(self, task_id: SpawnedTaskId,
               reason: str = "canceled by spawning Loop") -> SpawnedTaskSnapshot:
        """Cancel a queued or running spawned task and close its Loop."""
        if not isinstance(reason, str) or not reason.strip():
            raise DelegationError("a cancellation needs a non-empty reason")
        record = self._record(task_id)
        if record.status.terminal:
            return self._snapshot(record)
        record.control._request_cancel()
        if record.async_task is not None and not record.async_task.done():
            record.async_task.cancel()
        if record.spawned_loop is not None and not record.spawned_loop.is_terminal:
            record.spawned_loop.cancel(reason)
        counters = record.runtime.counters if record.runtime is not None else None
        result = SpawnedLoopResult(
            task_id=record.task_id,
            status=SpawnedTaskStatus.CANCELED,
            terminal_code="CANCELED",
            steps_run=counters.steps_run if counters else 0, model_calls=counters.model_calls if counters else 0,
            error_code="CANCELED",
            error=reason,
        )
        self._publish(record, result)
        return self._snapshot(record)

    def _prepare(self, spec: DelegationSpec) -> _SpawnedTaskRecord:
        if not isinstance(spec, DelegationSpec):
            raise DelegationError("start expects a DelegationSpec")
        active = sum(1 for record in self._records.values()
                     if not record.status.terminal)
        if active >= self._limits.max_active:
            raise DelegationError("the active spawned-task limit is reached")
        if len(self._records) >= self._limits.max_total:
            raise DelegationError("the total spawned-task limit is reached")
        self._validate_spec(spec)
        spec, offloaded = self._prepare_input_context(spec)
        self._counter += 1
        task_id = SpawnedTaskId(
            f"{self._parent.loop_id}.spawned-task.{self._counter}")
        config = self._spawned_loop_config(spec)
        identity = identity_for_profile(spec.profile)
        relationship = LoopRelationship.spawned_by(self._parent.loop_id)
        spawned_loop = self._parent.spawn(
            spec.goal, config, contract=spec.contract,
            identity=identity, relationship=relationship)
        record = _SpawnedTaskRecord(
            task_id=task_id,
            spec=spec,
            spawned_loop=spawned_loop,
            runtime=SpawnedLoopRuntimePort(
                spawned_loop, max_iterations=spec.budget.max_iterations),
            control=SpawnedTaskControl(),
            identity=identity, relationship=relationship,
            status=SpawnedTaskStatus.RUNNING,
        )
        self._records[task_id] = record
        self._parent.ledger.record(
            loop_id=self._parent.loop_id,
            event="custom",
            custom_kind="spawned_task_started",
            spawned_task_id=str(task_id),
            spawned_loop_id=spawned_loop.loop_id,
            profile=spec.profile.profile_id,
            role=identity.role.value,
            **relationship.to_dict(),
            mode=spec.mode,
            selected_ref_count=len(spec.context.selected_refs),
            shared_runtime_memory=spec.context.shared_runtime_memory,
            return_destination=spec.return_destination.value,
            workspace_policy_ref=spec.workspace_policy_ref,
            offloaded_input_roles=tuple(role for role, _digest in offloaded),
            offloaded_input_digests=tuple(
                digest for _role, digest in offloaded),
        )
        return record

    def _prepare_input_context(self, spec: DelegationSpec
            ) -> tuple[DelegationSpec, tuple[tuple[str, str], ...]]:
        if self._context_artifacts is None or not spec.context.fresh:
            return spec, ()
        prepared = []
        offloaded = []
        for port in spec.inputs:
            if not isinstance(port.value, str):
                prepared.append(port)
                continue
            payload = self._context_artifacts.capture(
                port.value, artifact_kind="spawned_loop_input")
            if payload.offloaded:
                prepared.append(LoopPortValue(port.role, payload.raw))
                offloaded.append((port.role, payload.raw.digest))
            else:
                prepared.append(port)
        if not offloaded:
            return spec, ()
        return replace(spec, inputs=tuple(prepared)), tuple(offloaded)

    def _validate_spec(self, spec: DelegationSpec) -> None:
        if (spec.context.shared_runtime_memory
                and self._runtime_memory is None):
            raise DelegationError(
                "shared Runtime Memory requires an explicit typed service")
        if spec.mode not in self._parent.config.delegated_modes:
            raise DelegationError(
                f"parent cannot delegate mode {spec.mode!r}; allowed "
                f"{tuple(self._parent.config.delegated_modes)!r}")
        if spec.contract.runtime_mode != spec.mode:
            raise DelegationError(
                f"contract runtime mode {spec.contract.runtime_mode!r} does "
                f"not match delegated mode {spec.mode!r}")
        profile = resolve_profile(spec.profile)
        if profile.spec.state != "registered":
            raise DelegationError("only a registered Loop profile can run")
        if spec.mode not in profile.allowed_modes:
            raise DelegationError(
                f"profile {spec.profile.profile_id!r} does not allow "
                f"mode {spec.mode!r}")
        automatic_fields = {
            "loop_contract", "loop_condition", "exit_condition",
            "step_profile", "mode_policy",
        }
        available = automatic_fields | set(
            spec.constraints.available_fields)
        missing_fields = [field for field in profile.required_fields
                          if field not in available]
        if missing_fields:
            raise DelegationError(
                f"profile is missing required fields {missing_fields!r}")
        missing_capabilities = [
            capability for capability in profile.required_capabilities
            if capability not in spec.constraints.capability_refs
        ]
        if missing_capabilities:
            raise DelegationError(
                "profile is missing required capabilities "
                f"{missing_capabilities!r}")
        excess_effects = [effect for effect in spec.contract.effects
                          if effect not in spec.constraints.allowed_effects]
        if excess_effects:
            raise DelegationError(
                f"spawned effects exceed the delegation constraints "
                f"{excess_effects!r}")
        if any(mode not in self._parent.config.delegated_modes
               for mode in spec.delegated_modes):
            raise DelegationError(
                "spawned delegation authority exceeds the spawning Loop's "
                "authority")

    def _spawned_loop_config(self, spec: DelegationSpec) -> LoopConfig:
        profile = resolve_profile(spec.profile)
        template = next(
            dict(item) for item in TEMPLATE_LIBRARY
            if item["template_id"] == profile.step_template_id)
        template["allowed_modes"] = (spec.mode,)
        template["logical_kind"] = profile.allowed_logical_kinds[0]
        template["loop_condition"] = profile.loop_condition
        template["exit_condition"] = profile.exit_condition
        config = config_from_template(
            template,
            power=self._parent.config.power,
            max_depth=self._parent.config.max_depth,
        )
        thinking = spec.llm_thinking_power
        if spec.mode in ("hybrid", "non_deterministic") and not thinking:
            thinking = self._parent.config.llm_thinking_power or "medium"
        return replace(
            config,
            allowable_modes=(spec.mode,),
            preferred_modes=(spec.mode,),
            delegated_modes=spec.delegated_modes,
            llm_thinking_power=thinking,
        )

    def _request(self, record: _SpawnedTaskRecord) -> SpawnedExecutionRequest:
        if record.runtime is None or record.spawned_loop is None:
            raise DelegationError(
                "a restored terminal task has no executor request")
        memory = None
        if record.spec.context.shared_runtime_memory:
            memory = SpawnedLoopRuntimeMemoryPort(
                self._runtime_memory, record.spawned_loop.loop_id)
        return SpawnedExecutionRequest(
            record.task_id, record.runtime, record.spec, record.control,
            memory)

    async def _execute_async(self, record: _SpawnedTaskRecord) -> None:
        try:
            value = self._executor(self._request(record))
            if not inspect.isawaitable(value):
                raise DelegationError(
                    "asynchronous executor returned a synchronous result")
            timeout = record.spec.budget.wall_time_seconds
            result = (await value if timeout is None else
                      await asyncio.wait_for(value, timeout=float(timeout)))
            if not record.status.terminal:
                self._finish(record, result)
        except TimeoutError:
            self._fail(
                record, "DEADLINE_EXCEEDED",
                "spawned executor exceeded its wall-time deadline",
                terminal_code="DEADLINE_EXCEEDED")
        except asyncio.CancelledError:
            if not record.status.terminal:
                self.cancel(record.task_id)
        except Exception as exc:
            self._fail(record, "EXECUTOR_FAILED", str(exc))

    def _finish(self, record: _SpawnedTaskRecord, result: Any) -> None:
        if not isinstance(result, SpawnedLoopResult):
            raise DelegationError(
                "executor must return a SpawnedLoopResult")
        if result.task_id != record.task_id:
            raise DelegationError("executor returned the wrong task id")
        if record.spawned_loop is None or not record.spawned_loop.is_terminal:
            raise DelegationError(
                "executor returned before the Spawned Loop reached a terminal "
                "state")
        if result.status == SpawnedTaskStatus.SUCCEEDED:
            expected = tuple(record.spec.contract.output_roles)
            actual = tuple(value.role for value in result.outputs)
            if actual != expected:
                raise DelegationError(
                    f"result output roles {actual!r} do not match "
                    f"{expected!r}")
            if (record.spec.context.summary_return
                    and not result.summary.strip()):
                raise DelegationError(
                    "the context policy requires a return summary")
        if not record.spec.context.summary_return and result.summary:
            result = replace(result, summary="")
        if result.steps_run > record.spec.budget.max_iterations:
            raise DelegationError("spawned task exceeded its iteration budget")
        if result.model_calls > record.spec.budget.max_model_calls:
            raise DelegationError("spawned task exceeded its model-call budget")
        size = sum(
            len(value.role.encode("utf-8"))
            + len(repr(value.value).encode("utf-8"))
            for value in result.outputs)
        size += len(result.summary.encode("utf-8"))
        if size > record.spec.budget.max_output_bytes:
            raise DelegationError("spawned result exceeded its output budget")
        self._publish(record, result)

    def _fail(self, record: _SpawnedTaskRecord, code: str, error: str, *,
              terminal_code: str = "INTERNAL_PROTOCOL_ERROR") -> None:
        if record.status.terminal:
            return
        if record.spawned_loop is not None and not record.spawned_loop.is_terminal:
            record.spawned_loop.cancel("spawned executor failed")
        counters = record.runtime.counters if record.runtime is not None else None
        result = SpawnedLoopResult(
            task_id=record.task_id,
            status=SpawnedTaskStatus.FAILED,
            terminal_code=terminal_code,
            steps_run=counters.steps_run if counters else 0, model_calls=counters.model_calls if counters else 0,
            error_code=code,
            error=error or "spawned executor failed",
        )
        self._publish(record, result)

    def _publish(self, record: _SpawnedTaskRecord,
                 result: SpawnedLoopResult) -> None:
        record.status = result.status
        record.result = result
        self._parent.ledger.record(
            loop_id=self._parent.loop_id,
            event="custom",
            custom_kind="spawned_task_terminal",
            spawned_task_id=str(record.task_id),
            status=result.status.value,
            terminal_code=result.terminal_code,
            output_roles=tuple(value.role for value in result.outputs),
            steps_run=result.steps_run,
            model_calls=result.model_calls,
            error_code=result.error_code,
        )

    def _record(self, task_id: SpawnedTaskId) -> _SpawnedTaskRecord:
        if not isinstance(task_id, SpawnedTaskId):
            raise DelegationError("task_id must be a SpawnedTaskId")
        try:
            return self._records[task_id]
        except KeyError as exc:
            raise DelegationError(
                f"unknown spawned task {task_id}") from exc

    @staticmethod
    def _snapshot(record: _SpawnedTaskRecord) -> SpawnedTaskSnapshot:
        return SpawnedTaskSnapshot(
            task_id=record.task_id,
            status=record.status,
            goal=record.spec.goal,
            profile=record.spec.profile,
            identity=record.identity, relationship=record.relationship,
            updates=len(record.control.updates()),
            result=record.result,
        )
def self_test() -> dict:
    from .delegation_runtime_checks import run_checks
    return run_checks()
