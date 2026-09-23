"""Engine connection_builtin_rules of the library_format_validation engine slot.

It checks the three connection files of one package against each harness's
documented shape, with no library beyond a TOML reader: Claude Code's
.mcp.json holds mcpServers, each server a stdio command with arguments and
environment references, or an http or sse address with headers; Codex's
config.toml holds one mcp_servers table with a command, arguments and
forwarded variable names, or a streamable HTTP address and header names;
OpenCode's opencode.json holds mcp, each server local with a command list
or remote with an address. Every address is HTTPS, every key is known, and
no file carries a value that has the shape of a secret. The published JSON
schemas of Codex and OpenCode are checked by a separate engine.
"""
from __future__ import annotations

import json
import re

from .connection_rendering import credential_shaped
from .https_transport import HTTPS_SCHEME, split_address

try:
    import tomllib as _toml
except ImportError:  # Python 3.10 reads TOML through the tomli package the environment ships
    import tomli as _toml

#: Each harness's word for a server it starts itself.
_CLAUDE_LOCAL, _OPENCODE_LOCAL = "stdio", "local"
_CLAUDE_KEYS = {_CLAUDE_LOCAL: {"type", "command", "args", "env"}, "http": {"type", "url", "headers"},
                "sse": {"type", "url", "headers"}}
_CODEX_KEYS = {"command", "args", "env_vars", "url", "http_headers", "env_http_headers"}
_OPENCODE_KEYS = {_OPENCODE_LOCAL: {"type", "command", "enabled", "environment"},
                  "remote": {"type", "url", "enabled", "headers"}}
_REFERENCE = re.compile(r"(?:\$\{[A-Za-z_][A-Za-z0-9_]*\}|\{env:[A-Za-z_][A-Za-z0-9_]*\})")


def _text_map(value) -> bool:
    return isinstance(value, dict) and all(isinstance(key, str) and isinstance(item, str)
                                           for key, item in value.items())


def _text_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item for item in value)


def _https(url) -> bool:
    if not isinstance(url, str):
        return False
    parts = split_address(url)
    return parts.scheme == HTTPS_SCHEME and bool(parts.hostname)


class ConnectionFileRules:
    """The documented shape of each harness's connection file, checked without a schema library."""

    engine_id = "connection_builtin_rules"
    engine_version = "1.0.0"
    engine_kind = "format_rules"
    effects = ("pure",)
    third_party = "tomllib or tomli to read TOML; rules written here from each harness's documentation"
    applies_to = ("tool",)

    @classmethod
    def availability(cls, settings: dict):
        return True, "always_available"

    @classmethod
    def from_settings(cls, settings: dict, resources: dict):
        """Construct from declared settings and the run's resources; nothing starts here."""
        return cls()

    def describe(self) -> dict:
        return {"engine_id": self.engine_id, "engine_version": self.engine_version,
                "engine_kind": self.engine_kind, "applies_to": list(self.applies_to)}

    def validate_package(self, document: dict) -> list:
        problems = []
        key = document.get("key")
        files = {row["harness"]: row["text"] for row in document.get("files", ())}
        for harness, text in files.items():
            if credential_shaped(text):
                problems.append(f"{harness}: a value has the shape of a secret")
        if "claude_code" in files:
            problems += self._claude(files["claude_code"], key)
        else:
            problems.append("claude_code: the file is missing")
        if "opencode" in files:
            problems += self._opencode(files["opencode"], key)
        else:
            problems.append("opencode: the file is missing")
        if "codex" in files:
            problems += self._codex(files["codex"], key)
        secret = [row for row in document.get("inputs", ()) if row.get("secret")]
        for row in secret:
            for harness, text in files.items():
                if row["name"] not in text:
                    problems.append(f"{harness}: the secret input {row['name']} is not referenced")
        return problems

    def _claude(self, text: str, key: str) -> list:
        try:
            servers = json.loads(text)["mcpServers"]
            entry = servers[key]
        except (ValueError, KeyError, TypeError):
            return ["claude_code: the file is not an mcpServers object holding the server key"]
        kind = entry.get("type") if isinstance(entry, dict) else None
        if kind not in _CLAUDE_KEYS or set(entry) - _CLAUDE_KEYS[kind] or len(servers) != 1:
            return ["claude_code: the server entry has an unknown type or field"]
        if kind == _CLAUDE_LOCAL:
            ok = (isinstance(entry.get("command"), str) and entry["command"] and _text_list(entry.get("args", []))
                  and _text_map(entry.get("env", {}))
                  and all(_REFERENCE.fullmatch(value) for value in entry.get("env", {}).values()))
        else:
            ok = _https(entry.get("url")) and _text_map(entry.get("headers", {}))
        return [] if ok else ["claude_code: the server entry breaks the documented shape"]

    def _opencode(self, text: str, key: str) -> list:
        try:
            servers = json.loads(text)["mcp"]
            entry = servers[key]
        except (ValueError, KeyError, TypeError):
            return ["opencode: the file is not an mcp object holding the server key"]
        kind = entry.get("type") if isinstance(entry, dict) else None
        if kind not in _OPENCODE_KEYS or set(entry) - _OPENCODE_KEYS[kind] or len(servers) != 1:
            return ["opencode: the server entry has an unknown type or field"]
        if kind == _OPENCODE_LOCAL:
            ok = (_text_list(entry.get("command")) and entry.get("enabled") is True
                  and _text_map(entry.get("environment", {}))
                  and all(_REFERENCE.fullmatch(value) for value in entry.get("environment", {}).values()))
        else:
            ok = _https(entry.get("url")) and entry.get("enabled") is True and _text_map(entry.get("headers", {}))
        return [] if ok else ["opencode: the server entry breaks the documented shape"]

    def _codex(self, text: str, key: str) -> list:
        try:
            table = _toml.loads(text)["mcp_servers"][key]
        except (_toml.TOMLDecodeError, KeyError, TypeError):
            return ["codex: the file is not an mcp_servers table holding the server key"]
        if set(table) - _CODEX_KEYS:
            return ["codex: the table has an unknown key"]
        if "command" in table:
            ok = (isinstance(table["command"], str) and _text_list(table.get("args", []))
                  and _text_list(table.get("env_vars", [])) and "url" not in table)
        else:
            ok = (_https(table.get("url")) and _text_map(table.get("http_headers", {}))
                  and _text_map(table.get("env_http_headers", {})))
        return [] if ok else ["codex: the table breaks the documented shape"]
