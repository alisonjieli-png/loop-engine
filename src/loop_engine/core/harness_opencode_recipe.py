"""OpenCode recipe for a new brokered semantic-step profile, not raw host use.

Owns: private prompt transport, per-process configuration and terminal parsing.
Does not own: execution, model authority, effects or acceptance. The historical
raw-host OpenCode adapter stays quarantined. A classified Loop owns this work.
Reference input: new_overnight_build/poc/harness.py at 309d668d plus dirty work.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

# OpenCode's own finish reason for a turn that ended on its own.
OPENCODE_STOP_REASON = "stop"


def prepare_opencode_recipe(config, base_url):
    """Return argv, local-relay environment and exact private task stdin."""
    url = urlsplit(base_url)
    if url.scheme != "http" or url.hostname != "127.0.0.1" or not url.port or url.username or url.password:
        raise ValueError("isolated_loopback_relay_required")
    model = config["model"]
    workspace = Path(config.get("workspace_path", "/work"))
    task = Path(config.get("task_path", "/relay/task.txt"))
    if not workspace.is_absolute() or not task.is_absolute():
        raise ValueError("absolute_private_paths_required")
    maximum = config.get("maximum_request_bytes", 2 * 1024 * 1024)
    if type(maximum) is not int or maximum < 1:
        raise ValueError("invalid_private_task_byte_limit")
    with task.open("rb") as handle:
        prompt = handle.read(maximum + 1)
    if not prompt or len(prompt) > maximum:
        raise ValueError("private_prompt_size_refused")
    prompt.decode("utf-8")
    if not config.get("context_capacity") or not config.get("output_capacity"):
        raise ValueError("opencode_exact_model_capacity_required")
    metadata = {"name": model, "limit": {"context": config["context_capacity"],
                 "output": config["output_capacity"]},
                "options": {"maxTokens": config["output_allowance"]}}
    body = {"autoupdate": False, "share": "disabled", "plugin": [], "mcp": {},
            "enabled_providers": ["engine"], "model": "engine/" + model,
            "small_model": "engine/" + model,
            "provider": {"engine": {"npm": "@ai-sdk/openai-compatible", "name": "Engine relay",
                "options": {"baseURL": base_url, "apiKey": "loop-engine-local-relay"},
                "models": {model: metadata}}},
            "tools": {"*": False}, "permission": {"*": "deny"},
            "agent": {"loop-engine": {"mode": "primary", "tools": {"*": False},
                "permission": {"*": "deny"},
                "prompt": "Return the semantic response requested by the supplied task. Native tools are unavailable."},
                "title": {"disable": True}, "summary": {"disable": True}}}
    environment = {"OPENCODE_CONFIG_CONTENT": json.dumps(body, allow_nan=False),
        "OPENCODE_DISABLE_PROJECT_CONFIG": "true", "OPENCODE_DISABLE_DEFAULT_PLUGINS": "true",
        "OPENCODE_DISABLE_AUTOUPDATE": "true", "OPENCODE_DISABLE_SHARE": "true",
        "XDG_DATA_HOME": str(workspace / "home/.local/share")}
    # --file numbers every input line and changes the canonical semantic packet.
    # The native stdin channel preserves the exact task with tool denial intact.
    argv = tuple(config["command_prefix"]) + ("run", "Follow the supplied task.",
        "--format", "json", "--log-level", "ERROR",
        "--dir", str(workspace), "--agent", "loop-engine", "--model", "engine/" + model, "--pure")
    return argv, environment, prompt


def extract_opencode_output(stdout, expected):
    """Require an exact text result, no native tool event and a stop terminal."""
    texts = []
    terminal = None
    for line in stdout.split("\n"):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except (ValueError, RecursionError):
            return ""
        if not isinstance(row, dict) or row.get("type") in ("error", "tool_use"):
            return ""
        part = row.get("part", {})
        if not isinstance(part, dict) or part.get("type") == "tool":
            return ""
        if row.get("type") == "text" and part.get("type") == "text":
            if not isinstance(part.get("text"), str):
                return ""
            texts.append(part["text"])
        if part.get("type") == "step-finish":
            terminal = part.get("reason")
    actual = "\n".join(texts)
    return expected if expected and actual == expected and terminal == OPENCODE_STOP_REASON else ""
