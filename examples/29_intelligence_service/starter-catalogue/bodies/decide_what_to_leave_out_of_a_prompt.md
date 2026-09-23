# Decide what to leave out of a prompt

Fit a step inside its budget by removing the least useful material first, and by saying plainly when the work does not fit.

## When to use it

Use it when the material for a step is larger than the window, larger than you want to pay for, or so large that the important part is lost among the rest.

## Steps

1. Rank the parts by how much the step's answer depends on them. The exact input it must act on ranks first.
2. Set a byte or token allowance for the whole step, and a separate allowance for each heavy part.
3. Remove whole parts before shortening any part. A missing section is honest; a silently truncated one is misleading.
4. When you must shorten, cut from the middle and mark the cut, so the reader and the model both know material was removed.
5. Remove repeated copies of the same bytes. Keep the copy that belongs to the current step and drop the older ones.
6. Never shorten the instruction, the output shape or the rules. Shorten the material instead.
7. Set a floor. Below a certain size a part carries nothing useful, and the right answer is to stop and say the work does not fit.
8. Record what was left out, so a wrong answer can be traced to a missing part.

## Checks

- The exact input the step must act on is never shortened.
- Removals happen in a stated order, not wherever the text ran out.
- Every shortened part is marked as shortened.
- When nothing more can be removed, the step reports that the work does not fit.

## Known-wrong example

A step builds the prompt by adding parts until the window is full, in the order the parts were written. The rules and the output shape sit last and fall off. The model answers in prose instead of the required shape, and the failure is blamed on the model. Ranking the parts and protecting the instruction would have removed an old piece of history instead.

## What to record

- The allowance for the step and for each heavy part.
- What was removed or shortened, in what order.
- The cases where the step reported that the work did not fit.

## Source

- `src/loop_engine/core/context_budget.py`: this repository holds a typed budget policy that names the fields carrying live input for the current step, names the heavy lists that share a byte allowance, halves the allowance a bounded number of times, and stops rather than producing something that fits and says nothing.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision a0ca182.
