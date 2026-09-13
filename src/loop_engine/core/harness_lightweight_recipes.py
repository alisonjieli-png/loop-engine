"""Confined text adapters for explicitly pinned lightweight harness projects.

These internal adapter functions are not executable graph vertices. They do
not grant provider or tool authority. A separately configured broker owns all
physical model calls, and Bubblewrap owns filesystem and network confinement.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit


class LightweightRecipeError(ValueError):
    """A requested lightweight adapter exceeds its qualified text boundary."""


NANOCODE_HEADLESS = '''"""Headless I/O and endpoint adapter; upstream model/tool loop is unchanged."""
import builtins
import importlib.util
import json
from pathlib import Path
import sys

config = json.loads(Path(sys.argv[1]).read_text())
spec = importlib.util.spec_from_file_location('pinned_nanocode', config['source'])
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)
entry.API_URL = config['base_url'] + '/messages'
entry.MODEL = config['model']
entry.TOOLS = {}
entry.separator = lambda: ''
entry.render_markdown = lambda text: text
answers = iter((Path(config['task']).read_text(), '/q'))
builtins.input = lambda prompt='': next(answers)
entry.main()
'''

TRAE_SEMANTIC = '''"""Modified SDK text-submission profile using the real Trae execution loop."""
import asyncio
import json
from pathlib import Path
import sys

from trae_agent.agent.agent import Agent
from trae_agent.utils.config import Config

async def main():
    settings = json.loads(Path(sys.argv[1]).read_text())
    config = Config.create(config_file=settings['upstream_config'])
    task = Path(settings['task']).read_text()
    engine = Agent('trae_agent', config, trajectory_file=settings['trajectory'])
    engine.agent.get_system_prompt = lambda: (
        'You are a software engineering agent in a text-only semantic profile. '
        'Follow the supplied task and its output contract. Native tools are unavailable. '
        'Submit candidate text in your final response. The owning Loop independently '
        'executes and verifies any proposed code or effects.')
    engine.agent.llm_indicates_task_completed = lambda response: (
        response.finish_reason == 'stop' and not response.tool_calls
        and isinstance(response.content, str) and bool(response.content))
    result = await engine.run(task, extra_args={'project_path': settings['workspace'],
        'issue': task, 'must_patch': 'false'}, tool_names=[])
    tool_calls_seen = any(step.llm_response and step.llm_response.tool_calls for step in result.steps)
    empty_registry = not engine.agent.tools
    ok = bool(result.success and empty_registry and not tool_calls_seen
              and isinstance(result.final_result, str) and result.final_result)
    print(json.dumps({'type': 'trae_semantic_result', 'profile': 'trae_text_submission/v1',
        'ok': ok, 'candidate': result.final_result if ok else '',
        'upstream_success': result.success, 'native_tool_registry_empty': empty_registry,
        'native_tool_calls_seen': tool_calls_seen, 'steps': len(result.steps),
        'error': result.final_result if not ok else None}, ensure_ascii=False))
    return 0 if ok else 1

sys.exit(asyncio.run(main()))
'''


def _private_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    path.chmod(0o600)


def prepare_lightweight_recipe(style, config, base_url):
    """Prepare private configuration and argv without loading upstream code."""
    base = urlsplit(base_url)
    if (base.scheme != "http" or base.hostname != "127.0.0.1" or not base.port
            or base.path != "/v1" or base.query or base.fragment or base.username or base.password):
        raise LightweightRecipeError("loopback_broker_required")
    prefix = tuple(config.get("command_prefix", ()))
    model = config.get("model")
    if not prefix or any(not isinstance(value, str) or not value or "\x00" in value for value in prefix):
        raise LightweightRecipeError("exact_command_required")
    if not isinstance(model, str) or not model or any(value in model for value in "\x00\r\n"):
        raise LightweightRecipeError("exact_model_required")
    workspace = Path(config.get("workspace_path", "/work"))
    task = Path(config.get("task_path", "/relay/task.txt"))
    if not workspace.is_absolute() or not task.is_absolute() or ".." in workspace.parts or ".." in task.parts:
        raise LightweightRecipeError("absolute_private_paths_required")
    content = task.read_bytes()
    if not content or len(content) > config.get("maximum_request_bytes", 2 * 1024 * 1024):
        raise LightweightRecipeError("private_prompt_size_refused")
    allowance = config.get("output_allowance")
    if type(allowance) is not int or allowance <= 0:
        raise LightweightRecipeError("typed_output_allocation_required")
    environment = {"NO_COLOR": "1", "DO_NOT_TRACK": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    if style == "nanocode":
        if len(prefix) != 2 or not Path(prefix[1]).is_absolute():
            raise LightweightRecipeError("nanocode_python_and_pinned_source_required")
        wrapper = workspace / "nanocode-headless.py"
        wrapper.write_text(NANOCODE_HEADLESS, encoding="utf-8")
        wrapper.chmod(0o600)
        settings = workspace / "nanocode-private.json"
        _private_json(settings, {"source": prefix[1], "base_url": base_url,
                                "model": model, "task": str(task)})
        return (prefix[0], str(wrapper), str(settings)), environment, None
    if style == "trae_agent":
        settings = {
            "model_providers": {"loop_engine": {"provider": "openrouter",
                "api_key": "loop-engine-local-relay", "base_url": base_url}},
            "models": {"loop_engine": {"model": model, "model_provider": "loop_engine",
                "temperature": 0, "top_p": 1, "top_k": 0, "parallel_tool_calls": False,
                "max_retries": 0, "max_tokens": allowance, "supports_tool_calling": False}},
            "agents": {"trae_agent": {"model": "loop_engine", "max_steps": 1,
                "tools": [], "enable_lakeview": False}},
            "mcp_servers": {}, "allow_mcp_servers": []}
        path = workspace / "trae-private.yaml"
        _private_json(path, settings)  # JSON is accepted by the upstream YAML reader.
        return prefix + ("run", "--file", str(task), "--config-file", str(path),
            "--working-dir", str(workspace), "--trajectory-file", str(workspace / "trajectory.json"),
            "--max-steps", "1", "--console-type", "simple"), environment, None
    if style == "freebuff":
        raise LightweightRecipeError("freebuff_hosted_protocol_not_qualified_for_model_broker")
    raise LightweightRecipeError("unsupported_lightweight_harness_style")


def _text_content(value):
    if isinstance(value, str):
        return value
    if not isinstance(value, list) or not value:
        raise LightweightRecipeError("anthropic_text_content_required")
    if any(not isinstance(part, dict) or set(part) != {"type", "text"}
           or part["type"] != "text" or not isinstance(part["text"], str) for part in value):
        raise LightweightRecipeError("anthropic_nontext_content_refused")
    return "".join(part["text"] for part in value)


def prepare_trae_semantic_recipe(config, base_url):
    """Select an explicit SDK text profile, retaining Trae's execution loop.

    Public Agent.run(tool_names=[]) preserves the empty tool registry. The
    private wrapper replaces only task completion with exact text-submission
    conditions and emits a versioned result. It never substitutes a raw model
    call for the upstream Agent execution.
    """
    _, environment, _ = prepare_lightweight_recipe("trae_agent", config, base_url)
    prefix = tuple(config["command_prefix"])
    if len(prefix) != 1 or not Path(prefix[0]).is_absolute():
        raise LightweightRecipeError("trae_explicit_python_required")
    workspace = Path(config.get("workspace_path", "/work"))
    wrapper = workspace / "trae-semantic.py"
    wrapper.write_text(TRAE_SEMANTIC, encoding="utf-8")
    wrapper.chmod(0o600)
    settings = workspace / "trae-semantic-private.json"
    _private_json(settings, {"upstream_config": str(workspace / "trae-private.yaml"),
        "task": config.get("task_path", "/relay/task.txt"), "workspace": str(workspace),
        "trajectory": str(workspace / "trajectory.json")})
    environment["PYTHONNOUSERSITE"] = "1"
    return prefix + (str(wrapper), str(settings)), environment, None


def decode_anthropic_text_request(path, body, exact_model):
    """Decode the nanocode Messages subset; refuse tools before model dispatch."""
    if path != "/v1/messages" or not isinstance(body, dict) or body.get("model") != exact_model:
        raise LightweightRecipeError("anthropic_exact_route_refused")
    if body.get("tools") or body.get("tool_choice"):
        raise LightweightRecipeError("native_tools_not_authorized")
    if set(body) - {"model", "max_tokens", "system", "messages", "tools", "temperature", "top_p"}:
        raise LightweightRecipeError("anthropic_request_fields_refused")
    maximum = body.get("max_tokens")
    if type(maximum) is not int or maximum <= 0:
        raise LightweightRecipeError("anthropic_output_allocation_refused")
    messages = []
    if "system" in body:
        messages.append({"role": "system", "content": _text_content(body["system"])})
    rows = body.get("messages")
    if not isinstance(rows, list) or not rows:
        raise LightweightRecipeError("anthropic_messages_required")
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {"role", "content"}
                or row["role"] not in ("user", "assistant")):
            raise LightweightRecipeError("anthropic_message_role_refused")
        messages.append({"role": row["role"], "content": _text_content(row["content"])})
    result = {"model": exact_model, "messages": messages, "max_tokens": maximum, "stream": False}
    for field in ("temperature", "top_p"):
        if field in body:
            number = body[field]
            if type(number) not in (float, int) or not math.isfinite(number) or not 0 <= number <= 1:
                raise LightweightRecipeError("anthropic_sampling_value_refused")
            result[field] = number
    return result


def encode_anthropic_text_response(response, exact_model):
    """Preserve exact text and reported usage; never admit a native tool call."""
    if not isinstance(response, dict) or response.get("model") != exact_model:
        raise LightweightRecipeError("anthropic_response_model_refused")
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise LightweightRecipeError("anthropic_one_response_required")
    message = choices[0].get("message")
    if not isinstance(message, dict) or message.get("tool_calls") or message.get("function_call"):
        raise LightweightRecipeError("native_tools_not_authorized")
    finish = {"stop": "end_turn"}
    if (message.get("role") != "assistant" or not isinstance(message.get("content"), str)
            or choices[0].get("finish_reason") not in finish):
        raise LightweightRecipeError("anthropic_text_response_required")
    result = {"id": response.get("id", "loop-engine-message"), "type": "message",
              "role": "assistant", "model": exact_model,
              "content": [{"type": "text", "text": message["content"]}],
              "stop_reason": finish[choices[0]["finish_reason"]], "stop_sequence": None}
    usage = response.get("usage")
    if usage is not None:
        if not isinstance(usage, dict):
            raise LightweightRecipeError("anthropic_usage_refused")
        result["usage"] = {}
        for source, target in (("prompt_tokens", "input_tokens"), ("completion_tokens", "output_tokens")):
            if usage.get(source) is not None:
                value = usage[source]
                if type(value) is not int or value < 0:
                    raise LightweightRecipeError("anthropic_usage_refused")
                result["usage"][target] = value
    return result


def extract_lightweight_output(style, stdout, expected):
    """Accept exact qualified text output; the hosted project stays unavailable."""
    if not isinstance(stdout, str) or not isinstance(expected, str) or not expected:
        return ""
    if style == "trae_agent":
        try:
            value = json.loads(stdout)
        except (ValueError, TypeError, RecursionError):
            return ""
        if (isinstance(value, dict) and value.get("type") == "trae_semantic_result"
                and value.get("profile") == "trae_text_submission/v1" and value.get("ok") is True
                and value.get("upstream_success") is True and value.get("native_tool_registry_empty") is True
                and value.get("native_tool_calls_seen") is False and value.get("candidate") == expected):
            return expected
        return ""
    if style != "nanocode":
        return ""
    text = re.sub(r"\x1b\[[0-9;]*m", "", stdout)
    marker = "⏺ " + expected
    return expected if marker in text and "⏺ Error:" not in text else ""
