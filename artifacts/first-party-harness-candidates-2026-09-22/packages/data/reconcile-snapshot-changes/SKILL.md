---
name: reconcile-snapshot-changes
description: Classify added, removed, and changed records between two complete snapshots. Use when comparing periodic exports or state captures by stable identity.
---

# Reconcile snapshot changes

## When to use

Use this to explain what changed between two captures of the same population. A partial extract, a different filter, or a changed identity rule cannot support a removal claim.

## Inputs

- Two read-only snapshots with capture time, scope, and completeness status.
- A stable entity key and the fields whose changes matter.
- Rules for comparing empty values, types, and normalized representations.

## Procedure

1. Confirm both captures cover the same population and that the entity key is stable across them. Count rows, null keys, and duplicate keys in each.
2. Build one record per key only when duplicate handling is explicitly defined. Otherwise hold duplicate keys for review.
3. Compare key sets to identify additions and absences. Call an absence a removal only when the newer capture is complete for that scope.
4. Compare selected fields for keys present in both. Keep the before and after values for each changed field; do not hide changes behind a single hash.
5. Reconcile counts: old keys plus additions minus removals must equal new keys. Report unchanged and unresolved keys separately.

## Completion check

Return counts and keyed examples for added, removed, changed, unchanged, and unresolved records. State the capture scopes and the exact comparison fields. The categories must account for every unique key in the union.

## Stop conditions

Do not classify removals if either capture's scope or completeness is unknown. Stop on key collisions or changed identity semantics until the owner supplies a mapping. Do not mutate either snapshot.
