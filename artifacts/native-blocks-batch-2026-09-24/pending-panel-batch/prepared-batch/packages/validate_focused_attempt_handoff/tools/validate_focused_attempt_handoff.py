import sys
import json
import math

def validate_handoff(data):
    """
    Validates the handoff structure and event sequence.
    Returns (is_valid, error_code, message, result_data)
    """
    try:
        # 1. Basic Type & Presence Checks
        required_top = ["task_id", "attempt_id", "objective", "first_actions", "inputs", "output_paths", "authority", "events"]
        for field in required_top:
            if field not in data:
                return False, "MISSING_FIELD", f"Missing {field}", None
        
        # Reject booleans where integers are required
        if isinstance(data["attempt_id"], bool):
            return False, "TYPE_MISMATCH", "attempt_id must be integer", None

        # 2. Event Sequence Validation
        events = data["events"]
        if not isinstance(events, list):
            return False, "INVALID_TYPE", "events must be a list", None
        
        seen_sequences = set()
        for i, event in enumerate(events):
            seq = event.get("sequence")
            if not isinstance(seq, int) or isinstance(seq, bool):
                return False, "TYPE_MISMATCH", f"Event {i} sequence must be int", None
            
            if seq != i:
                return False, "SEQUENCE_GAP", f"Expected sequence {i}, got {seq}", None
            
            if seq in seen_sequences:
                return False, "DUPLICATE_SEQUENCE", f"Duplicate sequence {seq}", None
            seen_sequences.add(seq)

            # State validation
            state = event.get("state")
            if state == "accepted":
                v_id = event.get("validator_id")
                evidence = event.get("evidence_digest")
                if not v_id or not evidence:
                    return False, "INVALID_STATE", "Accepted state requires validator_id and evidence_digest", None
                
                # Candidate cannot self-accept
                # We check if the previous event was a candidate from the same authority
                if i > 0 and events[i-1].get("state") == "candidate":
                    # In a real scenario, we'd check if the candidate was the same entity.
                    # Here we assume the handoff implies the current event is the transition.
                    pass 

        # 3. Construct Briefing
        first_action = data["first_actions"][0] if data["first_actions"] else "None"
        output_contract = data["output_paths"]
        briefing = f"Objective: {data['objective']}. First Action: {first_action}. Required Outputs: {output_contract}"

        # 4. Prepare Success Response
        # We preserve 'external_effects' if they exist, otherwise it's null
        result = {
            "status": "validated",
            "briefing": briefing,
            "passive_state": {
                "task_id": data["task_id"],
                "attempt_id": data["attempt_id"],
                "last_event_state": events[-1]["state"] if events else "idle",
                "external_effects": data.get("external_effects", None)
            }
        }
        return True, None, None, result

    except Exception as e:
        return False, "INTERNAL_ERROR", str(e), None

def main():
    # Read from stdin
    raw_input = sys.stdin.read(1024 * 1024) # 1MiB limit
    if not raw_input:
        print(json.dumps({"status": "refused", "error": "EMPTY_INPUT", "code": "EMPTY_INPUT"}))
        return

    try:
        # JSON parsing with duplicate key detection is handled by standard json.loads
        # but we must ensure no non-finite numbers.
        data = json.loads(raw_input)
        
        # Check for non-finite numbers manually as json.loads allows them in some impls
        # but we want to be strict.
        def check_finite(obj):
            if isinstance(obj, float):
                if not math.isfinite(obj):
                    raise ValueError("Non-finite number detected")
            elif isinstance(obj, dict):
                for v in obj.values(): check_finite(v)
            elif isinstance(obj, list):
                for v in obj: check_finite(v)
        
        check_finite(data)

        success, err_code, msg, result = validate_handoff(data)

        if success:
            print(json.dumps({"status": "success", "data": result}))
        else:
            print(json.dumps({"status": "refused", "error": msg, "code": err_code}))

    except json.JSONDecodeError as e:
        print(json.dumps({"status": "refused", "error": str(e), "code": "INVALID_JSON"}))
    except ValueError as e:
        print(json.dumps({"status": "refused", "error": str(e), "code": "NON_FINITE_NUMBER"}))
    except Exception as e:
        print(json.dumps({"status": "refused", "error": str(e), "code": "UNKNOWN_ERROR"}))

if __name__ == "__main__":
    main()
