"""Experimental composition controls. All model and executor replies are fixtures."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from embodiment_lab.artifact_task_trial import (
    ArtifactTrialRequest, TrialFeedback, _compose_prompt, _validate_feedback, run_artifact_trial)
from embodiment_lab.campaign_sources import snapshot_task_sources
from embodiment_lab.systematic_records import CampaignProjection
from embodiment_lab.task_database_campaign import file_digest
from loop_engine.code_nodes.solution_model_port import FixtureModelExecutionRequest, fixture_model_execution


class ArtifactTrialChecks(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='artifact-trial-check-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.directory = self.root / 'database' / 'task'
        self.directory.mkdir(parents=True)
        (self.directory / 'task.md').write_text('Return a JSON object containing the answer.')
        (self.directory / 'task.json').write_text(json.dumps({'id': 'fixture', 'attachments': []}))

    def request(self, changes=None):
        frozen = snapshot_task_sources(self.directory, self.directory.parent)
        task = {'id': 'fixture', 'task_directory': str(self.directory),
                'task_root': str(self.directory.parent), 'source_snapshot': frozen.to_dict(),
                'descriptor_digest': file_digest(self.directory / 'task.json'),
                'brief_digest': file_digest(self.directory / 'task.md')}
        configuration = {'harness': 'native_gateway', 'provider': 'fixture', 'model': 'fixture-model',
            'route': 'fixture.route', 'temperature': 0.0, 'output_allocation_tokens': 64,
            'context_delivery': 'bounded_inline', 'harness_fallback': 'none',
            'mode': 'non_deterministic', 'provider_failover': False}
        configuration.update(changes or {})
        return ArtifactTrialRequest(str(self.root / 'trial'), task, configuration,
            str(Path(__file__).resolve().parents[3]), 'fixture-image@sha256:' + 'a' * 64)

    def run_fixture(self, request, response):
        authority = fixture_model_execution(FixtureModelExecutionRequest(answers=(response,)))
        # Avoid host-wide software hashing in this contract fixture.
        with patch('embodiment_lab.artifact_task_trial.engine_identity', return_value={'fixture': True}):
            return run_artifact_trial(request, authority.gateway)

    def test_outer_project_contract_does_not_replace_original_deliverable_contract(self):
        original = 'Return only {"answer": 42} as the task deliverable.'
        prompt = json.loads(_compose_prompt(original, {'record_type': 'project'}, (), []))
        self.assertEqual(prompt['original_task'], original)
        self.assertEqual(prompt['response_contract']['record_type'], 'project')
        self.assertIn('not this outer response', prompt['contract_notes'])

    def test_unimplemented_configuration_is_recorded_without_a_model_call(self):
        result = self.run_fixture(self.request({'unknown_setting': True}), 'unused')
        self.assertEqual(result['status'], 'ineligible_configuration')
        self.assertEqual(result['model_calls'], 0)
        self.assertTrue(result['history_integrity']['intact'])

    def test_dataset_cannot_be_silently_omitted_by_attachment_only_composition(self):
        (self.directory / 'rows.txt').write_text('source dataset')
        (self.directory / 'task.json').write_text(json.dumps(
            {'id': 'fixture', 'attachments': [], 'data_path': 'rows.txt'}))
        result = self.run_fixture(self.request(), 'unused')
        self.assertEqual(result['ineligibility_reason'], 'dataset_materializer_not_bound')
        self.assertEqual(result['model_calls'], 0)

    def test_bad_manifest_keeps_history_diagnostic_and_exact_response(self):
        response = '{"answer": "private fixture response marker"}'
        result = self.run_fixture(self.request(), response)
        self.assertEqual(result['status'], 'failed', result)
        self.assertEqual(result['model_calls'], 1)
        self.assertTrue(result['history_integrity']['intact'])
        self.assertIn('diagnostic_ref', result)
        self.assertNotIn('private fixture response marker', json.dumps(result))
        projection = CampaignProjection(self.root / 'trial' / 'projection.duckdb')
        try:
            self.assertIsNotNone(projection.latest('candidate', 'response'))
            self.assertEqual(projection.latest('source_verification', 'after')['state'], 'verified')
        finally:
            projection.close()

    def test_executed_candidate_is_not_independently_accepted(self):
        manifest = {'record_type': 'generated_project_manifest/v1', 'project_id': 'fixture-project',
            'summary': 'Fixture candidate.',
            'files': [{'path': 'run.py', 'content': 'print("fixture")'}],
            'commands': [{'argv': ['python3', 'run.py'], 'purpose': 'Fixture execution',
                'timeout_seconds': 10, 'command_kind': 'execute', 'network_access': False,
                'expected_exit_codes': [0]}],
            'expected_artifacts': [{'path': 'output/result.txt', 'media_type': 'text/plain',
                                    'minimum_bytes': 1, 'constraint': ''}]}
        with patch('embodiment_lab.artifact_task_trial.execute_generated_project',
                   return_value={'deterministic_checks_passed': True, 'artifacts': [], 'workspace': 'fixture'}):
            result = self.run_fixture(self.request(), json.dumps(manifest))
        self.assertEqual(result['status'], 'finished_candidate_not_independently_accepted', result)
        self.assertTrue(result['execution_succeeded'])
        self.assertFalse(result['task_accepted'])
        self.assertFalse(result['full_system_benchmark'])
        self.assertEqual(result['model_calls'], 1)

    def test_feedback_requires_exact_unchanged_evidence(self):
        request = self.request()
        frozen = snapshot_task_sources(self.directory, self.directory.parent)
        evidence = self.root / 'evaluation.txt'
        evidence.write_text('independent development observation')
        feedback = TrialFeedback(frozen.content_digest, 'a' * 64, str(evidence),
                                hashlib.sha256(evidence.read_bytes()).hexdigest(), 'Scoped observation')
        _validate_feedback((feedback,), frozen)
        with self.assertRaises(ValueError):
            _validate_feedback((replace(feedback, source_snapshot_digest='b' * 64),), frozen)
        evidence.write_text('changed observation')
        with self.assertRaises(ValueError):
            _validate_feedback((feedback,), frozen)


if __name__ == '__main__':
    unittest.main()
