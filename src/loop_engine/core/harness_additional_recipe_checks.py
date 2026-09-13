"""Offline checks for additional harness recipes and the bounded Google codec.

Owns: positive and adversarial text-protocol checks without installed CLIs.
Does not own: provider integration, model quality, or operating-system isolation.
Actual installed-process probes remain separately recorded qualification work.
"""
from __future__ import annotations

from .harness_additional_recipes import (
    AdditionalRecipeError, QWEN_DISABLED_TOOLS, decode_google_request,
    encode_google_response, extract_additional_output,
)


def self_test():
    tests = []
    def check(name, value):
        tests.append({"test": name, "passed": bool(value)})
    def refuses(name, call):
        try:
            call()
        except AdditionalRecipeError:
            check(name, True)
        else:
            check(name, False)

    model = "fixture-model"
    path = "/v1beta/models/fixture-model:streamGenerateContent?alt=sse"
    body = {"systemInstruction": {"parts": [{"text": "system"}]},
            "contents": [{"role": "user", "parts": [{"text": "task"}]}],
            "generationConfig": {"maxOutputTokens": 71, "temperature": 0.3}}
    value = decode_google_request(path, body, model)
    check("google_text_mapping_preserves_role_body_and_allocation",
          value["messages"] == [{"role": "system", "content": "system"},
                                {"role": "user", "content": "task"}]
          and value["max_tokens"] == 71 and value["stream"] is True)
    refuses("google_foreign_model_path_refused", lambda:
            decode_google_request(path.replace("fixture-model", "other-model"), body, model))
    refuses("google_absolute_foreign_authority_refused", lambda:
            decode_google_request("https://foreign.invalid" + path, body, model))
    refuses("google_native_tool_schema_refused", lambda:
            decode_google_request(path, {**body, "tools": [{"functionDeclarations": [{"name": "write"}]}]}, model))
    check("google_empty_declaration_envelope_is_not_a_tool", "tools" not in
          decode_google_request(path, {**body, "tools": [{"functionDeclarations": []}]}, model))
    refuses("google_unknown_request_field_refused", lambda:
            decode_google_request(path, {**body, "cachedContent": "other-run"}, model))
    refuses("google_native_tool_part_refused", lambda:
            decode_google_request(path, {"contents": [{"parts": [{"functionCall": {"name": "write"}}]}]}, model))
    refuses("google_image_part_refused", lambda:
            decode_google_request(path, {"contents": [{"parts": [{"inlineData": {}}]}]}, model))
    refuses("google_generation_semantics_not_silently_dropped", lambda:
            decode_google_request(path, {**body, "generationConfig": {"thinkingConfig": {"thinkingBudget": 123}}}, model))
    refuses("google_boolean_output_allowance_refused", lambda:
            decode_google_request(path, {**body, "generationConfig": {"maxOutputTokens": True}}, model))
    refuses("google_nonfinite_sampling_refused", lambda:
            decode_google_request(path, {**body, "generationConfig": {"topP": float("nan")}}, model))
    response = {"model": model, "choices": [{"message": {"role": "assistant", "content": "answer"},
                                              "finish_reason": "stop"}]}
    encoded = encode_google_response(response, model)
    check("google_missing_usage_stays_missing", "usageMetadata" not in encoded)
    check("google_text_response_preserved", encoded["candidates"][0]["content"]["parts"] == [{"text": "answer"}])
    encoded = encode_google_response({**response, "usage": {"prompt_tokens": 0, "completion_tokens": None}}, model)
    check("google_real_zero_and_unknown_usage_distinct", encoded["usageMetadata"] == {"promptTokenCount": 0})
    refuses("google_response_model_drift_refused", lambda:
            encode_google_response({**response, "model": "other"}, model))
    refuses("google_negative_usage_refused", lambda:
            encode_google_response({**response, "usage": {"prompt_tokens": -1}}, model))
    refuses("google_model_proposed_tools_refused", lambda:
            encode_google_response({**response, "choices": [{"message": {"role": "assistant", "content": "",
                "tool_calls": [{"function": {"name": "write"}}]}, "finish_reason": "tool_calls"}]}, model))
    check("qwen_names_include_deferred_and_system_tools", len(QWEN_DISABLED_TOOLS) == len(set(QWEN_DISABLED_TOOLS))
          and {"tool_search", "structured_output", "get_goal", "agent", "write_file"} <= set(QWEN_DISABLED_TOOLS))
    check("cli_output_requires_exact_broker_text", extract_additional_output("gemini_cli", '{"response":"answer"}', "answer") == "answer"
          and not extract_additional_output("gemini_cli", '{"response":"other"}', "answer"))
    check("cli_error_cannot_become_output", not extract_additional_output("qwen_code", '{"response":"answer","error":"failed"}', "answer"))
    check("qwen_actual_event_array_success_is_required", extract_additional_output("qwen_code",
          '[{"type":"result","subtype":"success","is_error":false,"result":"answer"}]', "answer") == "answer"
          and not extract_additional_output("qwen_code",
          '[{"type":"result","subtype":"error_max_turns","is_error":true,"result":"answer"}]', "answer"))
    return {"passed": sum(t["passed"] for t in tests), "total": len(tests), "tests": tests}
