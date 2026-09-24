# Method: Validate Focused Attempt Handoff

## Algorithm
The validator performs a single-pass validation of the handoff JSON. It enforces strict typing to prevent ambiguity (e.g., distinguishing `1` from `true`). It verifies that the `events` array represents a linear, unbroken progression of states.

## Conventions
- **Sequence Numbers**: Must start at `0` and increment by exactly `1`.
- **States**: `running`, `failed`, `cancelled`, `candidate`, `accepted`.
- **Acceptance**: An `accepted` state is only valid if a `validator_id` and `evidence_digest` are provided, and the `validator_id` must differ from the `validator_id` of a preceding `candidate` state in the same sequence.

## Bounds
- **Input Size**: Max 1MiB.
- **Complexity**: O(N) where N is the number of events.
- **Memory**: O(N) to hold the event list.

## Known-Wrong Approach
A common mistake is to use `json.loads()` and assume `sequence_number: 1` and `sequence_number: true` are treated differently in a way that allows `true` to pass as an integer. In Python, `isinstance(True, int)` is `True`, so explicit `isinstance(x, bool)` checks are required to enforce strict integer types.

## Limitations
- Does not validate the *content* of the `evidence_digest` (it is treated as an opaque string).
- Does not validate the `authority_reference` against a live registry.
