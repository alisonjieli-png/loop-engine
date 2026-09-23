"""Missing provider identity never becomes the requested model; no live calls."""
import io
import json
import unittest
import urllib.error
from types import SimpleNamespace
from unittest.mock import patch

from loop_engine.core import ollama_client
from loop_engine.core.model_capabilities import ModelOutputCapability
from loop_engine.core.model_gateway import (
    ModelGateway,
    ModelGatewayConfig,
    ModelGatewayRequest,
    ProviderSpec,
)
from loop_engine.core.model_routes import ModelRoute

MODEL = "glm-5.3"
CAPACITY = ModelOutputCapability(4096, "explicit test fixture")


class Response:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return json.dumps(self.data).encode()


class Adapter:
    DEFAULT_MODEL = MODEL

    def __init__(self, model):
        self.model = model

    def output_capability_for(self, _model):
        return CAPACITY

    def verify(self, model=""):
        return True

    def live_models(self):
        return [MODEL]

    def chat_maxout(self, *_args, **_kwargs):
        values = {"text": "answer", "ok": True, "prompt_tokens": 11, "eval_tokens": 7,
                  "response_received": True, "done": True, "attempts": 1, "physical_requests": 1}
        if self.model != "missing":
            values["model"] = self.model
        return SimpleNamespace(**values)


class ProviderIdentityTest(unittest.TestCase):
    def test_malformed_unanswered_and_preflight_results_do_not_claim_requested_identity(self):
        class RawResponse(Response):
            def read(self):
                return self.data
        for raw in (b'not-json',b'[]',b'null'):
            with self.subTest(raw=raw), patch.object(ollama_client.urllib.request,'urlopen',return_value=RawResponse(raw)):
                result=ollama_client.chat('fixture',model=MODEL,api_key='fixture-only',output_capability=CAPACITY)
            self.assertFalse(result.ok)
            self.assertEqual(result.model,'')
        for kwargs in ({'api_key':''},{'api_key':'fixture-only','num_predict':0}):
            with self.subTest(kwargs=kwargs),patch.object(ollama_client.urllib.request,'urlopen',side_effect=AssertionError('no network')):
                result=ollama_client.chat('fixture',model=MODEL,output_capability=CAPACITY,**kwargs)
            self.assertEqual(result.model,'')
            self.assertEqual(result.physical_requests,0)
        result=ollama_client.chat_maxout('fixture',model=MODEL,max_attempts=2)
        self.assertEqual(result.model,'')
        self.assertEqual(result.physical_requests,0)

    def test_transport_errors_preserve_unknown_answering_identity(self):
        errors=(OSError('fixture'),urllib.error.HTTPError(ollama_client.ENDPOINT,503,'fixture',{},io.BytesIO(b'fixture')))
        for error in errors:
            with self.subTest(error=type(error).__name__),patch.object(ollama_client.urllib.request,'urlopen',side_effect=error):
                result=ollama_client.chat('fixture',model=MODEL,api_key='fixture-only',output_capability=CAPACITY)
            self.assertFalse(result.ok)
            self.assertEqual(result.model,'')

    def test_gateway_adapter_exception_never_fabricates_reported_identity(self):
        gateway=ModelGateway(providers=(ProviderSpec('fixture',Adapter(MODEL),'fixture','env:FIXTURE'),),
                             routes=(ModelRoute('fixture.route','fixture',MODEL),))
        with patch.object(Adapter,'chat_maxout',side_effect=RuntimeError('untrusted fixture detail')):
            result=gateway.invoke(ModelGatewayRequest('fixture',ModelGatewayConfig(
                route_names=('fixture.route',),allow_failover=False,max_route_attempts=1)))
        self.assertFalse(result.ok)
        self.assertEqual(result.attempts[-1].model,'')
        self.assertEqual(result.attempts[-1].expected_model,MODEL)
        self.assertIsNone(result.input_tokens)
        self.assertNotIn('untrusted fixture detail',result.error)

    def test_error_body_preserves_reported_usage_and_unknown_model(self):
        data = {"error": "fixture unavailable", "prompt_eval_count": 11, "eval_count": 7}
        with patch.object(ollama_client.urllib.request, "urlopen", return_value=Response(data)):
            result = ollama_client.chat("fixture", model=MODEL, api_key="fixture-only", output_capability=CAPACITY)
        self.assertFalse(result.ok)
        self.assertEqual(result.model, "")
        self.assertEqual((result.prompt_tokens, result.eval_tokens), (11, 7))
        self.assertTrue(result.usage_reported)

    def test_ollama_missing_null_empty_and_wrong_model_refuse_with_usage(self):
        for model in ("missing", None, "", "another-model"):
            with self.subTest(model=model):
                data = {"message": {"content": "answer"}, "done": True,
                        "prompt_eval_count": 11, "eval_count": 7}
                if model != "missing":
                    data["model"] = model
                with patch.object(ollama_client.urllib.request, "urlopen", return_value=Response(data)):
                    result = ollama_client.chat("fixture", model=MODEL, api_key="fixture-only",
                                                output_capability=CAPACITY)
                self.assertFalse(result.ok)
                self.assertIn("model_identity_mismatch", result.error)
                self.assertEqual(result.model, "another-model" if model == "another-model" else "")
                self.assertEqual((result.prompt_tokens, result.eval_tokens), (11, 7))

    def test_gateway_never_fills_missing_null_or_empty_identity(self):
        for model in ("missing", None, "", "another-model", MODEL):
            with self.subTest(model=model):
                gateway = ModelGateway(providers=(ProviderSpec("fixture", Adapter(model), "fixture", "env:FIXTURE"),),
                                       routes=(ModelRoute("fixture.route", "fixture", MODEL),))
                result = gateway.invoke(ModelGatewayRequest("fixture", ModelGatewayConfig(
                    route_names=("fixture.route",), allow_failover=False, max_route_attempts=1)))
                self.assertEqual(result.ok, model == MODEL)
                if model != MODEL:
                    self.assertEqual(result.error_code, "model_identity_mismatch")
                self.assertEqual((result.input_tokens, result.output_tokens), (11, 7))
                self.assertEqual(result.attempts[-1].expected_model, MODEL)
                self.assertEqual(result.attempts[-1].model, "" if model in ("missing", None, "") else model)

    def test_ollama_matching_reported_identity_succeeds(self):
        data = {"model": MODEL, "message": {"content": "answer"}, "done": True,
                "prompt_eval_count": 11, "eval_count": 7}
        with patch.object(ollama_client.urllib.request, "urlopen", return_value=Response(data)):
            result = ollama_client.chat("fixture", model=MODEL, api_key="fixture-only", output_capability=CAPACITY)
        self.assertTrue(result.ok)
        self.assertEqual(result.model, MODEL)


if __name__ == "__main__":
    unittest.main()
