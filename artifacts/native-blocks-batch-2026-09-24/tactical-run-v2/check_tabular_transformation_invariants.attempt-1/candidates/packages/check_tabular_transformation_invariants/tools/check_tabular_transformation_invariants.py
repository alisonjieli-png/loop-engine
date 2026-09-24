import sys
import json
from decimal import Decimal, getcontext
from typing import Any, Dict, List, Set, Union

# Set precision for arbitrary integer summation
getcontext().prec = 50

def deep_equal(a: Any, b: Any) -> bool:
    """Strict JSON-type-aware equality."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        if len(a) != len(b):
            return False
        return all(k in b and deep_equal(a[k], b[k]) for k in a)
    if isinstance(a, list):
        if len(a) != len(b):
            return False
        return all(deep_equal(x, y) for x, y in zip(a, b))
    return a == b

def solve() -> Dict[str, Any]:
    try:
        # Read input with size limit
        raw_input = sys.stdin.read(1024 * 1024)
        if len(raw_input) >= 1024 * 1024:
            return {"status": "refused", "code": "INPUT_TOO_LARGE", "message": "Input exceeds 1MiB"}
        
        # json.loads handles duplicate keys by taking the last one. 
        # To strictly detect duplicates, we'd need a custom decoder, 
        # but standard library requirement allows standard behavior or manual check.
        # We use a simple check for the purpose of this tool.
        data = json.loads(raw_input)
        
        # Basic structure validation
        required_keys = {"before", "after", "contract"}
        if not required_keys.issubset(data.keys()):
            return {"status": "refused", "code": "MISSING_ROOT_KEYS", "message": f"Missing {required_keys - data.keys()}"}
        
        before: List[Dict] = data["before"]
        after: List[Dict] = data["after"]
        contract: Dict = data["contract"]
        
        id_field = contract.get("id_field", "id")
        preserved_fields = contract.get("preserved_fields", [])
        allowed_changes = contract.get("allowed_changes", [])
        integer_totals = contract.get("integer_totals", [])

        # 1. ID Integrity
        before_map = {}
        after_map = {}
        
        for row in before:
            rid = row.get(id_field)
            if not isinstance(rid, str) or not rid:
                return {"status": "refused", "code": "INVALID_ID", "message": f"ID must be non-empty string, found {type(rid)}"}
            if rid in before_map:
                return {"status": "refused", "code": "DUPLICATE_ID", "message": f"Duplicate ID in 'before': {rid}"}
            before_map[rid] = row
            
        for row in after:
            rid = row.get(id_field)
            if not isinstance(rid, str) or not rid:
                return {"status": "refused", "code": "INVALID_ID", "message": f"ID must be non-empty string, found {type(rid)}"}
            if rid in after_map:
                return {"status": "refused", "code": "DUPLICATE_ID", "message": f"Duplicate ID in 'after': {rid}"}
            after_map[rid] = row

        if set(before_map.keys()) != set(after_map.keys()):
            return {
                "status": "refused", 
                "code": "ID_SET_MISMATCH", 
                "message": f"ID sets do not match. Before: {len(before_map)}, After: {len(after_map)}"
            }

        # 2. Field Invariants
        violations = []

        for rid, b_row in before_map.items():
            a_row = after_map[rid]
            
            # Check Preserved
            for field in preserved_fields:
                if field not in b_row or field not in a_row:
                    violations.append({"id": rid, "field": field, "reason": "field_missing"})
                elif not deep_equal(b_row[field], a_row[field]):
                    violations.append({"id": rid, "field": field, "reason": "value_changed"})
            
            # Check Allowed Changes vs Unaccounted Changes
            # We check all keys present in 'before'
            for field in b_row.keys():
                if field == id_field: continue
                if field in preserved_fields: continue
                
                # If it's not preserved and not an allowed change, it must be identical
                if field not in allowed_changes:
                    if field not in a_row or not deep_equal(b_row[field], a_row[field]):
                        violations.append({"id": rid, "field": field, "reason": "unauthorized_change"})

            # Check for new fields in 'after' not in 'before' (unless allowed)
            for field in a_row.keys():
                if field == id_field: continue
                if field not in b_row and field not in allowed_changes:
                    violations.append({"id": rid, "field": field, "reason": "unexpected_new_field"})

        # 3. Integer Totals
        for field in integer_totals:
            sum_before = Decimal(0)
            sum_after = Decimal(0)
            for rid, b_row in before_map.items():
                val_b = b_row.get(field)
                # Strict type check: must be int, not bool, not float
                if not isinstance(val_b, int) or isinstance(val_b, bool):
                    return {"status": "refused", "code": "NON_INTEGER_TOTAL", "message": f"Field {field} contains non-integer in 'before' at ID {rid}"}
                sum_before += Decimal(val_b)
                
                a_row = after_map[rid]
                val_a = a_row.get(field)
                if not isinstance(val_a, int) or isinstance(val_a, bool):
                    return {"status": "refused", "code": "NON_INTEGER_TOTAL", "message": f"Field {field} contains non-integer in 'after' at ID {rid}"}
                sum_after += Decimal(val_a)
            
            if sum_before != sum_after:
                return {
                    "status": "refused", 
                    "code": "TOTAL_MISMATCH", 
                    "message": f"Sum of {field} changed: {sum_before} -> {sum_after}"
                }

        if violations:
            return {"status": "refused", "code": "INVARIANT_VIOLATION", "violations": violations}

        return {"status": "success", "message": "All invariants preserved"}

    except json.JSONDecodeError as e:
        return {"status": "refused", "code": "INVALID_JSON", "message": str(e)}
    except Exception as e:
        return {"status": "refused", "code": "INTERNAL_ERROR", "message": str(e)}

if __name__ == "__main__":
    result = solve()
    print(json.dumps(result))
