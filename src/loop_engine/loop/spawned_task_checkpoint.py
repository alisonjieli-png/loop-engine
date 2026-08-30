"""Versioned spawned-task checkpoints and bounded async lifecycle joins.

Checkpoints preserve typed lifecycle metadata and terminal results. They never
serialize coroutines or claim that queued or running work resumed after restore.
"""
from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import re
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

from .loop_contract import LoopContract
from .loop_profile_catalog import LoopProfileRef
from .loop_role import LoopRelationship, LoopRoleIdentity

if TYPE_CHECKING:
    from .delegation_runtime import (
        SpawnedLoopResult,
        SpawnedTaskId,
        SpawnedTaskStatus,
        DelegationSpec,
    )


SPAWNED_TASK_CHECKPOINT_VERSION = "spawned_task_checkpoint/v2"
_SUPPORTED_SPAWNED_TASK_CHECKPOINT_VERSIONS = (
    SPAWNED_TASK_CHECKPOINT_VERSION,)
_UNSET = object()


class SpawnedTaskCheckpointError(ValueError):
    """Checkpoint state, schema, or digest failed closed."""


def _digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _known(value: dict, fields: tuple[str, ...], label: str) -> None:
    unknown = set(value) - set(fields)
    missing = set(fields) - set(value)
    if unknown or missing:
        raise SpawnedTaskCheckpointError(
            f"{label} fields mismatch; unknown {sorted(unknown)}; "
            f"missing {sorted(missing)}")


def _encode_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return {"type": "list", "items": [_encode_value(item) for item in value]}
    if isinstance(value, tuple):
        return {"type": "tuple", "items": [_encode_value(item) for item in value]}
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise SpawnedTaskCheckpointError(
                "checkpoint dictionaries require string keys")
        return {"type": "dict", "items": {
            key: _encode_value(item) for key, item in sorted(value.items())}}
    from ..core.context_artifacts import ContextArtifactRef
    if isinstance(value, ContextArtifactRef):
        return {"type": "context_artifact_ref", "value": value.to_dict()}
    from .spawned_workspace_executor import WorkspaceSpawnedCommandOutput
    if isinstance(value, WorkspaceSpawnedCommandOutput):
        return {"type": "workspace_spawned_command_output",
                "value": value.safe_summary()}
    raise SpawnedTaskCheckpointError(
        f"checkpoint value type {type(value).__name__!r} is not serializable")


def _decode_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if not isinstance(value, dict) or "type" not in value:
        raise SpawnedTaskCheckpointError(
            "encoded checkpoint value is invalid")
    kind = value["type"]
    if kind in ("list", "tuple"):
        _known(value, ("type", "items"), "sequence value")
        items = [_decode_value(item) for item in value["items"]]
        return items if kind == "list" else tuple(items)
    if kind == "dict":
        _known(value, ("type", "items"), "mapping value")
        return {str(key): _decode_value(item)
                for key, item in value["items"].items()}
    if kind == "context_artifact_ref":
        _known(value, ("type", "value"), "artifact value")
        from ..core.context_artifacts import ContextArtifactRef
        return ContextArtifactRef.from_dict(value["value"])
    if kind == "workspace_spawned_command_output":
        _known(value, ("type", "value"), "workspace output value")
        from .spawned_workspace_executor import WorkspaceSpawnedCommandOutput
        summary = value["value"]
        from ..core.context_artifacts import ContextArtifactRef
        return WorkspaceSpawnedCommandOutput(
            plan_digest=summary["plan_digest"],
            workspace_id=summary["workspace_id"],
            backend_kind=summary["backend_kind"],
            ok=summary["ok"],
            exit_code=summary["exit_code"],
            output_ref=ContextArtifactRef.from_dict(summary["output_ref"]),
            offloaded=summary["offloaded"],
            output_truncated=summary["output_truncated"],
            command_attempts=summary["command_attempts"],
            error_code=summary["error_code"])
    raise SpawnedTaskCheckpointError(
        f"unknown encoded value type {kind!r}")


def _contract_to_dict(contract: LoopContract) -> dict:
    return {
        "name": contract.name,
        "execution_mode": contract.execution_mode,
        "input_roles": list(contract.input_roles),
        "output_roles": list(contract.output_roles),
        "effects": list(contract.effects),
        "locality": contract.locality,
        "cost_class": contract.cost_class,
        "role": contract.role,
    }


def _contract_from_dict(value: dict) -> LoopContract:
    fields = ("name", "execution_mode", "input_roles", "output_roles",
              "effects", "locality", "cost_class", "role")
    _known(value, fields, "Loop contract")
    return LoopContract(
        name=str(value["name"]),
        execution_mode=str(value["execution_mode"]),
        input_roles=tuple(value["input_roles"]),
        output_roles=tuple(value["output_roles"]),
        effects=tuple(value["effects"]),
        locality=str(value["locality"]),
        cost_class=str(value["cost_class"]),
        role=str(value["role"]),
    )


def _spec_to_dict(spec: "DelegationSpec") -> dict:
    return {
        "goal": spec.goal,
        "profile": {"profile_id": spec.profile.profile_id,
                    "version": spec.profile.version},
        "contract": _contract_to_dict(spec.contract),
        "inputs": [{"role": item.role, "value": _encode_value(item.value)}
                   for item in spec.inputs],
        "mode": spec.mode,
        "budget": {
            "max_iterations": spec.budget.max_iterations,
            "max_model_calls": spec.budget.max_model_calls,
            "max_output_bytes": spec.budget.max_output_bytes,
            "max_updates": spec.budget.max_updates,
            "wall_time_seconds": spec.budget.wall_time_seconds,
        },
        "context": {
            "fresh": spec.context.fresh,
            "selected_refs": list(spec.context.selected_refs),
            "shared_runtime_memory": spec.context.shared_runtime_memory,
            "summary_return": spec.context.summary_return,
        },
        "workspace_policy_ref": spec.workspace_policy_ref,
        "return_destination": spec.return_destination.value,
        "constraints": {
            "available_fields": list(spec.constraints.available_fields),
            "capability_refs": list(spec.constraints.capability_refs),
            "allowed_effects": list(spec.constraints.allowed_effects),
        },
        "delegated_modes": list(spec.delegated_modes),
        "llm_thinking_power": spec.llm_thinking_power,
    }


def _spec_from_dict(value: dict) -> "DelegationSpec":
    fields = ("goal", "profile", "contract", "inputs", "mode", "budget",
              "context", "workspace_policy_ref", "return_destination",
              "constraints", "delegated_modes", "llm_thinking_power")
    _known(value, fields, "delegation spec")
    from .delegation_runtime import (
        SpawnedReturnDestination,
        ContextVisibilityPolicy,
        DelegationBudget,
        DelegationConstraints,
        DelegationSpec,
        LoopPortValue,
    )
    profile = value["profile"]
    _known(profile, ("profile_id", "version"), "profile reference")
    budget = value["budget"]
    _known(budget, ("max_iterations", "max_model_calls", "max_output_bytes",
                    "max_updates", "wall_time_seconds"), "delegation budget")
    context = value["context"]
    _known(context, ("fresh", "selected_refs", "shared_runtime_memory",
                     "summary_return"), "context policy")
    constraints = value["constraints"]
    _known(constraints, ("available_fields", "capability_refs",
                         "allowed_effects"), "delegation constraints")
    return DelegationSpec(
        goal=str(value["goal"]),
        profile=LoopProfileRef(
            str(profile["profile_id"]), str(profile["version"])),
        contract=_contract_from_dict(value["contract"]),
        inputs=tuple(LoopPortValue(
            str(item["role"]), _decode_value(item["value"]))
            for item in value["inputs"]),
        mode=str(value["mode"]),
        budget=DelegationBudget(**budget),
        context=ContextVisibilityPolicy(
            fresh=context["fresh"],
            selected_refs=tuple(context["selected_refs"]),
            shared_runtime_memory=context["shared_runtime_memory"],
            summary_return=context["summary_return"]),
        workspace_policy_ref=str(value["workspace_policy_ref"]),
        return_destination=SpawnedReturnDestination(
            value["return_destination"]),
        constraints=DelegationConstraints(
            available_fields=tuple(constraints["available_fields"]),
            capability_refs=tuple(constraints["capability_refs"]),
            allowed_effects=tuple(constraints["allowed_effects"])),
        delegated_modes=tuple(value["delegated_modes"]),
        llm_thinking_power=str(value["llm_thinking_power"]),
    )


def _result_to_dict(result: "SpawnedLoopResult | None") -> "dict | None":
    if result is None:
        return None
    return {
        "task_id": str(result.task_id),
        "status": result.status.value,
        "outputs": [{"role": item.role, "value": _encode_value(item.value)}
                    for item in result.outputs],
        "summary": result.summary,
        "terminal_code": result.terminal_code,
        "steps_run": result.steps_run,
        "model_calls": result.model_calls,
        "error_code": result.error_code,
        "error": result.error,
    }


def _result_from_dict(value: "dict | None") -> "SpawnedLoopResult | None":
    if value is None:
        return None
    fields = ("task_id", "status", "outputs", "summary", "terminal_code",
              "steps_run", "model_calls", "error_code", "error")
    _known(value, fields, "spawned Loop result")
    from .delegation_runtime import (
        LoopPortValue, SpawnedLoopResult, SpawnedTaskId, SpawnedTaskStatus)
    return SpawnedLoopResult(
        task_id=SpawnedTaskId(str(value["task_id"])),
        status=SpawnedTaskStatus(value["status"]),
        outputs=tuple(LoopPortValue(
            str(item["role"]), _decode_value(item["value"]))
            for item in value["outputs"]),
        summary=str(value["summary"]),
        terminal_code=str(value["terminal_code"]),
        steps_run=int(value["steps_run"]),
        model_calls=int(value["model_calls"]),
        error_code=str(value["error_code"]),
        error=str(value["error"]),
    )


@dataclass(frozen=True)
class SpawnedTaskCheckpoint:
    """Serializable spawned lifecycle state with no coroutine or Loop object."""

    task_id: "SpawnedTaskId"
    spec: "DelegationSpec"
    identity: LoopRoleIdentity
    relationship: LoopRelationship
    status: "SpawnedTaskStatus"
    update_count: int = 0
    steps_run: int = 0
    model_calls: int = 0
    result: "SpawnedLoopResult | None" = None
    schema_version: str = SPAWNED_TASK_CHECKPOINT_VERSION
    checkpoint_digest: str = ""

    def __post_init__(self) -> None:
        from .delegation_runtime import (
            DelegationSpec, SpawnedLoopResult, SpawnedTaskId,
            SpawnedTaskStatus)
        if (self.schema_version
                not in _SUPPORTED_SPAWNED_TASK_CHECKPOINT_VERSIONS):
            raise SpawnedTaskCheckpointError(
                f"unsupported checkpoint schema {self.schema_version!r}")
        if not isinstance(self.task_id, SpawnedTaskId):
            raise SpawnedTaskCheckpointError(
                "checkpoint task_id is not typed")
        if not isinstance(self.spec, DelegationSpec):
            raise SpawnedTaskCheckpointError("checkpoint spec is not typed")
        if not isinstance(self.identity, LoopRoleIdentity):
            raise SpawnedTaskCheckpointError(
                "checkpoint identity is not typed")
        if not isinstance(self.relationship, LoopRelationship):
            raise SpawnedTaskCheckpointError(
                "checkpoint relationship is not typed")
        if not isinstance(self.status, SpawnedTaskStatus):
            raise SpawnedTaskCheckpointError(
                "checkpoint status is not typed")
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 0
               for value in (self.update_count, self.steps_run,
                             self.model_calls)):
            raise SpawnedTaskCheckpointError(
                "checkpoint counters must be non-negative integers")
        if ((self.spec.budget.max_iterations is not None
             and self.steps_run > self.spec.budget.max_iterations)
                or (self.spec.budget.max_model_calls is not None
                    and self.model_calls
                    > self.spec.budget.max_model_calls)):
            raise SpawnedTaskCheckpointError(
                "checkpoint counters exceed the delegation budget")
        if self.status.terminal:
            if not isinstance(self.result, SpawnedLoopResult):
                raise SpawnedTaskCheckpointError(
                    "terminal checkpoint needs a terminal result")
            if self.result.status != self.status \
                    or self.result.task_id != self.task_id:
                raise SpawnedTaskCheckpointError(
                    "terminal result identity or status does not match")
            if (self.result.steps_run != self.steps_run
                    or self.result.model_calls != self.model_calls):
                raise SpawnedTaskCheckpointError(
                    "terminal result counters do not match checkpoint")
        elif self.result is not None:
            raise SpawnedTaskCheckpointError(
                "queued or running checkpoint cannot contain a result")
        if (self.identity.profile_id != self.spec.profile.profile_id
                or self.identity.profile_version != self.spec.profile.version):
            raise SpawnedTaskCheckpointError(
                "role identity profile does not match checkpoint spec")
        computed = _digest(self._body())
        if self.checkpoint_digest and self.checkpoint_digest != computed:
            raise SpawnedTaskCheckpointError("checkpoint digest mismatch")
        object.__setattr__(self, "checkpoint_digest", computed)

    def _body(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "task_id": str(self.task_id),
            "spec": _spec_to_dict(self.spec),
            "identity": self.identity.to_dict(),
            "relationship": self.relationship.to_dict(),
            "status": self.status.value,
            "update_count": self.update_count,
            "steps_run": self.steps_run,
            "model_calls": self.model_calls,
            "result": _result_to_dict(self.result),
        }

    def to_dict(self) -> dict:
        return {**self._body(), "checkpoint_digest": self.checkpoint_digest}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, value: dict) -> "SpawnedTaskCheckpoint":
        from .delegation_runtime import SpawnedTaskId, SpawnedTaskStatus
        schema_version = str(value["schema_version"])
        expected = {"schema_version", "task_id", "spec", "identity",
                    "relationship",
                       "status", "update_count", "steps_run", "model_calls",
                       "result", "checkpoint_digest"}
        _known(value, tuple(expected), "spawned task checkpoint")
        if schema_version != SPAWNED_TASK_CHECKPOINT_VERSION:
            raise SpawnedTaskCheckpointError(
                f"unsupported checkpoint schema {schema_version!r}")
        identity = LoopRoleIdentity.from_dict(value["identity"])
        relationship = LoopRelationship.from_dict(value["relationship"])
        task_id_value = str(value["task_id"])
        result_value = value["result"]
        return cls(
            task_id=SpawnedTaskId(task_id_value),
            spec=_spec_from_dict(value["spec"]),
            identity=identity,
            relationship=relationship,
            status=SpawnedTaskStatus(value["status"]),
            update_count=int(value["update_count"]),
            steps_run=int(value["steps_run"]),
            model_calls=int(value["model_calls"]),
            result=_result_from_dict(result_value),
            schema_version=SPAWNED_TASK_CHECKPOINT_VERSION,
            checkpoint_digest=str(value["checkpoint_digest"]),
        )

    @classmethod
    def from_json(cls, value: str) -> "SpawnedTaskCheckpoint":
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise SpawnedTaskCheckpointError(
                "checkpoint JSON must contain one object")
        return cls.from_dict(parsed)


class SpawnedTaskLifecycleMixin:
    """Bounded join and checkpoint operations for SpawnedTaskManager."""

    def _initialize_lifecycle_services(
            self, services=None, *, runtime_memory=None,
            context_artifacts=None) -> None:
        from .spawned_task_state_store import SpawnedTaskServices
        selected = SpawnedTaskServices.compose(
            services, runtime_memory=runtime_memory,
            context_artifacts=context_artifacts)
        self._services = selected
        self._runtime_memory = selected.runtime_memory
        self._context_artifacts = selected.context_artifacts
        self._state_store = selected.state_store
        self._saved_states = {}

    def list(self):
        return tuple(self._snapshot(record) for record in self._records.values())

    async def wait(self, task_id):
        record = self._record(task_id)
        if record.async_task is not None:
            try:
                await record.async_task
            except asyncio.CancelledError:
                pass
        return self._snapshot(record)

    def _executor_is_async(self) -> bool:
        return (inspect.iscoroutinefunction(self._executor)
                or inspect.iscoroutinefunction(
                    getattr(self._executor, "__call__", None)))

    async def wait_all(self, task_ids=None, *, timeout_seconds: float):
        if (not isinstance(timeout_seconds, (int, float))
                or isinstance(timeout_seconds, bool) or timeout_seconds <= 0):
            raise SpawnedTaskCheckpointError(
                "wait_all timeout_seconds must be positive")
        if task_ids is None:
            records = list(self._records.values())
        else:
            selected = tuple(task_ids)
            if len(selected) != len(set(selected)):
                raise SpawnedTaskCheckpointError(
                    "wait_all task IDs cannot repeat")
            wanted = {self._record(task_id).task_id for task_id in selected}
            records = [record for record in self._records.values()
                       if record.task_id in wanted]
        tasks = [record.async_task for record in records
                 if record.async_task is not None
                 and not record.async_task.done()]
        if tasks:
            _done, pending = await asyncio.wait(
                tasks, timeout=float(timeout_seconds))
            if pending:
                for record in records:
                    if (record.async_task in pending
                            and not record.status.terminal):
                        self.cancel(
                            record.task_id, "wait_all deadline exceeded")
                await asyncio.gather(*tasks, return_exceptions=True)
        for record in records:
            if not record.status.terminal:
                self.cancel(record.task_id, "wait_all left task active")
        return tuple(self._snapshot(record) for record in records)

    async def join(self, task_ids=None, *, timeout_seconds: float):
        return await self.wait_all(
            task_ids, timeout_seconds=timeout_seconds)

    def _checkpoint_for_record(
            self, record, *, status=None, result=_UNSET,
            update_count: "int | None" = None) -> SpawnedTaskCheckpoint:
        counters = (record.runtime.counters if record.runtime is not None
                    else None)
        selected_result = record.result if result is _UNSET else result
        selected_status = status or record.status
        steps = (selected_result.steps_run if selected_result is not None
                 else counters.steps_run if counters is not None else 0)
        calls = (selected_result.model_calls if selected_result is not None
                 else counters.model_calls if counters is not None else 0)
        return SpawnedTaskCheckpoint(
            task_id=record.task_id,
            spec=record.spec,
            identity=record.identity,
            relationship=record.relationship,
            status=selected_status,
            update_count=(len(record.control.updates()) if update_count is None
                          else update_count),
            steps_run=steps,
            model_calls=calls,
            result=selected_result,
        )

    def checkpoint(self, task_id) -> SpawnedTaskCheckpoint:
        return self._checkpoint_for_record(self._record(task_id))

    def checkpoints(self) -> tuple[SpawnedTaskCheckpoint, ...]:
        return tuple(self.checkpoint(record.task_id)
                     for record in self._records.values())

    def _persist_created(self, record) -> None:
        if self._state_store is None:
            return
        try:
            state = self._state_store.create(
                self._parent.loop_id, self._checkpoint_for_record(record))
        except Exception:
            if record.spawned_loop is not None \
                    and not record.spawned_loop.is_terminal:
                record.spawned_loop.cancel("durable task creation failed")
            self._records.pop(record.task_id, None)
            raise
        self._saved_states[record.task_id] = state

    def _persist_transition(self, record, checkpoint) -> None:
        if self._state_store is None:
            return
        expected = self._saved_states.get(record.task_id)
        if expected is None:
            expected = self._state_store.load(
                self._parent.loop_id, str(record.task_id))
        state = self._state_store.compare_and_swap(expected, checkpoint)
        self._saved_states[record.task_id] = state

    def _persist_update(self, record, update) -> None:
        record.control._add_update(update)
        try:
            self._persist_transition(
                record, self._checkpoint_for_record(record))
        except Exception:
            record.control._remove_last_update()
            raise

    def _persist_terminal(self, record, result) -> None:
        self._persist_transition(record, self._checkpoint_for_record(
            record, status=result.status, result=result))

    def restore_checkpoint(self, checkpoint: SpawnedTaskCheckpoint):
        return self._restore_checkpoint(checkpoint)

    def _restore_checkpoint(
            self, checkpoint: SpawnedTaskCheckpoint, *, saved_state=None):
        if not isinstance(checkpoint, SpawnedTaskCheckpoint):
            raise SpawnedTaskCheckpointError(
                "restore_checkpoint needs SpawnedTaskCheckpoint")
        if checkpoint.task_id in self._records:
            raise SpawnedTaskCheckpointError(
                f"spawned task {checkpoint.task_id} is already present")
        if (self._limits.max_total is not None
                and len(self._records) >= self._limits.max_total):
            raise SpawnedTaskCheckpointError(
                "the total spawned-task limit is reached")
        if not str(checkpoint.task_id).startswith(
                self._parent.loop_id + ".spawned-task."):
            raise SpawnedTaskCheckpointError(
                "checkpoint belongs to a different owning Loop")
        from .delegation_runtime import (
            SpawnedLoopResult,
            SpawnedTaskControl,
            SpawnedTaskStatus,
            SpawnedTaskUpdate,
            _SpawnedTaskRecord,
        )
        control = SpawnedTaskControl()
        for _index in range(checkpoint.update_count):
            control._add_update(SpawnedTaskUpdate(
                instruction="restored update metadata"))
        status = checkpoint.status
        result = checkpoint.result
        if not status.terminal:
            status = SpawnedTaskStatus.INTERRUPTED
            result = SpawnedLoopResult(
                task_id=checkpoint.task_id,
                status=status,
                terminal_code="INTERRUPTED",
                steps_run=checkpoint.steps_run,
                model_calls=checkpoint.model_calls,
                error_code="INTERRUPTED_ON_RESTORE",
                error=("queued or running Spawned Loop was not resumed; its "
                       "durable "
                       "metadata was restored as interrupted"),
            )
        record = _SpawnedTaskRecord(
            task_id=checkpoint.task_id,
            spec=checkpoint.spec,
            spawned_loop=None,
            runtime=None,
            control=control,
            identity=checkpoint.identity,
            relationship=checkpoint.relationship,
            status=status,
            result=result,
        )
        if self._state_store is not None:
            from .spawned_task_state_store import SpawnedTaskStateNotFound
            if saved_state is None:
                try:
                    saved_state = self._state_store.load(
                        self._parent.loop_id, str(checkpoint.task_id))
                except SpawnedTaskStateNotFound:
                    saved_state = self._state_store.create(
                        self._parent.loop_id, checkpoint)
                if saved_state.checkpoint.checkpoint_digest \
                        != checkpoint.checkpoint_digest:
                    raise SpawnedTaskCheckpointError(
                        "saved checkpoint conflicts with restore input")
            self._saved_states[checkpoint.task_id] = saved_state
            if checkpoint.status != status:
                self._persist_transition(
                    record, self._checkpoint_for_record(
                        record, status=status, result=result))
        self._records[checkpoint.task_id] = record
        suffix = re.search(
            r"\.spawned-task\.(\d+)$", str(checkpoint.task_id))
        if suffix:
            self._counter = max(self._counter, int(suffix.group(1)))
        self._parent.ledger.record(
            loop_id=self._parent.loop_id,
            event="custom",
            custom_kind="spawned_task_checkpoint_restored",
            spawned_task_id=str(checkpoint.task_id),
            checkpoint_status=checkpoint.status.value,
            restored_status=status.value,
            checkpoint_digest=checkpoint.checkpoint_digest,
            updates=checkpoint.update_count,
            steps_run=result.steps_run,
            model_calls=result.model_calls,
            error_code=result.error_code,
        )
        return self._snapshot(record)

    def restore_checkpoint_json(self, value: str):
        return self.restore_checkpoint(SpawnedTaskCheckpoint.from_json(value))

    def load_saved_checkpoints(self):
        """Load every saved task for this owner and close active work honestly."""
        if self._state_store is None:
            raise SpawnedTaskCheckpointError(
                "loading saved checkpoints requires a state store")
        states = self._state_store.load_owner(self._parent.loop_id)
        existing = set(self._records)
        saved_ids = {state.checkpoint.task_id for state in states}
        if existing & saved_ids:
            raise SpawnedTaskCheckpointError(
                "one or more saved tasks are already loaded")
        if (self._limits.max_total is not None
                and len(self._records) + len(states)
                > self._limits.max_total):
            raise SpawnedTaskCheckpointError(
                "saved task population exceeds the manager limit")
        snapshots = []
        for state in states:
            snapshots.append(self._restore_checkpoint(
                state.checkpoint, saved_state=state))
        return tuple(snapshots)

    def restart_as_new_attempt(self, task_id):
        """Start interrupted work under a new task and Loop identity."""
        if self._executor_is_async():
            raise SpawnedTaskCheckpointError(
                "an asynchronous executor needs restart_as_new_attempt_async")
        record = self._require_interrupted(task_id)
        new_id = self.start(record.spec)
        self._record_restart(record.task_id, new_id)
        return new_id

    async def restart_as_new_attempt_async(self, task_id):
        """Schedule interrupted work as a new asynchronous task attempt."""
        if not self._executor_is_async():
            raise SpawnedTaskCheckpointError(
                "a synchronous executor needs restart_as_new_attempt")
        record = self._require_interrupted(task_id)
        new_id = await self.start_async(record.spec)
        self._record_restart(record.task_id, new_id)
        return new_id

    def _require_interrupted(self, task_id):
        from .delegation_runtime import SpawnedTaskStatus
        record = self._record(task_id)
        if record.status is not SpawnedTaskStatus.INTERRUPTED:
            raise SpawnedTaskCheckpointError(
                "only interrupted work can start a new attempt")
        return record

    def _record_restart(self, previous_task_id, new_task_id) -> None:
        self._parent.ledger.record(
            loop_id=self._parent.loop_id, event="custom",
            custom_kind="spawned_task_restarted_as_new_attempt",
            previous_task_id=str(previous_task_id),
            new_task_id=str(new_task_id))
