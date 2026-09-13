"""Pinned Hermes, ForgeCode and Crush text recipes for the existing Loop adapter.

These passive preparation/decoding functions grant no effects or model authority.
The canonical broker must record every request, including auxiliary titles. The
process adapter owns containment, deadlines, output limits and software identity.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import re
import uuid
from urllib.parse import urlsplit


REMAINING_RECIPE_VERSIONS = {"hermes_agent": "0.21.1", "forgecode": "2.13.21", "crush": "0.92.0"}
CRUSH_DISABLED_TOOLS = (
    "agent", "bash", "crush_info", "crush_logs", "job_output", "job_kill", "download", "edit",
    "multiedit", "lsp_diagnostics", "lsp_references", "lsp_restart", "lsp_symbols", "lsp_definition",
    "lsp_call_hierarchy", "lsp_rename", "lsp_replace_symbol", "fetch", "agentic_fetch", "glob", "grep",
    "ls", "question", "sourcegraph", "todos", "view", "write", "list_mcp_resources", "read_mcp_resource",
)


class RemainingRecipeError(ValueError):
    """The requested pinned text profile has not been qualified."""


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise RemainingRecipeError("private_configuration_overwrite_refused")
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)


def prepare_remaining_recipe(style, config, base_url):
    """Return argv, private environment overrides and prompt stdin bytes.

    Hermes uses an exact (Python executable, source-directory) command prefix.
    Its original CLI entry point receives the private task through process stdin,
    not a public OS argument. This is I/O adaptation, not a replacement agent loop.
    """
    if (style not in REMAINING_RECIPE_VERSIONS
            or config.get("package_version", REMAINING_RECIPE_VERSIONS.get(style))
            != REMAINING_RECIPE_VERSIONS.get(style)):
        raise RemainingRecipeError("remaining_harness_version_not_qualified")
    parsed = urlsplit(base_url)
    if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1" or not parsed.port
            or parsed.path != "/v1" or parsed.username or parsed.password or parsed.query or parsed.fragment):
        raise RemainingRecipeError("isolated_loopback_relay_required")
    prefix = tuple(config.get("command_prefix", ()))
    model = config.get("model")
    if (not prefix or any(not isinstance(part, str) or not part or "\x00" in part for part in prefix)
            or not isinstance(model, str) or not model or model.startswith("-")
            or any(char in model for char in "\r\n\x00")):
        raise RemainingRecipeError("exact_harness_identity_required")
    workspace = Path(config.get("workspace_path", "/work"))
    task = Path(config.get("task_path", "/relay/task.txt"))
    if any(not path.is_absolute() or ".." in path.parts or any(
            item.is_symlink() for item in (path, *path.parents)) for path in (workspace, task)):
        raise RemainingRecipeError("absolute_private_paths_required")
    prompt = task.read_bytes()
    if not prompt or len(prompt) > config.get("maximum_request_bytes", 2 * 1024 * 1024):
        raise RemainingRecipeError("private_prompt_size_refused")
    allowance, capacity = config.get("output_allowance"), config.get("output_capacity")
    if type(allowance) is not int or type(capacity) is not int or not 0 < allowance <= capacity:
        raise RemainingRecipeError("explicit_output_allowance_required")
    context = config.get("context_capacity")
    if type(context) is not int or context <= 0:
        raise RemainingRecipeError("known_context_capacity_required")
    environment = {"NO_COLOR": "1", "DO_NOT_TRACK": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    if style == "crush":
        settings = {"providers": {"loop_engine": {"name": "Loop Engine", "type": "openai-compat",
            "base_url": base_url, "api_key": "loop-engine-local-relay", "discover_models": False,
            "models": [{"id": model, "name": model, "context_window": context,
                        "default_max_tokens": allowance}]}},
            "models": {kind: {"provider": "loop_engine", "model": model, "max_tokens": allowance}
                       for kind in ("large", "small")},
            "options": {"disabled_tools": list(CRUSH_DISABLED_TOOLS), "disabled_skills": ["crush-config"],
                "disable_default_providers": True, "disable_provider_auto_update": True, "disable_metrics": True,
                "disable_auto_summarize": True, "auto_lsp": False, "context_paths": [],
                "global_context_paths": [], "skills_paths": []}, "mcp": {}, "lsp": {}}
        _write(workspace / "crush.json", json.dumps(settings, ensure_ascii=False, allow_nan=False))
        return prefix + ("run", "--quiet"), environment, prompt
    if style == "forgecode":
        # Global defaults override the per-agent output field in 2.13.21.
        # An explicitly titled fresh Conversation suppresses title generation.
        home = workspace / "home/.forge"
        settings = ("subagents = false\nauto_install_vscode_extension = false\ntool_supported = false\n"
                    f"max_tokens = {allowance}\n[session]\nprovider_id = \"openai_compatible\"\n"
                    f"model_id = {json.dumps(model)}\n[updates]\nfrequency = \"never\"\nauto_update = false\n")
        _write(home / ".forge.toml", settings)
        _write(workspace / ".forge/agents/loop_engine.md", "---\nid: loop_engine\nprovider: openai_compatible\n"
               f"model: {json.dumps(model)}\ntool_supported: false\ntools: []\nmax_turns: 1\n"
               f"max_tokens: {allowance}\ncompact:\n  eviction_window: 0.0\n---\nAnswer the supplied task exactly.\n")
        environment.update(OPENAI_API_KEY="loop-engine-local-relay", OPENAI_URL=base_url, FORGE_CONFIG=str(home))
        conversation = workspace / "forge-private-conversation.json"
        _write(conversation, json.dumps({"id": str(uuid.uuid4()), "title": "Loop Engine semantic step",
            "context": None, "metrics": {}, "metadata": {
                "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": None}}))
        return prefix + ("--agent", "loop_engine", "--conversation", str(conversation)), environment, prompt
    if context < 64_000:
        raise RemainingRecipeError("hermes_requires_known_context_at_least_64000")
    if len(prefix) != 2 or not Path(prefix[1]).is_absolute() or not (Path(prefix[1]) / "hermes_cli/main.py").is_file():
        raise RemainingRecipeError("hermes_exact_python_and_source_directory_required")
    home = workspace / "home/.hermes"
    settings = {"model": {"default": model, "provider": "custom", "base_url": base_url,
        "api_key": "loop-engine-local-relay", "stream": False, "context_length": context},
        "platform_toolsets": {"cli": []}, "memory": {"memory_enabled": False, "user_profile_enabled": False},
        "compression": {"enabled": False}, "auxiliary": {"title_generation": {"enabled": False}},
        "mcp_servers": {}, "fallback_model": None}
    _write(home / "config.yaml", json.dumps(settings, ensure_ascii=False, allow_nan=False))
    # The CLI's -z argument does not merge stdin. Adapt only input transport;
    # the original main/oneshot path, configuration and agent execution run.
    wrapper = ("import sys\nsys.path.insert(0, " + repr(prefix[1]) + ")\n"
               "sys.argv=['hermes','--ignore-rules','-z',sys.stdin.read()]\n"
               "from hermes_cli.main import main\nmain()\n")
    entry = workspace / "hermes-private-entry.py"
    _write(entry, wrapper)
    environment.update(HERMES_HOME=str(home), OPENAI_API_KEY="loop-engine-local-relay",
                       OPENAI_BASE_URL=base_url, HERMES_MAX_ITERATIONS="1")
    return (prefix[0], str(entry)), environment, prompt


def extract_remaining_output(style, stdout, observed_broker_texts):
    """Match completed CLI output to a unique, actually observed broker reply.

    The selected Hermes/Forge profiles suppress titles and accept one exact
    broker string. Diagnostic Crush requires all observed texts because its
    auxiliary title can finish on either side of the answer. This does not
    authorize auxiliary requests or weaken the canonical semantic-packet gate.
    """
    if style not in REMAINING_RECIPE_VERSIONS or not isinstance(stdout, str):
        return ""
    if isinstance(observed_broker_texts, str):
        observed_broker_texts = (observed_broker_texts,)
    if not isinstance(observed_broker_texts, (tuple, list)):
        return ""
    expected = {value for value in observed_broker_texts if isinstance(value, str) and value.strip()}
    if style in ("crush", "hermes_agent"):
        candidate = stdout.strip()
    else:
        starts = list(re.finditer(r"(?m)^● \[\d{2}:\d{2}:\d{2}\] (?:Initialize|Continue) ([0-9a-f-]{36})\n", stdout))
        if len(starts) != 1:
            return ""
        start = starts[0]
        finishes = list(re.finditer(r"(?m)^● \[\d{2}:\d{2}:\d{2}\] Finished " + re.escape(start[1]) + r"\n?", stdout))
        if len(finishes) != 1 or finishes[0].start() <= start.end() or stdout[finishes[0].end():].strip():
            return ""
        candidate = stdout[start.end():finishes[0].start()].strip()
    matches = {value for value in expected if value.strip() == candidate}
    return matches.pop() if len(matches) == 1 else ""
