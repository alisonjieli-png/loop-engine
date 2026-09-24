# Agent Instructions: Focused Attempt Handoff Validation

This tool validates the integrity of a task handoff. It ensures that an agent's progress is recorded with contiguous, non-duplicate event sequences and that state transitions (especially 'accepted') are backed by valid evidence.

## Invocation
The tool reads a single JSON object from `stdin`.
The JSON must be < 1MiB.

## Contract
- **Input**: A handoff object containing `task_id`, `attempt_id`, `objective`, `first_actions`, `immutable_inputs`, `required_output_paths`, `authority_reference`, and `event_records`.
- **Output**: A JSON object indicating `status` ("success" or "refused"), a `briefing` (containing the first action and output contract), and the `validated_state`.

## Refusal Rules
- **Sequence Gaps**: Events must have contiguous sequence numbers (0, 1, 2...).
- **Duplicates**: No two events can share the same sequence number.
- **Invalid Acceptance**: An event with state `accepted` MUST provide a `validator_identity` and an `evidence_digest`.
- **Self-Acceptance**: A `candidate` state cannot transition to `accepted` without a different validator identity.
- **Type Mismatches**: Reject booleans where integers are expected (e.g., sequence numbers).
- **Non-finite Numbers**: Reject `NaN` or `Infinity`.
- **Duplicate Keys**: The input JSON must not contain duplicate keys.

## First Action & Output Contract
The `briefing` must explicitly state the first action from the `first_actions` list and the expected `required_output_paths`.
