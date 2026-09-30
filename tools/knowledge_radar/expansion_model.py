"""One text-only production turn through the existing model gateway.

The caller reserves each dispatch durably. Calls have one exact route, no
failover, bounded prompt bytes and a model-bound output allocation. A daily
reported-token stop is not misrepresented as an exact preflight token bound.
"""
from __future__ import annotations

import json

from loop_engine.core.model_capabilities import ModelOutputAllocation
from loop_engine.core.model_gateway import ModelGateway, ModelGatewayConfig, ModelGatewayRequest, builtin_provider_specs
from loop_engine.core.model_routes import ModelRoute, screen_route
from tools.generate_original_native_candidates import require_provider_credential, secret_present, strict_json

from .expansion_contracts import INSTRUCTIONS, SCHEMAS, validate


class ExpansionTurn:
    """A replaceable gateway adapter; it owns no catalogue or approval state."""
    def __init__(self, policy, repository):
        self.policy = policy
        panel = json.loads((repository / "tools/candidate_review/resources/panel.json").read_text())
        families = {row["family"] for row in panel["installations"]
                    if row["engine_kind"] == "model_gateway" and row["model"] == policy["model"]
                    and row["settings"].get("provider_id") == "ollama_cloud" and row["enabled"]}
        if families != {policy["producer_family"]}:
            raise ValueError("expansion_model_family_not_registered")
        self.spec = next(row for row in builtin_provider_specs() if row.provider_id == "ollama_cloud")
        require_provider_credential(self.spec)
        self.route = screen_route(ModelRoute("community.expansion", self.spec.provider_id, policy["model"],
                                             self.spec.locality, purposes=("generation",)), purpose="generation")
        self.gateway = ModelGateway(providers=(self.spec,), routes=(self.route,))

    def __call__(self, stage, payload):
        system = INSTRUCTIONS[stage] + "\nReturn one JSON object matching this schema:\n" + json.dumps(SCHEMAS[stage])
        prompt = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if len((system + prompt).encode()) > self.policy["maximum_prompt_bytes"]:
            return {"status": "failed", "reason": "prompt_limit", "physical_model_calls": 0, "reported_tokens": 0}
        if secret_present(prompt):
            return {"status": "failed", "reason": "secret_pattern_in_input", "physical_model_calls": 0, "reported_tokens": 0}
        allocation = ModelOutputAllocation(self.spec.output_capability_for(self.policy["model"]),
            self.spec.provider_id, self.policy["model"], self.route.name, self.policy["output_allocation_tokens"],
            "community_expansion_policy/v1#output_allocation_tokens", "Bounded internal candidate production turn.")
        request = ModelGatewayRequest(prompt, ModelGatewayConfig(purpose="generation", route_names=(self.route.name,),
            allowed_models=(self.policy["model"],), allow_failover=False, max_route_attempts=1,
            output_allocation=allocation, timeout_seconds=self.policy["timeout_seconds"]),
            system=system, temperature=0.0, output_contract="community_expansion_" + stage + "/v1")
        result = self.gateway.invoke(request)
        complete = all(type(value) is int and value >= 0 for value in (result.input_tokens, result.output_tokens))
        record = {"status": "failed", "reason": result.error_code or "answer_invalid",
                  "model": result.model, "provider": result.provider, "request_digest": request.request_digest,
                  "physical_model_calls": result.physical_model_calls,
                  "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
                  "reported_tokens": result.input_tokens + result.output_tokens if complete else None}
        if result.ok and result.physical_model_calls == 1 and result.model == self.policy["model"]:
            try:
                if len(result.text.encode()) > 48000 or secret_present(result.text):
                    raise ValueError("unsafe_or_oversized_answer")
                # No heuristic repair: an invalid answer remains a failed attempt.
                answer = validate(stage, strict_json(result.text))
                record.update(status="complete", reason="", answer=answer)
            except Exception as error:  # noqa: BLE001 - sanitized outcome, never raw provider text
                record["reason"] = type(error).__name__
        return record
