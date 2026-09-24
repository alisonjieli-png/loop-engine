# Method: Validate Focused Attempt Handoff

## Algorithm
1. **Ingestion**: Read up to 1MiB from `stdin`.
2. **Parsing**: Parse JSON using a `dict_with_dup_check` to ensure no duplicate keys exist in the input.
3. **Sanity Check**: Verify all required top-level fields exist. Check for non-finite numbers (`NaN`, `Inf`).
4. **Sequence Validation**:
   - Iterate through `event_records`.
   - Ensure `sequence` is an integer (reject booleans).
   - Ensure `sequence` is strictly increasing by exactly 1 (no gaps, no duplicates).
5. **State Validation**:
   - If `state == "accepted"`, verify `validator_identity` and `evidence_digest` are present.
   - If `state == "accepted"`, ensure `validator_identity != authority_reference` (prevents self-acceptance).
6. **Briefing Generation**: Construct a string containing the first element of `first_actions` and the `required_output_paths`.
7. **Output**: Return a JSON object with `status` and either `briefing`/`validated_state` or `error`.

## Conventions
- **Error Codes**: Use `TYPE_MISMATCH:<field>`, `SEQUENCE_GAP:<seq>`, `DUPLICATE_SEQUENCE:<seq>`, `MISSING_ACCEPTANCE_EVIDENCE`, `SELF_ACCEPTANCE_PROHIBITED`, `DUPLICATE_KEY:<key>`.
- **Types**: Strict integer checking is required to prevent `True` being treated as `1`.

## Bounds
- **Input Size**: 1MiB.
- **Complexity**: O(N) where N is the number of events.
- **Memory**: O(N) to store the event list.

## Known-Wrong Approach
- Using `eval()` to parse the input.
- Using `isinstance(x, int)` without checking `isinstance(x, bool)` (since `bool` is a subclass of `int` in Python).
- Assuming `sequence` is always present or can be inferred from list index (the explicit `sequence` field must be validated).
- Inferring success from a timeout or a lack of error.

## Limitations
- Does not validate the *content* of the `evidence_digest`, only its presence.
- Does not validate the actual existence of files in `required_output_paths` (it is a passive validator).
