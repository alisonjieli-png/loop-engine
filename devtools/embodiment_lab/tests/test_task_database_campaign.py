"""Offline controller checks; no provider or task-quality evidence is implied."""
from dataclasses import replace
from pathlib import Path
import io
import json
import tempfile
import unittest
from unittest.mock import patch

from embodiment_lab.task_database_campaign import RecordedSettingSession, campaign_space, confined_name, fair_order
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


if __name__ == '__main__':
    unittest.main()
