# Check that a result is stable and holds beyond the sample

Find out whether a result is a wide stable plateau or a fragile spike, and whether it will hold on data from another time, source or population.

## When to use it

Use it before a model, a setting or a finding is accepted, and before a small improvement is reported as real.

## Steps

1. Noise: estimate the noise in the labels and the measurements. Consider robust losses, denoising and the variance between repeated cross-validation runs.
2. Plateau or spike: run a sensitivity sweep over seeds, folds and feature subsets, and report the spread. A result that survives the sweep is a plateau. A result that needs one seed is a spike.
3. Sensitivity: change one input at a time and rank the inputs by how much the result moves. Decide whether the strongest dependence is acceptable.
4. Gap: ask whether the gap between training and cross-validated performance is a real signal or an artifact of the measurement. Repeat the cross-validation with several seeds and folds, and report the spread of the gap.
5. Shift: ask how the result would behave on inputs from a different time, source or population. Profile the drift of the features between the development sample and any newer sample, and test on the shifted slice.
6. Sample dependence: ask which parts of the result depend on details of this sample. Remove features and parameters one at a time, and note which removals barely change the outcome.
7. Name the first condition outside the sample that would break the result.

## Checks

- The reported number comes with its spread over seeds and folds.
- An improvement that is smaller than the spread is reported as not shown.
- At least one test used data from another time, source or population. Otherwise the report says that no such data exists.

## Known-wrong example

A new feature raises the score from 0.842 to 0.846 on one seed, and the team ships it. Over ten seeds the score moves between 0.838 and 0.849 with or without the feature. The improvement is inside the noise. The sweep costs ten runs and saves a release that changes nothing.

## What to record

- The sweep: seeds, folds, feature subsets and the spread of the result.
- The ranking of the inputs by their effect on the result.
- The shifted slices that were tested, with their results, and the condition that would break the result.

## Source

- `src/loop_engine/strings/interrogation.py`: the question bank, categories `noise_and_stability` and `generalization`.
- `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml`: the perspectives of the statistician and the generalization critic.

Licence: MIT. Compiled from revision d893bba.
