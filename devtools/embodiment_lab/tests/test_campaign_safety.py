"""Offline worker control-flow and real trial-boundary failure controls."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest

from embodiment_lab.systematic_records import CampaignProjection
from embodiment_lab.task_database_campaign import prepare, worker


class StopFixture(Exception):
    pass


class CampaignSafetyChecks(unittest.TestCase):
    def prepare_fixture(self, root, *, not_before=''):
        database = root / 'database'
        task = database / 'tasks/family/synthetic/T-1'
        task.mkdir(parents=True)
        (task / 'task.json').write_text(json.dumps({'id': 'T-1', 'attachments': []}))
        (task / 'task.md').write_text('Offline fixture instructions.')
        (database / 'catalog.json').write_text(json.dumps({'tasks': [{
            'id': 'T-1', 'path': 'tasks/family/synthetic/T-1', 'job_family': 'family',
            'status': 'ready', 'has_acceptance_criteria': True}]}))
        provider = root / 'provider.yaml'
        provider.write_text('models:\n  providers:\n    - id: fixture\n      kind: custom\n'
            '      endpoint: http://127.0.0.1:1/v1\n      model: fixture-model\n'
            '      auth_scheme: none\n      maximum_output_tokens: 65536\n'
            '      maximum_output_source: offline contract\n')
        return prepare(root / 'campaign', database, provider, root,
                       route_name='custom.fixture', not_before=not_before)

    def test_future_activation_cannot_probe_or_dispatch(self):
        with TemporaryDirectory(prefix='campaign-future-') as directory:
            root = Path(directory)
            self.prepare_fixture(root, not_before='9999-01-01T00:00:00Z')
            with patch('embodiment_lab.task_database_campaign.probe_gateway') as probe, \
                 patch('embodiment_lab.task_database_campaign.run_trial') as dispatch, \
                 patch('embodiment_lab.task_database_campaign.time.sleep', side_effect=StopFixture), \
                 patch('embodiment_lab.task_database_campaign.signal.signal'):
                with self.assertRaises(StopFixture):
                    worker(root / 'campaign')
                probe.assert_not_called()
                dispatch.assert_not_called()
            self.assertEqual(json.loads((root / 'campaign/status.json').read_text())['status'],
                             'waiting_for_activation_window')

    def test_quota_wait_does_not_fail_the_task_or_drain_the_queue(self):
        with TemporaryDirectory(prefix='campaign-quota-') as directory:
            root = Path(directory)
            self.prepare_fixture(root)
            failed = {'status': 'finished', 'engine_terminal': 'PROVIDER_UNAVAILABLE',
                      'failure_code': 'PROVIDER_UNAVAILABLE', 'provider_failure_codes': ['rate_limited']}
            with patch('embodiment_lab.task_database_campaign.probe_gateway', return_value={'reachable': True}), \
                 patch('embodiment_lab.task_database_campaign.run_trial', return_value=failed) as dispatch, \
                 patch('embodiment_lab.task_database_campaign.time.sleep'), \
                 patch('embodiment_lab.task_database_campaign.signal.signal'):
                worker(root / 'campaign', wait_attempt_ceiling=1)
            self.assertEqual(dispatch.call_count, 2)
            state = json.loads((root / 'campaign/status.json').read_text())
            self.assertEqual(state['status'], 'provider_wait_suspended')
            self.assertEqual(state['cursor']['task_position'], 0)
            self.assertEqual(state['cursor']['round'], 0)
            self.assertEqual(state['cursor']['completed_trials'], 0)
            self.assertEqual(state['cursor'].get('failed_cells', 0), 0)
            self.assertEqual(state['cursor']['allowance_attempts'], 1)

    def test_crash_marker_stays_pending_without_dispatch(self):
        with TemporaryDirectory(prefix='campaign-resume-') as directory:
            root = Path(directory)
            self.prepare_fixture(root)
            records = CampaignProjection(root / 'campaign/campaign.duckdb')
            records.record('controller', 'active_trial', {'task_id': 'T-1', 'status': 'running', 'configuration_index': 0})
            records.close()
            with patch('embodiment_lab.task_database_campaign.probe_gateway') as probe, \
                 patch('embodiment_lab.task_database_campaign.run_trial') as dispatch, \
                 patch('embodiment_lab.task_database_campaign.signal.signal'):
                worker(root / 'campaign')
                probe.assert_not_called()
                dispatch.assert_not_called()
            state = json.loads((root / 'campaign/status.json').read_text())
            self.assertEqual(state['status'], 'interrupted_requires_reconciliation')
            self.assertFalse(state['effects_reconciled'])
            self.assertFalse(state['replay_authorized'])

    def test_real_trial_boundary_keeps_authentication_cause(self):
        from urllib.error import HTTPError
        from embodiment_lab.task_database_campaign import CampaignTrialServices, outage_decision, run_trial
        from loop_engine.core.settings_loader import load_runtime_settings
        with TemporaryDirectory(prefix='campaign-authentication-') as directory:
            root = Path(directory)
            manifest = self.prepare_fixture(root)
            row = json.loads((root / 'campaign/task-population.json').read_text())['tasks'][0]
            gateway = load_runtime_settings(str(root / 'provider.yaml')).settings.build_gateway()
            configuration = {**manifest['configuration_space']['fixed_context'],
                'harness': 'native_gateway', 'temperature': 0.0, 'output_allocation_tokens': 16384,
                'context_delivery': 'bounded_inline', 'harness_fallback': 'none'}
            class DeniedTransport:
                def open(self, request, timeout):
                    raise HTTPError(request.full_url, 401, 'unauthorized', {}, None)
            with patch('loop_engine.core.custom_endpoint._endpoint_opener', return_value=DeniedTransport()):
                result = run_trial(root / 'campaign', row, configuration, manifest, 'authentication-control',
                                   services=CampaignTrialServices(gateway))
            self.assertEqual(result['status'], 'finished', result)
            self.assertEqual(result['engine_terminal'], 'PROVIDER_UNAVAILABLE', result)
            self.assertEqual(result['provider_failure_codes'], ['authentication_failed'])
            self.assertEqual(outage_decision(result, 0, 3)['decision'], 'stop_route')
            self.assertTrue(result['history_integrity']['intact'])


if __name__ == '__main__':
    unittest.main()
