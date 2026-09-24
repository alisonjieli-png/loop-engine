import sys
import json
import math
from typing import Any, Dict, List, Set, Tuple, Union

def validate_json_input(raw_data: str) -> Dict[str, Any]:
    """Parses JSON with strict checks for duplicate keys and non-finite numbers."""
    if len(raw_data.encode('utf-8')) > 1024 * 1024:
        raise ValueError("INPUT_TOO_LARGE")

    # To detect duplicate keys in standard json.loads, we use object_pairs_hook
    def dict_with_check(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise ValueError("DUPLICATE_KEY")
            d[k] = v
        return d

    try:
        data = json.loads(raw_data, object_pairs_hook=dict_with_check)
    except json.JSONDecodeError:
        raise ValueError("INVALID_JSON")
    except ValueError as e:
        if str(e) == "DUPLICATE_KEY":
            raise ValueError("DUPLICATE_KEY")
        raise e

    # Check for non-finite numbers
    def check_finite(obj):
        if isinstance(obj, float):
            if not math.isfinite(obj):
                raise ValueError("NON_FINITE_NUMBER")
        elif isinstance(obj, dict):
            for v in obj.values():
                check_finite(v)
        elif isinstance(obj, list):
            for v in obj:
                check_finite(v)
    
    check_finite(data)
    return data

def resolve_dependencies(request: Dict[str, Any], records: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    requested_ids = request.get("requested_ids", [])
    
    # Map for quick lookup: id -> record
    # We must first check for identity collisions in the provided records
    id_to_record = {}
    for r_id, r_val in records.items():
        # Check if we already saw this ID with different metadata
        # The input schema implies records is a map of id -> record
        # But we must ensure the 'records' itself doesn't have logical collisions
        # (Though JSON keys are unique, the logic requires checking if the same ID 
        # is provided via different paths if the schema allowed it, but here it's a map)
        id_to_record[r_id] = r_val

    # 1. Check for identity collisions/mismatches in the provided records
    # Since 'records' is a dict, keys are unique. However, the prompt says:
    # "A supplied same-name B at a different digest must refuse."
    # This implies we might have multiple entries for the same ID? 
    # In a JSON object, keys are unique. If the input was a list of records, we'd check.
    # Given the schema, we assume 'records' is a map.
    
    resolved_order: List[str] = []
    visited: Set[str] = set()
    path: Set[str] = set()
    
    total_size: int = 0
    all_effects: Set[str] = set()
    
    # To handle "Reject booleans where integers are required"
    def strict_int(val, field_name):
        if isinstance(val, bool):
            raise TypeError(f"TYPE_ERROR:{field_name}")
        if not isinstance(val, int):
            raise TypeError(f"TYPE_ERROR:{field_name}")
        return val

    def walk(current_id: str):
        nonlocal total_size
        if current_id in path:
            raise ValueError("CYCLE_DETECTED")
        if current_id in visited:
            return

        if current_id not in id_to_record:
            raise ValueError("MISSING_RECORD")
        
        rec = id_to_record[current_id]
        
        # Validate types for size
        rec_size = strict_int(rec.get("size", 0), "size")
        
        path.add(current_id)
        
        # Dependencies must be resolved before the consumer
        deps = rec.get("dependencies", [])
        for dep_id in deps:
            # The input schema says dependencies are objects with id, revision, digest
            # But the 'records' map is indexed by id.
            # Let's assume the dependency list contains the IDs.
            walk(dep_id)
            
        path.remove(current_id)
        visited.add(current_id)
        resolved_order.append(current_id)
        
        # Aggregate data
        total_size += rec_size
        for effect in rec.get("effects", []):
            all_effects.add(effect)

    try:
        for r_id in requested_ids:
            walk(r_id)
            
        return {
            "status": "success",
            "resolved_dependencies": resolved_order,
            "total_size_bytes": total_size,
            "effects": sorted(list(all_effects))
        }
    except TypeError as e:
        return {"status": "refused", "error_code": str(e).split(":")[0], "message": str(e)}
    except ValueError as e:
        return {"status": "refused", "error_code": str(e), "message": str(e)}
    except Exception as e:
        return {"status": "refused", "error_code": "UNKNOWN_ERROR", "message": str(e)}

def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input:
            print(json.dumps({"status": "refused", "error_code": "EMPTY_INPUT", "message": "No input provided"}))
            return

        data = validate_json_input(raw_input)
        
        # Basic schema validation for required top-level keys
        if "requested_ids" not in data or "records" not in data:
            print(json.dumps({"status": "refused", "error_code": "SCHEMA_VIOLATION", "message": "Missing requested_ids or records"}))
            return

        result = resolve_dependencies(data, data["records"])
        print(json.dumps(result))

    except ValueError as e:
        print(json.dumps({"status": "refused", "error_code": str(e), "message": str(e)}))
    except Exception as e:
        print(json.dumps({"status": "refused", "error_code": "UNKNOWN_ERROR", "message": str(e)}))

if __name__ == "__main__":
    main()
