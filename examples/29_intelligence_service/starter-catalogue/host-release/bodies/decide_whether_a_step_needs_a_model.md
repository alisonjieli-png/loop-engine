# Decide whether a step needs a language model

Before a step calls a language model, ask whether a deterministic function, a small specialized model or a reused result would do the same job with less cost and more certainty.

## When to use it

Use it when designing a pipeline, when the cost of model calls grows, and whenever the same kind of question is sent to a model again and again.

## Steps

1. Reuse first: before reasoning, name the verified procedure, tool or earlier result that could be reused as it is, and with which parameters.
2. Necessity: for the step, ask whether a language model is the most efficient way to do it. Give the verdict, then the cheapest alternative that was considered: a registered deterministic function, a small or specialized model, or a tool written for the step.
3. Choice of implementation: compare the implementations that satisfy the contract of the step. Rank them by expected total cost, including setup, verification and recovery. Name the evidence that would change the ranking.
4. Train or call: ask whether a model trained on your own verified records would beat calling a general model. State the verified examples that you hold, the number of reuses at which the costs break even, and the verdict.
5. Data sufficiency: list each data source that a specialist would need, with its size, the quality of its labels and what is missing.
6. Minimum context: list the least information that the step needs to be done correctly, and what breaks without each item.
7. Boundary probe: state the amount of information that you believe is right for the step. Name one addition and one removal that would test that belief, and the result that would refute it.
8. Efficiency: ask whether the inputs are too large and whether the outputs are too large, and name the alternatives with a confidence for each.
9. Confidence: give a number from 0 to 100 that the chosen step is the best one, and the single observation that would lower it most.
10. When a question is answered repeatedly and the answer is a computed measure, write a function for it and keep the model for the final judgment only.

## Checks

- Every step that calls a model has a recorded verdict on necessity and a named alternative.
- The ranking of implementations counts verification and recovery, not only the first call.
- The context given to the step matches the recorded minimum, or the difference is explained.

## Known-wrong example

A pipeline sends every phone number to a large model and asks it to format the number. The task is a digit count and a country code, which a small function does exactly, for nothing, with a named reason. The model is needed only for the few values that the function cannot explain.

## What to record

- For each step: the verdict, the alternatives, the ranking and the evidence that would change it.
- The minimum context and the result of each boundary probe.
- The reuse count of every step, so that the break even point can be checked later.

## Source

- `src/loop_engine/strings/question_engine.py`: the question forms named `model_necessity`, `implementation_choice`, `train_or_call`, `data_sufficiency`, `minimum_context`, `context_boundary_probe`, `efficiency_check`, `step_confidence` and `reuse_before_reasoning`.
- `src/loop_engine/strings/interrogation.py`: the integration question about turning a repeated answer into a deterministic function.

Licence: MIT. Compiled from revision 9a483df.
