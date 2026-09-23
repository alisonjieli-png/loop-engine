# Analyse errors by segment and by cluster

Read the individual failures, not only the total score. Find the segments that are always wrong and the few repeating types of error that one targeted fix would remove.

## When to use it

Use it when a model, a pipeline or an automated process has an acceptable average and unexplained failures, and before deciding what to improve.

## Steps

1. Systematic bias: ask whether the errors are systematic, which means a segment that is consistently wrong. Compute the error rate by segment and by feature bin, and analyse the slices.
2. Error clusters: ask whether the errors fall into a small number of repeating types. Cluster the failures by their message, by the shape of the failing input and by the step where they happened. Count the share that each cluster covers.
3. Errors of errors: ask whether there are patterns inside the errors, and inside the errors that remain after a correction. Model the residual, then model the residual of that model, and look for repeated structure.
4. Read a sample of individual failures from each cluster and say what they have in common.
5. Rank the clusters by their share, and choose the one fix that removes the largest cluster.
6. After the fix, repeat the analysis. The next largest cluster is often a different problem.

## Checks

- Every reported error rate has a count behind it.
- The shares of the clusters add up to the total, with a named remainder for failures that were not clustered.
- A segment is only called systematic when its difference is larger than the noise of its sample size.
- The chosen fix names the cluster that it targets and the expected change of the share.

## Known-wrong example

An extraction pipeline fails on 8 percent of documents. The team adds general retry logic, and the rate stays at 8 percent. A clustering of the failures shows that 6 of the 8 points come from one input shape: scanned pages that are rotated by 90 degrees. One rotation check removes three quarters of the failures. Retrying could never have helped, because the same input fails in the same way every time.

## What to record

- The error rate by segment, with counts.
- The clusters with their shares, and an example of each.
- The chosen fix, its target cluster and the share after the fix.

## Source

- `src/loop_engine/strings/interrogation.py`: the question bank, category `error_patterns`.
- `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml`: the perspective of the error analyst.

Licence: MIT. Compiled from revision 565e133.
