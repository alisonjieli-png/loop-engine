"""Structured decision execution owned by ModelGateway, not a second gateway.

The owning Loop supplies exact routes and existing authority. Every provider
attempt has a model Loop and safe accounting. This helper admits typed output;
the caller still owns semantic evaluation and independent task acceptance.
"""
from __future__ import annotations

import time
import uuid

from .contracts import (
    DecisionBatchRequest, DecisionProtocolError, DecisionProviderResult,
    PROVIDER_CAPABILITY, RESULT_VERSION, admit_answers, canonical,
)
from ..model_gateway import GatewayAttempt, ModelGatewayConfig, ModelGatewayResult
from ..typed_decision import validate_typed_decision_route
from ..response_contracts import TYPED_DECISION_BATCH


def invoke_decisions(gateway, request, *, config, parent=None, ledger=None):
    from ...loop.encapsulate import as_model_loop
    from ..model_call_contract import ModelCallRequest, ModelInput, ModelCallObservation, record_model_call
    from ..operation_cost_capture import OperationCostCapture
    if not isinstance(request, DecisionBatchRequest) or not isinstance(config, ModelGatewayConfig):
        raise DecisionProtocolError("typed_decision_request_and_configuration_required")
    from ...loop.recursive_loop import Loop
    if not isinstance(parent, Loop):
        raise DecisionProtocolError("owning_loop_required")
    result = ModelGatewayResult(semantic_call_id=request.semantic_call_id or "decision:" + uuid.uuid4().hex,
        owner_loop_id=getattr(parent, "loop_id", ""), request_digest=request.content_digest,
        prompt_digest=request.content_digest)
    # Jev's structured protocol has no generation-allocation field. Do not
    # invent an output capacity or silently ignore a caller's hard token bound.
    if (config.max_total_tokens is not None or config.max_output_tokens is not None
            or config.output_allocation is not None or any(row.max_output_tokens is not None for row in config.route_plan)):
        result.error_code = "typed_decision_token_bound_unavailable"
        return result
    if config.purpose != "decide_label" or not (config.route_names or config.route_plan):
        result.error_code = "explicit_decision_route_required"
        return result
    routes = gateway._routes(config)
    if not routes:
        result.error_code = "no_eligible_route"
        return result
    capture = (OperationCostCapture(gateway.cost_ledger, "model_call.typed_decisions", "model_gateway",
                                   gateway.run_id or "unknown-run") if gateway.cost_ledger is not None else None)
    if capture is not None:
        capture.phase("execution")
    deadline = time.monotonic() + config.timeout_seconds
    try:
        for route, attempt_spec in routes:
            spec = gateway.providers.get(route.provider)
            code = ""
            try:
                validate_typed_decision_route(route)
                if spec is None or PROVIDER_CAPABILITY not in spec.capabilities:
                    raise DecisionProtocolError("decision_provider_not_configured")
                handshake = spec.adapter.decision_capabilities()
                if (handshake.get("protocol") != PROVIDER_CAPABILITY
                        or any(item.kind not in handshake.get("kinds", ()) for item in request.questions)):
                    raise DecisionProtocolError("decision_provider_incompatible")
                spec.adapter.prepare_decisions(request, model=route.model)
            except Exception:
                code = "decision_provider_preflight_refused"
            if code:
                result.attempts.append(GatewayAttempt(route.provider, route.model, route.name, "", False, error_code=code))
                continue
            timeout = min(deadline - time.monotonic(), attempt_spec.timeout_seconds or config.timeout_seconds)
            if timeout <= 0:
                result.error_code = "decision_deadline_exhausted"
                break
            started = time.monotonic()
            def invoke(spec=spec, route=route, timeout=timeout):
                try:
                    value = spec.adapter.decide_questions(request, model=route.model, timeout=timeout)
                    if not isinstance(value, DecisionProviderResult):
                        raise DecisionProtocolError("typed_provider_result_required")
                    return value
                except Exception:
                    # The adapter may have crossed the network before raising.
                    return DecisionProviderResult(False, route.model, error_code="decision_provider_failed", physical_requests=1)
            call = as_model_loop(route.provider + ":" + route.model, invoke, parent=parent, ledger=ledger,
                semantic_call_id=result.semantic_call_id, owner_loop_id=result.owner_loop_id,
                llm_thinking_power=attempt_spec.thinking_power)
            observed = call["value"]
            result.owner_loop_id = result.owner_loop_id or call["owner_loop_id"]
            result.gateway_loop_id = result.gateway_loop_id or call["loop_id"]
            admitted = None
            try:
                if not observed.ok or observed.model != route.model:
                    raise DecisionProtocolError("decision_provider_failed")
                admitted = admit_answers(request, observed.answers)
            except DecisionProtocolError:
                code = (observed.error_code if observed.error_code in (
                    "authentication_failed", "rate_limited", "payment_required", "provider_unavailable")
                    else "decision_provider_failed" if not observed.ok else "decision_response_refused")
            elapsed = time.monotonic() - started
            if time.monotonic() > deadline:
                code = "decision_deadline_exhausted"
                admitted = None
            attempt = GatewayAttempt(route.provider, observed.model, route.name, call["loop_id"], admitted is not None,
                input_tokens=observed.prompt_tokens, output_tokens=observed.eval_tokens,
                validation_ok=admitted is not None, error_code=code, elapsed_seconds=elapsed,
                provider_ok=observed.ok, expected_model=route.model, response_received=observed.response_received,
                provider_physical_requests=observed.physical_requests, reported_provider_attempts=observed.physical_requests,
                semantic_call_id=result.semantic_call_id, owner_loop_id=result.owner_loop_id,
                prompt_digest=request.content_digest, logical_request_digest=request.content_digest)
            result.attempts.append(attempt)
            record_request = ModelCallRequest("decide_label", "judgment",
                (ModelInput("text", canonical(request.to_dict()), label="decision_batch"),),
                response_contract_id=TYPED_DECISION_BATCH, route_name=route.name, semantic_call_id=result.semantic_call_id)
            record = record_model_call(record_request, call["loop_id"], ModelCallObservation(
                route=route.name, provider=route.provider, model=observed.model,
                input_tokens=observed.prompt_tokens, output_tokens=observed.eval_tokens,
                latency_ms=int(elapsed * 1000), admitted=admitted is not None,
                output_text=canonical(admitted) if admitted is not None else "", outcome_label="decided" if admitted is not None else "refused"))
            active_ledger = parent.ledger if parent is not None else ledger
            if active_ledger is not None:
                active_ledger.record(loop_id=call["loop_id"], event="custom", action="typed_decision_observed", record=record.to_dict())
            if admitted is not None:
                result.ok = True
                result.provider, result.model, result.route = route.provider, observed.model, route.name
                result.text = canonical({"record_type": RESULT_VERSION, "answers": admitted,
                    "model": observed.model, "provider": route.provider, "route": route.name,
                    "request_digest": request.content_digest, "task_accepted": False})
                break
            if code == "authentication_failed":
                break
        physical = result.physical_provider_attempts
        if physical:
            result.input_tokens = (sum(item.input_tokens for item in physical)
                                   if all(item.input_tokens is not None for item in physical) else None)
            result.output_tokens = (sum(item.output_tokens for item in physical)
                                    if all(item.output_tokens is not None for item in physical) else None)
        if not result.ok and not result.error_code:
            result.error_code = result.attempts[-1].error_code if result.attempts else "no_eligible_route"
        if capture is not None:
            capture.end("unknown" if result.ok else "failed", model_calls=result.physical_model_calls,
                        input_tokens=result.input_tokens, output_tokens=result.output_tokens)
        return result
    except BaseException:
        if capture is not None:
            capture.end("failed")
        raise
