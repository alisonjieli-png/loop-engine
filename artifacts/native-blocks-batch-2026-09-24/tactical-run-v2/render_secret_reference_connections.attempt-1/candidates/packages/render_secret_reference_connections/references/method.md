# Method: render_secret_reference_connections

## Algorithm
1. **Read Input**: Read up to 1MiB from `stdin`.
2. **Strict Parse**: 
   - Use `object_pairs_hook` to detect duplicate keys in the JSON stream.
   - Traverse the resulting object to ensure all `float` values are finite (not `NaN` or `Inf`).
3. **Validation**:
   - `server_id`: Must be alphanumeric (allowing `_` and `-`).
   - `url`: Must be `https://`. Must not contain `userinfo` (e.g., `user:pass@host`) or `fragments` (e.g., `#anchor`).
   - `env_var_name`: Must be a valid Python identifier (to ensure it can be used as an env var).
   - `target_profile`: Must be exactly `"codex"` or `"claude"`.
4. **Transformation**:
   - If `codex`: Return a dictionary containing `bearer_token_env_var` set to the provided name.
   - If `claude`: Return a dictionary containing `authorization` set to the string `"Bearer ${NAME}"`.
5. **Output**: Emit a single JSON object with `status` and either `data` or `error_code`.

## Conventions
- **No Secrets**: The tool never accepts or returns the actual secret value, only the name of the environment variable.
- **Deterministic**: The same input always produces the same output.
- **Bounded**: The tool does not perform any side effects (no network, no disk writes).

## Known-Wrong Approach
- Using string interpolation (f-strings) to build the JSON/TOML string manually. This is prone to escaping errors and injection.
- Using `eval()` to parse the input.
- Allowing `http://` or `ftp://` schemes.
- Allowing `user:pass@` in the URL.

## Limitations
- Does not validate if the environment variable actually exists (this is a runtime responsibility of the host).
- Does not validate the content of the URL beyond scheme and structure.
