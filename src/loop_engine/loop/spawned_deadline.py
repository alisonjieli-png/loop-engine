"""Deadline observations for existing typed Spawned Loop dispatch.

Synchronous callbacks have a post-return acceptance deadline, not preemptive
execution control. A late return is retained and cannot become success.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
import inspect
import math
from time import monotonic

ASSESSMENT_PHASES = ("before_dispatch", "after_return", "after_exception")
BEFORE_DISPATCH, AFTER_RETURN, AFTER_EXCEPTION = ASSESSMENT_PHASES


@dataclass(frozen=True)
class SpawnedDeadlineAssessment:
    limit_seconds: float
    elapsed_seconds: float
    phase: str
    executor_returned: bool = False

    def __post_init__(self):
        if (type(self.limit_seconds) not in (int, float)
                or not math.isfinite(self.limit_seconds) or self.limit_seconds <= 0
                or type(self.elapsed_seconds) not in (int, float)
                or not math.isfinite(self.elapsed_seconds) or self.elapsed_seconds < 0):
            raise ValueError("deadline assessment requires finite measured durations")
        if self.phase not in ASSESSMENT_PHASES:
            raise ValueError("unsupported synchronous deadline assessment phase")
        if type(self.executor_returned) is not bool:
            raise ValueError("executor_returned must be Boolean")

    @property
    def exceeded(self):
        return self.elapsed_seconds > self.limit_seconds

    def to_dict(self):
        return {"record_type": "spawned_deadline_assessment/v1",
                "limit_seconds": self.limit_seconds,
                "elapsed_seconds": self.elapsed_seconds, "phase": self.phase,
                "exceeded": self.exceeded, "executor_returned": self.executor_returned,
                "enforcement": "non_preemptive_acceptance_deadline",
                "preemption_supported": False, "physical_cancellation_confirmed": False,
                "callback_effect_state": ("not_dispatched" if self.phase == BEFORE_DISPATCH
                                          else "unreconciled" if self.exceeded else "not_assessed"),
                "replay_authorized": False}


def _record_assessment(manager, record, assessment, result=None):
    fields = assessment.to_dict()
    if result is not None:
        fields.update(returned_status=result.status.value,
                      returned_terminal_code=result.terminal_code,
                      returned_error_code=result.error_code)
    manager._parent.ledger.record(loop_id=manager._parent.loop_id, event="custom",
        custom_kind="spawned_deadline_assessed", spawned_task_id=str(record.task_id),
        **fields)


def retain_deadline_result(result, assessment):
    """Keep admitted outputs and counters while refusing late success."""
    from .delegation_runtime import SpawnedTaskStatus

    if not isinstance(assessment, SpawnedDeadlineAssessment):
        raise ValueError("deadline result needs a typed assessment")
    if not assessment.exceeded:
        return result
    return replace(result, status=SpawnedTaskStatus.FAILED,
        terminal_code="DEADLINE_EXCEEDED", error_code="DEADLINE_EXCEEDED",
        error=("synchronous callback returned after its acceptance deadline; "
               "outputs are retained as unaccepted, effects remain unreconciled, "
               "and no cancellation or replay is claimed"))


def execute_synchronous_spawned(manager, spec, *, require_preemptive_deadline=False):
    from .delegation_runtime import DelegationError, DelegationSpec, SpawnedLoopResult

    if type(require_preemptive_deadline) is not bool:
        raise DelegationError("require_preemptive_deadline must be Boolean")
    if require_preemptive_deadline:
        raise DelegationError("this synchronous executor does not support preemptive deadlines")
    if manager._executor_is_async():
        raise DelegationError("this executor is asynchronous; use start_async()")
    if not isinstance(spec, DelegationSpec):
        raise DelegationError("start expects a DelegationSpec")
    limit = spec.budget.wall_time_seconds
    started = monotonic() if limit is not None else None
    record = manager._prepare(spec)
    if limit is not None:
        admission = SpawnedDeadlineAssessment(limit, monotonic() - started, BEFORE_DISPATCH)
        if admission.exceeded:
            _record_assessment(manager, record, admission)
            manager._fail(record, "DEADLINE_EXCEEDED",
                "deadline elapsed during admission; executor was not dispatched",
                terminal_code="DEADLINE_EXCEEDED")
            return record.task_id
    assessment = None
    try:
        value = manager._executor(manager._request(record))
        if inspect.isawaitable(value):
            close = getattr(value, "close", None)
            if callable(close):
                close()
            raise DelegationError("executor returned an awaitable; use start_async()")
        if limit is not None:
            assessment = SpawnedDeadlineAssessment(limit, monotonic() - started,
                                                   AFTER_RETURN, executor_returned=True)
            _record_assessment(manager, record, assessment,
                               value if isinstance(value, SpawnedLoopResult) else None)
        manager._finish(record, value, deadline_assessment=assessment)
    except Exception as exc:
        if limit is not None and assessment is None:
            assessment = SpawnedDeadlineAssessment(limit, monotonic() - started, AFTER_EXCEPTION)
            _record_assessment(manager, record, assessment)
        manager._fail(record, "EXECUTOR_FAILED", str(exc))
    return record.task_id


async def execute_async_spawned(manager, record):
    """Preserve the existing cooperative asynchronous timeout semantics."""
    from .delegation_runtime import DelegationError

    try:
        value = manager._executor(manager._request(record))
        if not inspect.isawaitable(value):
            raise DelegationError("asynchronous executor returned a synchronous result")
        timeout = record.spec.budget.wall_time_seconds
        result = (await value if timeout is None else
                  await asyncio.wait_for(value, timeout=float(timeout)))
        if not record.status.terminal:
            manager._finish(record, result)
    except (TimeoutError, asyncio.TimeoutError):
        manager._fail(record, "DEADLINE_EXCEEDED",
            "spawned executor exceeded its cooperative wall-time deadline",
            terminal_code="DEADLINE_EXCEEDED")
    except asyncio.CancelledError:
        if not record.status.terminal:
            manager.cancel(record.task_id)
    except Exception as exc:
        manager._fail(record, "EXECUTOR_FAILED", str(exc))
