import sys
import json
from typing import Any, Dict, List, Tuple, Union

def validate_handoff(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates the handoff structure and event sequence.
    Returns a success dict or raises a ValueError with a stable error code.
    """
    # 1. Basic Structure Validation
    required_top_level = [
        "task_id", "attempt_id", "objective", "first_actions", 
        "immutable_inputs", "required_output_paths", 
        "authority_reference", "event_records"
    ]
    for field in required_top_level:
        if field not in data:
            raise ValueError(f"MISSING_FIELD:{field}")

    # 2. Type/Value Validation (Reject booleans where integers are required)
    def strict_int(val: Any, name: str) -> int:
        if isinstance(val, bool):
            raise ValueError(f"TYPE_MISMATCH:{name}_expected_int_not_bool")
        if not isinstance(val, int):
            raise ValueError(f"TYPE_MISMATCH:{name}_expected_int")
        return val

    # 3. Event Sequence Validation
    events = data["event_records"]
    if not isinstance(events, list):
        raise ValueError("TYPE_MISMATCH:event_records_must_be_list")

    seen_sequences = set()
    last_seq = -1
    
    # We need to track the authority to prevent self-acceptance
    authority = data["authority_reference"]

    for event in events:
        seq = strict_int(event.get("sequence"), "event_sequence")
        state = event.get("state")
        
        if state not in ["running", "failed", "cancelled", "candidate", "accepted"]:
            raise ValueError(f"INVALID_STATE:{state}")

        # Check for duplicates and gaps
        if seq in seen_sequences:
            raise ValueError(f"DUPLICATE_SEQUENCE:{seq}")
        if seq != last_seq + 1:
            raise ValueError(f"SEQUENCE_GAP:{seq}")
        
        seen_sequences.add(seq)
        last_seq = seq

        # Acceptance Logic
        if state == "accepted":
            v_id = event.get("validator_identity")
            evidence = event.get("evidence_digest")
            if not v_id or not evidence:
                raise ValueError("MISSING_ACCEPTANCE_EVIDENCE")
            # Candidate cannot self-accept (if authority is the one who was a candidate)
            # In this context, we check if the validator is the same as the authority
            if v_id == authority:
                raise ValueError("SELF_ACCEPTANCE_PROHIBITED")

    # 4. Construct Briefing
    first_action = data["first_actions"][0] if data["first_actions"] else "None"
    output_contract = data["required_output_paths"]
    
    briefing = f"First Action: {first_action}. Output Contract: {output_contract}"

    return {
        "status": "success",
        "briefing": briefing,
        "validated_state": {
            "task_id": data["task_id"],
            "attempt_id": data["attempt_id"],
            "last_sequence": last_seq,
            "current_state": events[-1]["state"] if events else "idle"
        }
    }

def main():
    try:
        # Read stdin
        raw_input = sys.stdin.read(1024 * 1024) # 1MiB limit
        if not raw_input:
            print(json.dumps({"status": "refused", "error": "EMPTY_INPUT"}))
            return

        # JSON parsing with duplicate key detection is tricky in standard json.
        # We use a custom object_pairs_hook to detect duplicates.
        def dict_with_dup_check(pairs):
            d = {}
            for k, v in pairs:
                if k in d:
                    raise ValueError(f"DUPLICATE_KEY:{k}")
                d[k] = v
            return d

        try:
            data = json.loads(raw_input, object_pairs_hook=dict_with_dup_check)
        except json.JSONDecodeError as e:
            print(json.dumps({"status": "refused", "error": f"INVALID_JSON:{str(e)}"}))
            return
        except ValueError as e:
            print(json.dumps({"status": "refused", "error": str(e)}))
            return

        # Check for non-finite numbers manually as json.loads allows them in some impls
        # but we want to be strict.
        def check_finite(obj):
            if isinstance(obj, float):
                import math
                if not math.isfinite(obj):
                    raise ValueError("NON_FINITE_NUMBER")
            elif isinstance(obj, dict):
                for v in obj.values(): check_finite(v)
            elif isinstance(obj, list):
                for v in obj: check_finite(v)

        try:
            check_finite(data)
        except ValueError as e:
            print(json.dumps({"status": "refused", "error": str(e)}))
            return

        result = validate_handoff(data)
        print(json.dumps(result))

    except ValueError as e:
        print(json.dumps({"status": "refused", "error": str(e)}))
    except Exception as e:
        # Catch-all for unexpected but bounded errors
        print(json.dumps({"status": "refused", "error": f"INTERNAL_ERROR:{type(e).__name__}"}))

if __name__ == "__main__":
    main()
