"""Pinned Python CLI launch recipes for Loop-owned isolated semantic work.

Owns private configuration and output decoding for Mistral Vibe 2.25.0 and
gptme 0.33.0. The existing process adapter owns isolation and lifecycle; the
canonical gateway owns provider authority, actual output limits and accounting.
This module is stdlib-only so the isolated relay can import it directly.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit


PYTHON_RECIPE_VERSIONS = {"mistral_vibe": "2.25.0", "gptme": "0.33.0"}


class PythonRecipeError(ValueError):
    """A requested Python CLI profile lacks a qualified contract."""


def prepare_python_recipe(style, config, base_url):
    """Return argv, environment overrides and private prompt stdin bytes."""
    if style not in PYTHON_RECIPE_VERSIONS:
        raise PythonRecipeError("unsupported_python_harness_style")
    if config.get("package_version", PYTHON_RECIPE_VERSIONS[style]) != PYTHON_RECIPE_VERSIONS[style]:
        raise PythonRecipeError("python_harness_version_not_qualified")
    base = urlsplit(base_url)
    if (base.scheme != "http" or base.hostname != "127.0.0.1" or not base.port
            or base.username or base.password or base.query or base.fragment
            or base.path not in ("/v1", "/v1/")):
        raise PythonRecipeError("isolated_loopback_relay_required")
    prefix = tuple(config["command_prefix"])
    model = config["model"]
    if (not prefix or any(not isinstance(part, str) or not part or "\x00" in part for part in prefix)
            or not isinstance(model, str) or not model or model.startswith("-")
            or any(character in model for character in "\r\n\x00")):
        raise PythonRecipeError("exact_python_harness_identity_required")
    workspace = Path(config.get("workspace_path", "/work"))
    task = Path(config.get("task_path", "/relay/task.txt"))
    if (not workspace.is_absolute() or not task.is_absolute()
            or any(path.is_symlink() for path in (workspace, *workspace.parents, task, *task.parents))):
        raise PythonRecipeError("absolute_private_paths_required")
    prompt = task.read_bytes()
    if not prompt or len(prompt) > config.get("maximum_request_bytes", 4_000_000):
        raise PythonRecipeError("private_prompt_size_refused")
    capacity, allowance = config["output_capacity"], config["output_allowance"]
    if type(capacity) is not int or type(allowance) is not int or not 0 < allowance <= capacity:
        raise PythonRecipeError("explicit_output_allowance_required")
    if style == "gptme":
        if Path(prefix[0]).name != "gptme-util":
            raise PythonRecipeError("gptme_generation_requires_exact_gptme_util_entrypoint")
        # The ordinary non-interactive chat CLI forcibly adds its complete
        # tool even for --tools none. Its shortcut also consumes the model
        # option before forwarding. The exact gptme-util generation entrypoint
        # initializes an empty tool list and avoids that autonomous chat loop.
        argv = prefix + ("llm", "generate", "--output-format", "json", "--no-stream",
                         "--max-tokens", str(allowance), "--model", "local/" + model)
        environment = {
            "OPENAI_API_KEY": "loop-engine-local-relay", "OPENAI_BASE_URL": base_url,
            "PATH": str(Path(prefix[0]).parent) + ":/usr/bin:/bin",
            "GPTME_MAX_TOKENS": str(allowance), "GPTME_MAX_STEPS": "1",
            "GPTME_TELEMETRY_ENABLED": "false", "GPTME_TIKTOKEN_TIMEOUT": "0",
        }
        return argv, environment, prompt

    home = workspace / "home/.vibe"
    home.mkdir(parents=True, exist_ok=True)
    # Vibe's --max-tokens is a total session bound, not an output capacity.
    # No per-response setting exists on this installed ModelConfig. The
    # canonical broker must supply/enforce its exact selected output allowance.
    settings = [
        'active_model = "loop_engine"', 'allowed_models = ["loop_engine"]',
        'disabled_tools = ["*"]', 'disabled_skills = ["*"]', 'mcp_servers = []',
        'include_project_context = false', 'enable_telemetry = false',
        'enable_update_checks = false', 'enable_auto_update = false',
        'experimental_enable_registry_skills = false', 'show_greeting = false',
        '[experiments]', 'enable = false', '[session_logging]',
        'enabled = true', 'generate_titles = false',
        '[[providers]]', 'name = "loop_engine"', 'api_base = ' + json.dumps(base_url),
        'api_key_env_var = "LOOP_ENGINE_LOCAL_API_KEY"', 'api_style = "openai"',
        'backend = "generic"', '[[models]]', 'name = ' + json.dumps(model),
        'provider = "loop_engine"', 'alias = "loop_engine"', 'thinking = "off"',
        'supports_images = false',
    ]
    (home / "config.toml").write_text("\n".join(settings) + "\n", encoding="utf-8")
    argv = prefix + ("--prompt", "--disabled-tools", "*", "--output", "json",
                     "--trust", "--max-turns", "1")
    environment = {"VIBE_HOME": str(home), "LOOP_ENGINE_LOCAL_API_KEY": "loop-engine-local-relay",
                   "LOG_LEVEL": "ERROR", "DO_NOT_TRACK": "1"}
    return argv, environment, prompt


def extract_python_output(style, stdout, expected):
    """Accept only the final completed assistant text that matches the broker."""
    if style not in PYTHON_RECIPE_VERSIONS or not isinstance(expected, str) or not expected:
        return ""
    try:
        rows = json.loads(stdout)
    except (ValueError, TypeError, RecursionError):
        return ""
    if style == "gptme":
        return expected if (isinstance(rows, dict) and set(rows) == {"content", "model", "usage"}
            and isinstance(rows["model"], str) and rows["model"]
            and (rows["usage"] is None or isinstance(rows["usage"], dict))
            and rows["content"] == expected) else ""
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        return ""
    last = None
    for row in rows:
        if (row.get("error") or row.get("type") in ("error", "effect", "callback")
                or row.get("role") == "tool" or row.get("call_id")):
            return ""
        if row.get("type") != "message" or row.get("role") != "assistant":
            continue
        parts = row.get("content")
        if (row.get("generationStatus") != "completed" or not isinstance(parts, list)
                or any(not isinstance(part, dict) or part.get("type") != "text"
                       or not isinstance(part.get("text"), str) for part in parts)):
            last = None
        else:
            last = "\n\n".join(part["text"] for part in parts)
    return expected if last == expected else ""
