"""Pinned Qwen and Gemini recipes for the existing isolated harness adapter.

Owns: process-local configuration and a bounded text-only Google wire codec.
Does not own: model authority, effect approval, execution, or task acceptance.
The canonical Loop owns all work; these functions add no runtime or registry.
The parent broker must validate the converted request before any model call.
Checks live in ``harness_additional_recipe_checks.self_test``.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from urllib.parse import unquote, urlsplit


class AdditionalRecipeError(ValueError):
    """An unsupported recipe or wire value, refused before model dispatch."""


# Exact ToolNames values in @qwen-code/qwen-code 0.23.1. The package and its
# dependency tree are separately pinned by HarnessProcessSpec. No wildcard or
# empty-list behavior is assumed here; the installed wire probe asserts zero.
QWEN_DISABLED_TOOLS = (
    "edit", "write_file", "read_file", "zoom_image", "grep_search", "glob",
    "run_shell_command", "todo_write", "save_memory", "agent", "skill",
    "exit_plan_mode", "enter_plan_mode", "web_fetch", "web_search", "image_gen",
    "list_directory", "lsp", "ask_user_question", "cron_create", "cron_list",
    "cron_delete", "loop_wakeup", "create_sub_session", "list_agents", "task_stop",
    "task_create", "task_update", "task_list", "team_create", "team_delete",
    "team_plan_approval", "request_shutdown", "send_message", "structured_output",
    "monitor", "notebook_edit", "tool_search", "read_mcp_resource", "enter_worktree",
    "exit_worktree", "workflow", "artifact", "record_artifact", "report_findings",
    "get_goal", "update_goal", "propose_goal", "display_image",
)


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, allow_nan=False), encoding="utf-8")


def prepare_recipe(style, config, base_url):
    """Return (argv, environment overrides, private prompt stdin bytes).

    ``config`` is constructed by the owning process adapter, never by model
    output. ``workspace_path`` and ``task_path`` allow the existing isolated
    fixture driver to mount its private files without a second execution rig.
    """
    if style not in ("qwen_code", "gemini_cli"):
        raise AdditionalRecipeError("unsupported_additional_harness_style")
    base = urlsplit(base_url)
    if (base.scheme != "http" or base.hostname != "127.0.0.1" or not base.port
            or base.username or base.password or base.query or base.fragment):
        raise AdditionalRecipeError("isolated_loopback_relay_required")
    prefix = tuple(config["command_prefix"])
    model = config["model"]
    if not prefix or any(not isinstance(v, str) or not v for v in prefix):
        raise AdditionalRecipeError("exact_command_required")
    if (not isinstance(model, str) or not model or model.startswith("-")
            or any(c in model for c in "?#\r\n\x00")):
        raise AdditionalRecipeError("exact_model_required")
    workspace = Path(config.get("workspace_path", "/work"))
    task = Path(config.get("task_path", "/relay/task.txt"))
    if not workspace.is_absolute() or not task.is_absolute():
        raise AdditionalRecipeError("absolute_private_paths_required")
    prompt = task.read_bytes()
    if not prompt or len(prompt) > config.get("maximum_request_bytes", 4_000_000):
        raise AdditionalRecipeError("private_prompt_size_refused")
    if style == "qwen_code":
        argv = prefix + (
            "--bare", "--auth-type", "openai", "--openai-base-url", base_url,
            "--model", model, "--exclude-tools", *QWEN_DISABLED_TOOLS,
            "--max-tool-calls", "0", "--max-session-turns", "1",
            "--output-format", "json", "--prompt", "Follow the supplied task.",
        )
        environment = {"OPENAI_API_KEY": "loop-engine-local-relay",
                       "OPENAI_BASE_URL": base_url, "OPENAI_MODEL": model,
                       "QWEN_CODE_DISABLE_AUTO_UPDATE": "1"}
        return argv, environment, prompt
    if style == "gemini_cli":
        settings = {
            "security": {"auth": {"selectedType": "gemini-api-key"}},
            "tools": {"core": []},
            "telemetry": {"enabled": False},
            "general": {"disableAutoUpdate": True},
            "ide": {"enabled": False}, "skills": {"enabled": False},
            "hooksConfig": {"enabled": False},
            "experimental": {"autoMemory": False},
            "modelConfigs": {"customAliases": {model: {"modelConfig": {
                "model": model, "generateContentConfig": {
                    "maxOutputTokens": config["output_allowance"]}}}}},
            "admin": {"extensions": {"enabled": False}, "mcp": {"enabled": False},
                      "skills": {"enabled": False}},
        }
        _write_json(workspace / "home/.gemini/settings.json", settings)
        policy = workspace / "deny-native-tools.toml"
        policy.write_text('[[rule]]\ntoolName = "*"\ndecision = "deny"\npriority = 999\n',
                          encoding="utf-8")
        argv = prefix + ("--skip-trust", "--model", model, "--output-format", "json",
                         "--policy", str(policy), "--prompt", "Follow the supplied task.")
        environment = {"GEMINI_API_KEY": "loop-engine-local-relay",
                       "GOOGLE_GEMINI_BASE_URL": f"http://127.0.0.1:{base.port}",
                       "GEMINI_TELEMETRY_ENABLED": "false", "NO_BROWSER": "1"}
        return argv, environment, prompt
    raise AdditionalRecipeError("unsupported_additional_harness_style")


def _text_parts(value):
    if not isinstance(value, list):
        raise AdditionalRecipeError("google_text_parts_required")
    output = []
    for part in value:
        if not isinstance(part, dict) or set(part) != {"text"} or not isinstance(part["text"], str):
            raise AdditionalRecipeError("google_nontext_or_tool_part_refused")
        output.append(part["text"])
    return "".join(output)


def decode_google_request(path, body, exact_model):
    """Convert one exact text GenerateContent request; reject tools and drift."""
    parsed = urlsplit(path)
    allowed = {f"/v1beta/models/{exact_model}:generateContent": False,
               f"/v1beta/models/{exact_model}:streamGenerateContent": True,
               f"/v1/models/{exact_model}:generateContent": False,
               f"/v1/models/{exact_model}:streamGenerateContent": True}
    route = unquote(parsed.path)
    if parsed.scheme or parsed.netloc or route not in allowed or parsed.query not in ("", "alt=sse"):
        raise AdditionalRecipeError("google_exact_route_refused")
    if not isinstance(body, dict):
        raise AdditionalRecipeError("google_request_object_required")
    tools = body.get("tools", [])
    empty_declarations = (isinstance(tools, list) and all(
        isinstance(item, dict) and item == {"functionDeclarations": []} for item in tools))
    if not empty_declarations or body.get("toolConfig"):
        raise AdditionalRecipeError("native_tools_not_authorized")
    if set(body) - {"contents", "systemInstruction", "generationConfig", "tools", "toolConfig"}:
        raise AdditionalRecipeError("google_request_fields_refused")
    messages = []
    system = body.get("systemInstruction")
    if system is not None:
        if not isinstance(system, dict) or set(system) - {"parts", "role"}:
            raise AdditionalRecipeError("google_system_instruction_refused")
        messages.append({"role": "system", "content": _text_parts(system.get("parts"))})
    contents = body.get("contents")
    if not isinstance(contents, list) or not contents:
        raise AdditionalRecipeError("google_contents_required")
    for item in contents:
        if not isinstance(item, dict) or set(item) - {"parts", "role"}:
            raise AdditionalRecipeError("google_content_fields_refused")
        role = item.get("role", "user")
        if role not in ("user", "model"):
            raise AdditionalRecipeError("google_content_role_refused")
        messages.append({"role": "assistant" if role == "model" else "user",
                         "content": _text_parts(item.get("parts"))})
    result = {"model": exact_model, "messages": messages, "stream": allowed[route]}
    generation = body.get("generationConfig", {})
    if not isinstance(generation, dict):
        raise AdditionalRecipeError("google_generation_object_required")
    mapping = {"temperature": "temperature", "topP": "top_p",
               "maxOutputTokens": "max_tokens", "stopSequences": "stop"}
    if set(generation) - set(mapping) - {"candidateCount", "responseMimeType"}:
        raise AdditionalRecipeError("google_generation_fields_refused")
    if type(generation.get("candidateCount", 1)) is not int or generation.get("candidateCount", 1) != 1:
        raise AdditionalRecipeError("google_multiple_candidates_refused")
    for key in ("temperature", "topP"):
        if key in generation:
            number = generation[key]
            if (type(number) not in (float, int) or not math.isfinite(number)
                    or number < 0 or number > (1 if key == "topP" else 2)):
                raise AdditionalRecipeError("google_sampling_value_refused")
    if "maxOutputTokens" in generation:
        maximum = generation["maxOutputTokens"]
        if type(maximum) is not int or maximum <= 0:
            raise AdditionalRecipeError("google_output_allocation_refused")
    if "stopSequences" in generation:
        stops = generation["stopSequences"]
        if not isinstance(stops, list) or not all(isinstance(v, str) and v for v in stops):
            raise AdditionalRecipeError("google_stop_sequences_refused")
    for source, target in mapping.items():
        if source in generation:
            result[target] = generation[source]
    mime = generation.get("responseMimeType", "text/plain")
    if mime not in ("text/plain", "application/json"):
        raise AdditionalRecipeError("google_response_mime_refused")
    if mime == "application/json":
        result["response_format"] = {"type": "json_object"}
    return result


def encode_google_response(response, exact_model):
    """Encode one text-only broker response, preserving missing usage fields."""
    if not isinstance(response, dict) or response.get("model") != exact_model:
        raise AdditionalRecipeError("google_response_model_refused")
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise AdditionalRecipeError("google_one_response_choice_required")
    message = choices[0].get("message", {})
    if message.get("tool_calls") or message.get("function_call"):
        raise AdditionalRecipeError("native_tools_not_authorized")
    if message.get("role") != "assistant" or not isinstance(message.get("content"), str):
        raise AdditionalRecipeError("google_text_response_required")
    finish = {"stop": "STOP", "length": "MAX_TOKENS", "content_filter": "SAFETY"}
    if choices[0].get("finish_reason") not in finish:
        raise AdditionalRecipeError("google_finish_reason_refused")
    result = {"candidates": [{"index": 0,
               "content": {"role": "model", "parts": [{"text": message["content"]}]},
               "finishReason": finish[choices[0]["finish_reason"]]}], "modelVersion": exact_model}
    usage = response.get("usage")
    if usage is not None:
        if not isinstance(usage, dict):
            raise AdditionalRecipeError("google_usage_object_required")
        keys = {"prompt_tokens": "promptTokenCount", "completion_tokens": "candidatesTokenCount",
                "total_tokens": "totalTokenCount"}
        values = {}
        for source, target in keys.items():
            if source in usage and usage[source] is not None:
                value = usage[source]
                if type(value) is not int or value < 0:
                    raise AdditionalRecipeError("google_usage_value_refused")
                values[target] = value
        if values:
            result["usageMetadata"] = values
    return result


def extract_additional_output(style, stdout, expected):
    """Accept only a successful CLI response matching the broker's exact text."""
    if style not in ("qwen_code", "gemini_cli") or not isinstance(expected, str) or not expected:
        return ""
    try:
        value = json.loads(stdout)
    except (ValueError, TypeError, RecursionError):
        return ""
    if style == "qwen_code":
        if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
            return ""
        results = [row for row in value if row.get("type") == "result"]
        if len(results) != 1:
            return ""
        terminal = results[0]
        if (terminal.get("subtype") != "success" or terminal.get("is_error") is not False
                or terminal.get("permission_denials") or terminal.get("result") != expected):
            return ""
        return expected
    if not isinstance(value, dict) or value.get("error"):
        return ""
    return expected if value.get("response") == expected else ""
