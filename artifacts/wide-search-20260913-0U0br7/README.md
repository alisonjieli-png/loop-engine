# Wide-search implementation controls

These records describe proposal mechanics and a disclosed deterministic
Solution Canvas control. They are not a full task-database benchmark.

- [Verification](verification-summary.json): source, base installation,
  optional optimizer checks, and verified control-history totals.
- [Control outcomes](control-summary.json): all five methods, including
  the methods whose selected result failed the fresh-input check.
- [Trial histories](trial-history-summary.json): every trial's score,
  graph identity, evaluation digest, and verified history identity.
- [Package source](package-source-manifest.json): exact tested package bytes.

The selected-control folders retain the Canvas, rendered view, evaluation,
and fresh-input result for grid search, random search, Bayesian search,
genetic search, and covariance adaptation. The full 120 histories, every
proposal, and the 1,771-record task-pool inventory remain in the local
`.loop-engine-dev/wide-search-20260913-RMCLd0/controls-final/` directory.

The address control represented 1,000,000,000,000 configurations and checked
10,000 address round trips. Its 30,392-byte peak is traced allocation during
that address test, not total process memory or trial-storage usage.

All methods received 24 trials on the same disclosed arithmetic relation.
Bayesian and genetic search found the exact result and passed fresh-input
replay; grid, random, and covariance adaptation did not within this control.
This does not establish a generally superior optimizer.

Early verification failures remain local: the first isolated control
environment lacked `jsonschema`; the first source check found a stale
packaged architecture file; an early wheel captured another session's
in-progress work-ceiling default. Dependencies and projections were corrected
and a fresh source and wheel verification were run. The final counts refer
only to the `release-source` and `release-wheel` records.

Read the [path and dimension map](../../docs/verification/RUN-PATH-AND-DIMENSION-COVERAGE-2026-09-13.md)
and [research review](../../docs/research/HYPERLAMBDA-AND-WIDE-SEARCH-2026-09-13.md)
for implemented and unqualified boundaries.
