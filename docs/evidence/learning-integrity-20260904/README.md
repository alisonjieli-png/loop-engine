# Learning-integrity evidence

This bundle supports the
[implementation report](../../verification/LEARNING-INTEGRITY-AND-RESEARCH-2026-09-04.md)
and [research synthesis](../../research/LEARNING-FROM-VERIFIED-LOOP-OUTCOMES-2026-09-04.md).

## Research

- [Source and adaptation matrix](research-matrix.json): source claims,
  assumptions, repository mappings, experiments, falsifiers, and maturity.
- [Seed coverage](seed-coverage.json): 45 arXiv seed identities, plus separately
  scoped non-arXiv sources. Metadata checks are not full methods review.

## Checks

- [Pre-change source baseline](baseline-receipt.json): 2,430/2,430 with stable
  Python-source hashes and zero provider calls.
- [Delivery source check](delivery-source-receipt.json) and
  [result](delivery-source-result.json): the accepted final checkout.
- [Delivery conformance](delivery-conformance-receipt.json): 27 gates.
- [Delivery base-wheel check](delivery-wheel-receipt.json): installed package
  outside the checkout, with optional adapters explicitly listed as not tested.
- [Build](delivery-build-receipt.json) and [artifact hashes](build-artifacts.json).
- [Validation history](validation-history.json): intermediate checks remain
  visible. A green run with source changes during execution is not accepted
  as final-checkout evidence.
- [Delivery validation](delivery-validation.json): local links, Markdown,
  source preservation, syntax, and artifact integrity checks.

## Public offline mechanism

The [saved pair report](public-offline-pair.json) has one calibration run and
two comparison arms, with 21 total injected provider attempts. The advisory
fixture records `USE`; the fresh fixture records `START_FRESH`. All three
Run Histories are intact.

The [run artifacts](../runs/learning-integrity-public-offline-20260904/) include
prompts, exposures, decisions, action/verification records, and outputs.
Both model responses and project execution are injected. Fixture-reported
token counts are not live usage or cost evidence. This is `mechanism_only`,
not a valid live pair, independent semantic evaluation, or causal benefit.

## Reorientation

[Session state](session-state.json) records exact revision, dirty paths,
worktrees, process names/working directories, and the eight changed Python
files with before/after hashes. No process arguments, environment values,
keys, or authorization headers are exported.

[Authority hashes](source-authorities.json) identify the current repository
contracts. [Bundle manifest](bundle-manifest.json) identifies each generated
artifact. These reports do not replace Run History or grant future execution
or promotion authority.
