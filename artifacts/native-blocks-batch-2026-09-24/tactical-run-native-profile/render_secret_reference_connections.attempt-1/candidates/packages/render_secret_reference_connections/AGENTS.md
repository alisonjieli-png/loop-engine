# Render Secret-Reference Connections

## Task
Render a narrow HTTPS remote MCP connection profile for Codex (TOML) or Claude (JSON) projects.

## First Action
Invoke `tools/render_secret_reference_connections.py` via stdin with a JSON payload.

## Contract
- **Input**: JSON containing `server_id`, `url`, `env_var_name`, and `target_profile` ("codex" or "claude").
- **Output**: A JSON object with `status` ("success" or "refused"), `result` (the rendered string), or `error_code`.

## Refusal Rules
- **Secret Values**: If the input contains a value that looks like a secret (e.g., a long random string) instead of an environment variable name, refuse.
- **URL Validation**:
    - Must be `https`.
    - No `userinfo` (e.g., `https://user:pass@host`).
    - No fragments (`#`).
    - No newline characters in the URL or variable name.
- **Profile Support**: Only "codex" or "claude" are supported.
- **Types**: Reject booleans where integers are expected (e.g., if a port were added).
- **JSON Constraints**: Max 1MiB, no duplicate keys, no non-finite numbers.

## Helper Invocation
```bash
echo '{"server_id": "my-mcp", "url": "https://api.example.com", "env_var_name": "MCP_TOKEN", "target_profile": "codex"}' | python3 tools/render_secret_reference_connections.py
```
