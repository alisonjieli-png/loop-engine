"""Wall-clock and identity checks for asynchronous canonical Loop workers.

Owns overlap, exact-definition, unique-ID, and terminal-history proof.
It is verification only and never installs a production worker.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import tempfile
import time
from dataclasses import replace
from pathlib import Path
from threading import Event
from unittest.mock import patch

from ..code_nodes.solution_graph import LoopDefinitionRegistry
from ..loop.atomic_primitives import LoopValue, LoopValueCreateRequest
from ..loop.loop_contract import LoopContract
from ..loop.loop_definition import LoopDefinition
from ..loop.loop_role import LoopRole, LoopRoleIdentity
from ..loop.reactive_activation import (
    ActivationClaimRequest, ActivationHistoryDisposition, ActivationRecord,
    ActivationStatus, ActivationTerminalRequest, ReactiveSeriesDefinition, TriggerEnvelope)
from ..loop.reactive_contracts import (
    ActivationPolicy, AdmissionPolicy, EmissionPolicy, ExplorationPolicy,
    InputSchedulingPolicy, MetricDirection, OutputPortDefinition,
    PersistenceMode, PortfolioPolicy, PortfolioView, RankingDimension,
    ReactiveLivenessPolicy, ReactiveLoopProfile, RetentionPolicy,
    ServingPolicy, TriggerKind)
from ..loop.recursive_loop import LoopConfig, StepOutcome
from ..loop.runtime_context import LoopRuntimeContext
from .reactive_scheduler import ReactiveSchedulerError, SQLiteReactiveScheduler
from .reactive_worker import (
    AsyncReactiveWorker, CanonicalReactiveExecutor, ReactiveHandlerBinding,
    ReactiveHistoryPolicy, ReactiveWorkerError, ReactiveWorkerRequest)


def _definition() -> LoopDefinition:
    config = LoopConfig(
        framework="custom", custom_steps=("act",),
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",),
        delegated_modes=("deterministic",),
        exit_condition="accepted_success")
    contract = LoopContract(
        "reactive fixture", "code_only", ("trigger/v1",), ("answer/v1",),
        ("pure",), role="practitioner")
    return LoopDefinition.from_runtime(
        identity=LoopRoleIdentity(
            LoopRole.PRACTITIONER, "practitioner.code_execution"),
        contract=contract, config=config,
        definition_id="practitioner.reactive_fixture", version="1.0.0",
        installed_executor_modes=("deterministic",))


def _profile() -> ReactiveLoopProfile:
    return ReactiveLoopProfile(
        "profile-worker", "1.0.0",
        ActivationPolicy(
            (TriggerKind.PUSH_EVENT,), reactivation_enabled=True),
        AdmissionPolicy(10), InputSchedulingPolicy(),
        PersistenceMode.DURABLE_SERIES, ExplorationPolicy(),
        (OutputPortDefinition("result", "answer", "answer/v1"),),
        PortfolioPolicy(
            "policy-worker", "1.0.0", PortfolioView.VERIFIED_TOP_K,
            (RankingDimension("evidence_coverage", MetricDirection.MAXIMIZE),),
            10),
        EmissionPolicy(), ServingPolicy(10), RetentionPolicy(100, 100),
        ReactiveLivenessPolicy(30))


def _trigger(index: int, definition: LoopDefinition) -> TriggerEnvelope:
    value = LoopValue.create(
        {"index": index}, LoopValueCreateRequest(
            "trigger/v1", "trigger_input", "loop-source",
            definition.definition_id))
    moment = f"2026-08-29T17:00:0{index}Z"
    return TriggerEnvelope(
        f"trigger-worker-{index}", "series-worker", TriggerKind.PUSH_EVENT,
        f"subject-{index}", value.to_ref(), "loop-source", moment, moment,
        f"dedup-worker-{index}", 1.0)


def _restart_definition() -> LoopDefinition:
    base = _definition()
    effects = ("reads_fs", "writes_fs")
    return replace(base, contract=replace(base.contract, effects=effects),
                   effects=effects, permissions=("fixture.restart.write",))


def _restart_scheduler(root: Path):
    definition, profile = _restart_definition(), _profile()
    scheduler = SQLiteReactiveScheduler(str(root / "scheduler.sqlite"))
    scheduler.register_profile(profile)
    series = ReactiveSeriesDefinition(
        "series-worker", "Record one exactly approved private fixture effect.",
        definition.ref, profile.profile_id, profile.version, profile.content_digest,
        "trigger/v1", ("result",), 2, 1)
    scheduler.register_series(series)
    admission = scheduler.admit(_trigger(1, definition))
    return scheduler, definition, series, admission


def _restart_process_fixture(phase: str, directory: str) -> None:
    """Private process driver: only private fixture files are effects.

    os._exit deliberately skips Python cleanup after a committed scheduler
    transition. The running-crash branch first crosses the existing native
    approval/workspace boundary and then dies without an activation result.
    """
    from ..loop.approval_state_store import LocalJsonApprovalStateStore
    from ..loop.effect_approval import ApprovalDecision, EffectApprovalService
    from .runtime_observer import RuntimeObservationServices
    from .workspace_backends import FileOperation, FileRequest, RestrictedLocalWorkspace, WorkspaceSpec
    from .workspace_operations import WorkspaceOperationService

    if phase not in {"leased", "running", "complete", "definition_drift", "authority_drift"}:
        raise ValueError("unsupported private fixture phase")
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    scheduler, definition, series, admission = _restart_scheduler(root)
    if phase == "leased":
        claim = scheduler.claim(ActivationClaimRequest(
            "crashed-before-start", "2026-09-06T00:00:01Z", 1, series.series_id))
        print(json.dumps({"phase": phase, "activation": claim.activation.to_dict(),
                          "lease": claim.lease.to_dict()}), flush=True)
        os._exit(23)

    effect_root = root / "effects"
    effect_root.mkdir(exist_ok=True)
    marker = effect_root / "effect.txt"

    def handler(active, _step, trigger):
        runtime = RuntimeObservationServices(parent=active, ledger=active.ledger)
        approvals = EffectApprovalService(
            runtime, LocalJsonApprovalStateStore(str(root / "approvals")),
            authority_key=b"public-offline-reactive-fixture-key")
        backend = RestrictedLocalWorkspace(WorkspaceSpec("restart-effect", str(effect_root)))
        operations = WorkspaceOperationService(backend, approvals=approvals)
        prior = backend.file(FileRequest(FileOperation.READ, "effect.txt"))
        request = FileRequest(FileOperation.WRITE, "effect.txt",
            content=(prior.content if prior.ok else b"") + b"applied\n",
            replace_existing=prior.ok, expected_digest=prior.digest if prior.ok else "")
        plan = operations.plan_file_write(request, loop_id=active.loop_id,
                                         reason="Record the exact private crash-test effect.")
        pending = approvals.create(plan.approval)
        approvals.resume(pending.pending, pending.resume_token,
            ApprovalDecision.approve(plan.approval.request_id, "independent_fixture_host"))
        written = operations.file(plan.request, approval_id=plan.approval.request_id)
        if not written.ok:
            raise AssertionError("private fixture effect was not committed")
        if phase == "running":
            print(json.dumps({"phase": phase, "activation_id": trigger.activation_id,
                              "loop_id": active.loop_id, "approval_id": plan.approval.request_id,
                              "effect_digest": written.digest}), flush=True)
            os._exit(23)
        return StepOutcome("approved private effect recorded", "deterministic", 1.0)

    registered = replace(definition, version="1.0.1") if phase == "definition_drift" else definition
    context = LoopRuntimeContext.compatibility(
        capabilities=definition.required_capabilities,
        permissions=() if phase == "authority_drift" else definition.permissions,
        executor_modes=definition.installed_executor_modes)
    executor = CanonicalReactiveExecutor(LoopDefinitionRegistry((registered,)), context,
                                        (ReactiveHandlerBinding(registered.ref, handler),))
    worker = AsyncReactiveWorker(scheduler, executor)
    instant = "2026-09-06T00:00:01Z" if phase == "running" else "2026-09-06T00:00:10Z"
    outcome = asyncio.run(worker.run_once(ReactiveWorkerRequest(
        ActivationClaimRequest("restart-worker", instant, 1, series.series_id), instant, instant)))
    current = scheduler.get_activation(admission.activation.activation_id)
    fresh_executor = CanonicalReactiveExecutor(LoopDefinitionRegistry((definition,)), context,
                                              (ReactiveHandlerBinding(definition.ref, handler),))
    try:
        fresh_executor.ledger_for(current.activation_id)
        history_available = True
    except ReactiveWorkerError:
        history_available = False
    print(json.dumps({"phase": phase, "claimed": outcome.claimed,
                      "error_code": outcome.error_code, "activation": current.to_dict(),
                      "effect_count": marker.read_bytes().count(b"applied\n") if marker.exists() else 0,
                      "canonical_history_available_in_fresh_executor": history_available}), flush=True)
    scheduler.close()


def run_restart_proof(directory: str) -> dict:
    """Persist a bounded OS-process death/reopen proof in a new private root."""
    from ..loop.approval_state_store import LocalJsonApprovalStateStore
    from ..loop.effect_approval import EffectApprovalService

    root = Path(directory)
    root.mkdir(parents=True, exist_ok=False)
    tests, phases = [], []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def process(phase, target):
        from .workspace_backends import RestrictedLocalWorkspace
        from .workspace_contracts import CommandRequest, WorkspaceSpec
        command = (sys.executable, "-B", "-c", "import sys; sys.path.insert(0, sys.argv[3]); "
            "from loop_engine.core.reactive_worker_checks import _restart_process_fixture; "
            "_restart_process_fixture(sys.argv[1], sys.argv[2])", phase, str(target),
            str(Path(__file__).resolve().parents[2]))
        backend = RestrictedLocalWorkspace(WorkspaceSpec("restart-process-fixture", str(root),
            execution_enabled=True, allowed_commands=(sys.executable,)))
        completed = backend.command(CommandRequest(command, timeout_seconds=15, execution_authorized=True))
        expected = 23 if phase in {"leased", "running"} else 0
        if completed.exit_code != expected or completed.output_truncated:
            raise AssertionError(f"private restart fixture {phase} exited {completed.exit_code}: {completed.stderr}")
        value = json.loads(completed.stdout)
        phases.append({"phase": phase, "root": str(target), "exit_code": completed.exit_code,
                       "value": value})
        return value

    running_root = root / "running-crash"
    crashed = process("running", running_root)
    scheduler, _definition_ref, series, admission = _restart_scheduler(running_root)
    before = scheduler.get_activation(admission.activation.activation_id)
    scheduler.close()
    resumed = process("complete", running_root)
    check("process_death_after_approved_effect_is_not_replayed_on_reopen",
          before.status is ActivationStatus.RUNNING and not resumed["claimed"]
          and resumed["effect_count"] == 1
          and resumed["activation"]["status"] == ActivationStatus.DEAD_LETTER.value
          and resumed["activation"]["failure_code"] == "RUNNING_OUTCOME_UNKNOWN_RECONCILIATION_REQUIRED")
    scheduler, _, _, _ = _restart_scheduler(running_root)
    stale_refused = False
    try:
        scheduler.terminal(ActivationTerminalRequest(before.activation_id, before.lease_id,
            before.fencing_token, ActivationStatus.COMPLETED, "2026-09-06T00:00:11Z", "stale-loop", "ACCEPTED"))
    except ReactiveSchedulerError:
        stale_refused = True
    check("expired_running_worker_cannot_overwrite_unknown_outcome_with_completion", stale_refused)
    scheduler.close()
    approval_store = LocalJsonApprovalStateStore(str(running_root / "approvals"))
    consumed = approval_store.load(crashed["approval_id"])
    duplicate_refused = False
    service = EffectApprovalService(store=approval_store, authority_key=b"public-offline-reactive-fixture-key")
    try:
        service.consume(crashed["approval_id"], consumed.request.effect)
    except (RuntimeError, ValueError, PermissionError):
        duplicate_refused = True
    check("exact_consumed_effect_approval_survives_process_death_and_cannot_be_reused",
          consumed.status == "consumed" and duplicate_refused)

    unstarted_root = root / "unstarted-crash"
    leased = process("leased", unstarted_root)
    complete = process("complete", unstarted_root)
    check("process_death_before_start_can_reclaim_and_execute_once",
          complete["claimed"] and complete["effect_count"] == 1
          and complete["activation"]["status"] == ActivationStatus.COMPLETED.value
          and complete["activation"]["fencing_token"] == 2)
    scheduler, _, _, _ = _restart_scheduler(unstarted_root)
    stale_refused = False
    try:
        scheduler.terminal(ActivationTerminalRequest(leased["activation"]["activation_id"],
            leased["lease"]["lease_id"], leased["lease"]["fencing_token"], ActivationStatus.COMPLETED,
            "2026-09-06T00:00:11Z", "expired-worker", "ACCEPTED"))
    except ReactiveSchedulerError:
        stale_refused = True
    check("old_process_fencing_token_cannot_replace_new_attempt_result", stale_refused)
    scheduler.close()
    reopened = process("complete", unstarted_root)
    check("completed_activation_metadata_survives_another_process_reopen_without_reexecution",
          not reopened["claimed"] and reopened["effect_count"] == 1
          and reopened["activation"] == complete["activation"])
    check("durable_activation_metadata_does_not_claim_unpersisted_canonical_history",
          reopened["canonical_history_available_in_fresh_executor"] is False)

    for phase in ("definition_drift", "authority_drift"):
        target = root / phase
        process("leased", target)
        changed = process(phase, target)
        check("restart_refuses_" + phase + "_before_handler_effects",
              changed["claimed"] and changed["effect_count"] == 0
              and changed["activation"]["status"] == ActivationStatus.FAILED.value and changed["error_code"])

    canceled_root = root / "canceled-before-start"
    canceled_claim = process("leased", canceled_root)
    scheduler, _, _, _ = _restart_scheduler(canceled_root)
    cancellation = scheduler.terminal(ActivationTerminalRequest(
        canceled_claim["activation"]["activation_id"], canceled_claim["lease"]["lease_id"],
        canceled_claim["lease"]["fencing_token"], ActivationStatus.CANCELED, "2026-09-06T00:00:01Z",
        terminal_code="CANCELED"))
    scheduler.close()
    canceled = process("complete", canceled_root)
    check("confirmed_prestart_cancellation_is_distinct_from_running_outcome_unknown",
          not canceled["claimed"] and canceled["effect_count"] == 0
          and canceled["activation"] == cancellation.to_dict())
    return {"record_type": "reactive_process_restart_proof/v1", "tests": tests, "phases": phases,
            "provider_calls": 0, "external_system_mutations": 0,
            "limitations": ["Effects are exactly approved files inside a private fixture root.",
                            "Process death is tested, not power loss or distributed execution.",
                            "Canonical Loop history is not persisted by the current reactive executor.",
                            "Exact definition and runtime authority drift are checked; handler implementation bytes are not independently qualified."]}


def _cancellation_checks() -> list[dict]:
    """Cancel the awaiting coroutine while its thread still owns running work."""
    started, release = Event(), Event()
    definition, profile = _definition(), _profile()
    series = ReactiveSeriesDefinition("series-worker", "Await a bounded private fixture.", definition.ref,
        profile.profile_id, profile.version, profile.content_digest, "trigger/v1", ("result",), 2, 1)
    with tempfile.TemporaryDirectory(prefix="reactive-cancel-") as root:
        scheduler = SQLiteReactiveScheduler(str(Path(root) / "scheduler.sqlite"))
        scheduler.register_profile(profile)
        scheduler.register_series(series)
        admission = scheduler.admit(_trigger(1, definition))

        def handler(_active, _step, _trigger_value):
            started.set()
            if not release.wait(5):
                raise AssertionError("bounded cancellation fixture was not released")
            return StepOutcome("handler finished", "deterministic", 1.0)

        context = LoopRuntimeContext.compatibility(capabilities=definition.required_capabilities,
            permissions=definition.permissions, executor_modes=definition.installed_executor_modes)
        executor = CanonicalReactiveExecutor(LoopDefinitionRegistry((definition,)), context,
                                            (ReactiveHandlerBinding(definition.ref, handler),))
        worker = AsyncReactiveWorker(scheduler, executor)

        async def exercise():
            task = asyncio.create_task(worker.run_once(ReactiveWorkerRequest(
                ActivationClaimRequest("cancel-await", "2026-09-06T00:00:01Z", 1, series.series_id),
                "2026-09-06T00:00:01Z", "2026-09-06T00:00:01Z")))
            try:
                if not await asyncio.to_thread(started.wait, 3):
                    raise AssertionError("handler did not start")
                task.cancel()
                propagated = False
                try:
                    await task
                except asyncio.CancelledError:
                    propagated = True
                before = scheduler.get_activation(admission.activation.activation_id)
                recovered = scheduler.recover_expired("2026-09-06T00:00:03Z")
                replacement = scheduler.claim(ActivationClaimRequest(
                    "replacement-worker", "2026-09-06T00:00:04Z", 1, series.series_id))
                return propagated, before, recovered, replacement
            finally:
                release.set()

        propagated, before, recovered, replacement = asyncio.run(exercise())
        final = scheduler.get_activation(admission.activation.activation_id)
        scheduler.close()
    return [{"test": "canceling_wait_does_not_fabricate_handler_cancellation_or_permit_replay",
             "passed": propagated and before.status is ActivationStatus.RUNNING and len(recovered) == 1
             and replacement is None
             and final.status is ActivationStatus.DEAD_LETTER
             and final.failure_code == "RUNNING_OUTCOME_UNKNOWN_RECONCILIATION_REQUIRED",
             "detail": "Thread completion after await cancellation does not commit or replay the activation."}]


def _history_fixture(root: Path, *, behavior: str = "success", authorize=None,
                     required: bool = True):
    """Host preparation and explicit fixture authority, never a provider call."""
    from ..loop.effect_approval import ApprovalDecision
    root.mkdir(parents=True, exist_ok=True)
    history_root = root / "runs"
    if required:
        history_root.mkdir(exist_ok=True)
    definition, profile = _definition(), _profile()
    series = ReactiveSeriesDefinition("series-worker", "Verify a durable private fixture.",
        definition.ref, profile.profile_id, profile.version, profile.content_digest,
        "trigger/v1", ("result",), 2, 1)
    scheduler = SQLiteReactiveScheduler(str(root / "scheduler.sqlite"))
    scheduler.register_profile(profile)
    scheduler.register_series(series)
    trigger = _trigger(1, definition)
    scheduler.admit(trigger)
    calls, approvals = [], []

    def handler(active, _step, _trigger_value):
        calls.append(active.loop_id)
        if behavior == "fail":
            raise ValueError("deliberate fixture handler failure")
        if behavior == "cancel":
            active.cancel("explicit fixture cancellation")
        return StepOutcome("fixture:" + behavior, "deterministic", 1.0)

    def decide(request):
        approvals.append(request)
        return (authorize(request) if authorize is not None else
                ApprovalDecision.approve(request.request_id, "independent_fixture_host"))

    policy = (ReactiveHistoryPolicy(True, str(history_root), decide)
              if required else ReactiveHistoryPolicy())
    context = LoopRuntimeContext.compatibility(
        capabilities=definition.required_capabilities, permissions=definition.permissions,
        executor_modes=definition.installed_executor_modes)
    executor = CanonicalReactiveExecutor(LoopDefinitionRegistry((definition,)), context,
        (ReactiveHandlerBinding(definition.ref, handler, policy),))
    return scheduler, executor, series, trigger, calls, approvals


def _history_run(scheduler, executor, series):
    return asyncio.run(AsyncReactiveWorker(scheduler, executor).run_once(ReactiveWorkerRequest(
        ActivationClaimRequest("history-worker", "2026-09-06T00:00:01Z", 60, series.series_id),
        "2026-09-06T00:00:01Z", "2026-09-06T00:00:02Z")))


def _history_process_fixture(phase: str, directory: str) -> None:
    if phase not in {"complete", "reopen"}:
        raise ValueError("invalid history process fixture phase")
    scheduler, executor, series, trigger, calls, approvals = _history_fixture(Path(directory))
    outcome = _history_run(scheduler, executor, series)
    activation = scheduler.get_activation(trigger.activation_id)
    history = executor.load_verified_history(activation, series=series, trigger=trigger)
    print(json.dumps({"phase": phase, "claimed": outcome.claimed,
        "activation": activation.to_dict(), "handler_calls": len(calls),
        "approvals": len(approvals), "verified_history_events": len(history.event_log),
        "verified_history_head": history.event_log[-1].event_digest}), flush=True)
    scheduler.close()


def run_history_proof(directory: str) -> dict:
    """Required-history proof, including real process reopen and fault injection."""
    from ..loop.approval_state_store import LocalJsonApprovalStateStore
    from ..loop.effect_approval import ApprovalDecision, EffectClass, EffectSpec
    from ..loop.reactive_contracts import ReactiveContractError
    from .run_history import RunHistory

    root = Path(directory)
    root.mkdir(parents=True, exist_ok=False)
    tests, phases = [], []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refused(action):
        try:
            action()
        except (ReactiveWorkerError, ReactiveContractError, ValueError, OSError):
            return True
        return False

    for phase in ("complete", "reopen"):
        from .workspace_backends import RestrictedLocalWorkspace
        from .workspace_contracts import CommandRequest, WorkspaceSpec
        backend = RestrictedLocalWorkspace(WorkspaceSpec("history-process-fixture", str(root),
            execution_enabled=True, allowed_commands=(sys.executable,)))
        completed = backend.command(CommandRequest((sys.executable, "-B", "-c",
            "import sys; sys.path.insert(0, sys.argv[3]); "
            "from loop_engine.core.reactive_worker_checks import _history_process_fixture; "
            "_history_process_fixture(sys.argv[1], sys.argv[2])",
            phase, str(root / "process"), str(Path(__file__).resolve().parents[2])),
            timeout_seconds=15, execution_authorized=True))
        if completed.exit_code != 0 or completed.output_truncated:
            raise AssertionError("history process fixture failed: " + completed.stderr)
        phases.append(json.loads(completed.stdout.strip().splitlines()[-1]))
    original, reopened = phases
    check("required_history_is_committed_and_read_verified_before_completion",
          original["activation"]["status"] == "completed"
          and original["activation"]["history_disposition"] == "persisted"
          and original["approvals"] == 1 and original["handler_calls"] == 1
          and original["verified_history_head"] == original["activation"]["history_ref"]["head_digest"])
    check("new_process_reads_exact_terminal_history_without_reexecution_or_new_approval",
          reopened["activation"] == original["activation"] and not reopened["claimed"]
          and reopened["handler_calls"] == reopened["approvals"] == 0
          and reopened["verified_history_head"] == original["verified_history_head"])
    scheduler, executor, series, trigger, _, _ = _history_fixture(root / "process")
    activation = scheduler.get_activation(trigger.activation_id)
    reference = activation.history_ref
    load = lambda value=activation, source=series, trigger_value=trigger: executor.load_verified_history(
        value, series=source, trigger=trigger_value)
    check("terminal_history_reference_roundtrips_with_exact_versioned_contract",
          ActivationRecord.from_dict(activation.to_dict()) == activation)
    legacy = activation.to_dict()
    legacy["record_type"] = "activation_record/v1"
    legacy.pop("history_ref")
    legacy.pop("history_disposition")
    legacy_record = ActivationRecord.from_dict(legacy)
    check("legacy_activation_reader_never_invents_durable_history",
          legacy_record.history_disposition is ActivationHistoryDisposition.LEGACY_UNRECORDED
          and legacy_record.history_ref is None and refused(lambda: load(legacy_record)))
    for name, value in (("head_digest", "0" * 64), ("event_count", reference.event_count + 1),
                        ("approval_record_digest", "0" * 64), ("trigger_digest", "0" * 64),
                        ("series_digest", "0" * 64)):
        changed = replace(activation, history_ref=replace(reference, **{name: value}))
        check("history_reload_refuses_changed_" + name, refused(lambda: load(changed)))
    for name, value in (("attempt", reference.attempt + 1),
                        ("fencing_token", reference.fencing_token + 1)):
        changed = replace(activation, **{name: value},
                          history_ref=replace(reference, **{name: value}))
        check("history_reload_refuses_transplanted_" + name, refused(lambda: load(changed)))
    check("history_reload_refuses_current_series_and_source_drift",
          refused(lambda: load(source=replace(series, goal="Different responsibility")))
          and refused(lambda: load(trigger_value=replace(trigger, source_loop_id="different-source"))))
    check("activation_cannot_transplant_definition_input_or_loop_identity",
          all(refused(lambda field=field, value=value: replace(activation, **{field: value}))
              for field, value in (("loop_definition_ref", replace(series.loop_definition_ref, version="1.0.1")),
                                   ("input_ref", replace(trigger.input_ref, content_digest="0" * 64)),
                                   ("loop_id", "unrelated-loop"))))

    run_root = root / "process" / "runs" / reference.run_id
    store = LocalJsonApprovalStateStore(str(run_root / "approval"))
    record_path = store.object_path(reference.approval_request_id)
    record = store.load(reference.approval_request_id)
    check("history_write_approval_is_exact_consumed_and_not_reusable",
          record.status == "consumed" and record.authorized_effect() is None
          and record.request.effect.target == str(run_root)
          and dict(record.request.effect.parameters)["head_digest"] == reference.head_digest)

    def tamper(name, path, transform):
        before = path.read_bytes()
        try:
            path.write_bytes(transform(before))
            check(name, refused(load))
        finally:
            path.write_bytes(before)

    tamper("corrupt_canonical_history_is_never_served_as_verified", run_root / "events.jsonl",
           lambda _: b"invalid json\n")
    tamper("uncommitted_history_is_never_served_as_verified", run_root / "manifest.json",
           lambda raw: json.dumps({**json.loads(raw), "committed": False}).encode())
    tamper("corrupt_native_approval_record_invalidates_history_readback", record_path,
           lambda _: b"invalid record")
    missing = run_root / "events.jsonl"
    backup = missing.with_suffix(".fixture-backup")
    missing.rename(backup)
    try:
        check("missing_history_is_not_reconstructed_or_marked_verified", refused(load)
              and not missing.exists())
    finally:
        backup.rename(missing)
    before_metadata = scheduler.get_activation(activation.activation_id).to_dict()
    check("history_validation_never_rewrites_terminal_metadata_or_source_events",
          before_metadata == original["activation"]
          and load().event_log[-1].event_digest == reference.head_digest)
    scheduler.close()

    for label, authorize in (
            ("denied", lambda req: ApprovalDecision.reject(req.request_id, "fixture_host", reason="No write authority")),
            ("edited", lambda req: ApprovalDecision.edit(req.request_id, "fixture_host",
                EffectSpec(EffectClass.LOCAL_WRITE, req.effect.operation, req.effect.target + "-changed")))):
        target = root / label
        scheduler, executor, series, trigger, calls, approvals = _history_fixture(target, authorize=authorize)
        outcome = _history_run(scheduler, executor, series)
        failed = scheduler.get_activation(trigger.activation_id)
        check("history_" + label + "_authority_prevents_writes_and_completion",
              failed.status is ActivationStatus.FAILED
              and failed.history_disposition is ActivationHistoryDisposition.PERSISTENCE_FAILED
              and failed.history_ref is None and outcome.error_code == "HISTORY_PERSISTENCE_FAILED"
              and len(calls) == len(approvals) == 1 and not list((target / "runs").iterdir()))
        scheduler.close()

    for label, method in (("save", "save"), ("readback", "load")):
        scheduler, executor, series, trigger, _, _ = _history_fixture(root / (label + "-failure"))
        with patch.object(RunHistory, method, side_effect=OSError("injected fixture persistence failure")):
            outcome = _history_run(scheduler, executor, series)
        failed = scheduler.get_activation(trigger.activation_id)
        check("history_" + label + "_failure_cannot_publish_completed",
              failed.status is ActivationStatus.FAILED
              and failed.history_ref is None and failed.terminal_code == "ACCEPTED"
              and failed.history_disposition is ActivationHistoryDisposition.PERSISTENCE_FAILED
              and outcome.error_code == "HISTORY_PERSISTENCE_FAILED"
              and refused(lambda: executor.load_verified_history(failed, series=series, trigger=trigger)))
        scheduler.close()

    for behavior, status, code in (("fail", ActivationStatus.FAILED, "INTERNAL_PROTOCOL_ERROR"),
                                    ("cancel", ActivationStatus.CANCELED, "CANCELED")):
        scheduler, executor, series, trigger, _, _ = _history_fixture(root / behavior, behavior=behavior)
        outcome = _history_run(scheduler, executor, series)
        terminal = scheduler.get_activation(trigger.activation_id)
        valid = terminal.history_ref is not None
        if valid:
            executor.load_verified_history(terminal, series=series, trigger=trigger)
        check("canonical_" + behavior + "_keeps_its_real_status_and_durable_history",
              terminal.status is status and terminal.terminal_code == code and valid
              and terminal.history_disposition is ActivationHistoryDisposition.PERSISTED)
        scheduler.close()
    scheduler, executor, series, trigger, _, approvals = _history_fixture(root / "ephemeral", required=False)
    _history_run(scheduler, executor, series)
    ephemeral = scheduler.get_activation(trigger.activation_id)
    check("default_binding_is_explicitly_nonpersistent_and_makes_no_history_writes",
          ephemeral.status is ActivationStatus.COMPLETED
          and ephemeral.history_disposition is ActivationHistoryDisposition.NOT_PERSISTED
          and ephemeral.history_ref is None and not approvals
          and not (root / "ephemeral" / "runs").exists())
    scheduler.close()
    check("required_history_rejects_missing_authority_relative_root_and_hidden_root_creation",
          refused(lambda: ReactiveHistoryPolicy(True, str(root), None))
          and refused(lambda: ReactiveHistoryPolicy(True, "relative", lambda _: None))
          and refused(lambda: ReactiveHistoryPolicy(True, str(root / "missing"), lambda _: None))
          and not (root / "missing").exists())
    link = root / "symlink-root"
    link.symlink_to(root / "process" / "runs", target_is_directory=True)
    check("history_policy_refuses_symlink_root", refused(lambda:
          ReactiveHistoryPolicy(True, str(link), lambda _: None)))
    return {"record_type": "reactive_required_history_proof/v1", "tests": tests,
            "phases": phases, "provider_calls": 0,
            "limitations": ["Process reopen after terminal persistence, not abrupt-crash history recovery.",
                "Host-managed local roots are checked; hostile concurrent filesystem replacement is not a supported writer.",
                "Consumed record identity is rechecked, not reissued as effect authority.",
                "Exact Loop definition and input identity do not qualify arbitrary handler implementation bytes."]}


def self_test() -> dict:
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    definition = _definition()
    profile = _profile()
    series = ReactiveSeriesDefinition(
        "series-worker", "Run one bounded reactive fixture activation.",
        definition.ref, profile.profile_id, profile.version,
        profile.content_digest, "trigger/v1", ("result",), 2, 3)
    started: list[float] = []
    finished: list[float] = []

    def handler(_loop, step: str, _trigger_value) -> StepOutcome:
        if step != "act":
            raise AssertionError("fixture definition contains act only")
        started.append(time.monotonic())
        time.sleep(0.2)
        finished.append(time.monotonic())
        return StepOutcome("reactive:completed", "deterministic", 1.0)

    with tempfile.TemporaryDirectory() as temporary:
        scheduler = SQLiteReactiveScheduler(os.path.join(
            temporary, "worker.sqlite"))
        scheduler.register_profile(profile)
        scheduler.register_series(series)
        admissions = tuple(scheduler.admit(_trigger(index, definition))
                           for index in range(1, 4))
        context = LoopRuntimeContext.compatibility(
            capabilities=definition.required_capabilities,
            permissions=definition.permissions,
            executor_modes=definition.installed_executor_modes)
        executor = CanonicalReactiveExecutor(
            LoopDefinitionRegistry((definition,)), context,
            (ReactiveHandlerBinding(definition.ref, handler),))
        worker = AsyncReactiveWorker(scheduler, executor)
        requests = tuple(ReactiveWorkerRequest(
            ActivationClaimRequest(
                f"worker-{index}", "2026-08-29T17:01:00Z", 60,
                series.series_id),
            "2026-08-29T17:01:01Z", "2026-08-29T17:01:02Z")
            for index in range(1, 4))
        wall_start = time.monotonic()
        outcomes = asyncio.run(worker.run_many(requests))
        wall_elapsed = time.monotonic() - wall_start

        check("three_reactive_activations_create_three_distinct_loops",
              len({item.loop_id for item in outcomes}) == 3
              and all(item.claimed and item.terminal_code == "ACCEPTED"
                      for item in outcomes), str(outcomes))
        check("blocking_handlers_overlap_through_thread_placement",
              len(started) == 3 and len(finished) == 3
              and max(started) < min(finished),
              f"all handlers started before the first finished; "
              f"elapsed={wall_elapsed:.3f}")
        check("every_claimed_loop_has_its_own_terminal_history",
              all(any(event.get("event") == "terminal"
                      and event.get("loop_id") == item.loop_id
                      for event in executor.ledger_for(
                          item.activation_id).events)
                  for item in outcomes))
        terminal = tuple(scheduler.get_activation(
            admission.activation.activation_id) for admission in admissions)
        check("durable_activation_records_bind_exact_loop_results",
              all(item.status is ActivationStatus.COMPLETED
                  and item.loop_id in {outcome.loop_id for outcome in outcomes}
                  and item.loop_definition_ref == definition.ref
                  for item in terminal))
        scheduler.close()

    with tempfile.TemporaryDirectory(prefix="reactive-process-proof-") as root:
        tests.extend(run_restart_proof(str(Path(root) / "proof"))["tests"])
    tests.extend(_cancellation_checks())
    with tempfile.TemporaryDirectory(prefix="reactive-history-proof-") as root:
        tests.extend(run_history_proof(str(Path(root) / "proof"))["tests"])

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "reactive_worker_self_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
