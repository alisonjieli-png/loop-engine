"""Offline wire and accounting controls. No live provider is contacted."""
import io
import json
from dataclasses import replace
from unittest.mock import patch
from urllib.error import HTTPError
import unittest

from loop_engine.code_nodes.solution_model_port import (
    FixtureModelExecutionRequest, ModelInvocationRequest, fixture_model_execution)
from loop_engine.core.custom_endpoint import CustomEndpoint, make_adapter
from loop_engine.core.model_capabilities import ModelOutputCapability
from loop_engine.core.model_gateway import ModelGatewayConfig, ModelGatewayRequest
from loop_engine.loop.recursive_loop import Loop


class AccountingIntegrityChecks(unittest.TestCase):
    def endpoint(self, wire='openai'):
        return CustomEndpoint('accounting_control', 'https://fixture.invalid', 'fixture-model',
            wire=wire, stream='auto', auth_scheme='none',
            output_capability=ModelOutputCapability(64, 'offline accounting control'))

    def test_provider_zero_partial_missing_and_invalid_usage_are_distinct(self):
        for wire in ('openai', 'ollama'):
            for prompt, output in ((0, 0), (None, 3), (None, None), (True, -1), (1.5, '2')):
                with self.subTest(wire=wire, prompt=prompt, output=output):
                    if wire == 'ollama':
                        body = {'model': 'fixture-model', 'message': {'content': 'fixture'}, 'done': True,
                                'prompt_eval_count': prompt, 'eval_count': output}
                    else:
                        body = {'model': 'fixture-model', 'choices': [{'message': {'content': 'fixture'},
                                                                      'finish_reason': 'stop'}],
                                'usage': {'prompt_tokens': prompt, 'completion_tokens': output}}
                    class Transport:
                        def open(self, request, timeout):
                            return io.BytesIO(json.dumps(body).encode())
                    with patch('loop_engine.core.custom_endpoint._endpoint_opener', return_value=Transport()):
                        result = make_adapter(self.endpoint(wire)).chat('fixture', max_tokens=64)
                    self.assertTrue(result.ok)
                    self.assertEqual(result.total_tokens, 0 if (prompt, output) == (0, 0) else None)
                    if output == 3:
                        self.assertEqual(result.eval_tokens, 3)
                    if (prompt, output) == (0, 0):
                        self.assertTrue(result.usage_reported)

    def test_governed_adapter_does_not_hide_a_second_request_behind_auto_streaming(self):
        class Transport:
            calls = 0
            def open(self, request, timeout):
                self.calls += 1
                raise HTTPError(request.full_url, 504, 'fixture timeout', {}, io.BytesIO(b''))
        transport = Transport()
        with patch('loop_engine.core.custom_endpoint._endpoint_opener', return_value=transport):
            result = make_adapter(self.endpoint()).chat_maxout('fixture', max_output_tokens=64)
        self.assertEqual(transport.calls, 1)
        self.assertEqual(result.physical_requests, 1)
        self.assertFalse(result.ok)
        self.assertIsNone(result.total_tokens)

    def test_hidden_request_multiplicity_is_charged_and_refused(self):
        execution = fixture_model_execution(FixtureModelExecutionRequest(answers=('fixture answer',)))
        gateway = execution.gateway
        provider = gateway.providers['fixture'].adapter
        original = provider.chat_maxout
        def extra_request(*args, **kwargs):
            return replace(original(*args, **kwargs), physical_requests=2)
        with patch.object(provider, 'chat_maxout', side_effect=extra_request):
            result = gateway.invoke(ModelGatewayRequest('fixture', ModelGatewayConfig(
                route_names=('fixture.route',), max_route_attempts=1)))
        self.assertEqual(result.physical_model_calls, 2)
        self.assertEqual(result.error_code, 'provider_attempt_contract_violated')
        self.assertIsNone(result.total_tokens)


if __name__ == '__main__':
    unittest.main()
