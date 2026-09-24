# Method: Validate Focused Attempt Handoff

## Algorithm
1. **Ingestion**: Read exactly 1MiB from `stdin`. Parse as JSON.
2. **Sanity Check**: 
   - Ensure no `NaN` or `Infinity` in the JSON.
   - Ensure `attempt_id` is an integer (reject `True`/`False`).
3. **Sequence Validation**:
   - Iterate through `events`.
   - Verify `event.sequence == index`.
   - Verify no duplicate `sequence` values.
4. **State Logic**:
   - If `state == "accepted"`, verify `validator_id` and `evidence_digest` are present.
5. **Output Construction**:
   - Generate a `briefing` string: `Objective: <obj>. First Action: <first_action>. Required Outputs: <paths>`.
   - Return the `passive_state` containing the immutable identifiers and the last known state.

## Conventions
- **Error Codes**: `MISSING_FIELD`, `TYPE_MISMATCH`, `SEQUENCE_GAP`, `DUPLICATE_SEQUENCE`, `INVALID_STATE`, `NON_FINITE_NUMBER`, `INVALID_JSON`.
- **Status**: `success` or `refused`.

## Limitations
- Does not validate the *content* of `inputs` or `output_paths`, only their presence and type.
- Does not perform external lookups for `authority`.
- Does not verify if `evidence_digest` is a valid hash; it only checks for presence.
