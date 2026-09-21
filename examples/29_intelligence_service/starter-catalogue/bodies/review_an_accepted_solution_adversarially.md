# Review an accepted solution adversarially

After a solution is accepted, question it once more from the outside. Ask whether it is the best way, how close it is to the worst way, what would have prevented its errors, and which missing fact could reverse the conclusion.

## When to use it

Use it after a task is accepted and before its approach becomes a habit, a template or a recommendation to others.

## Steps

1. Best and worst: ask whether this is the best way to solve the problem, what the worst way would look like, and whether the solution is accidentally near it. Compare it with a strong baseline and a naive baseline, and rank the approaches.
2. Preventable failures: list the errors that happened. Trace each failure to its earliest cause, and name the missing reusable asset, such as a check, a note or a function, that would have prevented it.
3. Missing knowledge: list the assumptions that the acceptance rested on. Name the single unknown that carries the most weight, and the fact that could reverse the conclusion.
4. The case against: argue the strongest possible case against the solution.
5. Premortem: assume that the solution was used and failed badly, and write what caused the failure.
6. Analogy: state the structure of the problem in abstract terms. Name a solved problem in another field with the same structure, and say which part of its solution transfers.
7. Attack the framing: argue that the wrong question was answered, and say which question is the right one.
8. Turn every finding that holds beyond this task into a candidate for reuse. A candidate needs an independent review before it is used as a rule.

## Checks

- The review names at least one way in which the solution could be wrong that the original verification did not test.
- Every preventable failure names its earliest cause and not only its symptom.
- The most important unknown is named, together with the observation that would settle it.
- The reviewer is not the producer, or the report says that they are the same.

## Known-wrong example

A review of an accepted forecasting model asks only whether the code is clean. Nobody asks what was unknown at the time of acceptance. The validation period held no holiday season, and the acceptance silently assumed that it did not matter. The first December in production breaks the forecast. The question about missing knowledge would have named this unknown in one sentence.

## What to record

- The comparison with the strong baseline and the naive baseline.
- Each failure with its earliest cause and the asset that would have prevented it.
- The most important unknown, and the candidates for reuse with their evidence.

## Source

- `src/loop_engine/strings/interrogation.py`: the question bank, categories `adversarial_review` and `cross_domain`.
- `src/loop_engine/strings/question_engine.py`: the question forms named `devils_advocate`, `premortem` and `analogy_probe`.
- `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml`: the perspectives of the adversary, the contrarian and the independent verifier.

Licence: MIT. Compiled from revision 0cf19eb.
