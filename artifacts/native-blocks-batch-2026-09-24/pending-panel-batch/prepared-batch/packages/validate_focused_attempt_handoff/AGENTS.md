# Validate Focused Attempt Handoff

This tool validates the integrity of a task handoff. It ensures that an attempt's history is contiguous, that state transitions are valid, and that "accepted" states are backed by external validator evidence.

## Core Logic
1. **Input Validation**: Strict JSON parsing (max 1MiB). Rejects non-finite numbers and duplicate keys.
2. **Sequence Integrity**: Event sequence numbers must be contiguous starting from 0. No gaps, no duplicates.
3. **State Transitions**:
   - `running`, `failed`, `cancelled`, `candidate` are standard.
   - `accepted` requires `validator_id` and `evidence_digest`.
   - A `candidate` cannot transition to `accepted` without a different `validator_id`.
4. **Immutability**: `task_id`, `attempt_id`, `objective`, `inputs`, and `output_paths` must remain consistent.
5. **Briefing Generation**: The output must include a `startup_briefing` containing the first action and the required output contract.

## Constraints
- **No Side Effects**: The tool is purely deterministic. It does not spawn processes or read files itself.
- **No Inference**: It does not assume a task succeeded just because a timeout occurred.
- **Strict Types**: Rejects booleans where integers are expected (e.g., sequence numbers).

## Invocation
The tool reads a JSON object from `stdin` and writes a JSON object to `stdout`.
