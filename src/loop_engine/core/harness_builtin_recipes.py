"""Aider, Continue and Pi launch recipes for the brokered text-response runner.

Owns: private configuration and command construction for three pinned
command-line harnesses, and admission of their terminal output against the
broker's exact text. The code moved here unchanged in behaviour from the
relay's preparation chain and the runner's extraction chain (plan package X1),
so these three harnesses are catalogue recipes like every other one.
Does not own: model authority, native tools, effects, isolation or task
acceptance. The module uses the standard library only, because the relay loads
it inside the sandbox where no Loop Engine package is installed.
"""
from __future__ import annotations

import json
from pathlib import Path

#: The styles this module prepares; the catalogue record names the module.
BUILTIN_STYLES = ("aider", "continue", "pi")
#: The only model address a recipe accepts: the sandbox's own relay.
RELAY_ORIGIN_PREFIX = "http://127.0.0.1:"


class BuiltinRecipeError(ValueError):
    """A style or setting outside the three pinned built-in recipes."""


def _json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def _loopback(base_url):
    """Refuse any model address other than the sandbox's own relay."""
    if not isinstance(base_url, str) or not base_url.startswith(RELAY_ORIGIN_PREFIX):
        raise BuiltinRecipeError("isolated_loopback_relay_required")
    port, separator, path = base_url[len(RELAY_ORIGIN_PREFIX):].partition("/")
    if not port.isdigit() or separator != "/" or path != "v1":
        raise BuiltinRecipeError("isolated_loopback_relay_required")


def prepare_builtin_recipe(style, config, base_url):
    """Return the command, environment overrides and prompt bytes.

    The task always travels through a private file, so the prompt is None and
    the relay closes standard input, as it did before the move."""
    if style not in BUILTIN_STYLES:
        raise BuiltinRecipeError("unsupported_builtin_harness_style")
    _loopback(base_url)
    prefix, model = list(config["command_prefix"]), config["model"]
    workspace = Path(config.get("workspace_path", "/work"))
    task = str(config.get("task_path", "/relay/task.txt"))
    if not workspace.is_absolute() or not Path(task).is_absolute():
        raise BuiltinRecipeError("absolute_private_paths_required")
    if style == "aider":
        return tuple(prefix + [
            "--model", "openai/" + model, "--openai-api-base", base_url,
            "--openai-api-key", "loop-engine-local-relay", "--no-check-update",
            "--no-analytics", "--no-show-release-notes", "--no-git", "--no-stream",
            "--no-pretty", "--no-show-model-warnings", "--no-check-model-accepts-settings",
            "--map-tokens", "0", "--edit-format", "ask", "--yes-always",
            "--message-file", task]), {}, None
    if style == "continue":
        body = {"name": "Loop Engine confined model adapter", "version": "1.0.0", "schema": "v1",
                "models": [{"name": "loop-engine-model", "provider": "openai", "model": model,
                            "apiKey": "loop-engine-local-relay", "apiBase": base_url,
                            "roles": ["chat"],
                            "defaultCompletionOptions": {"maxTokens": config["output_allowance"]}}]}
        settings = workspace / "model-config.yaml"
        settings.write_bytes(_json(body))
        return tuple(prefix + [
            "--config", str(settings), "--exclude", "*", "-p", "--format", "json",
            "--prompt", task, "Follow the task in the supplied prompt file."]), {}, None
    models = {"providers": {"engine": {
        "baseUrl": base_url, "api": "openai-completions", "apiKey": "loop-engine-local-relay",
        "compat": {"supportsDeveloperRole": False, "supportsReasoningEffort": False,
                   "supportsStore": False, "maxTokensField": "max_tokens"},
        "models": [{"id": model, "name": model, "reasoning": False, "input": ["text"],
                    "contextWindow": config["context_capacity"],
                    "maxTokens": config["output_capacity"]}]}}}
    agent = workspace / "home" / ".pi" / "agent"
    agent.mkdir(parents=True, exist_ok=True)
    (agent / "models.json").write_bytes(_json(models))
    return tuple(prefix + [
        "--provider", "engine", "--model", model, "--mode", "json", "--print", "--no-session",
        "--no-tools", "--no-context-files", "--no-extensions", "--no-skills",
        "--no-prompt-templates", "--no-themes", "--no-approve", "@" + task]), {}, None


def extract_builtin_output(style, stdout, expected):
    """Admit only the broker's exact text, found where each harness prints it.

    Malformed JSON raises ValueError, which the runner records as invalid
    harness output rather than an empty success."""
    if style not in BUILTIN_STYLES or not isinstance(expected, str) or not expected:
        return ""
    if style == "continue":
        value = json.loads(stdout)
        if isinstance(value, dict) and value.get("status") == "success" and value.get("response") == expected:
            return value["response"]
        # Continue returns valid JSON assistant output directly without a wrapper.
        if isinstance(value, (dict, list)) and value == json.loads(expected):
            return stdout.strip()
        return ""
    if style == "aider":
        if expected in stdout:
            start = stdout.rfind(expected)
            return stdout[start:start + len(expected)]
        return ""
    for line in reversed(stdout.splitlines()):
        value = json.loads(line)
        if value.get("type") == "message_end" and value.get("message", {}).get("role") == "assistant":
            message = value["message"]
            actual = "".join(item["text"] for item in message.get("content", []) if item.get("type") == "text")
            return actual if actual == expected and message.get("stopReason") == "stop" else ""
    return ""


def self_test():
    """The checks of these recipes live beside them."""
    from .harness_builtin_recipe_checks import self_test as run_checks
    return run_checks()
