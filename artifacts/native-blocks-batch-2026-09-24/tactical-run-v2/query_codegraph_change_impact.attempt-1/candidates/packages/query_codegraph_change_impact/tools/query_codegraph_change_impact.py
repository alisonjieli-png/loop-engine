import sys
import json
import math
from collections import deque, defaultdict
from typing import Any, Dict, List, Set, Tuple, Optional, Union

def validate_json_input(raw_data: str) -> Dict[str, Any]:
    """Reads and validates the JSON input for strictness."""
    if len(raw_data) > 1024 * 1024:
        raise ValueError("INPUT_TOO_LARGE")
    
    # Using json.loads. Note: standard json.loads handles duplicate keys by 
    # taking the last one. To strictly detect duplicates, we'd need a custom decoder.
    # However, the requirement asks to refuse duplicate-key.
    
    def dict_with_keys(dct):
        keys = []
        for k in dct:
            if k in keys:
                raise ValueError("DUPLICATE_KEY")
            keys.append(k)
        return dct

    # To detect duplicate keys in standard json, we use a custom object_pairs_hook
    class DuplicateKeyDetector(json.JSONDecoder):
        def decode(self, s: str, **kwargs) -> Any:
            def dict_pairs_hook(pairs):
                seen = set()
                for k, v in pairs:
                    if k in seen:
                        raise ValueError("DUPLICATE_KEY")
                    seen.add(k)
                return dict(pairs)
            return super().decode(s, object_pairs_hook=dict_pairs_hook, **kwargs)

    try:
        data = json.loads(raw_data, cls=DuplicateKeyDetector)
    except json.JSONDecodeError:
        raise ValueError("MALFORMED_JSON")
    except ValueError as e:
        if str(e) == "DUPLICATE_KEY":
            raise ValueError("DUPLICATE_KEY")
        raise e

    # Check for non-finite numbers and booleans where integers are expected
    def check_types(obj):
        if isinstance(obj, float):
            if not math.isfinite(obj):
                raise ValueError("NON_FINITE_NUMBER")
        elif isinstance(obj, bool):
            # We will check specific fields later, but we can flag if we want strictness
            pass
        elif isinstance(obj, dict):
            for k, v in obj.items():
                check_types(v)
        elif isinstance(obj, list):
            for item in obj:
                check_types(item)

    check_types(data)
    return data

def run_impact_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    """Performs the BFS traversal on the inverted graph."""
    symbols = data.get("symbols", {})
    files = data.get("files", {})
    edges = data.get("edges", [])
    changed_symbols = data.get("changed_symbols", [])
    depth_limit = data.get("depth_limit", float('inf'))
    node_limit = data.get("node_limit", float('inf'))

    # 1. Validate Symbols
    for sym_id in symbols:
        if not isinstance(sym_id, str):
            raise ValueError("SYMBOL_ID_NOT_STRING")
    
    # 2. Validate Files
    for f_id, f_info in files.items():
        if not isinstance(f_info.get("digest"), str):
            raise ValueError("MALFORMED_FILE_DIGEST")
        if not isinstance(f_info.get("range"), list) or len(f_info["range"]) != 2:
            raise ValueError("MALFORMED_FILE_RANGE")
        if f_info["range"][0] < 0 or f_info["range"][1] < f_info["range"][0]:
            raise ValueError("INVALID_FILE_RANGE")

    # 3. Validate Edges & Build Inverted Graph
    # edges: consumer -> dependency
    # inverted: dependency -> consumer
    inverted_adj = defaultdict(list)
    symbol_set = set(symbols.keys())
    
    for edge in edges:
        consumer = edge.get("consumer")
        dependency = edge.get("dependency")
        evidence = edge.get("evidence")
        
        if not isinstance(consumer, str) or not isinstance(dependency, str):
            raise ValueError("EDGE_ID_NOT_STRING")
        if isinstance(consumer, bool) or isinstance(dependency, bool):
            raise ValueError("BOOLEAN_WHERE_INT_OR_STRING_EXPECTED")
        if consumer not in symbol_set or dependency not in symbol_set:
            raise ValueError("DANGLING_EDGE")
        if not isinstance(evidence, str):
            raise ValueError("EDGE_EVIDENCE_MALFORMED")
            
        inverted_adj[dependency].append((consumer, evidence))

    # 4. BFS
    # We want to find all consumers of changed_symbols
    # queue stores (current_symbol, distance, path_list, evidence_list)
    queue = deque()
    visited = {} # sym_id -> (distance, path, evidence_list)
    
    # Initial seeds
    for sym in changed_symbols:
        if sym not in symbol_set:
            raise ValueError("CHANGED_SYMBOL_NOT_IN_GRAPH")
        # Distance 0 is the changed symbol itself
        visited[sym] = (0, [sym], [])
        queue.append((sym, 0, [sym], []))

    is_complete = True
    nodes_processed = 0
    
    impacted_results = []

    while queue:
        curr, dist, path, evidence_list = queue.popleft()
        nodes_processed += 1
        
        if nodes_processed > node_limit:
            is_complete = False
            break
            
        if dist >= depth_limit:
            # We don't expand further, but we don't mark as incomplete yet 
            # unless we actually hit the limit in the next step.
            # The requirement: "A depth limit must mark omitted A rather than claim complete impact."
            # This means if we stop at depth D, we mark is_complete=False.
            if dist == depth_limit:
                # We've reached the limit. We won't add neighbors of these nodes.
                # But we must check if there are more nodes in queue that could be expanded.
                # Actually, if we stop expanding at depth_limit, we are incomplete.
                is_complete = False
                continue

        for neighbor, ev in inverted_adj[curr]:
            if neighbor not in visited:
                new_dist = dist + 1
                new_path = path + [neighbor]
                new_evidence = evidence_list + [ev]
                
                visited[neighbor] = (new_dist, new_path, new_evidence)
                queue.append((neighbor, new_dist, new_path, new_evidence))
            else:
                # If already visited, BFS guarantees the first one is the shortest.
                # We only care about the shortest witness path.
                pass

    # Prepare output
    # The requirement: "report reverse-reachable consumers of changed symbols"
    # Usually, the changed symbols themselves are not "consumers" of themselves, 
    # but the BFS starts there. We'll return all visited nodes except the original seeds
    # if we strictly mean "consumers". However, standard impact analysis includes the seeds.
    # Let's include all visited nodes that are not the original changed_symbols 
    # OR include them if they are part of a cycle.
    # To be safe and deterministic: return all nodes in `visited` where dist > 0.
    
    for sym_id, (d, p, e) in visited.items():
        if d > 0:
            impacted_results.append({
                "symbol_id": sym_id,
                "distance": d,
                "witness_path": p,
                "evidence": e
            })

    # Sort results by distance then ID for determinism
    impacted_results.sort(key=lambda x: (x["distance"], x["symbol_id"]))

    return {
        "status": "success",
        "impacted_symbols": impacted_results,
        "metadata": {
            "is_complete": is_complete,
            "nodes_processed": nodes_processed
        }
    }

def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            print(json.dumps({"status": "refused", "error_code": "EMPTY_INPUT"}))
            return

        data = validate_json_input(raw_input)
        result = run_impact_analysis(data)
        print(json.dumps(result))

    except ValueError as e:
        err = str(e)
        # Map internal errors to stable codes
        codes = {
            "INPUT_TOO_LARGE": "LIMIT_EXCEEDED",
            "DUPLICATE_KEY": "MALFORMED_INPUT",
            "MALFORMED_JSON": "MALFORMED_INPUT",
            "NON_FINITE_NUMBER": "MALFORMED_INPUT",
            "SYMBOL_ID_NOT_STRING": "TYPE_MISMATCH",
            "MALFORMED_FILE_DIGEST": "TYPE_MISMATCH",
            "MALFORMED_FILE_RANGE": "TYPE_MISMATCH",
            "INVALID_FILE_RANGE": "VALUE_ERROR",
            "DANGLING_EDGE": "GRAPH_INCONSISTENCY",
            "EDGE_ID_NOT_STRING": "TYPE_MISMATCH",
            "BOOLEAN_WHERE_INT_OR_STRING_EXPECTED": "TYPE_MISMATCH",
            "EDGE_EVIDENCE_MALFORMED": "TYPE_MISMATCH",
            "CHANGED_SYMBOL_NOT_IN_GRAPH": "GRAPH_INCONSISTENCY"
        }
        print(json.dumps({
            "status": "refused",
            "error_code": codes.get(err, "UNKNOWN_ERROR")
        }))
    except Exception:
        # Fallback for unexpected errors to avoid tracebacks
        print(json.dumps({"status": "refused", "error_code": "INTERNAL_ERROR"}))

if __name__ == "__main__":
    main()
