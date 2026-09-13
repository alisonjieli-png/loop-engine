"""Pinned Cline and Kilo text-only recipes for the canonical Loop process port.

Owns private configuration/input and terminal parsing, not execution, provider
authority, native tools, or task acceptance. Cline 3.0.61 settings are grounded
in its installed CLI help and @cline/core/@cline/shared schemas. Kilo 7.5.16 is
a distinct maintained OpenCode-derived project; its installed help/config
symbols and actual isolated request fixtures establish this bounded recipe.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
from urllib.parse import urlsplit


CLINE_DISABLED_TOOLS = (
    "read_files", "search_codebase", "run_commands", "fetch_web_content", "editor", "ask_question",
    "spawn_agent", "team_spawn_teammate", "team_shutdown_teammate", "team_status", "team_task",
    "team_run_task", "team_cancel_run", "team_list_runs", "team_await_runs", "team_send_message",
    "team_broadcast", "team_read_mailbox", "team_mission_log", "team_cleanup", "team_create_outcome",
    "team_attach_outcome_fragment", "team_review_outcome_fragment", "team_finalize_outcome", "team_list_outcomes",
)


def _configuration(config, base_url):
    base = urlsplit(base_url)
    if (base.scheme != "http" or base.hostname != "127.0.0.1" or not base.port
            or base.username or base.password or base.query or base.fragment):
        raise ValueError("isolated_loopback_relay_required")
    prefix, model = tuple(config["command_prefix"]), config["model"]
    if (not prefix or any(not isinstance(value, str) or not value or "\x00" in value for value in prefix)
            or not isinstance(model, str) or not model or model.startswith("-")
            or any(char in model for char in "\r\n\x00?#")):
        raise ValueError("exact_installed_command_and_model_required")
    workspace, task = Path(config.get("workspace_path", "/work")), Path(config.get("task_path", "/relay/task.txt"))
    if any(not path.is_absolute() or ".." in path.parts for path in (workspace, task)):
        raise ValueError("absolute_private_paths_required")
    limit = config.get("maximum_request_bytes", 2 * 1024 * 1024)
    if type(limit) is not int or limit <= 0:
        raise ValueError("invalid_private_task_byte_limit")
    with task.open("rb") as handle:
        prompt = handle.read(limit + 1)
    if not prompt or len(prompt) > limit:
        raise ValueError("private_prompt_size_refused")
    prompt.decode("utf-8")
    capacity, allowance = config.get("output_capacity"), config.get("output_allowance")
    if type(capacity) is not int or capacity <= 0 or type(allowance) is not int or not 0 < allowance <= capacity:
        raise ValueError("explicit_output_capacity_and_allocation_required")
    return prefix, model, workspace, prompt


def prepare_cline_kilo_recipe(style, config, base_url):
    """Return argv, private environment overrides and task bytes for stdin."""
    if style not in ("cline", "kilo"):
        raise ValueError("unsupported_cline_kilo_style")
    prefix, model, work, prompt = _configuration(config, base_url)
    if style == "cline":
        timeout = config.get("timeout_seconds")
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("explicit_cline_deadline_required")
        data = work / "cline-data"
        settings = data / "settings"
        settings.mkdir(parents=True, exist_ok=True)
        provider_path, global_path = settings / "providers.json", settings / "global-settings.json"
        provider = {"version": 1, "lastUsedProvider": "openai-compatible", "modes": {}, "providers": {
            "openai-compatible": {"settings": {"provider": "openai-compatible",
                "apiKey": "loop-engine-local-relay", "model": model, "baseUrl": base_url},
                # Required by Cline's StoredProviderSettingsEntry schema.
                "updatedAt": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                "tokenSource": "manual"}}}
        global_settings = {"telemetryOptOut": True, "autoUpdateEnabled": False,
            "compactionEnabled": False, "toolAutoApprove": False,
            "disabledTools": list(CLINE_DISABLED_TOOLS), "disabledPlugins": [],
            "tools": {"web_search": {"enabled": False}}}
        provider_path.write_text(json.dumps(provider, allow_nan=False), encoding="utf-8")
        global_path.write_text(json.dumps(global_settings, allow_nan=False), encoding="utf-8")
        environment = {"CLINE_DATA_DIR": str(data), "CLINE_PROVIDER_SETTINGS_PATH": str(provider_path),
                       "CLINE_GLOBAL_SETTINGS_PATH": str(global_path)}
        argv = prefix + ("--json", "--provider", "openai-compatible", "--model", model,
            "--auto-approve", "false", "--compaction", "off", "--retries", "1",
            "--timeout", str(math.ceil(timeout)), "--cwd", str(work),
            "--data-dir", str(data), "--config", str(work / "cline-config"), "Follow the supplied task.")
        return argv, environment, prompt

    context = config.get("context_capacity")
    if type(context) is not int or context <= 0:
        raise ValueError("kilo_exact_context_capacity_required")
    body = {"autoupdate": False, "share": "disabled", "plugin": [], "mcp": {},
        "enabled_providers": ["engine"], "model": "engine/" + model, "small_model": "engine/" + model,
        "tools": {"*": False}, "permission": {"*": "deny"}, "provider": {"engine": {
            "npm": "@ai-sdk/openai-compatible", "name": "Engine relay",
            "options": {"baseURL": base_url, "apiKey": "loop-engine-local-relay"},
            "models": {model: {"name": model, "limit": {"context": context, "output": config["output_capacity"]},
                               "options": {"maxTokens": config["output_allowance"]}}}}},
        "agent": {"loop-engine": {"mode": "primary", "tools": {"*": False}, "permission": {"*": "deny"},
                    "prompt": "Return the requested text. Native tools are unavailable."},
                  "title": {"disable": True}, "summary": {"disable": True}}}
    environment = {"KILO_CONFIG_CONTENT": json.dumps(body, allow_nan=False),
        "KILO_DISABLE_PROJECT_CONFIG": "true", "KILO_DISABLE_DEFAULT_PLUGINS": "true",
        "KILO_DISABLE_AUTOUPDATE": "true", "KILO_DISABLE_SHARE": "true",
        "KILO_DISABLE_MODELS_FETCH": "true", "KILO_DISABLE_CODEBASE_INDEXING": "true",
        "KILO_DISABLE_SESSION_INGEST": "true"}
    # --file triggers a denied native attachment read in this pinned Kilo version.
    # Its standard stdin channel delivers the exact task with deny-all intact.
    argv = prefix + ("run", "Follow the supplied task.", "--format", "json", "--log-level", "ERROR",
                     "--dir", str(work), "--agent", "loop-engine", "--model", "engine/" + model, "--pure")
    return argv, environment, prompt


def extract_cline_kilo_output(style, stdout, expected):
    """Require one successful terminal and the exact broker text; never exit alone."""
    if style not in ("cline", "kilo") or not isinstance(expected, str) or not expected:
        return ""
    rows = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except (ValueError, RecursionError):
            return ""
        if not isinstance(row, dict):
            return ""
        rows.append(row)
    if style == "cline":
        terminals, done = [], []
        for row in rows:
            if row.get("type") in ("error", "run_aborted"):
                return ""
            if row.get("type") == "agent_event":
                event = row.get("event")
                if (not isinstance(event, dict) or event.get("type") == "error"
                        or event.get("contentType") == "tool" or event.get("hadToolCalls") is True):
                    return ""
                if event.get("type") == "done":
                    done.append(event)
            if row.get("type") == "run_result":
                terminals.append(row)
        return expected if (len(terminals) == len(done) == 1
            and terminals[0].get("finishReason") == "completed" and terminals[0].get("text") == expected
            and done[0].get("reason") == "completed" and done[0].get("text") == expected) else ""
    texts, terminals = [], []
    for row in rows:
        if row.get("type") in ("error", "tool_use"):
            return ""
        part = row.get("part", {})
        if not isinstance(part, dict) or part.get("type") == "tool":
            return ""
        if row.get("type") == "text":
            if part.get("type") != "text" or not isinstance(part.get("text"), str):
                return ""
            texts.append(part["text"])
        if part.get("type") == "step-finish":
            terminals.append(part.get("reason"))
    return expected if terminals == ["stop"] and "\n".join(texts) == expected else ""
