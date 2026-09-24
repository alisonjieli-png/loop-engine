# Agent Skill: select-traceable-context-evidence

## Purpose
Selects a subset of provided evidence records to answer a specific question, ensuring all selected records are valid, traceable to exact source spans, and respect a strict byte budget.

## First Action
The agent must first parse the user's question and the provided `evidence_pool`. It should identify which records are "required" and which are "optional" based on the question's constraints, then invoke the `select_evidence.py` helper to perform deterministic validation and budget-constrained selection.

## Workflow
1. **Analyze**: Determine the relevance of each record in the `evidence_pool` to the question.
2. **Validate**: Pass the pool and constraints to the deterministic helper.
3. **Verify**: Ensure the helper's output respects the `byte_budget` and handles `contradiction_groups` by marking missing sides as `unresolved`.
4. **Synthesize**: Use the validated, traceable evidence to construct the final answer.

## Limits & Constraints
- **Budget**: Total bytes of selected `content` must not exceed `byte_budget`.
- **Traceability**: Every selected record must have a `source_id`, `revision`, and an exact `span` (start/end) within the source.
- **Contradictions**: If a `contradiction_group` is provided, selecting only one side of a contradiction results in the other side being marked `unresolved` in the output metadata.
- **No Hallucination**: Do not claim a fact is proven if the selected evidence is part of an unresolved contradiction.

## Output Contract
The helper returns a JSON object containing:
- `status`: "success" or "refused".
- `selected_records`: List of validated records.
- `unresolved_contradictions`: List of IDs representing the "missing" sides of contradictions.
- `total_bytes`: Sum of `len(record.content.encode('utf-8'))`.
- `error_code`: If status is "refused".

## Abstention
The agent should abstain (return "refused" or signal inability) if:
- The `byte_budget` is too small to include all `required` records.
- The `evidence_pool` contains invalid types (e.g., booleans where integers are expected).
- The `source_id` or `revision` in a record does not match the provided registry.
