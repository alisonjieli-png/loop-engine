"""Offline controller checks; no provider or task-quality evidence is implied."""
from dataclasses import replace
from pathlib import Path
import io
import json
import tempfile
import unittest
from unittest.mock import patch

from embodiment_lab.task_database_campaign import (
    RecordedSettingSession, campaign_space, confined_name, fair_order, outage_decision,
    reconcile_interrupted, run_trial)
from embodiment_lab.systematic_records import CampaignProjection
from loop_engine.code_nodes.solution_model_port import (
    FixtureModelExecutionRequest, ModelInvocationRequest, fixture_model_execution)
from loop_engine.loop.recursive_loop import Loop


class TaskDatabaseCampaignChecks(unittest.TestCase):
    def test_identifiers_cannot_escape_trial_directories(self):
        for invalid in ('../escape', '/absolute', 'a/b', 'a\\b', '.', '..', '', 'x\x00y'):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                confined_name(invalid)
        self.assertEqual(confined_name('SWE-001'), 'SWE-001')

    def test_family_order_preserves_every_task_without_a_sample_cap(self):
        tasks = [{'id': str(i), 'job_family': 'large' if i < 1500 else 'small',
                  'has_acceptance_criteria': i % 2 == 0} for i in range(1771)]
        ordered = fair_order(tasks)
        self.assertEqual(len(ordered), 1771)
        self.assertEqual({r['id'] for r in ordered}, {r['id'] for r in tasks})
        self.assertNotEqual(ordered[0]['job_family'], ordered[1]['job_family'])

    def test_grid_values_are_applied_fields_not_prose_claims(self):
        space = campaign_space(('native_gateway', 'pi', 'opencode', 'codex'))
        self.assertEqual(space.cardinality, 64)
        for i in range(space.cardinality):
            selected = space.configuration_at(i)
            self.assertEqual(space.index_of(selected), i)
            self.assertFalse(selected['provider_failover'])
            self.assertIsNone(selected['max_model_calls'])
            self.assertIsNone(selected['max_passes'])

    def test_diagonal_schedule_is_exhaustive_per_task(self):
        space = campaign_space(('native_gateway', 'pi'))
        for task_position in range(13):
            visited = {(round_number + task_position) % space.cardinality
                       for round_number in range(space.cardinality)}
            self.assertEqual(visited, set(range(space.cardinality)))

    def test_setting_wrapper_retains_gateway_authority_and_history(self):
        with tempfile.TemporaryDirectory(prefix='task-campaign-check-') as directory:
            records = CampaignProjection(Path(directory) / 'projection.duckdb')
            authority = fixture_model_execution(FixtureModelExecutionRequest(answers=('actual fixture',), max_model_calls=1))
            configuration = campaign_space(('native_gateway',)).configuration_at(0)
            session = RecordedSettingSession(authority, None, configuration, records)
            owner = Loop('configuration campaign fixture owner')
            invocation = ModelInvocationRequest('Fixture input', semantic_call_id='fixture-campaign-step')
            try:
                self.assertEqual(session.invoke(invocation, owner), 'actual fixture')
                self.assertEqual(session.calls_used, 1)
                self.assertFalse(session.accounting_uncertain)
                self.assertEqual(session.authority.config, authority.config)
                applied = records.latest('applied_configuration', invocation.semantic_call_id)
                self.assertEqual(applied['setting_report']['after']['settings'][0]['value'], 0.0)
                self.assertEqual(applied['input_digest'], invocation.exact_input_digest)
                history = records.latest('step_history', invocation.semantic_call_id)
                self.assertTrue(history['integrity']['intact'])
                self.assertEqual(history['known_calls'], 1)
                self.assertTrue(session.results)
            finally:
                records.close()

    def test_setting_refusal_cannot_invoke_provider(self):
        with tempfile.TemporaryDirectory(prefix='task-campaign-refusal-') as directory:
            records = CampaignProjection(Path(directory) / 'projection.duckdb')
            authority = fixture_model_execution(FixtureModelExecutionRequest(answers=('must not be used',)))
            configuration = {**campaign_space(('native_gateway',)).configuration_at(0), 'temperature': 100}
            session = RecordedSettingSession(authority, None, configuration, records)
            try:
                with self.assertRaises(ValueError):
                    session.invoke(ModelInvocationRequest('Fixture input'), Loop('refusal fixture'))
                self.assertEqual(session.calls_used, 0)
            finally:
                records.close()

    def test_hosted_and_loopback_urls_use_the_same_endpoint_contract(self):
        from loop_engine.core.custom_endpoint import CustomEndpoint
        from loop_engine.core.model_capabilities import ModelOutputCapability
        from loop_engine.core.model_gateway import ModelGateway, ModelGatewayConfig, provider_spec_from_endpoint
        from loop_engine.core.model_routes import ModelRoute, RoutePolicy
        from loop_engine.code_nodes.solution_model_port import ModelExecution
        # Explicit offline transports. This proves shared dispatch and URL
        # construction, not access to these hosts or real model quality.
        observed = []
        class Transport:
            def open(self, request, timeout):
                observed.append(request.full_url)
                if request.full_url.endswith('/api/chat'):
                    body = {'model': 'fixture-model', 'message': {'content': 'fixture response'},
                            'prompt_eval_count': 2, 'eval_count': 3, 'done': True}
                else:
                    body = {'model': 'fixture-model', 'choices': [{'message': {'content': 'fixture response'},
                            'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 2, 'completion_tokens': 3}}
                return io.BytesIO(json.dumps(body).encode())
        for base, locality, wire in (
                ('https://fixture.invalid/v1', 'cloud', 'openai'),
                ('http://127.0.0.1:12345/v1', 'local', 'openai'),
                ('http://127.0.0.1:12345/v1', 'cloud', 'openai'),
                ('https://fixture.invalid', 'cloud', 'ollama'),
                ('http://127.0.0.1:12345', 'local', 'ollama')):
            with self.subTest(base=base, locality=locality, wire=wire):
                endpoint = CustomEndpoint('endpoint_fixture', base, 'fixture-model', locality=locality,
                    wire=wire, stream='buffer', auth_scheme='none', counts_as_evidence=True,
                    output_capability=ModelOutputCapability(64, 'offline endpoint contract'))
                gateway = ModelGateway(providers=(provider_spec_from_endpoint(endpoint),),
                    routes=(ModelRoute('fixture.route', 'endpoint_fixture', 'fixture-model', locality),),
                    policy=RoutePolicy(allow_local_counted_generation=True))
                execution = ModelExecution(gateway, ModelGatewayConfig(route_names=('fixture.route',),
                    allowed_models=('fixture-model',), allow_failover=False), max_model_calls=1)
                with patch('loop_engine.core.custom_endpoint._endpoint_opener', return_value=Transport()):
                    result = execution.start_session().invoke(ModelInvocationRequest('Fixture input'),
                                                               Loop('shared endpoint contract fixture'))
                self.assertEqual(result, 'fixture response')
                self.assertEqual(observed[-1], endpoint.chat_url)

    def test_outage_decisions_are_bounded_and_never_wait_on_configuration_faults(self):
        def result(code, terminal='PROVIDER_UNAVAILABLE'):
            return {'engine_terminal': terminal, 'failure_code': code}
        self.assertIsNone(outage_decision(result('anything', terminal='VERIFICATION_FAILED'), 0, 3))
        self.assertEqual(outage_decision(result('authentication_failed'), 0, 3)['decision'], 'stop_route')
        self.assertEqual(outage_decision(result('model_not_found'), 0, 3)['decision'], 'stop_route')
        self.assertEqual(outage_decision(result('network_unreachable'), 0, 3)['decision'], 'wait_for_recovery')
        self.assertEqual(outage_decision(result('rate_limited'), 1, 3)['decision'], 'wait_for_allowance')
        self.assertEqual(outage_decision(result('network_unreachable'), 3, 3)['decision'], 'fail_cell')
        self.assertEqual(outage_decision(result('rate_limited'), 3, 3)['decision'], 'fail_cell')
        # A code the vocabulary does not know is read as an outage under this
        # terminal, and that reading is still bounded.
        self.assertEqual(outage_decision(result('SolutionModelError'), 0, 3)['decision'], 'wait_for_recovery')
        self.assertEqual(outage_decision(result(''), 3, 3)['decision'], 'fail_cell')

    def test_an_interrupted_trial_is_reconciled_on_restart(self):
        with tempfile.TemporaryDirectory(prefix='task-campaign-reconcile-') as directory:
            records = CampaignProjection(Path(directory) / 'campaign.duckdb')
            try:
                cursor = {'round': 2, 'task_position': 5, 'completed_trials': 7, 'trial_attempt': 1}
                self.assertIsNone(reconcile_interrupted(records, cursor))
                records.record('controller', 'active_trial', {'status': 'running', 'task_id': 'T-003',
                                                              'configuration_index': 9})
                row = reconcile_interrupted(records, cursor)
                self.assertEqual(row['status'], 'interrupted')
                self.assertEqual(row['occurrence'], '2-attempt-1')
                self.assertEqual(records.latest('trial_projection', 'T-003:2-attempt-1')['status'], 'interrupted')
                self.assertEqual(records.latest('controller', 'active_trial'), {})
                self.assertEqual(cursor['trial_attempt'], 2)
                self.assertEqual(cursor['interrupted_trials'], 1)
                self.assertEqual(records.latest('controller', 'cursor')['trial_attempt'], 2)
            finally:
                records.close()

    def test_run_trial_reports_an_existing_cell_instead_of_crashing(self):
        with tempfile.TemporaryDirectory(prefix='task-campaign-cell-') as directory:
            row = {'id': 'T-001', 'task_directory': '/nonexistent/task-database/T-001'}
            from embodiment_lab.systematic_records import digest
            cell = Path(directory) / 'trials' / ('T-001-' + digest(row['task_directory'])[:8]) / '0-attempt-0'
            cell.mkdir(parents=True)
            (cell / 'evidence.txt').write_text('kept')
            state = run_trial(directory, row, {'temperature': 0.0}, {}, '0-attempt-0')
            self.assertEqual(state['status'], 'failed')
            self.assertEqual(state['error_type'], 'FileExistsError')
            self.assertEqual((cell / 'evidence.txt').read_text(), 'kept')
            self.assertEqual(sorted(p.name for p in cell.iterdir()), ['evidence.txt'])


if __name__ == '__main__':
    unittest.main()
