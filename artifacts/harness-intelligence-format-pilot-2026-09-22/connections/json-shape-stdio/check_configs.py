"""Validate candidate native connection layouts without starting a client."""

from __future__ import annotations

import json
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parent
SERVER_RELATIVE = Path("tools/json_shape_mcp/server.py")
REQUIREMENTS_RELATIVE = Path("tools/json_shape_mcp/requirements.txt")
ARGUMENTS = [SERVER_RELATIVE.as_posix()]


def _server_entry(configuration: dict, client: str) -> dict:
    if client == "codex":
        expected_top = {"mcp_servers"}
        expected_entry = {"command", "args"}
        entries = configuration.get("mcp_servers")
    elif client == "claude":
        expected_top = {"mcpServers"}
        expected_entry = {"command", "args"}
        entries = configuration.get("mcpServers")
    else:
        expected_top = {"$schema", "mcp", "permission"}
        expected_entry = {"type", "command", "cwd", "enabled"}
        entries = configuration.get("mcp")
    if set(configuration) != expected_top:
        raise ValueError(f"unexpected top-level fields for {client}")
    if not isinstance(entries, dict) or set(entries) != {"baltor_json_shape"}:
        raise ValueError(f"unexpected server set for {client}")
    entry = entries["baltor_json_shape"]
    if not isinstance(entry, dict):
        raise TypeError(f"invalid server declaration for {client}")
    if set(entry) != expected_entry:
        raise ValueError(f"unexpected server fields for {client}")
    return entry


def check(root: Path = ROOT) -> dict:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("connection candidate root is missing or symlinked")
    canonical = (root / "server.py").read_bytes()
    requirements = (root / "requirements.txt").read_bytes()
    if requirements != b"mcp==1.29.0\n":
        raise ValueError("candidate dependency version differs")
    configs = {
        "codex": Path(".codex/config.toml"),
        "claude": Path(".mcp.json"),
        "opencode": Path("opencode.json"),
    }
    for client, config_path in configs.items():
        work = root / "layouts" / client / "work"
        server_copy = work / SERVER_RELATIVE
        requirements_copy = work / REQUIREMENTS_RELATIVE
        selected = work / config_path
        if server_copy.is_symlink() or requirements_copy.is_symlink() or selected.is_symlink():
            raise ValueError(f"symlinked candidate layout for {client}")
        if server_copy.read_bytes() != canonical:
            raise ValueError(f"server bytes differ in {client} layout")
        if requirements_copy.read_bytes() != requirements:
            raise ValueError(f"dependency declaration differs in {client} layout")
        raw = selected.read_bytes()
        parsed = tomllib.loads(raw.decode("utf-8")) if client == "codex" else json.loads(raw)
        entry = _server_entry(parsed, client)
        if client == "opencode":
            if (entry.get("type") != "local" or entry.get("cwd") != "."
                    or entry.get("enabled") is not True
                    or entry.get("command") != ["python3", *ARGUMENTS]
                    or parsed.get("permission") != {"baltor_json_shape_*": "ask"}):
                raise ValueError("OpenCode candidate command or permission differs")
        elif entry.get("command") != "python3" or entry.get("args") != ARGUMENTS:
            raise ValueError(f"{client} candidate command differs")
    return {"record_type": "candidate_connection_layout_check/v1",
            "clients": sorted(configs), "native_client_load": "unmeasured"}


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
