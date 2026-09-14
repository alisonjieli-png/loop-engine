"""Offline controls for route selection and time-gated access checks."""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from embodiment_lab.campaign_activation import CampaignAccessPolicy, activation_due, probe_gateway, utc_time
from embodiment_lab.systematic_records import CampaignProjection
from embodiment_lab.task_database_campaign import campaign_space
from loop_engine.code_nodes.solution_model_port import FixtureModelExecutionRequest, fixture_model_execution
from loop_engine.core.model_routes import ModelRoute


class CampaignActivationChecks(unittest.TestCase):
    def test_probe_policy_is_explicit_and_does_not_probe_every_cell_by_default(self):
        policy = CampaignAccessPolicy()
        self.assertTrue(policy.requires_probe(False))
        self.assertFalse(policy.requires_probe(True))
        self.assertTrue(CampaignAccessPolicy('per_trial').requires_probe(True))
        self.assertEqual(CampaignAccessPolicy.from_dict(policy.to_dict()), policy)
        with self.assertRaises(ValueError):
            CampaignAccessPolicy('never_check')
        with self.assertRaises(TypeError):
            policy.requires_probe('yes')

    def test_time_gate_is_explicit_and_never_uses_a_naive_clock(self):
        gate = '2026-09-14T00:23:46+00:00'
        self.assertFalse(activation_due(gate, datetime(2026, 9, 13, 23, tzinfo=timezone.utc)))
        self.assertTrue(activation_due(gate, utc_time(gate)))
        self.assertTrue(activation_due('', datetime.now(timezone.utc)))
        self.assertTrue(activation_due(None, datetime.now(timezone.utc)))
        # A hand-edited manifest cannot open the gate with a value that is
        # not a declared time: zero, false, and a number are refused.
        for value in (0, False, 1.5, ['2026-09-14T00:23:46+00:00']):
            with self.assertRaises(ValueError):
                activation_due(value, datetime.now(timezone.utc))
        with self.assertRaises(ValueError):
            utc_time('2026-09-14T00:23:46')
        with self.assertRaises(ValueError):
            activation_due(gate, datetime(2026, 9, 14))

    def test_grid_binds_a_typed_route_without_a_provider_specific_branch(self):
        for location in ('local', 'cloud'):
            route = ModelRoute('configured.route', 'configured_provider', 'exact-model', location)
            space = campaign_space(('native_gateway',), route=route)
            for index in range(space.cardinality):
                configuration = space.configuration_at(index)
                self.assertEqual(configuration['provider'], route.provider)
                self.assertEqual(configuration['model'], route.model)
                self.assertEqual(configuration['route'], route.name)
                self.assertFalse(configuration['provider_failover'])

    def test_access_probe_uses_the_gateway_and_keeps_its_own_history(self):
        authority = fixture_model_execution(FixtureModelExecutionRequest(answers=('READY',)))
        route = authority.gateway.registry.get('fixture.route')
        with tempfile.TemporaryDirectory(prefix='campaign-access-check-') as directory:
            records = CampaignProjection(Path(directory) / 'campaign.duckdb')
            try:
                result = probe_gateway(authority.gateway, route, records)
                self.assertTrue(result['reachable'])
                self.assertEqual(result['model_calls'], 1)
                self.assertTrue(result['history_integrity']['intact'])
                self.assertFalse(result['task_accepted'])
                self.assertFalse(result['model_quality_verified'])
                self.assertEqual(result['gateway_results'][0]['attempts'][0]['maximum_output_tokens'], 64)
                self.assertEqual(records.latest('provider_access', route.name), result)
            finally:
                records.close()


if __name__ == '__main__':
    unittest.main()
