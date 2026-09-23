# Resolve missing information before asking the person

Decide for each missing item how it can be resolved and who owns the answer. Ask the person only when the answer matters and only the person can give it.

## When to use it

Use it whenever a task has gaps: an unstated format, an unknown version, a missing file, an unclear permission.

## Steps

1. List every fact that is missing before the work can proceed safely. Rank the unknowns by how much each one blocks.
2. Give each item one disposition: derive it, research it, retrieve it, request it from the person, assume it with a label, or leave it unknown.
3. Retrieve or research before asking, when the question can be answered safely without the person.
4. Ask the person only when the answer materially changes the outcome, the authority, safety, privacy, the cost boundary, the acceptance or the usefulness.
5. When best judgment is allowed, select one defensible option and record the rationale. Do not return a list of options for the person to sort out.
6. Keep unknown, conflicting, insufficient and blocked as states of their own. Unknown does not mean no.
7. Never turn a proposal into a permission. A guess about what the person would allow grants nothing.

## Checks

- Every question to the person is justified by one of the reasons in step 4.
- Questions that the system can answer stay inside the system.
- Every assumption is labelled and can be found again in the result.
- An unknown value is still unknown in the final report.

## Known-wrong example

An agent stops and asks five questions. One asks which Python version is installed, which one command would show. One asks which of two equal libraries to use, which was a delegated choice. One asks whether it may email the report to the customer, which is the only question that needed the person. The useful message is one question about the email, with the other four items resolved and recorded.

## What to record

- Each missing item with its disposition and its owner.
- Each assumption with its label, and each question with its reason.
- The items that remain unknown.

## Source

- `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml`: the guidance records about material questions, delegated choices, unknown states and permissions.
- `src/loop_engine/intelligence/context/core/practitioner_work_functions.yaml`: the work function for acquiring missing information.
- `src/loop_engine/strings/question_engine.py`: the question form named `state_the_unknowns`.

Licence: MIT. Compiled from revision 9a483df.
