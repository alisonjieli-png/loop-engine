"""Offline controls for response policies; these do not qualify a live harness."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from embodiment_lab.configuration_study import AdmissionConfiguration
from embodiment_lab.systematic_runtime import NativeGatewayAdapter, SemanticStepSession
from loop_engine.code_nodes.solution_model_port import FixtureModelExecutionRequest, fixture_model_execution
from loop_engine.core.context_artifacts import (
    ContextArtifactManager,ContextArtifactServices,ContextArtifactStore,ContextArtifactStoreSpec)
from loop_engine.core.external_harness import HarnessRegistry
from loop_engine.core.harness_semantic import HarnessSemanticBinding


class ConfigurationStudyChecks(unittest.TestCase):
    def run_response(self, answer, policy):
        with tempfile.TemporaryDirectory(prefix='configuration-check-') as directory:
            root=Path(directory)
            artifacts=ContextArtifactManager(ContextArtifactServices(ContextArtifactStore(ContextArtifactStoreSpec(directory))))
            authority=fixture_model_execution(FixtureModelExecutionRequest(answers=(answer,),max_model_calls=1))
            binding=HarnessSemanticBinding('native_gateway',HarnessRegistry((NativeGatewayAdapter(),)),
                str(root/'processes'),artifact_store=artifacts)
            authority=replace(authority,harness=binding)
            step=object.__new__(SemanticStepSession)
            step.root,step.harness_id,step.artifacts=root,'native_gateway',artifacts
            step.session,step.history=authority.start_session(artifact_store=artifacts),[]
            return step.invoke('Check one response',{'request':'return answer=7'},
                {'type':'object','properties':{'answer':{'type':'integer'}},'required':['answer']},
                response_policy=AdmissionConfiguration('native_gateway',policy).policy())

    def test_strict_refuses_fence_without_fabricating_an_answer(self):
        result=self.run_response('```json\n{"answer":7}\n```','strict_json')
        self.assertFalse(result['accepted_response'])
        self.assertEqual(result['model_calls'],1)
        self.assertIsNone(result['value'])
        self.assertIsNone(result['raw_output_digest'])

    def test_explicit_normalization_preserves_value_and_single_physical_call(self):
        result=self.run_response('```json\n{"answer":7}\n```','meaning_preserving')
        self.assertTrue(result['accepted_response'],result['error'])
        self.assertEqual(result['value'],{'answer':7})
        self.assertEqual(result['model_calls'],1)
        self.assertFalse(result['task_accepted'])
        self.assertEqual(result['response_admission']['strategy'],'json_markdown_fence_removed')

    def test_normalization_does_not_invent_missing_fields(self):
        result=self.run_response('```json\n{"different":7}\n```','meaning_preserving')
        self.assertFalse(result['accepted_response'])
        self.assertIsNone(result['value'])
        self.assertEqual(result['model_calls'],1)

    def test_configuration_refuses_unregistered_axes(self):
        with self.assertRaises(ValueError):AdmissionConfiguration('unknown','strict_json')
        with self.assertRaises(ValueError):AdmissionConfiguration('native_gateway','invent_missing_fields')


if __name__=='__main__':unittest.main()
