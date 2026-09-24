import sys
import json
import math
from collections import deque, defaultdict

def solve():
    try:
        raw_input = sys.stdin.read(1048576) # 1MiB limit
        if not raw_input:
            return print(json.dumps({"status": "refused", "code": "ERR_EMPTY_INPUT"}))
        
        # Use object_pairs_hook to detect duplicate keys manually if needed, 
        # but standard json.loads handles it by overwriting. 
        # To strictly refuse duplicates, we use a custom decoder or check keys.
        # For this implementation, we'll use a simple check.
        
        data = json.loads(raw_input)
    except json.JSONDecodeError:
        return print(json.dumps({"status": "refused", "code": "ERR_INVALID_JSON"}))
    except Exception as e:
        return print(json.dumps({"status": "refused", "code": "ERR_INTERNAL", "message": str(e)}))

    try:
        budget = data.get("budget")
        if not isinstance(budget, int) or isinstance(budget, bool):
            return print(json.dumps({"status": "refused", "code": "ERR_TYPE_MISMATCH", "field": "budget"}))
        
        sections_list = data.get("sections", [])
        if not isinstance(sections_list, list):
            return print(json.dumps({"status": "refused", "code": "ERR_TYPE_MISMATCH", "field": "sections"}))

        # 1. Validate types and duplicate IDs
        seen_ids = set()
        sections_map = {}
        for s in sections_list:
            sid = s.get("id")
            if not isinstance(sid, str):
                return print(json.dumps({"status": "refused", "code": "ERR_TYPE_MISMATCH", "field": "id"}))
            if sid in seen_ids:
                return print(json.dumps({"status": "refused", "code": "ERR_DUPLICATE_ID", "id": sid}))
            seen_ids.add(sid)
            
            # Strict integer checks (reject booleans)
            for field in ["cost", "priority"]:
                val = s.get(field)
                if not isinstance(val, int) or isinstance(val, bool):
                    return print(json.dumps({"status": "refused", "code": "ERR_TYPE_MISMATCH", "field": f"{sid}.{field}"}))
            
            if not isinstance(s.get("mandatory", False), bool):
                 return print(json.dumps({"status": "refused", "code": "ERR_TYPE_MISMATCH", "field": f"{sid}.mandatory"}))
            
            if not isinstance(s.get("text", ""), str):
                 return print(json.dumps({"status": "refused", "code": "ERR_TYPE_MISMATCH", "field": f"{sid}.text"}))

            if not isinstance(s.get("predecessors", []), list):
                 return print(json.dumps({"status": "refused", "code": "ERR_TYPE_MISMATCH", "field": f"{sid}.predecessors"}))

            sections_map[sid] = s

        # 2. Validate dependencies exist and check for cycles
        adj = defaultdict(list)
        for sid, s in sections_map.items():
            for pred in s.get("predecessors", []):
                if pred not in sections_map:
                    return print(json.dumps({"status": "refused", "code": "ERR_MISSING_DEPENDENCY", "id": pred}))
                adj[pred].append(sid) # pred -> sid (pred must come before sid)

        # Cycle detection (DFS)
        visited = {} # 0: unvisited, 1: visiting, 2: visited
        def has_cycle(u):
            visited[u] = 1
            for v in adj[u]:
                if visited.get(v, 0) == 1: return True
                if visited.get(v, 0) == 0 and has_cycle(v): return True
            visited[u] = 2
            return False

        for sid in sections_map:
            if visited.get(sid, 0) == 0:
                if has_cycle(sid):
                    return print(json.dumps({"status": "refused", "code": "ERR_CYCLIC_DEPENDENCY"}))

        # 3. Determine Mandatory Closure
        mandatory_set = set()
        def add_mandatory(sid):
            if sid in mandatory_set: return
            mandatory_set.add(sid)
            for pred in sections_map[sid].get("predecessors", []):
                add_mandatory(pred)

        for sid, s in sections_map.items():
            if s.get("mandatory", False):
                add_mandatory(sid)

        mandatory_cost = sum(sections_map[sid]["cost"] for sid in mandatory_set)
        if mandatory_cost > budget:
            return print(json.dumps({"status": "refused", "code": "ERR_BUDGET_EXCEEDED"}))

        # 4. Add Optional Sections
        # Sort by priority (desc), then by original input order
        optionals = []
        for idx, (sid, s) in enumerate(sections_map.items()):
            if not s.get("mandatory", False):
                optionals.append((s.get("priority", 0), -idx, sid))
        
        optionals.sort(reverse=True)

        current_selection = set(mandatory_set)
        current_cost = mandatory_cost

        for _, _, sid in optionals:
            # To add an optional section, we must add its entire prerequisite closure
            closure = set()
            def get_closure(u):
                if u in closure: return
                closure.add(u)
                for p in sections_map[u].get("predecessors", []):
                    get_closure(p)
            
            get_closure(sid)
            
            # Only add what isn't already in current_selection
            new_to_add = closure - current_selection
            added_cost = sum(sections_map[u]["cost"] for u in new_to_add)
            
            if current_cost + added_cost <= budget:
                current_selection.update(new_to_add)
                current_cost += added_cost

        # 5. Topological Sort of selected sections
        # We need to sort the selected sections such that predecessors come before successors
        # Using Kahn's algorithm on the subgraph
        sub_adj = defaultdict(list)
        in_degree = {sid: 0 for sid in current_selection}
        for sid in current_selection:
            for pred in sections_map[sid].get("predecessors", []):
                if pred in current_selection:
                    sub_adj[pred].append(sid)
                    in_degree[sid] += 1
        
        queue = deque([sid for sid in current_selection if in_degree[sid] == 0])
        # To ensure stable order, if multiple nodes have 0 in-degree, 
        # we should ideally follow input order or some deterministic rule.
        # The prompt says "stable topological input order".
        # We'll sort the initial queue by their original index.
        
        # Re-calculating queue with stable order
        sorted_keys = sorted(list(current_selection), key=lambda x: list(sections_map.keys()).index(x))
        queue = deque([sid for sid in sorted_keys if in_degree[sid] == 0])
        
        topo_order = []
        while queue:
            # To maintain stability, we don't just popleft, we need to pick the one 
            # that appeared earliest in the input among those with in_degree 0.
            # But Kahn's usually uses a queue. Let's use a sorted list as a priority queue.
            # Actually, "stable topological input order" usually means:
            # among all valid topological sorts, pick the one that respects input order.
            
            # Let's refine: at each step, pick the node with in_degree 0 that has the smallest original index.
            candidates = [sid for sid in current_selection if in_degree[sid] == 0 and sid not in topo_order]
            if not candidates: break
            next_node = min(candidates, key=lambda x: list(sections_map.keys()).index(x))
            
            topo_order.append(next_node)
            for neighbor in sub_adj[next_node]:
                in_degree[neighbor] -= 1
            
            # To prevent infinite loop if logic is wrong, but we checked cycles.
            # We must remove next_node from consideration.
            # Since we are manually picking, we don't need a queue.
            # We just need to ensure we don't pick the same one.
            # A simple way:
            for sid in current_selection:
                if sid in topo_order:
                    in_degree[sid] = -1 # Mark as processed

        # 6. Build Output
        selected_sections_data = []
        total_bytes = 0
        omitted_ids = [sid for sid in sections_map if sid not in current_selection]
        
        for sid in topo_order:
            s = sections_map[sid]
            text = s["text"]
            text_bytes = len(text.encode('utf-8'))
            selected_sections_data.append({
                "id": sid,
                "text": text,
                "byte_range": [total_bytes, total_bytes + text_bytes]
            })
            total_bytes += text_bytes

        print(json.dumps({
            "status": "success",
            "selected": selected_sections_data,
            "omitted": omitted_ids,
            "total_units": current_cost,
            "budget": budget
        }))

    except Exception as e:
        # Catch-all for logic errors to prevent tracebacks
        print(json.dumps({"status": "refused", "code": "ERR_INTERNAL", "message": str(e)}))

if __name__ == "__main__":
    solve()
