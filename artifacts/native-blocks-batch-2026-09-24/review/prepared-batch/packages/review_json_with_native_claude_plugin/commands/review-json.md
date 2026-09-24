---
description: "Review the structure and validity of a JSON object."
---

# review-json

Analyze a JSON object to ensure it meets strict structural requirements and to obtain a statistical breakdown of its types.

## Usage
Provide a JSON string via stdin. The command will validate the input against depth, duplicate key, and number finiteness constraints.

## Procedure
1. **Input**: A single JSON value (object, array, or primitive).
2. **Validation**:
   - Checks for duplicate keys in objects.
   - Checks for depth $\le$ 32.
   - Checks for finite numbers.
3. **Output**: A JSON object containing `status` ("success" or "refused"), `counts` (type distribution), and `max_depth`.

## Reference
Uses `scripts/check_json.py` for the core logic.
