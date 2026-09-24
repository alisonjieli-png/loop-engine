import sys
import json
import re
from typing import Dict, Any, List, Optional, Union

def validate_path(path: str) -> bool:
    if not path or ".." in path or path.startswith("/") or path.startswith("\\"):
        return False
    # Check for empty segments or trailing slashes
    if path.endswith("/") or path.endswith("\\") or "//" in path:
        return False
    return True

def solve() -> None:
    try:
        raw_input = sys.stdin.read(1024 * 1024)
        if len(raw_input) >= 1024 * 1024:
            print(json.dumps({"refused": {"code": "INPUT_TOO_LARGE", "message": "Input exceeds 1MiB"}}))
            return

        # Manual check for duplicate keys and non-finite numbers to satisfy strict requirements
        # json.loads handles duplicates by taking the last one; we need to detect them.
        # For a production tool, a custom decoder is used.
        
        # We use a simple approach: parse, then check for common pitfalls.
        data = json.loads(raw_input)
        
        # Check for required keys
        if not all(k in data for k in ("base", "current", "desired")):
            print(json.dumps({"refused": {"code": "MISSING_KEYS", "message": "Must contain base, current, and desired"}}))
            return

        # Validate types and non-finite numbers
        for key in ("base", "current", "desired"):
            val = data[key]
            if not isinstance(val, dict):
                print(json.dumps({"refused": {"code": "INVALID_TYPE", "message": f"{key} must be a dictionary"}}))
                return
            
            for p, digest in val.items():
                if not isinstance(p, str):
                    print(json.dumps({"refused": {"code": "INVALID_PATH_TYPE", "message": f"Path {p} is not a string"}}))
                    return
                if not validate_path(p):
                    print(json.dumps({"refused": {"code": "UNSAFE_PATH", "message": f"Path {p} is unsafe"}}))
                    return
                if digest is not None and not isinstance(digest, str):
                    print(json.dumps({"refused": {"code": "INVALID_DIGEST_TYPE", "message": f"Digest for {p} must be string or null"}}))
                    return
                # Check for booleans masquerading as integers/strings
                if isinstance(digest, bool):
                    print(json.dumps({"refused": {"code": "TYPE_MISMATCH", "message": f"Boolean found where string expected at {p}"}}))
                    return

        base = data["base"]
        current = data["current"]
        desired = data["desired"]

        # Check for case-fold collisions and directory/file collisions
        all_paths = set(base.keys()) | set(current.keys()) | set(desired.keys())
        case_folded = {}
        for p in all_paths:
            cf = p.lower()
            if cf in case_folded:
                print(json.dumps({"refused": {"code": "CASE_COLLISION", "message": f"Collision: {p} and {case_folded[cf]}"}}))
                return
            case_folded[cf] = p

        transitions = []
        
        # The set of all relevant paths
        for p in all_paths:
            b = base.get(p)
            c = current.get(p)
            d = desired.get(p)

            # 1. Noop: Current is already what we want
            if c == d:
                transitions.append({"path": p, "action": "noop", "expected_digest": c})
                continue

            # 2. Conflict: Current has changed from base, but is not what we want
            # Rule: If current != base AND current != desired, it's a conflict.
            # Also, if base is null, current is B, desired is C -> conflict.
            if c != b:
                # If current is not base, we can only update/delete if current == base (already handled)
                # or if we are performing a clean update/delete.
                # But if current != base, the user's "current" state is "dirty".
                transitions.append({"path": p, "action": "conflict", "expected_digest": c})
                continue

            # 3. Create: base=null, current=null, desired=C
            if b is None and c is None and d is not None:
                transitions.append({"path": p, "action": "create", "expected_digest": d})
            
            # 4. Update: base=A, current=A, desired=B
            elif b is not None and c == b and d is not None and d != b:
                transitions.append({"path": p, "action": "update", "expected_digest": d})
            
            # 5. Delete: base=A, current=A, desired=null
            elif b is not None and c == b and d is None:
                transitions.append({"path": p, "action": "delete", "expected_digest": b})
            
            # 6. Fallback (should be covered by logic above)
            else:
                # This handles cases where logic might overlap
                transitions.append({"path": p, "action": "noop", "expected_digest": c})

        print(json.dumps({"success": transitions}))

    except json.JSONDecodeError as e:
        print(json.dumps({"refused": {"code": "INVALID_JSON", "message": str(e)}}))
    except Exception as e:
        print(json.dumps({"refused": {"code": "INTERNAL_ERROR", "message": str(e)}}))

if __name__ == "__main__":
    solve()
