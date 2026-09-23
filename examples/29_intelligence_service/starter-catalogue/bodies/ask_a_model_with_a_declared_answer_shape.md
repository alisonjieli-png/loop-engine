# Ask a model with a stored question form and a declared answer shape

Keep the ways of asking as stored templates. Each template declares the shape of its answer, so the reply can be parsed by contract. Vary the asking without a random source.

## When to use it

Use it when a language model is asked the same kind of question many times: to propose, rank, eliminate, check, compare or decompose.

## Steps

1. Store each way of asking as a named form with placeholders, for example `{task}`, `{options}` and `{candidate}`.
2. Declare the answer shape of each form from a closed list: proposals, ranking, score, elimination, verdict, comparison, decomposition, list or free text.
3. Check that the declared placeholders equal the placeholders in the template. Refuse to render a form when a value is missing. A form never leaves half filled.
4. Use forms such as these:
   - elimination: given candidate solutions, eliminate every one that cannot work, with the disqualifying reason, and keep only the survivors;
   - check: given a proposed solution, say whether it is correct, complete and safe, with the verdict first and the defects after it;
   - pairwise: given A and B, say which is better and why, with the letter first;
   - premortem: assume the candidate was tried and failed badly, and write what caused the failure;
   - calibration: give each option a probability of success with one sentence of reasoning.
5. To get different views, combine each form with a reviewer persona and with one fixed reframing sentence, for example `Assume the obvious answer is wrong.` or `Answer first, then list what would change your mind.`
6. Generate the combinations in a fixed order. In the stride order every form appears once before any form repeats, so a short sample still covers all forms. The same inputs always give the same sequence.
7. Register a form that a model wrote once, as experimental, with its provenance. It earns a higher tier only through recorded outcomes.

## Checks

- A reply that does not have the declared shape is rejected before it is used.
- Two runs with the same inputs produce the same sequence of questions.
- A form whose placeholders cannot all be filled is skipped and is not rendered with gaps.

## Known-wrong example

A pipeline asks the model in free prose to have a look at three options and then searches the reply for the word best. The reply praises all three. With the elimination form, the reply must name the options that cannot work and the reason for each, and the parser knows where to find them.

## What to record

- The form, the persona, the reframing sentence and the filled values of every question.
- The declared answer shape and whether the reply matched it.
- The provenance of every form that a model wrote.

## Source

- `src/loop_engine/strings/question_engine.py`: `QuestionForm`, `core_forms`, `multiply`, `register_generated_form` and the fixed reframing sentences.

Licence: MIT. Compiled from revision 40fce69.
