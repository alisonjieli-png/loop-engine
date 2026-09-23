# Propose a dedupe without deleting rows

Turn duplicate pairs into clusters, choose one survivor for each cluster, and publish the result as a proposal. The rows stay untouched, and possible pairs wait for a decision.

## When to use it

Use it after duplicate pairs have been scored, when someone must approve the merge before any data changes.

## Steps

1. Build clusters only from pairs that were classified as duplicates. A possible pair never joins two clusters.
2. Choose one survivor for each cluster with a declared strategy. `keep_first` keeps the row that comes first in the table. `keep_most_complete` keeps the row with the most filled fields and breaks ties by table order.
3. Write the proposal: the strategy, the survivors, each merge with its survivor and its merged identities, the rows in and the rows out.
4. Turn each possible pair into one bounded decision request. The question asks whether the two records describe the same entity. There are exactly two candidates: same entity and different entities. The evidence is the field values of both rows and the measured signals.
5. Treat each answer as a decision record. An answer is not a merge. Apply merges only when a separate step copies the table with the approved proposal.

## Checks

- The rows out equal the rows in minus the merged rows. With six rows and one cluster of two rows, the proposal keeps the first row of the cluster under `keep_first`, merges the other row and reports 6 rows in and 5 rows out.
- The possible pairs stay outside the clusters before and after the decision requests.
- An unknown strategy is refused.
- The source rows are equal before and after.

## Known-wrong example

A job chains possible pairs into clusters. Row A is possibly B, and B is possibly C, so A and C are merged. A and C were never compared as duplicates, and a weak link joined two different companies. Only duplicate pairs may build clusters. A second wrong design deletes the merged rows from the source table. After that no reviewer can check the decision.

## What to record

- The proposal with its strategy, survivors and merges.
- Each decision request with its answer and the record of the call that answered it.
- The identity of the duplicate report that the proposal was built from.

## Source

- `src/loop_engine/code_nodes/duplicate_detection.py`: `dedupe`, `DedupeProposal`, `escalation_request` and `decide_possible_pairs`.

Licence: MIT. Compiled from revision 9cec9d7. The module imports the typed decision module of the same package for the decision requests. The proposal itself is plain data.
