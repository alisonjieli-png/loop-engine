"""Crash one actual worker while another runs and queued work can complete.

Private fault injection uses the existing scheduler, executor, history and
approval/workspace boundaries. It installs no production crash operation.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time
import unittest

if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == '_worker':
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

from loop_engine.code_nodes.solution_graph import LoopDefinitionRegistry
from loop_engine.core.reactive_worker_checks import _definition, _profile, _trigger
from loop_engine.core.reactive_scheduler import SQLiteReactiveScheduler
from loop_engine.core.reactive_worker import (
    AsyncReactiveWorker, CanonicalReactiveExecutor, ReactiveHandlerBinding,
    ReactiveHistoryPolicy, ReactiveWorkerRequest)
from loop_engine.core.record_operations_records import canonical_json
from loop_engine.core.runtime_observer import RuntimeObservationServices
from loop_engine.core.workspace_contracts import CommandRequest, WorkspaceSpec
from loop_engine.core.workspace_local import RestrictedLocalWorkspace
from loop_engine.core.workspace_operations import WorkspaceOperationService
from loop_engine.loop.effect_approval import ApprovalDecision, EffectApprovalService
from loop_engine.loop.reactive_activation import ActivationClaimRequest, ActivationStatus, ReactiveSeriesDefinition
from loop_engine.loop.recursive_loop import LoopLedger, StepOutcome
from loop_engine.loop.runtime_context import LoopRuntimeContext


def fixture(root):
    definition, profile = _definition(), _profile()
    scheduler = SQLiteReactiveScheduler(str(root / 'scheduler.sqlite'))
    scheduler.register_profile(profile)
    series = ReactiveSeriesDefinition('series-worker', 'Independent crash-isolation fixture activations.',
        definition.ref, profile.profile_id, profile.version, profile.content_digest,
        'trigger/v1', ('result',), 2, 2)
    scheduler.register_series(series)
    return scheduler, definition, series


def run_worker(root, phase):
    scheduler, definition, series = fixture(root)
    moment = '2026-09-06T00:00:10Z' if phase == 'recovery' else '2026-09-06T00:00:01Z'
    def handler(active, _step, _trigger_value):
        if phase == 'crash':
            time.sleep(0.2)
            os._exit(23)
        if phase == 'healthy':
            time.sleep(2.0)
        return StepOutcome('independent fixture work complete', 'deterministic', 1.0)
    policy = ReactiveHistoryPolicy(True, str(root / 'history'),
        lambda request: ApprovalDecision.approve(request.request_id, 'fixture.history'))
    context = LoopRuntimeContext.compatibility(capabilities=definition.required_capabilities,
        permissions=definition.permissions, executor_modes=definition.installed_executor_modes)
    executor = CanonicalReactiveExecutor(LoopDefinitionRegistry((definition,)), context,
        (ReactiveHandlerBinding(definition.ref, handler, policy),))
    result = asyncio.run(AsyncReactiveWorker(scheduler, executor).run_once(ReactiveWorkerRequest(
        ActivationClaimRequest(phase, moment, 1 if phase == 'crash' else 60, series.series_id), moment, moment)))
    print(canonical_json({'claimed': result.claimed, 'activation_id': result.activation_id,
        'terminal_code': result.terminal_code, 'pid': os.getpid()}))
    scheduler.close()


class ProcessIsolationChecks(unittest.TestCase):
    def test_crash_does_not_stop_running_peer_or_later_queue_and_history_survives(self):
        with TemporaryDirectory(prefix='loop-shared-queue-crash-') as directory:
            root = Path(directory)
            (root / 'history').mkdir()
            scheduler, definition, series = fixture(root)
            triggers = [_trigger(index, definition) for index in (1, 2, 3)]
            for trigger in triggers:
                scheduler.admit(trigger)
            def launch(phase):
                runtime = RuntimeObservationServices(ledger=LoopLedger())
                approvals = EffectApprovalService(runtime)
                operations = WorkspaceOperationService(RestrictedLocalWorkspace(WorkspaceSpec(
                    'crash-isolation-test', str(root), execution_enabled=True, allowed_commands=(sys.executable,))),
                    approvals=approvals, runtime=runtime)
                request = CommandRequest((sys.executable, '-I', '-B', str(Path(__file__).resolve()),
                    '_worker', str(root), phase), execution_authorized=True, timeout_seconds=15)
                plan = operations.plan_command(request, loop_id='test.supervisor', reason='Run this exact private process-isolation fault injection.')
                pending = approvals.create(plan.approval)
                approvals.resume(pending.pending, pending.resume_token,
                    ApprovalDecision.approve(plan.approval.request_id, 'fixture.explicit_test'))
                return operations.command(request, approval_id=plan.approval.request_id)
            def wait_running(trigger):
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    if scheduler.get_activation(trigger.activation_id).status is ActivationStatus.RUNNING:
                        return
                    time.sleep(0.01)
                self.fail('fixture worker did not start')
            with ThreadPoolExecutor(max_workers=3) as pool:
                crashed = pool.submit(launch, 'crash')
                wait_running(triggers[0])
                healthy = pool.submit(launch, 'healthy')
                wait_running(triggers[1])
                self.assertEqual(crashed.result(timeout=5).exit_code, 23)
                self.assertFalse(healthy.done())
                recovery = pool.submit(launch, 'recovery').result(timeout=5)
                self.assertEqual(recovery.exit_code, 0, recovery.stderr)
                self.assertEqual(json.loads(recovery.stdout)['terminal_code'], 'ACCEPTED')
                self.assertEqual(scheduler.get_activation(triggers[0].activation_id).status, ActivationStatus.DEAD_LETTER)
                self.assertEqual(scheduler.get_activation(triggers[1].activation_id).status, ActivationStatus.RUNNING)
                completed = healthy.result(timeout=5)
                self.assertEqual(completed.exit_code, 0, completed.stderr)
            scheduler.close()
            reopened, _, _ = fixture(root)
            try:
                self.assertEqual(reopened.get_activation(triggers[0].activation_id).failure_code,
                    'RUNNING_OUTCOME_UNKNOWN_RECONCILIATION_REQUIRED')
                for trigger in triggers[1:]:
                    record = reopened.get_activation(trigger.activation_id)
                    self.assertEqual(record.status, ActivationStatus.COMPLETED)
                    self.assertIsNotNone(record.history_ref)
                    self.assertEqual(record.attempt, 1)
                self.assertIsNone(reopened.claim(ActivationClaimRequest('reopened',
                    '2026-09-06T00:00:30Z', 30, series.series_id)))
            finally:
                reopened.close()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '_worker':
        run_worker(Path(sys.argv[2]), sys.argv[3])
    else:
        unittest.main()
