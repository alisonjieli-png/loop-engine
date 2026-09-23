"""Declared effects of an outside item, derived from what its steps ask for.

An item declares every effect one of its steps asks the reader to perform:
running a command, reading or writing files, using the network or reading
a secret. The effect names are the engine's own (core.facets.EFFECTS). A
skill's requested tools count, because a request names what the author
expects even though it grants nothing. The rules over-declare on purpose:
an item that declares more than it needs is only withheld from a step that
lacks the authority, while one that declares less would be offered where it
cannot run safely. Each effect keeps the rule that declared it, for review.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..facets import EFFECTS

_TOOL_EFFECTS = {"bash": "spawns_process", "shell": "spawns_process", "exec": "spawns_process",
                 "powershell": "spawns_process", "read": "reads_fs", "glob": "reads_fs",
                 "grep": "reads_fs", "ls": "reads_fs", "write": "writes_fs", "edit": "writes_fs",
                 "multiedit": "writes_fs", "notebookedit": "writes_fs", "webfetch": "network",
                 "websearch": "network", "fetch": "network"}
_SHELL_FENCE = re.compile(r"^\s*(?:```|~~~)\s*(?:bash|sh|shell|zsh|console|terminal|powershell|pwsh|ps1|cmd|bat)\b",
                          re.I | re.M)
_COMMANDS = r"(?:npm|npx|pnpm|yarn|pip|pip3|uv|uvx|git|make|docker|python3?|node|cargo|go|pytest|bun|deno|kubectl|terraform|brew|apt|curl|wget|gh|sh|bash)"
_COMMAND_LINE = re.compile(rf"(?:^\s*\$\s+\S|`{_COMMANDS}\s[^`]*`|^\s*{_COMMANDS}\s+\S)", re.M)
_NETWORK = re.compile(r"\b(?:curl|wget|git\s+clone|git\s+pull|git\s+push|docker\s+pull|pip3?\s+install|npm\s+install|"
                      r"npx\s|uvx\s|pnpm\s+add|yarn\s+add|cargo\s+install|go\s+get|http\s+request|webfetch|"
                      r"websearch|fetch\()", re.I)
_READS = re.compile(r"(?:\b(?:cat|grep|rg|find|ls|head|tail|less)\s+\S|\bread\s+(?:the|each|every|all)\s+"
                    r"(?:file|files|source|logs?)\b|\bopen\s+the\s+file\b)", re.I)
_WRITES = re.compile(r"(?:\s>{1,2}\s*[\w./-]+|\btee\s+\S|\bmkdir\s|\btouch\s|\b(?:write|save|create)\s+"
                     r"(?:the|a|an|this|that|each|every)?\s*(?:new\s+)?(?:file|files|folder|directory)\b)", re.I)
_SECRETS = re.compile(r"(?:\b[A-Z][A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD|CREDENTIALS?)\b|\.env\b|"
                      r"\bcredentials?\s+file\b|\bsecret\s+manager\b)")
_ORDER = {name: index for index, name in enumerate(EFFECTS)}


@dataclass(frozen=True)
class DeclaredEffects:
    effects: tuple
    evidence: tuple


def _tool_names(allowed) -> list:
    if isinstance(allowed, (list, tuple)):
        allowed = " ".join(str(item) for item in allowed)
    return [re.split(r"[(:]", token)[0].strip().lower() for token in str(allowed or "").replace(",", " ").split()
            if token.strip()]


def declared_effects(kind: str, text: str, frontmatter: dict, *, connection: "dict | None" = None) -> DeclaredEffects:
    """The effects one item declares, each with the rule that declared it."""
    found: dict = {}

    def add(effect: str, rule: str) -> None:
        found.setdefault(effect, rule)

    if connection is not None:
        transport = (connection.get("server") or {}).get("transport")
        if transport == "stdio":
            add("spawns_process", "starts_a_local_server_process")
            add("network", "downloads_the_server_package")
        else:
            add("network", "reaches_a_remote_server")
        if any(row.get("secret") for row in connection.get("inputs", ())):
            add("reads_secret", "passes_a_secret_input")
    for tool in _tool_names(frontmatter.get("allowed-tools")):
        if tool in _TOOL_EFFECTS:
            add(_TOOL_EFFECTS[tool], f"requests_tool_{tool}")
    if _SHELL_FENCE.search(text) or _COMMAND_LINE.search(text):
        add("spawns_process", "shows_a_command_to_run")
    if _NETWORK.search(text):
        add("network", "uses_the_network")
    if _READS.search(text):
        add("reads_fs", "reads_files")
    if _WRITES.search(text):
        add("writes_fs", "writes_files")
    if _SECRETS.search(text):
        add("reads_secret", "names_a_secret")
    effects = tuple(sorted(found, key=_ORDER.__getitem__))
    return DeclaredEffects(effects, tuple({"effect": effect, "rule": found[effect]} for effect in effects))
