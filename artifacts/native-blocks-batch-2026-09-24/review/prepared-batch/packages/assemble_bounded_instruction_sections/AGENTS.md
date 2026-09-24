# Agent Instructions: assemble_bounded_instruction_sections

## First Action
1. Validate the input JSON against `contracts/input.schema.json`.
2. Check for duplicate keys in the input (requires custom parsing or strict schema validation).
3. Verify all `cost`, `priority`, and `budget` values are integers (reject booleans).
4. Build the dependency graph and check for cycles or unknown references.
5. Calculate the mandatory closure cost. If it exceeds `budget`, return `REFUSED_MANDATORY_OVER_BUDGET`.
6. Greedily add optional sections by descending `priority`, then by input order, ensuring all prerequisites fit the remaining budget.
7. Perform a topological sort on the final selection to ensure stable output order.
8. Calculate byte offsets for the final concatenated text.

## Contract & Refusal Rules
- **Refusal: `ERR_DUPLICATE_KEY`**: Input contains duplicate keys.
- **Refusal: `ERR_NONFINITE_NUMBER`**: Cost or budget is not a finite integer.
- **Refusal: `ERR_TYPE_MISMATCH`**: A boolean was provided where an integer was expected.
- **Refusal: `ERR_UNKNOWN_DEPENDENCY`**: A section references a predecessor that does not exist.
- **Refusal: `ERR_CYCLIC_CONSTRAINT`**: Precedence constraints form a cycle.
- **Refusal: `ERR_MANDATORY_OVER_BUDGET`**: The sum of all mandatory sections and their required predecessors exceeds `budget`.
- **Success**: Return `status: "SUCCESS"` with `selected_sections`, `omitted_sections`, `total_units`, and the `assembled_text` with byte ranges.
