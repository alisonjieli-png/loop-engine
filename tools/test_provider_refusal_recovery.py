"""A counted failed canonical invocation may have no reported model identity."""
import copy
import tempfile
import unittest
from types import SimpleNamespace

from loop_engine.core.context_artifacts import (
    ContextArtifactManager,
    ContextArtifactStore,
    ContextArtifactStoreSpec,
)
from loop_engine.core.external_harness import (
    HarnessAdapterInfo,
    HarnessBudget,
    HarnessError,
    HarnessModelCall,
    HarnessModelIdentity,
    HarnessRunRequest,
    HarnessRunResult,
    HarnessServices,
    ModelOutputLimit,
    run_external_harness,
)
from loop_engine.core.external_harness_accounting import _validate_gateway_references
from loop_engine.core.external_harness_contract import (
    ADAPTER_CONTRACT_VERSION,
    MODEL_RESPONSE_EDGE,
)
from loop_engine.core.harness_execution_contracts import HarnessExecutionCapabilities
from loop_engine.core.model_routes import ModelRoute
from loop_engine.loop.encapsulate import as_model_loop
from loop_engine.loop.loop_contract import LoopContract
from loop_engine.loop.recursive_loop import Loop


def refusal_call():
    return HarnessModelCall('fixture-provider', '', False, error_code='invalid_response_body',
                            gateway_loop_id='physical-call', route_id='fixture.route')


def events():
    common = {'loop_id': 'physical-call', 'owner_loop_id': 'owner', 'semantic_call_id': 'semantic-call',
              'loop_definition_id': 'definition', 'loop_definition_version': '1', 'loop_definition_digest': 'a' * 64}
    return [{**common, 'event': 'model_boundary_deferred', 'request_model_binding': {
        'record_type': 'model_request_binding/v1', 'provider': 'fixture-provider',
        'model': 'requested-model', 'route': 'fixture.route'}},
        {**common, 'event': 'model_invocation_failed', 'provider': 'fixture-provider', 'model': '',
         'prompt_tokens': None, 'eval_tokens': None}]


class ProviderRefusalRecoveryChecks(unittest.TestCase):
    def test_failed_unknown_call_is_still_checked_against_requested_model_authority(self):
        def invoke(requested_model):
            owner = Loop('Unknown-model authority fixture')
            route = ModelRoute('fixture.route', 'fixture-provider', requested_model)
            class Adapter:
                def info(self):
                    return HarnessAdapterInfo('host_gateway', 'fixture/v1', 'fixture', available=True,
                        execution_capabilities=HarnessExecutionCapabilities(supported_features=('model_routes',)),
                        adapter_contract_version=ADAPTER_CONTRACT_VERSION, engine_kind='direct_model_step',
                        supported_edge_contracts=(MODEL_RESPONSE_EDGE,))

                def run(self, request, services):
                    observed = as_model_loop('Opaque refusal fixture', lambda: SimpleNamespace(
                        provider='fixture-provider', model='', ok=False, prompt_tokens=None, eval_tokens=None),
                        parent=owner, request_route=route)
                    call = HarnessModelCall('fixture-provider', '', False, error_code='invalid_response_body',
                        gateway_loop_id=observed['loop_id'], route_id='fixture.route')
                    return HarnessRunResult(request.request_id, request.harness_id, 'failed',
                        error_code='invalid_response_body', model_calls=(call,), adapter_version='fixture/v1')

            limit = ModelOutputLimit(64, 'custom_endpoint_declared', 'offline fixture',
                provider_id='fixture-provider', model_id='requested-model', route_id='fixture.route')
            request = HarnessRunRequest('refusal-authority', 'host_gateway', 'Observe a failed call',
                LoopContract('refusal', 'model_led', ('prompt/v1',), ('answer/v1',), ('pure',)),
                HarnessBudget(1, output_limit=limit), provider_id='fixture-provider', model_id='requested-model',
                model_routes=('fixture.route',), authorize_model_calls=True,
                authorized_model_identities=(HarnessModelIdentity('fixture-provider', 'requested-model', 'fixture.route'),))
            with tempfile.TemporaryDirectory() as directory:
                services = HarnessServices(artifact_store=ContextArtifactManager(
                    ContextArtifactStore(ContextArtifactStoreSpec(directory))))
                return run_external_harness(Adapter(), request, parent=owner, services=services)

        accepted = invoke('requested-model')
        self.assertFalse(accepted.completed)
        self.assertEqual(accepted.model_calls[0].error_code, 'invalid_response_body')
        self.assertEqual(accepted.physical_model_calls, 1)
        self.assertIsNone(accepted.total_tokens)
        self.assertEqual(accepted.model_calls[0].model, '')
        with self.assertRaises(HarnessError):
            invoke('unapproved-model')

    def test_failed_unknown_model_keeps_observation_separate_from_requested_authority(self):
        call = refusal_call()
        bindings = _validate_gateway_references((call,), events(), {'owner'})
        self.assertEqual(call.model, '')
        self.assertIsNone(call.total_tokens)
        self.assertEqual(bindings['physical-call'], ('fixture-provider', 'requested-model', 'fixture.route'))

    def test_unknown_model_requires_failed_typed_canonical_observation(self):
        for fields in ({'ok': True}, {'error_code': ''}, {'gateway_loop_id': ''}, {'model': ' '}):
            value = {'provider': 'fixture-provider', 'model': '', 'ok': False,
                     'error_code': 'invalid_response_body', 'gateway_loop_id': 'physical-call', 'route_id': 'fixture.route'}
            value.update(fields)
            with self.subTest(fields=fields), self.assertRaises(HarnessError):
                HarnessModelCall(**value)

    def test_unknown_observation_cannot_guess_or_forge_requested_binding(self):
        for kind in ('missing', 'version', 'provider', 'route', 'empty_model', 'extra', 'wrong_owner', 'not_failed'):
            rows = copy.deepcopy(events())
            if kind == 'missing': rows[0].pop('request_model_binding')
            elif kind == 'version': rows[0]['request_model_binding']['record_type'] = 'model_request_binding/v999'
            elif kind == 'provider': rows[0]['request_model_binding']['provider'] = 'other-provider'
            elif kind == 'route': rows[0]['request_model_binding']['route'] = 'other.route'
            elif kind == 'empty_model': rows[0]['request_model_binding']['model'] = ''
            elif kind == 'extra': rows[0]['request_model_binding']['unexpected'] = True
            elif kind == 'wrong_owner': rows[1]['owner_loop_id'] = 'other-owner'
            else: rows[1]['event'] = 'model_led'
            with self.subTest(kind=kind), self.assertRaises(HarnessError):
                _validate_gateway_references((refusal_call(),), rows, {'owner'})


if __name__ == '__main__':
    unittest.main()
