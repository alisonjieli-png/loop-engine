import sys
import json
from decimal import Decimal, getcontext
from typing import Any, Dict, List, Set, Union

# Set precision for arbitrary precision integer sums
getcontext().prec = 28

def is_integer_type(val: Any) -> bool:
    """Strict check for integer type, excluding booleans."""
    return isinstance(val, int) and not isinstance(val, bool)

def deep_equal(a: Any, b: Any) -> bool:
    """JSON-type-aware recursive equality."""
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

def solve() -> None:
    # 1. Read input with constraints
    try:
        raw_data = sys.stdin.read(1024 * 1024) # 1MiB limit
        if len(raw_data) >= 1024 * 1024:
            print(json.dumps({"status": "refused", "code": "INPUT_TOO_LARGE", "message": "Input exceeds 1MiB"}))
            return

        # Use object_pairs_hook to detect duplicate keys manually if needed, 
        # but standard json.loads handles it by last-key-wins. 
        # To strictly refuse duplicates, we use a custom decoder.
        def dict_raise_on_duplicates(ordered_pairs):
            d = {}
            for k, v in ordered_pairs:
                if k in d:
                    raise ValueError(f"Duplicate key: {k}")
                d[k] = v
            return d

        data = json.loads(raw_data, object_pairs_hook=dict_raise_on_duplicates)
    except ValueError as e:
        msg = str(e)
        code = "DUPLICATE_KEY" if "Duplicate key" in msg else "INVALID_JSON"
        print(json.dumps({"status": "refused", "code": code, "message": msg}))
        return
    except Exception as e:
        print(json.dumps({"status": "refused", "code": "PARSE_ERROR", "message": str(e)}))
        return

    # 2. Validate Schema Structure
    required_top = ["before", "after", "contract"]
    if not all(k in data for k in required_top):
        print(json.dumps({"status": "refused", "code": "MISSING_TOP_LEVEL_KEYS", "message": f"Required: {required_top}"}))
        return

    contract = data["contract"]
    before = data["before"]
    after = data["after"]
    
    id_field = contract.get("id_field")
    preserved_fields = contract.get("preserved_fields", [])
    allowed_changed_fields = contract.get("allowed_changed_fields", [])
    integer_total_fields = contract.get("integer_total_fields", [])

    if not id_field:
        print(json.dumps({"status": "refused", "code": "MISSING_ID_FIELD_DEFINITION", "message": "Contract must define id_field"}))
        return

    # 3. Process Rows
    def get_rows_map(rows: List[Dict]) -> Dict[str, Dict]:
        row_map = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Row is not an object")
            rid = row.get(id_field)
            if not isinstance(rid, str) or not rid:
                raise ValueError(f"ID must be non-empty string, got {rid}")
            if rid in row_map:
                raise ValueError(f"Duplicate ID: {rid}")
            row_map[rid] = row
        return row_map

    try:
        before_map = get_rows_map(before)
        after_map = get_rows_map(after)
    except ValueError as e:
        print(json.dumps({"status": "refused", "code": "ID_INTEGRITY_ERROR", "message": str(e)}))
        return

    # 4. Check ID Set Invariants
    before_ids = set(before_map.keys())
    after_ids = set(after_map.keys())
    
    if before_ids != after_ids:
        diff = before_ids.symmetric_difference(after_ids)
        print(json.dumps({
            "status": "refused", 
            "code": "ID_SET_MISMATCH", 
            "message": f"ID sets do not match. Diff: {list(diff)[:10]}"
        }))
        return

    violations = []

    # 5. Check Row-level Invariants
    for rid, b_row in before_map.items():
        a_row = after_map[rid]
        
        # Check Preserved Fields
        for field in preserved_fields:
            if field in b_row and field in a_row:
                if not deep_equal(b_row[field], a_row[field]):
                    violations.append({"id": rid, "field": field, "type": "PRESERVED_FIELD_CHANGED"})
            elif field in b_row or field in a_row:
                # One has it, the other doesn't
                violations.append({"id": rid, "field": field, "type": "PRESERVED_FIELD_MISSING"})

        # Check Allowed Mutations
        # We check all fields present in 'before' to see if they changed
        for field in b_row:
            if field == id_field:
                continue
            if field in a_row:
                if not deep_equal(b_row[field], a_row[field]):
                    if field not in allowed_changed_fields:
                        violations.append({"id": rid, "field": field, "type": "UNAUTHORIZED_MUTATION"})
            else:
                # Field disappeared
                if field not in allowed_changed_fields:
                    violations.append({"id": rid, "field": field, "type": "UNAUTHORIZED_REMOVAL"})

    # 6. Check Integer Totals
    for field in integer_total_fields:
        sum_before = Decimal(0)
        sum_after = Decimal(0)
        
        for rid, b_row in before_map.items():
            val_b = b_row.get(field)
            if val_b is not None:
                if not is_integer_type(val_b):
                    print(json.dumps({"status": "refused", "code": "NON_INTEGER_VALUE", "message": f"Field {field} contains non-integer at ID {rid}"}))
                    return
                sum_before += Decimal(val_b)
            
            a_row = after_map[rid]
            val_a = a_row.get(field)
            if val_a is not None:
                if not is_integer_type(val_a):
                    print(json.dumps({"status": "refused", "code": "NON_INTEGER_VALUE", "message": f"Field {field} contains non-integer at ID {rid}"}))
                    return
                sum_after += Decimal(val_a)

        if sum_before != sum_after:
            print(json.dumps({
                "status": "refused", 
                "code": "TOTAL_SUM_MISMATCH", 
                "message": f"Sum of {field} changed from {sum_before} to {sum_after}"
            }))
            return

    # 7. Final Output
    if violations:
        print(json.dumps({
            "status": "refused",
            "code": "INVARIANT_VIOLATION",
            "violations": violations
        }))
    else:
        print(json.dumps({"status": "success", "message": "All invariants preserved"}))

if __name__ == "__main__":
    solve()
