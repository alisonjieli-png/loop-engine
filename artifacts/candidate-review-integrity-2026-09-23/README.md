# Candidate review integrity checks

Offline evidence for the three review defects recorded in the
[library integration handoff](../../docs/verification/HANDOFF-LIBRARY-LS1-LS2-2026-09-23.md).
The source base is `9c57c9a4c813578bffa504108ef9d785b308bb86`.

- [Before repair](tests-before-repair.txt): 11 test methods, 16 failed
  assertions including subtests. A digest-mismatched body reached fixture
  approval; Codex substituted requested identity; Claude erased unknown and
  partial usage. A mixed Claude model set also escaped identity refusal.
- [After the first repair](tests-after-repair.txt): 234 owning-component
  tests, one optional dependency skip, no failures.
- [Before the availability repair](tests-before-availability-repair.txt):
  the new check showed Codex still eligible to spend a call although its
  response protocol could not qualify identity.
- [Final owning-component run](tests-final.txt): 235 tests, one optional
  dependency skip, no failures.
- [Final removed-guard run](removed-guards-20260923T140834059840.json): all
  six guards detected; every baseline passed and every removed guard caused
  an assertion failure, not an import or environment error. The
  [earlier run](removed-guards-20260923T140614828580.json) remains alongside it.
- [Lint before local cleanup](ruff-before.json) and
  [lint comparison](ruff-delta.json): the changed existing modules retain
  46 existing diagnostics, with zero new diagnostics. Both newly authored
  Python files pass the full local Ruff configuration after cleanup.

Run `check_removed_guards.py` with the repository dependencies available.
It executes fixed local functions with one guard removed in memory and runs
the associated regression test. It does not modify source, reach a provider
or approve any library item. Each run writes a new dated result.

The skipped owning-component case needs optional `datasketch`. These changes
do not touch its duplicate-search engine. Real provider behavior, production
deployment and full repository continuous integration are outside this record.
The [verification note](../../docs/verification/CANDIDATE-REVIEW-INTEGRITY-REPAIR-2026-09-23.md)
explains the runtime consequences and remaining record limitation.
