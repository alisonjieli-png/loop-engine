"""Private Responses text adapters for pinned Codex-family CLI processes.

Configuration, codecs, and output records are internal mechanics owned by a
Loop. These functions do not call models or grant native tool authority.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from urllib.parse import urlsplit


class ResponsesRecipeError(ValueError):
    """The requested process exceeds the qualified text-only protocol."""


DISABLED_FEATURES = (
    "shell_tool", "unified_exec", "shell_snapshot", "view_image", "sleep_tool",
    "deferred_executor", "js_repl", "code_mode", "code_mode_host", "code_mode_only",
    "js_repl_tools_only", "standalone_web_search",
    "search_tool", "memories", "apply_patch_freeform", "hooks", "request_permissions_tool",
    "remote_models", "enable_request_compression", "unbounded_connection_retries", "multi_agent",
    "multi_agent_v2", "multi_agent_mode", "enable_fanout", "apps", "enable_mcp_apps",
    "tool_search", "tool_suggest", "recommended_plugins", "plugins", "plugin_hooks",
    "browser_use", "computer_use", "image_generation", "skill_mcp_dependency_install",
    "skill_search", "skill_env_var_dependency_prompt", "send_async_message", "goals",
    "token_budget", "current_time_reminder", "collaboration_modes", "artifact",
    "realtime_conversation", "remote_control", "responses_websockets", "responses_websockets_v2",
)


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)


def prepare_responses_recipe(style, config, base_url):
    """Create a private provider and exact text model catalog; no native tools."""
    if style not in ("codex", "openinterpreter_rust"):
        raise ResponsesRecipeError("unsupported_responses_harness")
    parsed = urlsplit(base_url)
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or not parsed.port
            or parsed.path != "/v1" or parsed.query or parsed.fragment or parsed.username or parsed.password):
        raise ResponsesRecipeError("private_loopback_provider_required")
    prefix = tuple(config.get("command_prefix", ()))
    if not prefix or any(not isinstance(value, str) or not value or "\x00" in value for value in prefix):
        raise ResponsesRecipeError("exact_command_required")
    model = config.get("model")
    if not isinstance(model, str) or not model or any(value in model for value in "\x00\r\n"):
        raise ResponsesRecipeError("exact_model_required")
    context = config.get("context_capacity")
    allocation = config.get("output_allowance")
    timeout = config.get("timeout_seconds")
    if type(context) is not int or context <= 0 or type(allocation) is not int or allocation <= 0:
        raise ResponsesRecipeError("typed_capacities_required")
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
        raise ResponsesRecipeError("typed_deadline_required")
    workspace = Path(config.get("workspace_path", "/work"))
    task = Path(config.get("task_path", "/relay/task.txt"))
    if any(not path.is_absolute() or ".." in path.parts for path in (workspace, task)):
        raise ResponsesRecipeError("absolute_private_paths_required")
    prompt = task.read_bytes()
    if not prompt or len(prompt) > config.get("maximum_request_bytes", 2 * 1024 * 1024):
        raise ResponsesRecipeError("private_prompt_size_refused")
    home = workspace / "home" / (".codex" if style == "codex" else ".openinterpreter")
    home.mkdir(parents=True, exist_ok=True)
    instructions = home / "text-instructions.txt"
    _write(instructions, "Follow the supplied task and its output contract. Return a complete text candidate. "
           "Native tools are unavailable. The owning Loop independently verifies proposed code or effects.\n")
    catalog = home / "models.json"
    metadata = {"slug": model, "display_name": model, "description": "Explicit caller-bound text route",
        "supported_reasoning_levels": [], "shell_type": "disabled", "visibility": "list",
        "supported_in_api": True, "priority": 1, "upgrade": None, "model_messages": None,
        "base_instructions": instructions.read_text(encoding="utf-8"),
        "default_reasoning_summary": "none", "supports_reasoning_summary_parameter": False,
        "support_verbosity": False, "default_verbosity": None, "apply_patch_tool_type": None,
        "truncation_policy": {"mode": "bytes", "limit": config.get("maximum_output_bytes", 1048576)},
        "context_window": context, "experimental_supported_tools": [], "input_modalities": ["text"],
        "include_skills_usage_instructions": False, "include_plugin_usage_instructions": False,
        "include_apps_usage_instructions": False, "supports_search_tool": False}
    _write(catalog, json.dumps({"models": [metadata]}, ensure_ascii=False))
    wire = "chat" if style == "openinterpreter_rust" else "responses"
    toml = [f"model = {json.dumps(model)}", 'model_provider = "loop_engine"',
        'approval_policy = "never"', 'sandbox_mode = "read-only"', 'web_search = "disabled"',
        'check_for_update_on_startup = false', 'model_reasoning_summary = "none"',
        'suppress_unstable_features_warning = true',
        f"model_context_window = {context}", f"model_catalog_json = {json.dumps(str(catalog))}",
        f"model_instructions_file = {json.dumps(str(instructions))}",
        '[model_providers.loop_engine]', 'name = "Loop Engine private broker"',
        f"base_url = {json.dumps(base_url)}", f'wire_api = {json.dumps(wire)}', 'requires_openai_auth = false',
        'env_key = "LOOP_ENGINE_BROKER_KEY"', 'supports_websockets = false',
        'request_max_retries = 0', 'stream_max_retries = 0',
        f'stream_idle_timeout_ms = {math.ceil(timeout * 1000)}',
        '[tools.update_plan]', 'enabled = false', '[tools.experimental_request_user_input]', 'enabled = false',
        '[analytics]', 'enabled = false', '[skills]', 'include_instructions = false',
        '[skills.bundled]', 'enabled = false', '[features]',
        *[f'{key} = false' for key in DISABLED_FEATURES], 'skip_host_skill_discovery = true']
    _write(home / "config.toml", "\n".join(toml) + "\n")
    environment = {"CODEX_HOME" if style == "codex" else "INTERPRETER_HOME": str(home),
                   "LOOP_ENGINE_BROKER_KEY": "loop-engine-local-relay", "NO_COLOR": "1",
                   "DO_NOT_TRACK": "1", "RUST_LOG": "error"}
    # openinterpreter_rust resolves non-o-series model slugs to a non-Responses
    # wire and then refuses it ("non-Responses wire APIs require the
    # compatibility transport"). Its --chat-completions flag selects the
    # OpenAI chat wire the relay serves generically; codex keeps Responses.
    chat = ("--chat-completions",) if style == "openinterpreter_rust" else ()
    return prefix + ("exec",) + chat + ("--skip-git-repo-check", "--ephemeral", "--json", "--color", "never", "-"), environment, prompt


def _content(value):
    if isinstance(value, str):
        return value
    if not isinstance(value, list):
        raise ResponsesRecipeError("responses_text_content_required")
    parts = []
    for part in value:
        if (not isinstance(part, dict) or part.get("type") not in ("input_text", "output_text")
                or not isinstance(part.get("text"), str)
                or set(part) - {"type", "text", "annotations"} or part.get("annotations")):
            raise ResponsesRecipeError("responses_nontext_content_refused")
        parts.append(part["text"])
    return "".join(parts)


def decode_responses_text_request(path, body, exact_model):
    """Translate one stateless text request, refusing every native tool schema."""
    if path != "/v1/responses" or not isinstance(body, dict) or body.get("model") != exact_model:
        raise ResponsesRecipeError("responses_exact_route_refused")
    if ("tools" in body and body["tools"] != []) or body.get("tool_choice") not in (None, "none", "auto"):
        raise ResponsesRecipeError("native_tools_not_authorized")
    allowed = {"model", "instructions", "input", "tools", "tool_choice", "parallel_tool_calls",
        "store", "stream", "include", "prompt_cache_key", "reasoning", "text", "metadata", "client_metadata",
        "max_output_tokens", "temperature", "top_p"}
    if set(body) - allowed:
        raise ResponsesRecipeError("responses_request_fields_refused")
    if (body.get("store", False) is not False or type(body.get("stream", False)) is not bool
            or type(body.get("parallel_tool_calls", False)) is not bool):
        raise ResponsesRecipeError("responses_state_or_stream_refused")
    if body.get("reasoning") not in (None, {}) or body.get("text") not in (None, {}):
        raise ResponsesRecipeError("responses_unsupported_semantic_settings")
    if body.get("include", []) not in ([], ["reasoning.encrypted_content"]):
        raise ResponsesRecipeError("responses_include_refused")
    # These are client correlation fields, never a source of model authority.
    for field in ("metadata", "client_metadata"):
        if field in body and (not isinstance(body[field], dict)
                or any(not isinstance(key, str) or not isinstance(value, str) for key, value in body[field].items())):
            raise ResponsesRecipeError("responses_metadata_refused")
    messages = []
    if body.get("instructions"):
        if not isinstance(body["instructions"], str):
            raise ResponsesRecipeError("responses_instructions_refused")
        messages.append({"role": "system", "content": body["instructions"]})
    items = body.get("input")
    if isinstance(items, str):
        messages.append({"role": "user", "content": items})
    elif isinstance(items, list) and items:
        for item in items:
            if (not isinstance(item, dict) or item.get("type", "message") != "message"
                    or item.get("role") not in ("system", "developer", "user", "assistant")
                    or set(item) - {"type", "role", "content", "id", "status", "phase"}):
                raise ResponsesRecipeError("responses_native_or_nonmessage_item_refused")
            messages.append({"role": item["role"], "content": _content(item.get("content"))})
    else:
        raise ResponsesRecipeError("responses_input_required")
    result = {"model": exact_model, "messages": messages, "stream": False}
    if "max_output_tokens" in body:
        maximum = body["max_output_tokens"]
        if type(maximum) is not int or maximum <= 0:
            raise ResponsesRecipeError("responses_allocation_refused")
        result["max_tokens"] = maximum
    for field in ("temperature", "top_p"):
        if field in body:
            value = body[field]
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= (1 if field == "top_p" else 2):
                raise ResponsesRecipeError("responses_sampling_refused")
            result[field] = value
    return result


def encode_responses_text_events(response, exact_model):
    """Encode a completed text answer as a finite Responses event stream."""
    if not isinstance(response, dict) or response.get("model") != exact_model:
        raise ResponsesRecipeError("responses_model_mismatch")
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise ResponsesRecipeError("responses_single_choice_required")
    message = choices[0].get("message")
    if not isinstance(message, dict) or message.get("tool_calls") or message.get("function_call"):
        raise ResponsesRecipeError("native_tools_not_authorized")
    if (message.get("role") != "assistant" or not isinstance(message.get("content"), str)
            or choices[0].get("finish_reason") != "stop"):
        raise ResponsesRecipeError("responses_completed_text_required")
    text = message["content"]
    item = {"id": "msg_loop_engine", "type": "message", "role": "assistant", "status": "completed",
            "content": [{"type": "output_text", "text": text, "annotations": []}]}
    record = {"id": response.get("id", "resp_loop_engine"), "object": "response", "created_at": 1,
              "status": "completed", "model": exact_model, "output": [item]}
    usage = response.get("usage")
    if usage is not None:
        if not isinstance(usage, dict):
            raise ResponsesRecipeError("responses_usage_refused")
        record["usage"] = {}
        for source, target in (("prompt_tokens", "input_tokens"), ("completion_tokens", "output_tokens"), ("total_tokens", "total_tokens")):
            if usage.get(source) is not None:
                value = usage[source]
                if type(value) is not int or value < 0:
                    raise ResponsesRecipeError("responses_usage_refused")
                record["usage"][target] = value
    events = [{"type": "response.created", "response": {**record, "status": "in_progress", "output": []}},
              {"type": "response.output_item.added", "output_index": 0, "item": {**item, "status": "in_progress", "content": []}},
              {"type": "response.content_part.added", "item_id": item["id"], "output_index": 0,
               "content_index": 0, "part": {"type": "output_text", "text": "", "annotations": []}},
              {"type": "response.output_text.delta", "item_id": item["id"], "output_index": 0, "content_index": 0, "delta": text},
              {"type": "response.output_text.done", "item_id": item["id"], "output_index": 0, "content_index": 0, "text": text},
              {"type": "response.content_part.done", "item_id": item["id"], "output_index": 0, "content_index": 0, "part": item["content"][0]},
              {"type": "response.output_item.done", "output_index": 0, "item": item},
              {"type": "response.completed", "response": record}]
    return tuple(dict(event, sequence_number=index) for index, event in enumerate(events))


def extract_responses_output(style, stdout, expected):
    """Require exact final assistant text and a completed, tool-free CLI turn."""
    if (style not in ("codex", "openinterpreter_rust") or not isinstance(stdout, str)
            or not isinstance(expected, str) or not expected):
        return ""
    try:
        rows = [json.loads(line) for line in stdout.splitlines() if line.strip()]
    except (ValueError, TypeError, RecursionError):
        return ""
    if not rows or any(not isinstance(row, dict) or not isinstance(row.get("type"), str) for row in rows):
        return ""
    if any(row.get("type") in ("turn.failed", "error") for row in rows):
        return ""
    items = [row.get("item", {}) for row in rows if row.get("type", "").startswith("item.")]
    if any(not isinstance(item, dict) or item.get("type") not in ("agent_message", "reasoning") for item in items):
        return ""
    outputs = [row.get("item", {}).get("text") for row in rows if row.get("type") == "item.completed"
               and row.get("item", {}).get("type") == "agent_message"]
    return expected if outputs and outputs[-1] == expected and rows[-1].get("type") == "turn.completed" else ""
