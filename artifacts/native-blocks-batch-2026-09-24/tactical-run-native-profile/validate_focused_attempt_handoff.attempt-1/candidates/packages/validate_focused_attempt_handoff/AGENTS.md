# Focused Attempt Handoff Validation

This tool validates the integrity of a task handoff. It ensures that the sequence of events is contiguous, that state transitions are valid, and that "accepted" states are backed by external validator evidence.

## Core Logic
1. **Input Parsing**: Reads a UTF-8 JSON from `stdin`. Rejects if > 1MiB, contains duplicate keys, or non-finite numbers.
2. **Type Strictness**: Rejects booleans where integers are expected (e.g., `sequence_number: true` is invalid).
3. **Event Validation**:
   - Sequence numbers must be contiguous starting from 0.
   - No duplicate sequence numbers.
   - No gaps in sequence.
   - `accepted` state requires `validator_id` and `evidence_digest`.
   - `candidate` state cannot transition to `accepted` without a different `validator_id`.
4. **Briefing Generation**: Returns the first action and the required output contract.

## Refusal Rules
- **ERR_DUPLICATE_KEY**: JSON contains duplicate keys.
- **ERR_NON_FINITE**: JSON contains `NaN` or `Infinity`.
- **ERR_TYPE_MISMATCH**: Boolean used where integer/string expected.
- **ERR_SEQUENCE_GAP**: Missing sequence number.
- **ERR_SEQUENCE_DUPE**: Repeated sequence number.
- **ERR_INVALID_STATE**: `accepted` without evidence or `candidate` self-accepting.
- **ERR_SIZE_EXCEEDED**: Input > 1MiB.

## Execution
Invoke via `python3 tools/validate_focused_attempt_handoff.py`.
