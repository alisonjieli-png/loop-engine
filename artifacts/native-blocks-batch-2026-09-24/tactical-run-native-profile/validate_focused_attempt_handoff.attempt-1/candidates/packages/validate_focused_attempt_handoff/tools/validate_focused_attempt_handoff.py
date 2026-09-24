import sys
import json
import math

def validate_handoff():
    try:
        # Read stdin
        raw_data = sys.stdin.buffer.read()
        if len(raw_data) > 1024 * 1024:
            print(json.dumps({"status": "refused", "code": "ERR_SIZE_EXCEEDED"}), file=sys.stderr)
            sys.exit(0)
        
        # Manual check for duplicate keys and non-finite numbers
        # json.loads handles duplicates by taking the last one; we need to detect them.
        # We use a custom decoder or a simple scan for the purpose of this tool.
        
        # To strictly detect duplicate keys without complex regex, we use a custom object_pairs_hook
        def dict_with_check(pairs):
            keys = []
            for k, v in pairs:
                if k in keys:
                    raise ValueError("DUPLICATE_KEY")
                keys.append(k)
            return dict(pairs)

        try:
            data = json.loads(raw_data.decode('utf-8'), object_pairs_hook=dict_with_check)
        except ValueError as e:
            code = "ERR_DUPLICATE_KEY" if str(e) == "DUPLICATE_KEY" else "ERR_INVALID_JSON"
            print(json.dumps({"status": "refused", "code": code}), file=sys.stderr)
            sys.exit(0)

        # Check for non-finite numbers
        def check_finite(obj):
            if isinstance(obj, float):
                if not math.isfinite(obj):
                    raise ValueError("NON_FINITE")
            elif isinstance(obj, dict):
                for v in obj.values(): check_finite(v)
            elif isinstance(obj, list):
                for v in obj: check_finite(v)
        
        try:
            check_finite(data)
        except ValueError:
            print(json.dumps({"status": "refused", "code": "ERR_NON_FINITE"}, file=sys.stderr)
            sys.exit(0)

        # Required Fields
        required = ["task_id", "attempt_id", "objective", "first_actions", "immutable_inputs", "required_output_paths", "authority_reference", "events"]
        for field in required:
            if field not in data:
                print(json.dumps({"status": "refused", "code": "ERR_MISSING_FIELD", "field": field}), file=sys.stderr)
                sys.exit(0)

        # Type Strictness: Reject booleans where integers are required
        # Specifically checking sequence_number in events
        events = data["events"]
        if not isinstance(events, list):
            print(json.dumps({"status": "refused", "code": "ERR_TYPE_MISMATCH", "field": "events"}, file=sys.stderr)
            sys.exit(0)

        last_seq = -1
        for i, event in enumerate(events):
            seq = event.get("sequence_number")
            
            # Strict type check: seq must be int, not bool
            if not isinstance(seq, int) or isinstance(seq, bool):
                print(json.dumps({"status": "refused", "code": "ERR_TYPE_MISMATCH", "field": f"events[{i}].sequence_number"}, file=sys.stderr)
                sys.exit(0)
            
            if seq != i:
                if seq <= last_seq:
                    print(json.dumps({"status": "refused", "code": "ERR_SEQUENCE_DUPE"}, file=sys.stderr)
                    sys.exit(0)
                else:
                    print(json.dumps({"status": "refused", "code": "ERR_SEQUENCE_GAP"}, file=sys.stderr)
                    sys.exit(0)
            
            last_seq = seq
            
            # State validation
            state = event.get("state")
            if state == "accepted":
                v_id = event.get("validator_id")
                ev_dig = event.get("evidence_digest")
                if not v_id or not ev_dig:
                    print(json.dumps({"status": "refused", "code": "ERR_INVALID_STATE", "reason": "missing_evidence"}, file=sys.stderr)
                    sys.exit(0)
                
                # Candidate cannot self-accept
                if i > 0 and events[i-1].get("state") == "candidate":
                    if events[i-1].get("validator_id") == v_id:
                        print(json.dumps({"status": "refused", "code": "ERR_INVALID_STATE", "reason": "candidate_self_accept"}, file=sys.stderr)
                        sys.exit(0)

        # Success Output
        briefing = {
            "first_action": data["first_actions"][0] if data["first_actions"] else None,
            "output_contract": data["required_output_paths"]
        }
        
        # Preserve unknown external-effect outcome
        # We assume 'external_effects' might exist in the input
        external_effects = data.get("external_effects", {})

        result = {
            "status": "success",
            "briefing": briefing,
            "passive_state": {
                "task_id": data["task_id"],
                "attempt_id": data["attempt_id"],
                "current_state": events[-1]["state"] if events else "idle",
                "external_effects": external_effects
            }
        }
        print(json.dumps(result))

    except Exception as e:
        # Fallback for unexpected errors
        print(json.dumps({"status": "refused", "code": "ERR_INTERNAL", "message": str(e)}))

if __name__ == "__main__":
    validate_handoff()
