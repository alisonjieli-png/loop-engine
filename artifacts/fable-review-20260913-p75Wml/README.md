# Local review preparation, September 13, 2026

Start with the
[Claude Fable 5.1 review handoff](../../docs/context/CLAUDE-FABLE-5.1-REVIEW-HANDOFF-2026-09-13.md)
and the
[complete configuration dimension requirement](../../docs/architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md).
The owner requires initial choices and ordered fallback priorities for all
25 recorded dimensions. The document distinguishes that target from the
narrower current implementation.

This directory is a local review artifact, not a release or a new Run History
store. Nothing here was sent to another model, committed, or published.

## Review files

- `review-summary.json`: generated check results, exact source comparison,
  limitations, and preserved failed attempts.
- `source-manifest.json`: exact names, sizes, and digests of the selected
  review files, including untracked first-party source.
- `source-review.zip`: current package source, selected architecture and
  context documents, authored experiment files, review evidence, and a
  generated comparison against the scoped pre-change source baseline.
- `review-projection.duckdb`: rebuildable review report projection. Canonical
  Run History remains with its existing writer.

The archive is a selected review surface, not a complete repository backup.
It excludes provider credentials, private session stores, raw model prompts,
local run directories, installed dependencies, copied repositories, and
large benchmark datasets. Some links from selected documents refer to other
files in the full repository. The manifest states the exact included scope.

Use the shared repository to resolve a dependency or historical reference
that is outside the archive. Do not assume the archive installs third-party
harness runtimes or authorizes their execution.

## Verification and limits

The final source suite passed 3,940/3,940. A fresh Python 3.10 environment
installed the newly built distribution with its base dependencies and DuckDB,
then passed 3,905/3,905. The targeted runtime checks passed 175/175. The
experiment and documentation suite passed 39/39. Exact command output,
conformance results, source digests, and documentation checks are retained in
the generated summary and archive.

The clean installation did not exercise the optional Model Context Protocol,
embedding, data-science, and telemetry integrations. The source suite's
optional checks remain local contract tests. Hosted continuous integration,
browser behavior, and live model qualification of the new selection policy
are not claimed.

Failed intermediate attempts are preserved. They include an incomplete
package-source copy, a stale packaged terminology projection, a report-shape
error in the targeted-check exporter, and an interrupted scan of installed
third-party dependencies. None was reclassified as a success.

The source baseline and full working evidence remain in
`.loop-engine-dev/step-adaptation-20260913-ziLjPa/`. The 70-call live
configuration study remains a separate earlier experiment in
`.loop-engine-dev/configuration-study-20260912-KRiBSo/`; it does not qualify
the later selector or semantic evaluator.

Markdown edits follow the repository's neutral technical writing rules and
the humanizer skill, preserving exact terms, historical conclusions under
explicit correction notices, and the complete behavioral explanation.
The prose check uses the workflow-pinned
[Vale 3.18.0 release](https://github.com/vale-cli/vale/releases/tag/v3.18.0)
with the repository's existing rules. No lint rules or failure baselines were
relaxed for this review.
