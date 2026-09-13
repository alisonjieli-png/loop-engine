"""Pinned Goose launch recipe for the existing Loop-owned process adapter.

Owns: private task transport and native-provider Chat-mode configuration.
Does not own: execution, provider authority, effects, or task acceptance.
The canonical Loop remains the only executable graph vertex. This module is
stdlib-only so the existing relay can load it inside its isolated namespace.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit


def prepare_goose_recipe(config, base_url):
    """Return argv, environment overrides and the private prompt stdin bytes."""
    base = urlsplit(base_url)
    if (base.scheme != "http" or base.hostname != "127.0.0.1" or not base.port
            or base.username or base.password or base.query or base.fragment):
        raise ValueError("isolated_loopback_relay_required")
    prefix = tuple(config["command_prefix"])
    model = config["model"]
    if not prefix or not isinstance(model, str) or not model or model.startswith("-"):
        raise ValueError("exact_goose_identity_required")
    workspace = Path(config.get("workspace_path", "/work"))
    task = Path(config.get("task_path", "/relay/task.txt"))
    if not workspace.is_absolute() or not task.is_absolute():
        raise ValueError("absolute_private_paths_required")
    prompt = task.read_bytes()
    if not prompt or len(prompt) > config.get("maximum_request_bytes", 4_000_000):
        raise ValueError("private_prompt_size_refused")
    origin = f"http://127.0.0.1:{base.port}"
    path = base.path.strip("/") + "/chat/completions"
    environment = {
        "GOOSE_PROVIDER": "openai", "GOOSE_MODEL": model, "GOOSE_MODE": "chat",
        "OPENAI_HOST": origin, "OPENAI_BASE_PATH": path,
        "OPENAI_API_KEY": "loop-engine-local-relay", "GOOSE_DISABLE_KEYRING": "1",
        "GOOSE_TELEMETRY_ENABLED": "false",
    }
    settings = workspace / "home/.config/goose/config.yaml"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps({"GOOSE_PROVIDER": "openai", "GOOSE_MODEL": model,
        "GOOSE_MODE": "chat", "extensions": {}}, allow_nan=False), encoding="utf-8")
    return prefix + ("run", "--no-profile", "--name", "Loop Engine semantic step", "--quiet", "--instructions", "-",
                     "--output-format", "stream-json"), environment, prompt


def extract_goose_output(stdout, expected):
    """Require complete output and the final assistant's exact broker text."""
    if not isinstance(expected, str) or not expected:
        return ""
    final_text = None
    complete = False
    for line in stdout.split("\n"):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except (ValueError, RecursionError):
            continue
        if not isinstance(value, dict):
            continue
        if value.get("type") == "error" or value.get("error"):
            return ""
        if value.get("type") == "complete":
            complete = True
        message = value.get("message")
        if isinstance(message, dict) and message.get("role") == "assistant":
            parts = message.get("content", [])
            if not isinstance(parts, list) or any(not isinstance(p, dict) or p.get("type") != "text"
                                                 or not isinstance(p.get("text"), str) for p in parts):
                final_text = None
            else:
                final_text = "".join(p["text"] for p in parts)
    return expected if complete and final_text == expected else ""
