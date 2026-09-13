"""Offline application accounting regression, with no live provider calls."""
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

import duckdb

from embodiment_lab.systematic_runtime import SemanticStepSession, NativeGatewayAdapter
from loop_engine.code_nodes.solution_model_port import FixtureModelExecutionRequest, fixture_model_execution
from loop_engine.core.context_artifacts import (
    ContextArtifactManager, ContextArtifactServices, ContextArtifactStore, ContextArtifactStoreSpec)
from loop_engine.core.external_harness import HarnessRegistry
from loop_engine.core.harness_semantic import HarnessSemanticBinding


class SystematicRuntimeChecks(unittest.TestCase):
    def test_malformed_test_result_is_not_counted_as_a_boolean_pass(self):
        from embodiment_lab.qualify_harness_recovery import summarize_tests
        summary = summarize_tests({'tests':[
            {'passed': True}, {'passed': False}, {'passed': 'nonempty explanation'}]})
        self.assertEqual(summary['strict_boolean_passed'], 1)
        self.assertEqual(len(summary['failures']), 1)
        self.assertEqual(len(summary['malformed_test_results']), 1)
        self.assertEqual(summary['total'], 3)

    def test_multiple_brokered_calls_are_not_reported_as_one_outer_physical_call(self):
        class TwoCallFixture(NativeGatewayAdapter):
            def run(self, request, services):
                client = services.runtime_binding.runtime_object
                client({'model':request.model_id, 'messages':[
                    {'role':'user','content':request.input_data['prompt']}]})
                return super().run(request, services)

        with tempfile.TemporaryDirectory(prefix='systematic-runtime-check-') as directory:
            root = Path(directory)
            manager = ContextArtifactManager(ContextArtifactServices(
                ContextArtifactStore(ContextArtifactStoreSpec(str(root/'artifacts')))))
            authority = fixture_model_execution(FixtureModelExecutionRequest(
                answers=('{"answer":1}', '{"answer":1}'), max_model_calls=2))
            binding = HarnessSemanticBinding('native_gateway', HarnessRegistry((TwoCallFixture(),)),
                str(root/'processes'), artifact_store=manager)
            authority = replace(authority, harness=binding,
                config=replace(authority.config, max_route_attempts=2))
            # Bind the application to an explicit offline fixture, not a named
            # external harness or a fabricated provider-integration result.
            step = object.__new__(SemanticStepSession)
            step.root, step.harness_id, step.artifacts = root, 'native_gateway', manager
            step.session, step.history = authority.start_session(artifact_store=manager), []
            result = step.invoke('Resolve an offline accounting control', {'input':1},
                {'type':'object','properties':{'answer':{'const':1}},'required':['answer']})
            self.assertTrue(result['accepted_response'], result['error'])
            self.assertEqual(result['model_calls'], 2)
            self.assertTrue(result['model_call_accounting_complete'])
            connection = duckdb.connect()
            try:
                count = connection.execute(
                    "SELECT count(*) FROM read_json_objects(?) WHERE json_extract_string(json,'$.event_type')='model_invocation'",
                    [str(Path(result['run_history'])/'events.jsonl')]).fetchone()[0]
            finally:
                connection.close()
            self.assertEqual(count, 2)


if __name__ == '__main__':
    unittest.main()
