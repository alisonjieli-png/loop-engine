# baltor-json-review Plugin

This package provides a specialized tool for validating and analyzing JSON structures within a Claude Code environment. It is designed for read-only structural inspection without side effects.

## First Steps
1. **Installation**: Explicitly add the `.claude-plugin/` directory to your Claude Code plugin path. This plugin requires manual activation via version-qualified configuration.
2. **Verification**: Run `python3 scripts/check_json.py` with a small JSON string on stdin to ensure the helper is functional.
3. **Usage**: Invoke the `review-json` command or the `json-reviewer` agent to analyze local or provided JSON data.

## Contract & Refusal Rules
- **Read-Only**: The plugin never writes to the filesystem or modifies the environment.
- **Bounded Input**: Maximum input size is 1MiB.
- **Strictness**: The tool refuses JSON with duplicate keys, non-finite numbers (NaN/Inf), or a nesting depth exceeding 32.
- **Type Safety**: Booleans are treated as distinct from integers.
- **No Side Effects**: The helper script (`check_json.py`) does not perform network calls, subprocess spawns, or filesystem mutations.
