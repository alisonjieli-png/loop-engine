import sys
import json
import math
from typing import Dict, Any, List, Optional, Union

def parse_strict_json(raw_data: str) -> Dict[str, Any]:
    """Parses JSON with strict checks for duplicates and non-finite numbers."""
    # Note: standard json.loads doesn't detect duplicate keys easily without a custom decoder
    class StrictDecoder(json.JSONDecoder):
        def __init__(self, *args, **kwargs):
            super().__init__(object_pairs_hook=self._handle_pairs, *args, **kwargs)
        
        def _handle_pairs(self, pairs):
            seen = set()
            for k, v in pairs:
                if k in seen:
                    raise ValueError(f"DUPLICATE_KEY: {k}")
                seen.add(k)
                # Check for non-finite numbers in values
                if isinstance(v, (int, float)):
                    if not math.isfinite(v):
                        raise ValueError(f"NON_FINITE_NUMBER: {v}")
                # Check for booleans where we might expect integers (though schema handles this)
                # In this specific tool, we check if a boolean is passed where a string/int is expected
                # but since we are parsing the whole blob, we check types later.
                seen.add(k)
            return dict(pairs)

    # To detect duplicates, we use a custom object_pairs_hook
    def dict_with_dup_check(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise ValueError(f"DUPLICATE_KEY: {k}")
            d[k] = v
        return d

    # We use a two-pass or custom approach to ensure we catch everything
    # Standard json.loads is used, but we must ensure we don't allow booleans in place of strings/ints
    # if the schema requires them.
    
    try:
        # We use a custom decoder to catch duplicates
        data = json.loads(raw_data, object_pairs_hook=dict_with_dup_check)
        
        # Second pass: check for non-finite numbers and booleans in specific places
        def walk_and_check(node):
            if isinstance(node, float):
                if not math.isfinite(node):
                    raise ValueError("NON_FINITE_NUMBER")
            elif isinstance(node, dict):
                for k, v in node.items():
                    walk_and_check(v)
            elif isinstance(node, list):
                for item in node:
                    walk_and_check(item)
        
        walk_and_check(data)
        return data
    except ValueError as e:
        err_msg = str(e)
        if "DUPLICATE_KEY" in err_msg:
            raise Exception(f"DUPLICATE_KEY|{err_msg}")
        if "NON_FINITE_NUMBER" in err_msg:
            raise Exception(f"NON_FINITE_NUMBER|{err_msg}")
        raise Exception(f"INVALID_JSON|{err_msg}")
    except json.JSONDecodeError as e:
        raise Exception(f"INVALID_JSON|{e.msg}")

def validate_path(path: str) -> None:
    """Validates path safety."""
    if not path or path == "." or path == "/":
        raise ValueError("UNSAFE_PATH: Empty or root")
    if ".." in path or path.startswith("/") or path.startswith("\\"):
        raise ValueError("UNSAFE_PATH: Traversal or absolute")
    # Check for case-fold collisions in the same directory level
    # This is handled in the main loop by checking the set of paths.

def plan_transitions() -> None:
    try:
        raw_input = sys.stdin.read(1024 * 1024)
        if not raw_input:
            raise Exception("INVALID_JSON|Empty input")
        
        data = parse_strict_json(raw_input)
        
        # Schema validation
        required_keys = ["base", "current", "desired"]
        for k in required_keys:
            if k not in data:
                raise Exception(f"SCHEMA_VIOLATION|Missing {k}")
        
        for k in required_keys:
            if not isinstance(data[k], dict):
                raise Exception(f"SCHEMA_VIOLATION|{k} must be a map")
            # Check for booleans where strings/nulls are expected
            for path, digest in data[k].items():
                if isinstance(digest, bool):
                    raise Exception(f"TYPE_MISMATCH|Boolean found at {path}")
                if digest is not None and not isinstance(digest, str):
                    raise Exception(f"TYPE_MISMATCH|Digest at {path} must be string")

        base = data["base"]
        current = data["current"]
        desired = data["desired"]

        # Collision checks
        all_paths = set(base.keys()) | set(current.keys()) | set(desired.keys())
        # Remove None keys if any (though dicts shouldn't have them)
        all_paths = {p for p in all_paths if p is not None}
        
        # Check for case-fold collisions and path safety
        seen_paths_lower = {}
        for p in all_paths:
            validate_path(p)
            p_lower = p.lower()
            if p_lower in seen_paths_lower:
                raise Exception(f"COLLISION|Case-fold collision: {p} and {seen_paths_lower[p_lower]}")
            seen_paths_lower[p_lower] = p

        transitions = []
        
        # The set of all unique paths across all three states
        universe = set(base.keys()) | set(current.keys()) | set(desired.keys())
        
        for path in sorted(universe):
            b = base.get(path)
            c = current.get(path)
            d = desired.get(path)
            
            # 1. Noop: current == desired
            if c == d:
                if c is not None:
                    transitions.append({
                        "path": path,
                        "op": "noop",
                        "expected_digest": c
                    })
                continue

            # 2. Create: base=null, current=null, desired=val
            if b is None and c is None and d is not None:
                transitions.append({
                    "path": path,
                    "op": "create",
                    "expected_digest": d
                })
                continue

            # 3. Update: base=val, current=val, desired=diff_val
            if b is not None and c == b and d is not None and d != b:
                transitions.append({
                    "path": path,
                    "op": "update",
                    "expected_digest": b
                })
                continue

            # 4. Delete: base=val, current=val, desired=null
            if b is not None and c == b and d is None:
                transitions.append({
                    "path": path,
                    "op": "delete",
                    "expected_digest": b
                })
                continue

            # 5. Conflict:
            # - base=A, current=B, desired=C (current changed from base, but not to desired)
            # - base=null, current=B, desired=C (current is not null, but base was null)
            # - base=A, current=B, desired=B (This is actually a noop in the logic above, 
            #   but the prompt says: "base=A,current=B,desired=B is noop". 
            #   Wait, the prompt says: "Current=desired is noop even when base differs.")
            # Let's re-evaluate the "noop" rule: "Current=desired is noop even when base differs."
            # This means if c == d, it's a noop.
            
            # If we reached here, c != d.
            # If c != b, it's a conflict (stale or independently modified).
            # Exception: if c == d, it's a noop (already handled).
            # If c != b and c != d, it's a conflict.
            # If b is null and c is not null, it's a conflict (unexpected file).
            
            transitions.append({
                "path": path,
                "op": "conflict",
                "expected_digest": b
            })

        print(json.dumps({"status": "success", "transitions": transitions}))

    except Exception as e:
        err_str = str(e)
        if "|" in err_str:
            code, msg = err_str.split("|", 1)
            print(json.dumps({"status": "refused", "error": {"code": code, "message": msg}}))
        else:
            print(json.dumps({"status": "refused", "error": {"code": "UNKNOWN", "message": err_str}}))

def plan_transitions():
    plan_transitions()

if __name__ == "__main__":
    plan_transitions()
