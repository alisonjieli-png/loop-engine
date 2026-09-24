# Assemble Bounded Instruction Sections

## Task
Assemble a sequence of text sections based on a budget, priority, and dependency constraints.

## First Action
1. Read the JSON input from `stdin`.
2. Validate the schema and constraints (acyclic, budget, types).
3. Select mandatory sections and their dependencies.
4. Select optional sections by descending priority and input order.
5. Return a topological sort of the selected sections with byte offsets.

## Contract
- **Input**: A JSON object containing `budget` (int), `sections` (list of objects).
- **Sections**: `id` (string), `text` (string), `cost` (int), `mandatory` (bool), `priority` (int), `predecessors` (list of strings).
- **Refusals**:
    - `ERR_INVALID_JSON`: Malformed JSON or non-finite numbers.
    - `ERR_DUPLICATE_ID`: Non-unique section IDs.
    - `ERR_MISSING_DEPENDENCY`: A predecessor ID that does not exist.
    - `ERR_CYCLIC_DEPENDENCY`: A cycle in the precedence graph.
    - `ERR_TYPE_MISMATCH`: Non-integer where integer is expected (e.g., boolean for cost).
    - `ERR_BUDGET_EXCEEDED`: Mandatory sections + dependencies exceed budget.
- **Output**: A JSON object with `status: "success"` or `status: "refused"`.

## Helper Invocation
The tool is a standalone Python script: `python3 tools/assemble_bounded_instruction_sections.py`.
