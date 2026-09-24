# Agent Instructions: render_secret_reference_connections

## Task
Render a narrow HTTPS remote MCP connection profile for either a Codex (TOML) or Claude (JSON) project. The goal is to create a configuration that references an environment variable for a secret, rather than embedding the secret itself.

## First Action
Invoke the helper `tools/render_secret_reference_connections.py` via `stdin` with a JSON payload containing:
- `server_id`: A unique alphanumeric identifier.
- `url`: A valid HTTPS URL (no userinfo, no fragments).
- `env_var_name`: The name of the environment variable holding the secret.
- `target_profile`: Either `"codex"` or `"claude"`.

## Contract & Refusal Rules
1. **Secret Safety**: The output must contain the `env_var_name` but **never** the actual secret value.
2. **URL Validation**: 
   - Must use `https://`.
   - Must NOT contain `user:pass@` (userinfo).
   - Must NOT contain `#` (fragments).
   - If a URL contains a newline in the variable name or userinfo, it must be refused.
3. **Profile Specifics**:
   - `codex`: Uses `bearer_token_env_var = "NAME"`.
   - `claude`: Uses `"authorization": "Bearer ${NAME}"`.
4. **Input Constraints**:
   - Max 1MiB UTF-8 JSON.
   - Reject duplicate keys in input.
   - Reject non-finite numbers (NaN, Inf).
   - Reject booleans where integers are expected.
5. **Output**: A single JSON object with `status` ("success" or "refused") and either `data` or `error_code`.
