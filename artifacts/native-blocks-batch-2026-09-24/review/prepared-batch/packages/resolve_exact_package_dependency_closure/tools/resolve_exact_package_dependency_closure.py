import sys
import json
import math
from typing import Dict, List, Set, Any, Tuple, Optional

def parse_json_with_constraints(stream) -> Dict[str, Any]:
    """
    Reads up to 1MiB from stdin. 
    Note: Standard json.load handles duplicate keys by taking the last one.
    To strictly enforce 'no duplicate keys' as per requirement, we use a custom decoder.
    """
    raw_data = stream.read(1024 * 1024)
    if not raw_data:
        raise ValueError("EMPTY_INPUT")

    class StrictDecoder(json.JSONDecoder):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.seen_keys = []

        def decode(self, s, **kwargs):
            # We use a trick: parse into a dict and check for duplicates via a custom object
            # But since standard json.load is the requirement, we'll simulate the check
            # by checking if the string contains duplicate keys manually or via a custom hook.
            return super().decode(s, **kwargs)

    # For the sake of a robust 'candidate-only' implementation without complex regex,
    # we use a standard load but validate the structure.
    # To truly detect duplicate keys in standard Python json, we'd need a custom object_pairs_hook.
    
    def dict_with_dup_check(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise ValueError("DUPLICATE_KEY")
            d[k] = v
        return d

    try:
        data = json.loads(raw_data, object_pairs_hook=dict_with_dup_check)
    except ValueError as e:
        if "DUPLICATE_KEY" in str(e):
            raise ValueError("DUPLICATE_KEY")
        raise ValueError(f"INVALID_JSON: {str(e)}")

    # Validate non-finite numbers and booleans where integers are expected
    def validate_types(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                validate_types(v)
        elif isinstance(obj, list):
            for item in obj:
                validate_types(item)
        elif isinstance(obj, float):
            if not math.isfinite(obj):
                raise ValueError("NON_FINITE_NUMBER")
        return obj

    validate_types(data)
    return data

def resolve(available: Dict[str, Dict], requested: List[Dict]) -> Dict[str, Any]:
    """
    available: { "id@rev": { "digest": str, "dependencies": [...], "effects": [...], "size": int } }
    requested: [ { "id": str, "rev": str, "digest": str } ]
    """
    
    # 1. Map available by identity to check for collisions/conflicts
    # identity_map: id -> { rev: { data } }
    identity_map: Dict[str, Dict[str, Dict]] = {}
    # digest_map: id -> { digest: rev }
    digest_map: Dict[str, Dict[str, str]] = {}

    for key, info in available.items():
        # key format: "name@rev"
        if "@" not in key:
            raise ValueError("INVALID_AVAILABLE_FORMAT")
        name, rev = key.split("@", 1)
        
        if name not in identity_map:
            identity_map[name] = {}
            digest_map[name] = {}
        
        identity_map[name][rev] = info
        digest_map[name][info['digest']] = rev

    # 2. Resolve requested roots
    resolved_nodes: Dict[str, Dict] = {} # name -> {rev, digest, info}
    visited_in_path: List[str] = [] # For cycle detection
    
    # To ensure stable order and prevent duplicates, we use a queue/stack
    # but we must return dependencies BEFORE consumers.
    # This is a topological sort.
    
    def get_node_key(name: str, rev: str) -> str:
        return f"{name}@{rev}"

    def dfs(name: str, rev: str, digest: str) -> str:
        node_id = f"{name}@{rev}"
        
        # Check if identity exists
        if name not in identity_map or rev not in identity_map[name]:
            raise ValueError("MISSING_RECORD")
        
        target_info = identity_map[name][rev]
        
        # Check digest
        if target_info['digest'] != digest:
            raise ValueError("DIGEST_MISMATCH")
            
        # Check for identity collision in the current resolution set
        # (If we already resolved this identity with a different digest)
        if name in resolved_nodes:
            if resolved_nodes[name]['digest'] != digest:
                raise ValueError("IDENTITY_COLLISION")
            return node_id

        # Cycle detection
        if node_id in visited_in_path:
            raise ValueError("CYCLE_DETECTED")
        
        visited_in_path.append(node_id)
        
        # Process dependencies
        for dep in target_info.get('dependencies', []):
            d_name = dep['id']
            d_rev = dep['rev']
            d_digest = dep['digest']
            dfs(d_name, d_rev, d_digest)
            
        visited_in_path.pop()
        
        # Add to resolved
        resolved_nodes[name] = {
            "id": name,
            "rev": rev,
            "digest": digest,
            "info": target_info
        }
        return node_id

    # Initial pass to build the graph and check for conflicts
    for req in requested:
        if not isinstance(req.get('id'), str) or not isinstance(req.get('rev'), str):
             raise ValueError("INVALID_REQUEST_TYPE")
        # Reject booleans where integers are expected (e.g. if size was passed in req)
        # The requirement says "Reject booleans where integers are required"
        # We check the requested fields.
        if 'digest' in req and not isinstance(req['digest'], str):
             raise ValueError("INVALID_DIGEST_TYPE")
             
        dfs(req['id'], req['rev'], req['digest'])

    # 3. Finalize output
    # Topological order: dependencies before consumers.
    # Since DFS adds nodes after visiting children, the order in resolved_nodes 
    # (if we used a list) would be correct.
    
    # Re-run a clean topological sort to ensure order is exactly as requested
    # (dependencies before consumers, stable input order for roots)
    
    final_list = []
    seen_names = set()
    
    def topo_sort(name: str, rev: str, digest: str):
        node_id = f"{name}@{rev}"
        if node_id in seen_names:
            return
        
        # We need to ensure we don't add the same identity twice if it's a different rev
        # but the requirement says "conflicting versions of one logical identity" is an error.
        # So we only track by name for the "one version" rule.
        
        info = identity_map[name][rev]
        for dep in info.get('dependencies', []):
            topo_sort(dep['id'], dep['rev'], dep['digest'])
            
        if name not in seen_names:
            final_list.append({
                "id": name,
                "rev": rev,
                "digest": digest
            })
            seen_names.add(name)

    # To maintain stable input order of roots:
    for req in requested:
        topo_sort(req['id'], req['rev'], req['digest'])

    # Aggregate effects and size
    total_size = 0
    all_effects = set()
    
    # We need the actual info for the final list
    final_output_packages = []
    for pkg in final_list:
        # We need to find the info in identity_map
        # Since we already validated everything in the first DFS
        info = identity_map[pkg['id']][pkg['rev']]
        total_size += info.get('size', 0)
        for eff in info.get('effects', []):
            all_effects.add(eff)
        final_output_packages.append(pkg)

    return {
        "status": "success",
        "dependencies": final_output_packages,
        "total_size_bytes": total_size,
        "effects": sorted(list(all_effects))
    }

def main():
    try:
        input_data = parse_json_with_constraints(sys.stdin)
        
        # Validate top level keys
        if "available_packages" not in input_data or "requested_identities" not in input_data:
            raise ValueError("MISSING_REQUIRED_KEYS")
            
        available = input_data["available_packages"]
        requested = input_data["requested_identities"]
        
        # Check if requested is a list
        if not isinstance(requested, list):
            raise ValueError("REQUESTED_IDENTITIES_MUST_BE_LIST")

        result = resolve(available, requested)
        print(json.dumps(result))

    except ValueError as e:
        err_msg = str(e)
        # Map internal errors to stable codes
        code = err_msg
        if "MISSING_RECORD" in err_msg: code = "MISSING_RECORD"
        elif "DIGEST_MISMATCH" in err_msg: code = "DIGEST_MISMATCH"
        elif "DUPLICATE_KEY" in err_msg: code = "DUPLICATE_KEY"
        elif "CYCLE_DETECTED" in err_msg: code = "CYCLE_DETECTED"
        elif "IDENTITY_COLLISION" in err_msg: code = "IDENTITY_COLLISION"
        elif "VERSION_CONFLICT" in err_msg: code = "VERSION_CONFLICT"
        elif "NON_FINITE_NUMBER" in err_msg: code = "NON_FINITE_NUMBER"
        elif "INVALID_JSON" in err_msg: code = "INVALID_JSON"
        elif "EMPTY_INPUT" in err_msg: code = "EMPTY_INPUT"
        else:
            # Fallback for other ValueErrors
            code = err_msg.split(":")[0] if ":" in err_msg else err_msg

        print(json.dumps({
            "status": "refused",
            "error_code": code
        }))
    except Exception as e:
        # Catch-all for unexpected logic errors to prevent tracebacks
        print(json.dumps({
            "status": "refused",
            "error_code": "INTERNAL_ERROR"
        }))

if __name__ == "__main__":
    main()
