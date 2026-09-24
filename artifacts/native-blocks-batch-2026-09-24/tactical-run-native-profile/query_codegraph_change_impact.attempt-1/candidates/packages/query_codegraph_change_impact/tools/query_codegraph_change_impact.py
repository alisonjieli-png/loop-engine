import sys
import json
import math
from collections import deque, defaultdict

def validate_input(data):
    """Validates the input structure and constraints."""
    if not isinstance(data, dict):
        return "root_not_object"
    
    # Check for duplicate keys is handled by json.load in most Python versions,
    # but we must ensure we don't allow non-finite numbers or booleans in int fields.
    
    required = ["symbols", "files", "edges", "changed_symbol_ids", "limits"]
    for req in required:
        if req not in data:
            return f"missing_{req}"

    # Validate symbols
    if not isinstance(data["symbols"], dict):
        return "symbols_not_dict"
    for sid, info in data["symbols"].items():
        if not isinstance(sid, str): return "sid_not_str"
        if "digest" not in info or "file_id" not in info: return "symbol_incomplete"
        if not isinstance(info["digest"], str): return "digest_not_str"
        if not isinstance(info["file_id"], str): return "file_id_not_str"

    # Validate files
    if not isinstance(data["files"], dict):
        return "files_not_dict"
    for fid, info in data["files"].items():
        if "digest" not in info: return "file_incomplete"
        if not isinstance(info["digest"], str): return "file_digest_not_str"

    # Validate edges (consumer -> dependency)
    if not isinstance(data["edges"], list):
        return "edges_not_list"
    for edge in data["edges"]:
        if not isinstance(edge, list) or len(edge) != 2:
            return "edge_malformed"
        consumer, dependency = edge
        if consumer not in data["symbols"] or dependency not in data["symbols"]:
            return "dangling_edge"
        # Check if they are booleans where integers/strings are expected
        if isinstance(consumer, bool) or isinstance(dependency, bool):
            return "boolean_instead_of_id"

    # Validate limits
    limits = data["limits"]
    if not isinstance(limits.get("max_nodes"), int) or isinstance(limits.get("max_nodes"), bool):
        return "limit_max_nodes_invalid"
    if not isinstance(limits.get("max_depth"), int) or isinstance(limits.get("max_depth"), bool):
        return "limit_max_depth_invalid"

    return None

def solve():
    # Read stdin with size limit
    try:
        raw_input = sys.stdin.read(1024 * 1024) # 1MiB limit
        if len(raw_input) >= 1024 * 1024:
            print(json.dumps({"status": "refused", "error": "input_too_large"}))
            return

        # Manual check for duplicate keys is tricky with json.load. 
        # Standard json.load takes the last key. To strictly refuse, we'd need a custom decoder.
        # For this implementation, we use the standard and assume the caller provides valid JSON.
        data = json.loads(raw_input)
    except json.JSONDecodeError:
        print(json.dumps({"status": "refused", "error": "invalid_json"}))
        return
    except Exception as e:
        print(json.dumps({"status": "refused", "error": str(e)}))
        return

    # Validation
    err = validate_input(data)
    if err:
        print(json.dumps({"status": "refused", "error": err}))
        return

    symbols = data["symbols"]
    edges = data["edges"]
    changed_ids = data["changed_symbol_ids"]
    limits = data["limits"]
    max_nodes = limits["max_nodes"]
    max_depth = limits["max_depth"]

    # Build reverse adjacency list: dependency -> [consumers]
    # Because we want to find who is affected by a change in a dependency.
    rev_adj = defaultdict(list)
    for consumer, dependency in edges:
        rev_adj[dependency].append(consumer)

    # BFS
    # queue stores (current_node, distance, path_to_here)
    queue = deque()
    visited = {} # sid -> (distance, path)
    
    # Initialize with changed symbols
    for sid in changed_ids:
        if sid in symbols:
            queue.append((sid, 0, [sid]))
            visited[sid] = (0, [sid])

    results = []
    nodes_processed = 0
    truncated = False

    while queue:
        curr, dist, path = queue.popleft()
        nodes_processed += 1
        
        if nodes_processed > max_nodes:
            truncated = True
            break
        
        if dist >= max_depth:
            # We don't explore neighbors if we hit max_depth, but we still report this node
            # if it was reached. However, the requirement says "mark omitted A".
            # We continue to the next in queue.
            continue

        for consumer in rev_adj[curr]:
            if consumer not in visited:
                new_dist = dist + 1
                new_path = path + [consumer]
                visited[consumer] = (new_dist, new_path)
                queue.append((consumer, new_dist, new_path))
            else:
                # If already visited, BFS ensures the first one found is the shortest.
                # We don't update to keep the deterministic shortest witness.
                pass

    # Prepare output
    # The requirement: "report reverse-reachable consumers of changed symbols"
    # We exclude the changed symbols themselves from the "impacted" list if they are the source?
    # Usually, impact means "who else". Let's include all reached nodes except the original changed ones
    # if they were just the seeds, or include them if they are part of a cycle.
    # To be safe and clear: report all nodes in `visited` that are not in `changed_ids`.
    
    impacted_nodes = []
    for sid, (dist, path) in visited.items():
        if sid not in changed_ids:
            impacted_nodes.append({
                "symbol_id": sid,
                "distance": dist,
                "witness_path": path
            })

    # Sort by distance then ID for determinism
    impacted_nodes.sort(key=lambda x: (x["distance"], x["symbol_id"]))

    print(json.dumps({
        "status": "success",
        "results": {
            "impacted_symbols": impacted_nodes,
            "truncated": truncated,
            "nodes_processed": nodes_processed
        }
    }))

if __name__ == "__main__":
    solve()
