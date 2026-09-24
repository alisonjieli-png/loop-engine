import sys
import json
from typing import Dict, List, Any, Set, Tuple

def parse_strict_json(data: str) -> Dict[str, Any]:
    """Parses JSON and checks for duplicate keys and non-finite numbers."""
    # Using a custom decoder to detect duplicate keys
    class DuplicateKeyDetector(json.JSONDecoder):
        def __init__(self, *args, **kwargs):
            super().__init__(object_pairs_hook=self.decode_pairs, *args, **kwargs)
        
        def decode_pairs(self, pairs):
            keys = []
            for k, v in pairs:
                if k in keys:
                    raise ValueError("ERR_DUPLICATE_KEY")
                keys.append(k)
            return dict(pairs)

    try:
        # Check size limit (1MiB)
        if len(data.encode('utf-8')) > 1024 * 1024:
            raise ValueError("ERR_INPUT_TOO_LARGE")
        
        obj = DuplicateKeyDetector().decode(data)
        
        # Check for non-finite numbers and type mismatches (booleans as ints)
        def walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    # Check if value is a boolean where integer is expected in specific fields
                    # The prompt says "Reject booleans where integers are required"
                    # We'll check all numeric-intended fields
                    if k in ['cost', 'priority', 'budget', 'id'] and isinstance(v, bool):
                        raise TypeError("ERR_TYPE_MISMATCH")
                    walk(v)
            elif isinstance(node, list):
                for item in node:
                    walk(item)
            elif isinstance(node, (int, float)):
                if not isinstance(node, bool) and (node == float('inf') or node == float('-inf')):
                    raise ValueError("ERR_NONFINITE_NUMBER")
        
        walk(obj)
        return obj
    except ValueError as e:
        if str(e) == "ERR_DUPLICATE_KEY":
            return {"status": "REFUSED", "code": "ERR_DUPLICATE_KEY"}
        raise e
    except TypeError as e:
        if str(e) == "ERR_TYPE_MISMATCH":
            return {"status": "REFUSED", "code": "ERR_TYPE_MISMATCH"}
        raise e
    except Exception:
        return {"status": "REFUSED", "code": "ERR_INVALID_JSON"}

def solve():
    raw_input = sys.stdin.read()
    if not raw_input:
        print(json.dumps({"status": "REFUSED", "code": "ERR_EMPTY_INPUT"}))
        return

    try:
        data = parse_strict_json(raw_input)
    except Exception:
        print(json.dumps({"status": "REFUSED", "code": "ERR_PARSE_FAILURE"}))
        return

    if isinstance(data, dict) and data.get("status") == "REFUSED":
        print(json.dumps(data))
        return

    try:
        budget = data['budget']
        sections_list = data['sections']
        
        # Map sections by ID
        sections: Dict[str, Dict] = {}
        for s in sections_list:
            sid = s['id']
            if sid in sections:
                print(json.dumps({"status": "REFUSED", "code": "ERR_DUPLICATE_ID"}))
                return
            sections[sid] = s

        # Build dependency graph
        adj = {sid: set(s.get('predecessors', [])) for sid, s in sections.items()}
        
        # Check for unknown dependencies and cycles
        for sid, preds in adj.items():
            for p in preds:
                if p not in sections:
                    print(json.dumps({"status": "REFUSED", "code": "ERR_UNKNOWN_DEPENDENCY"}))
                    return

        # Cycle detection (DFS)
        visited = set()
        path = set()
        def has_cycle(u):
            visited.add(u)
            path.add(u)
            for v in adj[u]:
                if v not in visited:
                    if has_cycle(v): return True
                elif v in path:
                    return True
            path.remove(u)
            return False

        for sid in sections:
            if sid not in visited:
                if has_cycle(sid):
                    print(json.dumps({"status": "REFUSED", "code": "ERR_CYCLIC_CONSTRAINT"}))
                    return

        # Helper to get full closure of a section
        def get_closure(sid: str) -> Set[str]:
            closure = {sid}
            stack = [sid]
            while stack:
                curr = stack.pop()
                for p in adj[curr]:
                    if p not in closure:
                        closure.add(p)
                        stack.append(p)
            return closure

        # 1. Identify mandatory sections and their required closure
        mandatory_ids = {s['id'] for s in sections_list if s.get('mandatory', False)}
        mandatory_closure = set()
        for mid in mandatory_ids:
            mandatory_closure.update(get_closure(mid))
        
        mandatory_cost = sum(sections[sid]['cost'] for sid in mandatory_closure)
        
        if mandatory_cost > budget:
            print(json.dumps({"status": "REFUSED", "code": "ERR_MANDATORY_OVER_BUDGET"}))
            return

        # 2. Add optional sections
        # Sort optional by priority DESC, then by original input order
        optional_candidates = []
        for i, s in enumerate(sections_list):
            if s['id'] not in mandatory_closure and not s.get('mandatory', False):
                optional_candidates.append((s['priority'], -i, s['id']))
        
        optional_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

        selected_ids = set(mandatory_closure)
        current_cost = mandatory_cost
        
        for _, _, sid in optional_candidates:
            closure = get_closure(sid)
            # Only add if the entire closure (not already in) fits
            new_elements = closure - selected_ids
            new_cost = sum(sections[nid]['cost'] for nid in new_elements)
            
            if current_cost + new_cost <= budget:
                selected_ids.update(new_elements)
                current_cost += new_cost

        # 3. Topological Sort for stable output order
        # We use the order of input for tie-breaking in topological sort if needed, 
        # but standard Kahn's or DFS is fine. The prompt asks for "stable topological input order".
        # This usually means if multiple nodes can be picked, pick the one that appeared first in input.
        
        in_degree = {sid: 0 for sid in selected_ids}
        sub_adj = {sid: [] for sid in selected_ids}
        for sid in selected_ids:
            for p in adj[sid]:
                if p in selected_ids:
                    # p is a predecessor of sid -> p -> sid
                    sub_adj[p].append(sid)
                    in_degree[sid] += 1
        
        # To ensure stable topological order based on input order:
        # Use a min-priority queue where priority is the original index in sections_list
        idx_map = {s['id']: i for i, s in enumerate(sections_list)}
        import heapq
        queue = []
        for sid in selected_ids:
            if in_degree[sid] == 0:
                heapq.heappush(queue, (idx_map[sid], sid))
        
        final_order = []
        while queue:
            _, u = heapq.heappop(queue)
            final_order.append(u)
            for v in sub_adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    heapq.heappush(queue, (idx_map[v], v))

        # 4. Construct Output
        assembled_text_parts = []
        selected_details = []
        current_byte_offset = 0
        
        for sid in final_order:
            text = sections[sid]['text']
            text_bytes = text.encode('utf-8')
            length = len(text_bytes)
            
            selected_details.append({
                "id": sid,
                "byte_range": [current_byte_offset, current_byte_offset + length]
            })
            assembled_text_parts.append(text)
            current_byte_offset += length

        # Note: The prompt says "Render selected sections in stable topological input order".
        # If the text is concatenated, we need to decide if there are separators. 
        # Usually, "assemble" implies direct concatenation.
        full_text = "".join(assembled_text_parts)
        # Re-calculate byte ranges on the final string to be safe with Unicode
        # but since we are concatenating, the logic above is correct.
        
        omitted_ids = [s['id'] for s in sections_list if s['id'] not in selected_ids]
        
        print(json.dumps({
            "status": "SUCCESS",
            "selected_sections": selected_details,
            "omitted_sections": omitted_ids,
            "total_units": current_cost,
            "assembled_text": full_text
        }))

    except KeyError as e:
        print(json.dumps({"status": "REFUSED", "code": f"ERR_MISSING_FIELD_{str(e)}"}))
    except Exception as e:
        print(json.dumps({"status": "REFUSED", "code": f"ERR_INTERNAL_{type(e).__name__}"}))

if __name__ == "__main__":
    solve()
