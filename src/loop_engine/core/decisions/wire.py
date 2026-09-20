"""Shared System One serialization and typed admission, without network access.

Provider choice does not change output contracts. Unknown accounting remains
unknown and failed calls never return a fabricated answer. The provider owns
one explicitly bound transport; this module does not discover or retry it.
"""
from __future__ import annotations

import math
from .contracts import (DecisionBatchRequest, DecisionProtocolError, DecisionProviderResult,
    CHOICE, SCORE, BOOLEAN_PROBABILITY, admit_answers, canonical, strict_json)

NATIVE_NOUL = "noul"
MAXIMUM_CHOICES = 255
MAXIMUM_LEVELS = 10
NATIVE_QUESTION_KINDS = {CHOICE: CHOICE, SCORE: SCORE, BOOLEAN_PROBABILITY: NATIVE_NOUL}
ERROR_CODES = frozenset(("provider_http_failure", "provider_response_allowance_exceeded", "invalid_json",
    "invalid_decision_deadline", "decision_model_or_request_mismatch", "decision_provider_authority_required",
    "provider_choice_limit", "provider_score_limit", "decision_request_allowance_exceeded",
    "configured_secret_unavailable", "decision_model_identity_mismatch", "invalid_provider_usage",
    "answer_identity_mismatch", "answer_kind_mismatch", "score_legend_mismatch", "invalid_probability",
    "probability_identity_mismatch", "probabilities_do_not_sum_to_one", "invalid_selected_choice",
    "score_does_not_match_distribution", "invalid_answer_fields", "decision_provider_failed",
    "authentication_failed", "rate_limited", "payment_required", "provider_unavailable"))


def prepare_payload(request, *, model, configuration, maximum_choices, maximum_levels):
    if not isinstance(request, DecisionBatchRequest) or model != configuration.model:
        raise DecisionProtocolError("decision_model_or_request_mismatch")
    if not configuration.allow_network or not configuration.allow_model_calls:
        raise DecisionProtocolError("decision_provider_authority_required")
    questions = {}
    for item in request.questions:
        row = {"type": NATIVE_QUESTION_KINDS[item.kind], "instructions": item.instructions}
        if item.kind == CHOICE:
            if len(item.choices) > maximum_choices:
                raise DecisionProtocolError("provider_choice_limit")
            row["criteria"] = dict(item.choices)
        elif item.kind == SCORE:
            if len(item.levels) > maximum_levels:
                raise DecisionProtocolError("provider_score_limit")
            row["criteria"] = list(item.levels)
        elif item.positive or item.negative:
            row["criteria"] = {"true": item.positive, "false": item.negative}
        questions[item.question_id] = row
    payload = canonical({"model": model, "state": strict_json(request.state_json), "questions": questions}).encode()
    if len(payload) > configuration.maximum_request_bytes:
        raise DecisionProtocolError("decision_request_allowance_exceeded")
    return payload


def normalized_answers(request, body):
    values = body.get("answers")
    if not isinstance(values, dict) or set(values) != {item.question_id for item in request.questions}:
        raise DecisionProtocolError("answer_identity_mismatch")
    answers = {}
    for item in request.questions:
        raw = values[item.question_id]
        if not isinstance(raw, dict) or raw.get("type") != NATIVE_QUESTION_KINDS[item.kind]:
            raise DecisionProtocolError("answer_kind_mismatch")
        if item.kind == BOOLEAN_PROBABILITY:
            answers[item.question_id] = {"kind": item.kind, "probability": raw.get(NATIVE_NOUL)}
        else:
            if item.kind == SCORE and raw.get("legend") != {str(i): label for i, label in enumerate(item.levels)}:
                raise DecisionProtocolError("score_legend_mismatch")
            answers[item.question_id] = {"kind": item.kind, item.kind: raw.get(item.kind),
                "probabilities": raw.get("probabilities"), "confidence": raw.get("confidence")}
    return admit_answers(request, answers)


def invoke_once(adapter, request, *, model, timeout):
    opened = received = False
    input_tokens = output_tokens = None
    try:
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise DecisionProtocolError("invalid_decision_deadline")
        payload = adapter.prepare_decisions(request, model=model)
        secret = adapter.secret_resolver(adapter.configuration.credential_ref)
        if not isinstance(secret, str) or not secret or any(ch in secret for ch in "\r\n"):
            raise DecisionProtocolError("configured_secret_unavailable")
        opened = True
        body = adapter.transport(payload, secret, timeout, adapter.configuration.maximum_response_bytes)
        received = True
        if not isinstance(body, dict) or body.get("model") != model:
            raise DecisionProtocolError("decision_model_identity_mismatch")
        usage = body.get("usage", {})
        if not isinstance(usage, dict):
            raise DecisionProtocolError("invalid_provider_usage")
        for name in ("input_tokens", "output_tokens"):
            value = usage.get(name)
            if value is not None and (type(value) is not int or value < 0):
                raise DecisionProtocolError("invalid_provider_usage")
        input_tokens, output_tokens = usage.get("input_tokens"), usage.get("output_tokens")
        return DecisionProviderResult(True, model, normalized_answers(request, body), input_tokens,
                                      output_tokens, physical_requests=1, response_received=True)
    except Exception as error:
        code = str(error) if isinstance(error, DecisionProtocolError) and str(error) in ERROR_CODES else "decision_provider_failed"
        return DecisionProviderResult(False, model, prompt_tokens=input_tokens, eval_tokens=output_tokens,
            error_code=code, physical_requests=int(opened), response_received=received)
