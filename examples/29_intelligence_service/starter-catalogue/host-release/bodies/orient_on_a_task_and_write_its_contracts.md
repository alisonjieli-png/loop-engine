# Orient on a task and write down its contracts

Understand what is asked before doing anything. Then write the task in a typed form that loses nothing from the original request.

## When to use it

Use it at the start of every task that is more than one obvious step, and whenever work passes from one agent or person to another.

## Steps

1. Keep the original request unchanged beside every interpretation of it.
2. Answer the orientation questions:
   - What is the person actually asking to accomplish? What are the current state and the desired state?
   - Which inputs were supplied, and which must be discovered?
   - Which outputs and artifacts are expected, and what kind of response is required?
   - What will consume the result, and what evidence would prove that the task is complete?
   - Which constraints, permissions, risks and unknowns matter? What must not happen?
   - Which choices are left to best judgment? Which values can be derived or safely defaulted?
   - What needs research, a question to the person, or more authority?
   - Which independent parts does the task have, what depends on what, and what can run in parallel?
   - Which folders, files, data and tools have been inspected, and which are only assumed?
   - Where should the work happen, and what must the working folder contain and allow?
   - When the literal outcome cannot be completed yet, what useful report, draft, estimate or model can still be completed?
3. Write the task statement with five contracts: input, output, success, failure and verification.
4. Label every statement as a fact, a preference, a delegated choice, an assumption or an unknown.
5. Name the form of the response and the person or system that will use the decision.

## Checks

- The goal of the original request is preserved.
- Every input and every output is covered.
- Every constraint is preserved.
- A reader who sees only the task statement would do the same work.

## Known-wrong example

The request says: clean the customer file and send me the result. The agent starts editing the file in place. Orientation would have found four gaps. Clean is not defined. The output format is not stated. Sending is an external effect that needs permission. Editing in place destroys the input.

## What to record

- The original request and the answers to the orientation questions.
- The task statement with its labelled statements and its open questions.

## Source

- `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml`: the questions of the orient and standardize steps, and the guidance records about preserving the original request and separating facts from assumptions.
- `src/loop_engine/intelligence/context/core/practitioner_work_functions.yaml`: the work function for orienting and representing a task.

Licence: MIT. Compiled from revision 7ed4e85.
