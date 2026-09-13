"""One campaign trial end to end through a fixture gateway.

No provider, no network, no task-database task: a fabricated task
directory, a gateway whose only endpoint answers from a canned transport,
and the runner's own run_trial. It proves the trial path records what it
claims (sources, applied configuration, step history, a terminal state)
and ends in a recorded state, before a real provider is spent on it. It
does not claim the fixture answer solves anything.
"""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from embodiment_lab.systematic_records import CampaignProjection
from embodiment_lab.trial_evidence import (_artifact_verified, _step_history_verified,
                                           campaign_evidence_summary, trial_evidence_report)
from embodiment_lab.task_database_campaign import CampaignTrialServices, file_digest, run_trial
from loop_engine.core.custom_endpoint import CustomEndpoint
from loop_engine.core.model_capabilities import ModelOutputCapability
from loop_engine.core.model_gateway import ModelGateway, provider_spec_from_endpoint
from loop_engine.core.model_routes import ModelRoute, RoutePolicy

REPOSITORY = Path(__file__).resolve().parents[3]


class CannedTransport:
    """Answers every chat request with one fixed completion, counting them."""

    def __init__(self):
        self.calls = 0
        self.urls = []

    def open(self, request, timeout):
        self.calls += 1
        self.urls.append(request.full_url)
        body = {'model': 'fixture-model',
                'choices': [{'message': {'content': 'fixture response'}, 'finish_reason': 'stop'}],
                'usage': {'prompt_tokens': 2, 'completion_tokens': 3}}
        return io.BytesIO(json.dumps(body).encode())


class OfflineTrialChecks(unittest.TestCase):
    def test_one_trial_runs_end_to_end_through_a_fixture_gateway(self):
        with tempfile.TemporaryDirectory(prefix='campaign-trial-offline-') as directory:
            root = Path(directory)
            task_directory = root / 'database' / 'family' / 'T-OFFLINE'
            task_directory.mkdir(parents=True)
            (task_directory / 'task.json').write_text(json.dumps({'id': 'T-OFFLINE', 'attachments': []}))
            (task_directory / 'task.md').write_text('# Offline fixture task\n\nReply with the word READY.\n')
            row = {'id': 'T-OFFLINE', 'task_directory': str(task_directory),
                   'descriptor_digest': file_digest(task_directory / 'task.json'),
                   'brief_digest': file_digest(task_directory / 'task.md')}
            endpoint = CustomEndpoint('offline_fixture', 'https://fixture.invalid/v1', 'fixture-model',
                locality='cloud', wire='openai', stream='buffer', auth_scheme='none', counts_as_evidence=True,
                output_capability=ModelOutputCapability(65536, 'offline trial contract'))
            gateway = ModelGateway(providers=(provider_spec_from_endpoint(endpoint),),
                routes=(ModelRoute('fixture.route', 'offline_fixture', 'fixture-model', 'cloud'),),
                policy=RoutePolicy(allow_local_counted_generation=True))
            configuration = {'harness': 'native_gateway', 'temperature': 0.0, 'output_allocation_tokens': 16384,
                             'context_delivery': 'bounded_inline', 'harness_fallback': 'none',
                             'mode': 'non_deterministic', 'provider': 'offline_fixture', 'model': 'fixture-model',
                             'route': 'fixture.route', 'provider_failover': False,
                             'max_model_calls': None, 'max_passes': None}
            manifest = {'harnesses': ['native_gateway'], 'repository': str(REPOSITORY),
                        'harness_file_digests': {}, 'provider_file': ''}
            transport = CannedTransport()
            with patch('loop_engine.core.custom_endpoint._endpoint_opener', return_value=transport):
                state = run_trial(root / 'campaign', row, configuration, manifest, '0-attempt-0',
                                  services=CampaignTrialServices(gateway=gateway))
            self.assertIn(state['status'], ('finished', 'failed'), state)
            self.assertEqual(state['task_id'], 'T-OFFLINE')
            self.assertFalse(state['task_accepted'])
            cell = Path(state['path'])
            self.assertTrue((cell / 'status.json').is_file())
            self.assertEqual(json.loads((cell / 'status.json').read_text())['status'], state['status'])
            records = CampaignProjection(cell / 'projection.duckdb')
            try:
                sources = records.latest('task_sources', 'selected')
                self.assertEqual(sources['source_digests'], {})
                self.assertTrue(sources['input_digest'])
                self.assertEqual(records.latest('trial', 'state')['status'], state['status'])
                if state['status'] == 'finished':
                    self.assertTrue((cell / 'outcome.json').is_file())
                    self.assertIn('engine_terminal', state)
                    self.assertIsNotNone(state.get('model_calls'))
                    self.assertGreaterEqual(transport.calls, 1)
                    self.assertTrue(all(url.endswith('/chat/completions') for url in transport.urls))
                    self.assertTrue(state['history_integrity']['intact'])
                else:
                    # A failure is a recorded trial with its error class and
                    # message, never an exception out of the trial.
                    self.assertTrue(state['error_type'])
                    self.assertIn('error_message', state)
            finally:
                records.close()
            report = trial_evidence_report(cell)
            self.assertEqual(report['task_id'], 'T-OFFLINE')
            self.assertTrue(report['links']['trial_state'])
            self.assertTrue(report['links']['task_sources'])
            if state['status'] == 'finished':
                self.assertGreaterEqual(report['links']['applied_configuration'], 1)
                self.assertGreaterEqual(report['links']['step_history'], 1)
                self.assertTrue(report['links']['outcome'])
                self.assertTrue(report['links']['run_history_intact'])
                self.assertTrue(report['links']['model_calls_accounted'])
                self.assertEqual(report['physical_model_calls'], transport.calls)
            # A trial nothing evaluated and nothing delivered is not complete
            # evidence, and the report says which links are missing.
            self.assertFalse(report['complete'])
            self.assertIn('independent_evaluation', report['gaps'])
            self.assertIn('delivered_artifacts', report['gaps'])
            # What the writer recorded and what the report re-verified from
            # disk agree for this cell, and the report says which links it
            # re-verified rather than took as recorded.
            self.assertEqual(report['disagreements'], {})
            self.assertIn('step_history', report['reverified_links'])
            self.assertEqual(report['recorded']['step_history'], report['links']['step_history'])
            # The re-verification helpers refuse what disk does not prove: a
            # missing artifact, a digest that no longer matches, a step
            # history directory that is not a saved history.
            artifact = root / 'delivered.txt'
            artifact.write_bytes(b'delivered')
            import hashlib
            digest = hashlib.sha256(b'delivered').hexdigest()
            self.assertTrue(_artifact_verified({'path': str(artifact), 'sha256': digest}))
            self.assertTrue(_artifact_verified({'path': str(artifact)}))
            self.assertFalse(_artifact_verified({'path': str(artifact), 'sha256': 'not-the-digest'}))
            self.assertFalse(_artifact_verified({'path': str(root / 'absent.txt')}))
            self.assertFalse(_artifact_verified({'artifact_ref': ''}))
            self.assertFalse(_step_history_verified({'history': str(root / 'not-a-history')}))
            (root / 'not-a-history').mkdir()
            self.assertFalse(_step_history_verified({'history': str(root / 'not-a-history')}))
            self.assertFalse(_step_history_verified({}))
            summary = campaign_evidence_summary(root / 'campaign')
            self.assertEqual((summary['trials'], summary['complete']), (1, 0))
            self.assertEqual(summary['gaps']['independent_evaluation'], 1)
            self.assertEqual(json.loads(json.dumps(summary)), summary)


class RefusalPageTrialChecks(unittest.TestCase):
    def test_a_page_in_the_providers_place_keeps_its_typed_code_and_its_call_count(self):
        """A login page or proxy notice answering a trial's model call is a
        classified outage on one counted call, never uncertain accounting
        with no code, which the worker would score as a failed cell."""
        class PageTransport:
            def __init__(self):
                self.calls = 0

            def open(self, request, timeout):
                self.calls += 1
                return io.BytesIO(b'<!doctype html><html><body><h1>Sign in</h1></body></html>')

        with tempfile.TemporaryDirectory(prefix='campaign-trial-page-') as directory:
            root = Path(directory)
            task_directory = root / 'database' / 'family' / 'T-PAGE'
            task_directory.mkdir(parents=True)
            (task_directory / 'task.json').write_text(json.dumps({'id': 'T-PAGE', 'attachments': []}))
            (task_directory / 'task.md').write_text('# Page fixture task\n\nReply READY.\n')
            row = {'id': 'T-PAGE', 'task_directory': str(task_directory),
                   'descriptor_digest': file_digest(task_directory / 'task.json'),
                   'brief_digest': file_digest(task_directory / 'task.md')}
            endpoint = CustomEndpoint('page_fixture', 'https://fixture.invalid/v1', 'fixture-model',
                locality='cloud', wire='openai', stream='buffer', auth_scheme='none', counts_as_evidence=True,
                output_capability=ModelOutputCapability(65536, 'offline trial contract'))
            gateway = ModelGateway(providers=(provider_spec_from_endpoint(endpoint),),
                routes=(ModelRoute('fixture.route', 'page_fixture', 'fixture-model', 'cloud'),),
                policy=RoutePolicy(allow_local_counted_generation=True))
            configuration = {'harness': 'native_gateway', 'temperature': 0.0, 'output_allocation_tokens': 16384,
                             'context_delivery': 'bounded_inline', 'harness_fallback': 'none',
                             'mode': 'non_deterministic', 'provider': 'page_fixture', 'model': 'fixture-model',
                             'route': 'fixture.route', 'provider_failover': False,
                             'max_model_calls': None, 'max_passes': None}
            manifest = {'harnesses': ['native_gateway'], 'repository': str(REPOSITORY),
                        'harness_file_digests': {}, 'provider_file': ''}
            transport = PageTransport()
            with patch('loop_engine.core.custom_endpoint._endpoint_opener', return_value=transport):
                state = run_trial(root / 'campaign', row, configuration, manifest, '0-attempt-0',
                                  services=CampaignTrialServices(gateway=gateway))
            self.assertEqual(state['status'], 'finished')
            self.assertEqual(state['engine_terminal'], 'PROVIDER_UNAVAILABLE')
            self.assertEqual(state['provider_failure_codes'], ['invalid_response_body'])
            self.assertEqual(state['model_calls'], transport.calls)
            self.assertTrue(state['model_call_accounting_complete'])
            from embodiment_lab.task_database_campaign import outage_decision
            from loop_engine.core.provider_failure_classes import WAIT_FOR_RECOVERY
            self.assertEqual(outage_decision(state, 0, 3)['decision'], WAIT_FOR_RECOVERY)
            from embodiment_lab.campaign_report import campaign_report, render_campaign_html
            report = campaign_report(root / 'campaign')
            self.assertEqual(report['coverage']['cells'], 1)
            self.assertEqual(report['accounting']['model_calls'], transport.calls)
            page = render_campaign_html(report)
            self.assertIn('T-PAGE', page)
            self.assertIn('PROVIDER_UNAVAILABLE', page)
            self.assertNotIn('<script', page)
            self.assertNotIn('http://', page.split('<main>', 1)[1].split('</main>')[0].replace('https://fixture.invalid', ''))


if __name__ == '__main__':
    unittest.main()
