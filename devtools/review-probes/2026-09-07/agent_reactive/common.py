"""Shared probe fixtures: real scheduler/worker/executor classes, fixture style of reactive_worker_checks."""
import asyncio, json, os, shutil, sys, tempfile
from pathlib import Path
from dataclasses import replace

SCRATCH = Path(__file__).resolve().parent

from loop_engine.code_nodes.solution_graph import LoopDefinitionRegistry
from loop_engine.core.reactive_worker_checks import _definition, _profile, _trigger
from loop_engine.core.reactive_scheduler import SQLiteReactiveScheduler, ReactiveSchedulerError
from loop_engine.core.reactive_worker import (
    AsyncReactiveWorker, CanonicalReactiveExecutor, ReactiveHandlerBinding,
    ReactiveHistoryPolicy, ReactiveWorkerRequest, ReactiveWorkerError)
from loop_engine.loop.effect_approval import ApprovalDecision
from loop_engine.loop.reactive_activation import (
    ActivationClaimRequest, ActivationHistoryDisposition, ActivationRecord,
    ActivationStartRequest, ActivationStatus, ActivationTerminalRequest,
    ReactiveSeriesDefinition, TriggerEnvelope)
from loop_engine.loop.recursive_loop import StepOutcome
from loop_engine.loop.runtime_context import LoopRuntimeContext


def tmpdir(prefix):
    return Path(tempfile.mkdtemp(prefix=prefix, dir=str(SCRATCH)))


def make_scheduler(root, max_attempts=2, max_active=1, db="scheduler.sqlite", profile=None):
    definition = _definition()
    profile = profile or _profile()
    scheduler = SQLiteReactiveScheduler(str(root / db))
    scheduler.register_profile(profile)
    series = ReactiveSeriesDefinition(
        "series-worker", "Probe fixture.", definition.ref, profile.profile_id,
        profile.version, profile.content_digest, "trigger/v1", ("result",),
        max_attempts, max_active)
    scheduler.register_series(series)
    return scheduler, definition, series, profile


def make_executor(definition, handler, policy=None):
    context = LoopRuntimeContext.compatibility(
        capabilities=definition.required_capabilities,
        permissions=definition.permissions,
        executor_modes=definition.installed_executor_modes)
    binding = (ReactiveHandlerBinding(definition.ref, handler, policy)
               if policy is not None else ReactiveHandlerBinding(definition.ref, handler))
    return CanonicalReactiveExecutor(LoopDefinitionRegistry((definition,)), context, (binding,))


def approve(request):
    return ApprovalDecision.approve(request.request_id, "probe.host")


def run_once(scheduler, executor, series, worker="probe", at="2026-09-07T00:00:01Z",
             lease=60, terminal_at=None):
    return asyncio.run(AsyncReactiveWorker(scheduler, executor).run_once(
        ReactiveWorkerRequest(ActivationClaimRequest(worker, at, lease, series.series_id),
                              at, terminal_at or at)))


def ok_outcome(*_):
    return StepOutcome("probe work complete", "deterministic", 1.0)


def dump(name, value):
    path = SCRATCH / name
    path.write_text(json.dumps(value, indent=1, default=str))
    print(f"[wrote {path}]")
