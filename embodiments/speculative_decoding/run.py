"""Unqualified provider-side experiment; no model pull or implicit fallback."""

import json

if __name__ == "__main__":
    print(
        json.dumps(
            {
                "status": "unavailable",
                "embodiment": "speculative_decoding",
                "reason": "adapter_not_qualified",
                "model_calls": 0,
            }
        )
    )
    raise SystemExit(2)
