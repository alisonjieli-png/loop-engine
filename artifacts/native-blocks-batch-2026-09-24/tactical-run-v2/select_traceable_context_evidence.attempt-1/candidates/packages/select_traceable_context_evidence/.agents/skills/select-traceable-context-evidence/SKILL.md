# Skill: select-traceable-context-evidence

## Description
A deterministic tool for selecting a subset of evidence records that are valid, traceable to a source registry, and fit within a specified byte budget. It is designed to support model-led reasoning by providing a "ground truth" selection mechanism that handles contradictions explicitly.

## Applicability
Use this skill when you have a large pool of potential evidence and need to extract a compact, verifiable set of facts to answer a question. It is particularly useful when the evidence contains conflicting claims.

## Workflow
1. **Model Phase**: The agent analyzes the question and the `evidence_pool` to determine which `id`s are `required_ids` and which `contradiction_groups` exist.
2. **Tool Phase**: The agent calls the `select_evidence.py` script with the determined constraints.
3. **Verification Phase**: The agent checks the `unresolved_contradictions` in the output. If a fact is part of an unresolved contradiction, the agent must phrase the answer with appropriate uncertainty (e.g., "Evidence suggests X, though Y remains unresolved").

## Implementation Details
- **Executable**: `.agents/skills/select-traceable-context-evidence/scripts/select_evidence.py`
- **Input Contract**: `contracts/input.schema.json`
- **Output Contract**: `contracts/output.schema.json`
- **Example Input**: `examples/input.json`
- **Example Output**: `examples/output.json`

## Distinction: Relevance vs. Integrity
- **Relevance (Model-led)**: Deciding if a record is "important" or "required" for the answer.
- **Integrity (Tool-led)**: Deciding if a record is "valid" (correct span, within budget, correct type).
The agent provides the relevance; the tool provides the integrity.
