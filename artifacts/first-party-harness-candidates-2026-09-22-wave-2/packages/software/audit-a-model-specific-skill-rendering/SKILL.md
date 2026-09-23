---
name: audit-a-model-specific-skill-rendering
description: Compare a condensed or reworded skill candidate with its approved source, checking preserved obligations and exact model applicability before review.
---

# Audit a model-specific skill rendering

## Use case

Use when a source skill has been shortened, simplified, expanded, or reworded for one model. Produce an obligation and native-format review packet; this skill cannot approve the derivative.

## Required inputs

- The exact approved source package and digest, derivative candidate and digest, and transformation record.
- The intended provider, model revision, tokenizer or chat template identity when relevant, target harness layout, and task population for later comparison.
- Source permissions, limits, negative conditions, output contract, and relative resource map.

## Procedure

1. Extract each obligation from the source: required input, permitted effect, prohibition, approval condition, output field, exception, and stop rule. Retain source locations.
2. Map each obligation to a derivative passage or mark it missing, changed, or ambiguous. Check negations, numbers, units, recipients, and examples that could be mistaken for commands.
3. Check native package structure, frontmatter identity, relative resource paths, and any client size or activation rule. A shorter body that loses a required reference is not equivalent.
4. Check whether the transformation created new factual claims or broadened authority. Mark every new claim for source and rights review; the parent approval does not transfer to changed bytes.
5. Specify a positive task and at least one known-wrong task where dropping a protected obligation would cause an observable error. Reserve a separate held-out comparison of source, derivative, and no-skill conditions for the exact target model.
6. Return the obligation matrix, format findings, model-binding record, test proposals, and independent-review questions.

## Completion check

Every required source obligation is preserved or explicitly marked as a blocking loss. A derivative that changes `no network` to optional network fails the semantic check even if it uses fewer tokens.

## Stop or hold

Hold approval, serving, or a cost-saving claim when a required clause is missing, the exact model changed, rights are unclear, or matched-task evidence is absent. Do not publish, install, or treat this audit as independent approval.
