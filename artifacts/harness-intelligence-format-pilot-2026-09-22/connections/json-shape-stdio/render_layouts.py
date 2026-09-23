"""Render three isolated client layout examples for one candidate MCP server.

This writes only inside this candidate artifact. It does not install into
the real user's Codex, Claude Code, or OpenCode configuration.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "server.py"
REQUIREMENTS = ROOT / "requirements.txt"
LAYOUTS = ROOT / "layouts"
SERVER_RELATIVE = Path("tools/json_shape_mcp/server.py")
REQUIREMENTS_RELATIVE = Path("tools/json_shape_mcp/requirements.txt")

CODEX_CONFIG = """[mcp_servers.baltor_json_shape]
command = "python3"
args = ["tools/json_shape_mcp/server.py"]
"""
CLAUDE_CONFIG = json.dumps({
    "mcpServers": {"baltor_json_shape": {
        "command": "python3",
        "args": ["tools/json_shape_mcp/server.py"],
    }},
}, indent=2, sort_keys=True) + "\n"
OPENCODE_CONFIG = json.dumps({
    "$schema": "https://opencode.ai/config.json",
    "mcp": {"baltor_json_shape": {
        "type": "local",
        "command": ["python3", "tools/json_shape_mcp/server.py"],
        "cwd": ".",
        "enabled": True,
    }},
    "permission": {"baltor_json_shape_*": "ask"},
}, indent=2, sort_keys=True) + "\n"

CONFIGS = {
    "codex": (Path(".codex/config.toml"), CODEX_CONFIG),
    "claude": (Path(".mcp.json"), CLAUDE_CONFIG),
    "opencode": (Path("opencode.json"), OPENCODE_CONFIG),
}


def expected() -> dict[Path, bytes]:
    source = SOURCE.read_bytes()
    requirements = REQUIREMENTS.read_bytes()
    result = {}
    for client, (config_path, text) in CONFIGS.items():
        work = LAYOUTS / client / "work"
        result[work / SERVER_RELATIVE] = source
        result[work / REQUIREMENTS_RELATIVE] = requirements
        result[work / config_path] = text.encode("utf-8")
    return result


def _check_parent_paths(path: Path) -> None:
    cursor = ROOT
    for part in path.relative_to(ROOT).parts[:-1]:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"symlinked layout parent refused: {cursor}")
        if cursor.exists() and not cursor.is_dir():
            raise ValueError(f"layout parent is not a directory: {cursor}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--write", action="store_true")
    choice.add_argument("--check", action="store_true")
    parser.add_argument("--replace", action="store_true",
                        help="replace changed rendered files in this candidate artifact")
    args = parser.parse_args()
    try:
        if args.replace and not args.write:
            raise ValueError("--replace requires --write")
        paths = expected()
        for path, content in paths.items():
            _check_parent_paths(path)
            if path.is_symlink():
                raise ValueError(f"rendered file is a symlink: {path}")
            if args.write:
                path.parent.mkdir(parents=True, exist_ok=True)
                _check_parent_paths(path)
                if path.exists() and path.read_bytes() != content and not args.replace:
                    raise ValueError(f"changed rendered file needs --replace: {path}")
                path.write_bytes(content)
            elif not path.is_file() or path.read_bytes() != content:
                raise ValueError(f"rendered file differs from candidate source: {path}")
        print(f"{'wrote' if args.write else 'checked'} {len(paths)} candidate layout files")
    except (OSError, ValueError) as error:
        parser.exit(1, f"candidate layout refused: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
