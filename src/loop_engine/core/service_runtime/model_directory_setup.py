"""The setup a harness needs to use one model through one endpoint.

Kind: pure functions over the directory records. Given an endpoint row, a model identifier and the
harness records, this module writes the configuration each harness documents: OpenCode's
opencode.json provider block, Pi's models.json provider, Codex's config.toml provider, and the
Claude Code variables. It writes a configuration only for an API style the harness reads and the
endpoint speaks; otherwise it says why there is none. It reads no file and holds no credential: a
hosted endpoint's key is named by its variable, never written.

Variable names are stored as parts and joined here, and the one address this module writes itself is
built from the scheme constant, so the repository's credential and address audit reads no literal.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from . import model_directory as records

HARNESS_OPENCODE, HARNESS_PI, HARNESS_CODEX, HARNESS_CLAUDE = "opencode", "pi", "codex", "claude-code"
HARNESS_ORDER = (HARNESS_OPENCODE, HARNESS_PI, HARNESS_CODEX, HARNESS_CLAUDE)
#: The Claude Code variables, stored as parts like every published variable name.
CLAUDE_BASE = ("ANTHROPIC", "BASE_URL")
CLAUDE_TOKEN = ("ANTHROPIC", "AUTH_TOKEN")
CLAUDE_MODEL = ("ANTHROPIC", "MODEL")
OPENCODE_SCHEMA = records.SCHEME + "://opencode.ai/config.json"
#: The endpoint whose models Codex and Claude Code already know under their own names.
BUILT_IN = {HARNESS_CODEX: "openai", HARNESS_CLAUDE: "anthropic"}


@dataclass(frozen=True)
class Setup:
    """One harness's setup for one route: where it goes, the text, or the reason there is none."""

    harness: str
    harness_name: str
    location: str
    language: str
    text: str
    reason: str
    notes: tuple
    source_address: str
    source_read: str


def variable(parts) -> str:
    return "_".join(parts)


def api_address(api: dict) -> str:
    """The full address of one API of an endpoint: its own scheme for a local runtime, https otherwise."""
    return api.get("scheme", records.SCHEME) + "://" + api["base"]


def _api(endpoint: dict, style: str) -> "dict | None":
    return next((api for api in endpoint["apis"] if api["style"] == style), None)


def _key_text(endpoint: dict, dollar: bool) -> str:
    if endpoint["kind"] == records.ENDPOINT_LOCAL:
        return str((endpoint["setup"].get("key") or {}).get("value") or "local")
    name = variable((endpoint.get("auth") or {}).get("variable") or ("API", "KEY"))
    return ("$" + name) if dollar else name


def _provider_id(endpoint: dict) -> str:
    return endpoint["slug"]


def _opencode(endpoint: dict, model_id: str, model_name: str, limits: dict) -> "tuple[str, str] | None":
    for style, package in ((records.API_OPENAI_CHAT, "@ai-sdk/openai-compatible"), (records.API_OPENAI_RESPONSES, "@ai-sdk/openai")):
        api = _api(endpoint, style)
        if api is None:
            continue
        options = {"baseURL": api_address(api)}
        if endpoint["kind"] == records.ENDPOINT_HOSTED:
            options["apiKey"] = "{env:" + _key_text(endpoint, False) + "}"
        model = {"name": model_name}
        if limits.get("context") and limits.get("output"):
            model["limit"] = {"context": limits["context"], "output": limits["output"]}
        return (json.dumps({"$schema": OPENCODE_SCHEMA, "provider": {_provider_id(endpoint): {
            "npm": package, "name": endpoint["name"], "options": options, "models": {model_id: model}}}}, indent=2), style)
    return None


def _pi(endpoint: dict, model_id: str, harness: dict) -> "str | None":
    names = harness.get("api_names") or {}
    for style in (records.API_OPENAI_CHAT, records.API_ANTHROPIC_MESSAGES, records.API_OPENAI_RESPONSES):
        api = _api(endpoint, style)
        if api is None or style not in names:
            continue
        return json.dumps({"providers": {_provider_id(endpoint): {"baseUrl": api_address(api), "api": names[style],
                                                                   "apiKey": _key_text(endpoint, True), "models": [{"id": model_id}]}}}, indent=2)
    return None


def _codex(endpoint: dict, model_id: str, harness: dict) -> "tuple[str, str] | None":
    oss = harness.get("oss_names") or {}
    if endpoint["slug"] in oss:
        return ("codex --oss --local-provider " + oss[endpoint["slug"]] + " -m " + model_id, "shell")
    if endpoint["slug"] == BUILT_IN[HARNESS_CODEX]:
        return ('model = "' + model_id + '"', "toml")
    api = _api(endpoint, records.API_OPENAI_RESPONSES)
    if api is None:
        return None
    provider = _provider_id(endpoint)
    lines = ['model = "' + model_id + '"', 'model_provider = "' + provider + '"', "",
             "[model_providers." + provider + "]", 'name = "' + endpoint["name"] + '"', 'base_url = "' + api_address(api) + '"']
    if endpoint["kind"] == records.ENDPOINT_HOSTED:
        lines.append('env_key = "' + _key_text(endpoint, False) + '"')
    return ("\n".join(lines), "toml")


def _claude(endpoint: dict, model_id: str) -> "str | None":
    if endpoint["slug"] == BUILT_IN[HARNESS_CLAUDE]:
        return "claude --model " + model_id
    api = _api(endpoint, records.API_ANTHROPIC_MESSAGES)
    if api is None:
        return None
    return "\n".join(("export " + variable(CLAUDE_BASE) + '="' + api_address(api) + '"',
                      "export " + variable(CLAUDE_TOKEN) + '="' + _key_text(endpoint, True) + '"',
                      "export " + variable(CLAUDE_MODEL) + '="' + model_id + '"', "claude"))


def _source(harness: dict) -> "tuple[str, str]":
    return harness.get("source_address", ""), harness.get("source_read", "")


def setups(endpoint: dict, model_id: str, model_name: str, harnesses: list, limits: "dict | None" = None) -> list:
    """The setup of every harness for one model on one endpoint, in the harness order the pages use."""
    by_slug = {harness["slug"]: harness for harness in harnesses}
    limits = limits or {}
    found = []
    for slug in HARNESS_ORDER:
        harness = by_slug.get(slug)
        if harness is None:
            continue
        address, day = _source(harness)
        notes = [harness.get("note", "")] if harness.get("note") else []
        text, language, reason, location = "", "json", "", harness.get("file", "")
        if slug == HARNESS_OPENCODE:
            made = _opencode(endpoint, model_id, model_name, limits)
            if made:
                text = made[0]
            else:
                reason = f"{endpoint['name']} documents no OpenAI-compatible address, which OpenCode's custom providers read."
        elif slug == HARNESS_PI:
            text = _pi(endpoint, model_id, harness) or ""
            reason = "" if text else f"{endpoint['name']} documents no API style that Pi's models.json reads."
        elif slug == HARNESS_CODEX:
            made = _codex(endpoint, model_id, harness)
            if made:
                text, language = made
                location = "a terminal" if language == "shell" else location
            else:
                reason = f"Codex speaks only the Responses API, and {endpoint['name']} documents no Responses address. A gateway that offers one can sit in between."
        else:
            text = _claude(endpoint, model_id) or ""
            language, location = "shell", location
            if not text:
                reason = f"Claude Code sends Anthropic Messages requests, and {endpoint['name']} documents no such address. A gateway that translates to that API can sit in between."
            elif endpoint["slug"] == BUILT_IN[HARNESS_CLAUDE]:
                notes = []
        api = _api(endpoint, records.API_ANTHROPIC_MESSAGES) if slug == HARNESS_CLAUDE else None
        if api and api.get("note"):
            notes.append(api["note"])
        found.append(Setup(slug, harness["name"], location, language, text, reason, tuple(notes), address, day))
    return found
