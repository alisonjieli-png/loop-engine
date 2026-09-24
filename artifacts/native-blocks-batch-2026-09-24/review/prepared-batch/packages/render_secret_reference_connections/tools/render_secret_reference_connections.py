import sys
import json
from urllib.parse import urlparse

def validate_input(data):
    """Validates the input dictionary according to strict rules."""
    # Check for non-finite numbers or booleans in place of integers
    # Note: json.loads handles basic types, but we check logic
    
    required = {"server_id", "url", "env_var_name", "target_profile"}
    if not all(k in data for k in required):
        return "MISSING_FIELDS"

    server_id = data["server_id"]
    url_str = data["url"]
    env_name = data["env_var_name"]
    profile = data["target_profile"]

    # Validate server_id (alphanumeric + underscores/hyphens)
    if not isinstance(server_id, str) or not server_id.replace("_", "").replace("-", "").isalnum():
        return "INVALID_SERVER_ID"

    # Validate env_var_name
    if not isinstance(env_name, str) or not env_name.isidentifier():
        return "INVALID_ENV_VAR_NAME"

    # Validate URL
    try:
        parsed = urlparse(url_str)
        if parsed.scheme != "https":
            return "INVALID_SCHEME"
        if parsed.netloc != parsed.hostname: # Check for userinfo (user:pass@host)
            return "URL_HAS_USERINFO"
        if parsed.fragment:
            return "URL_HAS_FRAGMENT"
        if not parsed.netloc:
            return "INVALID_URL_HOST"
        # Check for newline in URL string
        if "\n" in url_str:
            return "URL_HAS_NEWLINE"
    except Exception:
        return "INVALID_URL_FORMAT"

    if profile not in ["codex", "claude"]:
        return "UNSUPPORTED_PROFILE"

    return None

def parse_json_strict(raw_bytes):
    """Parses JSON with duplicate key and non-finite number detection."""
    # Standard json.loads allows duplicate keys (last one wins). 
    # To detect them, we use object_pairs_hook.
    
    def dict_with_order(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise ValueError("DUPLICATE_KEY")
            d[k] = v
        return d

    # Check for non-finite numbers manually or via a custom decoder
    # For simplicity in a single file, we check the raw string for NaN/Inf 
    # which are technically valid in some JSON parsers but often disallowed.
    # However, standard json.loads handles them. We want to reject them.
    
    # A more robust way is to check the parsed values.
    try:
        # We use a custom decoder to catch duplicates
        data = json.loads(raw_bytes, object_pairs_hook=dict_with_order)
        
        # Check for non-finite numbers
        def check_finite(obj):
            if isinstance(obj, float):
                if not (float('-inf') < obj < float('inf')):
                    raise ValueError("NON_FINITE_NUMBER")
            elif isinstance(obj, dict):
                for v in obj.values(): check_finite(v)
            elif isinstance(obj, list):
                for v in obj: check_finite(v)
        
        check_finite(data)
        return data, None
    except ValueError as e:
        if str(e) == "DUPLICATE_KEY":
            return None, "DUPLICATE_KEY"
        if str(e) == "NON_FINITE_NUMBER":
            return None, "NON_FINITE_NUMBER"
        return None, "INVALID_JSON"
    except Exception:
        return None, "INVALID_JSON"

def main():
    try:
        raw_input = sys.stdin.buffer.read(1024 * 1024) # 1MiB limit
        if not raw_input:
            print(json.dumps({"status": "refused", "error_code": "EMPTY_INPUT"}))
            return

        data, err = parse_json_strict(raw_input)
        if err:
            print(json.dumps({"status": "refused", "error_code": err}))
            return

        # Check if env_var_name is a boolean where string expected
        if not isinstance(data.get("env_var_name"), str):
             print(json.dumps({"status": "refused", "error_code": "INVALID_TYPE_ENV_VAR"}))
             return

        validation_err = validate_input(data)
        if validation_err:
            print(json.dumps({"status": "refused", "error_code": validation_err}))
            return

        # Rendering
        profile = data["target_profile"]
        url = data["url"]
        env_name = data["env_var_name"]
        server_id = data["server_id"]

        if profile == "codex":
            # Codex uses TOML format
            # We simulate the structure. Since we must emit JSON, 
            # we return the data that would be serialized to TOML.
            result = {
                "server_id": server_id,
                "url": url,
                "bearer_token_env_var": env_name
            }
        else: # claude
            # Claude uses JSON format
            result = {
                "server_id": server_id,
                "url": url,
                "authorization": f"Bearer ${{{env_name}}}"
            }

        print(json.dumps({"status": "success", "data": result}))

    except Exception as e:
        # Catch-all for unexpected errors to ensure stable output
        print(json.dumps({"status": "refused", "error_code": "INTERNAL_ERROR"}))

if __name__ == "__main__":
    main()
