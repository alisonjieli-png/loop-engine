# Escalate an uncertain value with candidates and one fixed question

When a deterministic pass cannot decide a value, hand over a small typed request: the value, the candidates with their confidence, the reasons, one fixed question and the ordered places to ask. The request itself makes no call.

## When to use it

Use it after a rule based pass leaves values below the escalation threshold. Use it also for held values when the policy says that held values are escalated.

## Steps

1. Build one request for each uncertain cell. Include the row reference, the column and the input value.
2. Include at least one candidate. The first candidate is the proposed output with its confidence. When the proposal differs from the input, the second candidate is the input with one minus that confidence.
3. Include the named reasons from the deterministic pass.
4. Name the ordered targets, drawn from a closed list: a model judgment, research in a browser, review by a person.
5. Render one fixed question form. It names the column, the task, the value and the candidates, asks for a ranking with a confidence from 0 to 1 or a better form with its reason, and allows abstaining when no candidate is defensible.
6. Name the response contract, so the answer can be checked before it is used.
7. Let the caller dispatch the request under its own permissions. Building the request grants nothing and spends nothing.
8. Store each accepted answer as an entry in the top exception layer, so the same value is not asked again.

## Checks

- For the held value `AA CAREERS`, the candidates are `AA Careers` at 0.75 and `AA CAREERS` at 0.25.
- A request with no candidate is refused. A target outside the closed list is refused.
- The number of requests equals the number of escalated values, plus held values when that option is on.

## Known-wrong example

A pipeline sends the whole column to a language model with the instruction to clean it. The model rewrites confident values too, nothing names a reason, and the cost grows with the table. The correct request covers only the uncertain cells, carries candidates and allows the answer to abstain.

## What to record

- Each request and the target that answered it.
- Each answer with its confidence, and whether it became an exception entry.
- The decision that a model was the next step, with the confidence that fell short.

## Source

- `src/loop_engine/code_nodes/text_conformance.py`: `EscalationRequest`, `ConformancePolicy` and `run_conformance`.
- `src/loop_engine/strings/question_engine.py`: the stored question form named `disambiguate_value`.

Licence: MIT. Compiled from revision db18890.
