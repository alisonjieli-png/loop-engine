# Hand over a result that its consumer can use

Shape the result for the person or system that will use it. Include the evidence, the assumptions, the limits and the further steps, so the consumer does not need to know how the result was produced.

## When to use it

Use it at the end of a task, before a report, a pull request, a data file or an answer leaves the work session.

## Steps

1. Name who or what consumes the result. Ask what would make the result useless to them even when it is technically correct.
2. Choose the structure and the wording for that consumer: the structure of the report, the layout of the artifacts, and plain direct wording.
3. Include the evidence, the assumptions, the limits and the further actions.
4. Ask whether someone who was not present could run this again from what is written down.
5. Check provenance. Ask where each input came from, what its use permits, and whether the result may be distributed as intended.
6. Check privacy. Identify personal or identifying data, where it travels, and what the result would reveal about an individual.
7. Separate the verified results that are safe to build on from the observations that stay local to this work.
8. Stage reusable lessons and procedures as candidates for an independent review. The producer does not approve its own lessons.

## Checks

- The consumer can use the result without rework and without asking how it was made.
- The provenance of every input is kept.
- Every lesson for reuse is marked as a candidate.
- The references to outputs are exact: path, version or digest.

## Known-wrong example

A manager asks whether the migration can go ahead on Friday. The answer is a log of two thousand lines and a sentence that says to see the details above. The manager needed a yes or a no, the three largest risks and what is still unknown. The work was correct and the handover was useless. The same content, shaped for the person who decides, fits on half a page.

## What to record

- The consumer and the form that was chosen for them.
- The exact references to the delivered artifacts.
- The staged candidates for reuse, with their evidence.

## Source

- `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml`: the questions of the step that integrates and commits results, and the perspectives of the interface designer, the documentation author, the provenance reviewer and the privacy reviewer.
- `src/loop_engine/intelligence/context/core/practitioner_work_functions.yaml`: the work function for communicating and preparing reuse.
- `src/loop_engine/strings/question_engine.py`: the question forms named `report_shaping` and `stakeholder_view`.

Licence: MIT. Compiled from revision db18890.
