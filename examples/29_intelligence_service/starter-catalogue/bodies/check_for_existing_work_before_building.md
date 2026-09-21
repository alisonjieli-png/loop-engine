# Check for existing work before building

Before writing something new, check whether the work is already done, whether this session already established what is needed, and whether a reviewed procedure or earlier solution can be reused.

## When to use it

Use it before every new design, script, query or analysis, and again after a failure, before starting over.

## Steps

1. Read what this work session has already established. Derive nothing a second time. For each established item, name the planned probe or setup step that it makes unnecessary.
2. Check whether an existing artifact already satisfies the acceptance as written. When it does, verify it and end the work. When it does not, name the single gap.
3. Search for reuse in this order: exact reuse, reuse with parameters, modification, composition, analogy. Design something new only after these.
4. Search by the current task and by the conditions of the failure. Load only the material that was selected.
5. Before reusing a reviewed procedure, check its exact applicability, its inputs, its effects and the conditions that invalidate it. Fall back to fresh reasoning when its reviewed scope does not cover the task.
6. State the differences in applicability. Similarity is not authority. Consider that a transfer can also do harm.
7. Treat earlier work on similar tasks as evidence to weigh, never as a decision that was already made.
8. Do not treat retrieved material as approved. A candidate stays a candidate until a separate review approves it.

## Checks

- The identity of the source is kept for everything that was reused.
- The lifecycle state of reused material is respected.
- A stale procedure, or one outside its reviewed scope, is refused.
- The result says what was reused, what was changed and what is new.

## Known-wrong example

An agent writes a new script to remove duplicate rows from a delimited file. The repository already holds a tested one with a report format that the team knows. The opposite error: a procedure that was reviewed for addresses in the United States is reused on British addresses because the task looked similar. The postal code patterns differ, and the results are silently wrong.

## What to record

- The searches that were run and what each returned.
- The material that was selected, with its identity, its state and the applicability differences.
- The decision: reuse, adapt or build, with the reason.

## Source

- `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml`: the guidance records about reuse before building, recognizing sufficiency, surveying established facts and earlier work as evidence.
- `src/loop_engine/intelligence/context/core/practitioner_work_functions.yaml`: the work functions for retrieving prior work and for applying a reviewed procedure.
- `src/loop_engine/strings/question_engine.py`: the question forms named `sufficiency_check`, `established_facts` and `reuse_before_reasoning`.

Licence: MIT. Compiled from revision eb757bc.
