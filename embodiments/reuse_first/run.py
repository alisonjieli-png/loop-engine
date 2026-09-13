"""Explicitly unavailable experimental embodiment; no fallback or effects."""

import json

if __name__ == "__main__":
    print(
        json.dumps(
            {
                "status": "unavailable",
                "embodiment": "reuse_first",
                "reason": "adapter_not_qualified",
                "model_calls": 0,
            }
        )
    )
    raise SystemExit(2)
