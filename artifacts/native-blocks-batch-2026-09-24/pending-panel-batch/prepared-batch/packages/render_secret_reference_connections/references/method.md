# Render Secret-Reference Connections Algorithm

## Overview
The tool converts a high-level connection intent into a specific configuration format for either Codex (TOML) or Claude (JSON). It focuses on security by ensuring that actual secret values are never passed; only the *names* of environment variables are used.

## Algorithm
1. **Read Input**: Read up to 1MiB from `stdin`.
2. **Parse JSON**: Use standard `json.loads`.
3. **Validate**:
    - Check for duplicate keys (via standard parser behavior).
    - Check for non-finite numbers (`NaN`, `Inf`).
    - Validate `server_id` and `env_var_name` are valid Python-style identifiers.
    - Validate `url` is `https`, has no `userinfo`, and no `fragment`.
    - Validate `target_profile` is in `['codex', 'claude']`.
4. **Render**:
    - **Codex**: Generate a TOML string using `[server."id"]` syntax with `bearer_token_env_var`.
    - **Claude**: Generate a JSON string with `mcpServers` structure and `Authorization: Bearer ${NAME}`.
5. **Emit**: Return a JSON object with `status` and either `result` or `error_code`.

## Conventions
- **Identifiers**: `server_id` and `env_var_name` must follow `^[a-zA-Z_][a-zA-Z0-9_]*$`.
- **Security**: The `url` must not contain credentials to prevent accidental leakage of userinfo.

## Known-Wrong Approach
- Using string interpolation (f-strings) to build TOML/JSON instead of proper serialization. This can lead to broken syntax if the `server_id` contains quotes.
- Allowing `http` instead of `https`.
- Accepting the secret value itself instead of the environment variable name.

## Limitations
- Does not verify if the environment variable actually exists at runtime.
- Does not verify if the URL is reachable.
