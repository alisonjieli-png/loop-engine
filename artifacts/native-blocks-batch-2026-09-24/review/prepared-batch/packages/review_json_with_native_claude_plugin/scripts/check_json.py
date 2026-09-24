import sys
import json
import math
from typing import Any, Dict, Union

class JSONReviewer:
    def __init__(self, max_depth: int = 32, max_bytes: int = 1048576):
        self.max_depth = max_depth
        self.max_bytes = max_bytes
        self.counts = {
            "object": 0,
            "array": 0,
            "string": 0,
            "number": 0,
            "boolean": 0,
            "null": 0
        }
        self.current_max_depth = 0

    def _validate_and_count(self, val: Any, depth: int) -> None:
        self.current_max_depth = max(self.current_max_depth, depth)
        
        if depth > self.max_depth:
            raise ValueError("ERR_DEPTH")

        if val is None:
            self.counts["null"] += 1
        elif isinstance(val, bool):
            self.counts["boolean"] += 1
        elif isinstance(val, str):
            self.counts["string"] += 1
        elif isinstance(val, (int, float)):
            if not math.isfinite(val):
                raise ValueError("ERR_NONFINITE_NUMBER")
            self.counts["number"] += 1
        elif isinstance(val, list):
            self.counts["array"] += 1
            for item in val:
                self._validate_and_count(item, depth + 1)
        elif isinstance(val, dict):
            self.counts["object"] += 1
            # To detect duplicate keys, we must use a custom decoder or 
            # check the raw input. Since we use json.loads, we rely on 
            # the fact that standard json.loads overwrites. 
            # To strictly detect duplicates as per requirements, 
            # we use the object_pairs approach.
            pass 
        else:
            # Fallback for unexpected types if any
            pass

    def run(self, raw_data: bytes) -> Dict[str, Any]:
        if len(raw_data) > self.max_bytes:
            return {"status": "refused", "error": "ERR_SIZE_EXCEEDED"}

        try:
            # Custom logic to detect duplicate keys
            # json.loads(raw_data) alone doesn't raise on duplicates.
            # We use object_pairs to catch them.
            def dict_raise_on_duplicates(ordered_pairs):
                keys = []
                for k, v in ordered_pairs:
                    if k in keys:
                        raise ValueError("ERR_DUPLICATE_KEY")
                    keys.append(k)
                return dict(ordered_pairs)

            data = json.loads(raw_data, object_pairs_hook=dict_raise_on_duplicates)
            
            # Reset counts and depth before traversal
            self.counts = {k: 0 for k in self.counts}
            self.current_max_depth = 0
            
            # We need a slightly different traversal to handle the dict_raise_on_duplicates
            # because the hook returns a standard dict. We re-traverse the parsed data.
            # The duplicate check is already done by the hook.
            
            def traverse(node, d):
                self.current_max_depth = max(self.current_max_depth, d)
                if d > self.max_depth: raise ValueError("ERR_DEPTH")
                
                if node is None:
                    self.counts["null"] += 1
                elif isinstance(node, bool):
                    self.counts["boolean"] += 1
                elif isinstance(node, str):
                    self.counts["string"] += 1
                elif isinstance(node, (int, float)):
                    if not math.isfinite(node): raise ValueError("ERR_NONFINITE_NUMBER")
                    self.counts["number"] += 1
                elif isinstance(node, list):
                    self.counts["array"] += 1
                    for item in node: traverse(item, d + 1)
                elif isinstance(node, dict):
                    self.counts["object"] += 1
                    for k, v in node.items(): traverse(v, d + 1)

            traverse(data, 0)

            return {
                "status": "success",
                "counts": self.counts,
                "max_depth": self.current_max_depth
            }

        except ValueError as e:
            err_msg = str(e)
            if err_msg.startswith("ERR_"):
                return {"status": "refused", "error": err_msg}
            return {"status": "refused", "error": "ERR_INVALID_JSON"}
        except Exception:
            return {"status": "refused", "error": "ERR_INVALID_JSON"}

def main():
    try:
        input_data = sys.stdin.buffer.read()
        if not input_data:
            print(json.dumps({"status": "refused", "error": "ERR_EMPTY_INPUT"}))
            return

        reviewer = JSONReviewer()
        result = reviewer.run(input_data)
        print(json.dumps(result))
    except Exception as e:
        # Final fallback to ensure no tracebacks escape
        print(json.dumps({"status": "refused", "error": "ERR_INTERNAL"}))

if __name__ == "__main__":
    main()
