# September 13 integration verification

This directory contains the bounded evidence for the
[Astra integration review](../../docs/verification/ASTRA-INTEGRATION-REVIEW-2026-09-13.md).
It contains no provider credentials or private session transcripts.

- [Verification summary](verification-summary.json): source, clean-wheel,
  conformance, development checks, and offline examples.
- [Package source manifest](package-source-manifest.json): exact file digests
  used to build the tested wheel, checked against the final source.
- [Hardcoding delta](hardcoding-delta.json): the still-failing audit gate,
  compared with the starting revision using the same corrected scanner.

Full local command output and DuckDB projections remain under
`.loop-engine-dev/astra-integration-20260913-zDN3bn/`. The first in-progress
source check retained one failed missing-directory expectation. The release
checks followed its correction. An earlier wheel passed but preceded the
last prompt-file and process cleanup changes, so a new wheel was built and
checked again. Only the `release-source` and `release-wheel` results describe
the final package bytes.
