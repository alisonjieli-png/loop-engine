"""Configured endpoint contracts over real loopback HTTP, without model weights.

The server explicitly returns provider-shaped fixtures. The checks establish
configuration and transport interchangeability, not Circuit or Jev quality.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import json

from .configuration import configured_engines, configured_gateway
from .contracts import strict_json
from .contract_checks import fixture_request, refused, report
from .jev_checks import provider_body
from .system_one import SystemOneAdapter, SystemOneConfiguration, CIRCUIT, COMPATIBLE

FIXTURE_DEPLOYMENT = "a" * 64
FIXTURE_SECRET = "LOCAL_SYSTEM_ONE_FIXTURE_SECRET"


@contextmanager
def loopback_fixture():
    state = {"model": "lora:circuit-8b", "status": 200, "calls": [], "payload": None}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            return
        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            state["calls"].append(strict_json(body))
            status = state["status"] if self.headers.get("Authorization") == "Bearer " + FIXTURE_SECRET else 401
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Location", "https://untrusted.example/v1/systemone")
            self.end_headers()
            payload = state["payload"] or {**provider_body(), "model": state["model"]}
            self.wfile.write(json.dumps(payload).encode())
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port) + "/v1/systemone", state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def endpoint_settings(endpoint, *, engine=CIRCUIT):
    return SystemOneConfiguration(engine=engine, model="lora:circuit-8b", endpoint=endpoint,
        credential_ref="env:CIRCUIT_API_KEY", locality="local", provenance="open_weights", deployment_revision=FIXTURE_DEPLOYMENT,
        allow_network=True, allow_model_calls=True, allow_loopback_http=True)


def engine_record(config, name="local-circuit"):
    settings = asdict(config)
    engine = settings.pop("engine")
    return {"name": name, "engine": engine, "settings": settings}


def run_checks():
    tests = []
    def check(name, value):
        tests.append({"test": name, "passed": bool(value)})
    with loopback_fixture() as (endpoint, state):
        config = endpoint_settings(endpoint)
        request = fixture_request()
        enabled = SystemOneAdapter(config, lambda _reference: FIXTURE_SECRET)
        disabled = replace(enabled, configuration=replace(config, allow_model_calls=False))
        meta = disabled.decision_capabilities()
        result = disabled.decide_questions(request, model=config.model, timeout=2)
        check("configured_circuit_discovery_and_disabled_calls_are_effect_free",
              meta["engine"] == CIRCUIT and not state["calls"] and result.physical_requests == 0)
        result = enabled.decide_questions(request, model=config.model, timeout=2)
        check("real_loopback_circuit_request_preserves_all_three_question_kinds",
              result.ok and result.answers["route"]["choice"] == "inspect"
              and set(state["calls"][0]) == {"model", "state", "questions"} and result.physical_requests == 1)
        check("external_endpoint_needs_no_private_server_extension_or_deployment_digest",
              replace(config, deployment_revision=None).deployment_revision is None
              and enabled.decision_capabilities()["server_lifecycle"] == "externally_managed"
              and enabled.decision_capabilities()["context_policy"] == "provider_behavior_unqualified")
        for title, mutation in (
                ("fake", {"model": "fake"}), ("model", {"model": "lora:other"}),
                ("redirect", {"status": 302}), ("authentication", {"status": 401})):
            original = {key: state[key] for key in mutation}
            state.update(mutation)
            before = len(state["calls"])
            value = enabled.decide_questions(request, model=config.model, timeout=2)
            check("configured_circuit_" + title + "_refuses_without_retry",
                  not value.ok and not value.answers and len(state["calls"]) == before + 1)
            state.update(original)
        count = len(state["calls"])
        limited = replace(enabled, configuration=replace(config, maximum_request_bytes=1))
        check("configured_endpoint_input_allowance_refuses_before_transport",
              not limited.decide_questions(request, model=config.model, timeout=2).ok and len(state["calls"]) == count)
        limited = replace(enabled, configuration=replace(config, maximum_response_bytes=1), transport=None)
        check("configured_endpoint_output_allowance_refuses", not limited.decide_questions(request, model=config.model, timeout=2).ok)
        other = SystemOneAdapter(replace(config, engine=COMPATIBLE, model="owner-specialist-1"), lambda _ref: FIXTURE_SECRET)
        state.update(model="owner-specialist-1")
        check("another_compatible_endpoint_uses_the_same_request_and_admission",
              other.decide_questions(request, model="owner-specialist-1", timeout=2).ok
              and other.decision_capabilities()["context_policy"] == "provider_behavior_unqualified")
        record = engine_record(config)
        check("named_engine_configuration_constructs_the_existing_gateway",
              "local-circuit" in configured_gateway([record]).providers)
        check("local_endpoint_configuration_preserves_route_and_provider_placement",
              configured_gateway([record]).providers["local-circuit"].locality == "local"
              and refused(lambda: replace(config, locality="cloud")))
        check("configured_model_provenance_is_explicit_not_guessed_from_its_name",
              enabled.decision_capabilities()["provenance"] == "open_weights"
              and refused(lambda: replace(config, provenance="guessed"))
              and refused(lambda: replace(config, provenance="custom_trained"))
              and replace(config, provenance="custom_trained", provenance_digest="c" * 64).provenance == "custom_trained")
        check("unknown_engines_duplicates_and_raw_secret_fields_refuse",
              refused(lambda: configured_engines([{**record, "engine": "import:anything"}]))
              and refused(lambda: configured_engines([record, record]))
              and refused(lambda: configured_engines([{**record, "settings": {**record["settings"], "api_key": "private"}}])))
        check("one_credential_reference_cannot_cross_provider_origins",
              refused(lambda: configured_engines([record, {**record, "name": "another",
                  "settings": {**record["settings"], "endpoint": "https://another.example/v1/systemone"}}])))
        check("unsafe_endpoints_fake_models_and_unknown_profiles_refuse",
              all(refused(lambda endpoint=value: replace(config, endpoint=endpoint)) for value in (
                  "http://remote.example/v1/systemone", "http://localhost/v1/systemone",
                  "https://user:password@service.example/v1/systemone", "https://service.example/v1/systemone?key=secret",
                  "https://service.example/other"))
              and refused(lambda: replace(config, model="fake"))
              and refused(lambda: replace(config, record_type="system_one_configuration/v0")))
    return report(tests)
