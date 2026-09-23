---
name: build-a-project-decision-provenance-map
description: Reconstruct a project's active decisions from supplied records while exposing conflicting, superseded, and ownerless decisions.
---

# Build a project decision provenance map

## Use case

Use when a project has meeting notes, issue comments, and plans that disagree about what was decided. Produce a read-only map of decisions and their authority before work relies on them.

## Required inputs

- A bounded collection of project records with stable references, authors, and dates.
- A stated rule for who may decide each subject, if such a rule exists.
- The target decision subjects and the date at which the map should be valid.

## Steps

1. Extract statements that make or change a decision. Do not classify a suggestion, question, or task assignment as an approved decision merely because it appears in a meeting note.
2. Record each decision's subject, chosen option, maker, date, source passage, stated scope, and conditions. Keep the discarded alternatives when the record names them.
3. Link each amendment or reversal to the decision it changes. A later date alone does not establish authority to override an earlier decision.
4. Mark each decision instance `active`, `superseded`, `conflicted`, or `unresolved`, then resolve the current state of its subject. A subject can have one active decision and older superseded decisions. If authority is unknown or competing authorized decisions conflict, leave the subject unresolved.
5. Draw dependencies only when the records state them or the dependency follows from an explicit contract. Mark inferred dependencies for review.
6. Return a compact map with exact references, an unresolved-conflict list, and the decisions that a planned action would rely on.

## Completion check

A reviewer can locate the source passage and authority basis for every active decision. Contradictory and superseded sources remain visible. No ownerless or authority-unknown statement becomes active merely by being recent or repeated.

## Stop or hold

Hold an action that relies on a conflicted or authority-unknown decision. Do not resolve a governance dispute by guessing, rewrite project records, or turn the map itself into an approval.
