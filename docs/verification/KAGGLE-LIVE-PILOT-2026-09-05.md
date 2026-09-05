# Live provider and Kaggle pilot

The configured Ollama endpoint answered a real probe. A subsequent public
`solve_task` run generated and executed a tabular prediction tool in Docker.
Its eight generated tests passed, but independent source review found defects
that contradict the task contract. The tool is not accepted for competition
use. No competition data was downloaded and no Kaggle submission or score was
produced in this checkpoint.

This is a hand-authored verification report over saved evidence. The
[evidence export](../evidence/kaggle-live-pilot-verification-2026-09-05.json)
contains source hashes, exact verification commands, private report references,
archive hashes, usage totals, and the original runtime outcome. It is not an
operational record store. The separate repair run is outside this initial
checkpoint's call totals.

## Authority and source state

Work started on `main` at
`690303f3ee97669f638da950daca665b747f450d`. The user authorized a real Kaggle
campaign and specified no monetary spending ceiling. The separate showcase
worktree and unrelated operator processes were left untouched. The changed
files were assigned explicitly and reviewed independently.

No monetary ceiling does not establish a token bound, approve new competition
terms, permit raw-data export, or remove platform quotas. The initial tool
pilot had a 40-call and 40-pass execution guard with no total-token ceiling.
It finished before either guard. Only the public task description and generated
synthetic data were used. The configured local environment exposed an Ollama
credential and standard Kaggle credentials; other named hosted providers were
not tested.

## Implementation changes

| Boundary | Change | Evidence |
|---|---|---|
| Source inspection | One read supplies selected text, digest, and manifest metadata. Root symlinks are refused before resolution. | Source checks and independent review. |
| Project inputs | A previously selected input cannot disappear silently or remap to another file with the same basename. | Missing-file, alias, and changed-content regressions. |
| Live provider probe | An explicit `allow_unbounded_total_tokens=True` grant permits a one-call, finite-timeout probe without a total-token ceiling. Omission alone still refuses; a grant cannot override an explicit ceiling. | 16 offline checks and one real call. |
| Kaggle selection | An optional `--search` filter is included in the frozen population identity. Resume rejects changed filters. | 34 access-preflight checks. |
| Source qualification reader | New filtered populations and legacy unfiltered populations retain their exact digest shapes. Tampering refuses. | 39 qualification checks. |

These changes use existing contracts and the canonical `Loop`. They introduce
no competition-specific solver or second runtime. The source repair does not
provide an atomic directory snapshot or immutable capture across separate calls.

Strict total-token budgets still require a qualified exact-request provider
bound. The no-ceiling probe does not qualify that mechanism. UTF-8 prompt length
is no longer described as a trustworthy minimum billed-token count.

## Real provider result

The exact route was `ollama_cloud / cloud.default / deepseek-v4-flash:0731`.
The probe requested the source-backed 65,536-token output capacity and returned
the exact expected repository metadata in one physical call: 66 input tokens,
100 output tokens, 166 total, and 0.930 seconds. It saved no raw prompt,
completion, credential, or provider error text.

Ollama publishes token-based pricing and plan-specific usage credits. An API
key does not establish a zero-price route. Actual invoiced cost was not retrieved
and remains unknown. See [Ollama pricing](https://ollama.com/pricing) and
[usage accounting](https://docs.ollama.com/api/usage).

## Initial generated tool

The public specification requested a configurable CSV training and prediction
CLI, fold-local preprocessing, probability output, exact identifier alignment,
and executable synthetic tests. No real competition rows were supplied.

The runtime returned `COMPLETED_VERIFIED` for run
`adaptive-73203b75487eece93d022b8b` after 515.029 seconds. It recorded 26 physical
model calls, 22 tool calls, and 276 Loops. All 608,331 provider-reported tokens
were accounted for: 494,788 input and 113,543 output.

One physical response lacked an admissible final answer. A counted recovery
call selected a retry. Twenty-five calls requested full source-backed capacity;
one retry used a reasoned 4,096-token allocation. That allocation was a recorded
decision, not a new default or an accounting estimate.

The 2,582-event Run History verifies as intact and binds the exact saved
outcome. Its head is
`715afded27b7eaaa6bae0cf91a5e9685dffc7987dbd230ee6d4e8376cb7bf536`.

Independent source review rejected the tool's broader correctness claim:

- Preprocessing is fitted before the cross-validation split, leaking validation
  information into training-fold transformations.
- Predictions are paired positionally with sample-submission IDs. A reordered
  sample can silently assign a prediction to the wrong ID.
- High-cardinality categorical input can produce a sparse matrix that the
  selected classifier cannot consume.
- Metrics are always labeled synthetic, even when called with another input.

The generated tests missed these cases. Their synthetic AUC is not accepted as
leakage-free validation evidence and is not a Kaggle score. The original outcome
and source remain unchanged for diagnosis. A separate model-led repair was
started from these findings; it cannot retroactively make the first run correct.

## Kaggle readiness

A fresh filtered access preflight selected one competition and
read its complete three-file listing: 70,743,425 listed bytes. A source-page
check stored seven private page artifacts and an intact 415-event Run History.
It returned `DEFERRED`, not `QUALIFIED`.

The remaining gates are human data-use review, independent evaluator review,
and deadline normalization. The public timeline supplies UTC dates, but the
current qualification reader still refuses the timezone-free deadline returned
by the CLI. Accessible metadata is not a source-bound data-use review.
The [competition rules](https://www.kaggle.com/competitions/playground-series-s6e9/rules)
also require care about data sharing, so raw rows were not sent to a hosted model.

The current dataset solve interface couples sandbox materialization with
source-to-model permission. It does not yet implement a private tool-only input
mode. Until that boundary exists, an approved alternative is public-specification
code generation followed by separate local data execution with no further model
calls. Such a result must be labeled a two-stage pilot, not an autonomous
end-to-end competition solve.

The existing submission helper also lacks complete digest-bound idempotency
and score correlation. A successful submit command is not a score. A future
pilot must preserve the exact returned submission reference and poll that
reference without silently submitting again.

## Offline verification

| Check | Result |
|---|---:|
| Full source self-test | 2,825 / 2,825 |
| Clean base-wheel self-test | 2,780 / 2,780 |
| Source conformance | 27 / 27 |
| Clean-wheel conformance | 27 / 27 |
| Runtime file parity across source, wheel, sdist, and installation | 475 / 475 |
| Access preflight | 34 / 34 |
| Source qualification | 39 / 39 |

The offline checks made zero provider calls. The base wheel explicitly omitted
optional DuckDB, MCP, model2vec, NumPy, OpenTelemetry SDK, pandas, and scikit-learn
adapter tests. Build, offline installation, and dependency checks passed.
Runtime verification used Python 3.14.4; generated-tool execution used the
existing pinned Python 3.10 Docker image. Documentation was completed separately
from the frozen runtime-body checks.

## Continuation

First independently test the repaired tool against the discovered failures.
Then resolve the recorded source and evaluator gates, run on approved local
competition data, and bind one submission to its returned Kaggle score. Only
after that result should the campaign expand. The 100+ graded-task target,
unseen-task generalization, and assisted-versus-fresh benefit remain unproven.

## Follow-up: withdrawn launch cap and preserved repair

The independent Docker probes passed 1 of 6 checks. They reproduced leakage,
prediction/ID misalignment, acceptance of a wrong ID set, loss of leading zeros
in identifiers, and a sparse-input failure. The original source hashes did not
change. Passing the eight generated tests was a false acceptance for the broader
task contract.

The repair run `adaptive-bae025a8a2bb9c6dc9ab00a6` made 50 physical calls and
stopped at an agent-imposed launch ceiling. The user did not request that
ceiling and explicitly rejected it. This was an operator mistake, not a
provider requirement or product default. `ModelExecution.max_model_calls` and
`SolveRequest.max_passes` already default to `None`. Future launches for this
work must leave them unset unless the user supplies a ceiling. Explicit user
budgets, effect permissions, and provider capacity remain separate contracts.

An offline regression executes 51 fixture calls through an uncapped model
session. The separate explicit-budget test still refuses an overrun. No real
provider was called by these tests, and they do not prove an optimal stopping
policy.

The stopped repair used 1,764,229 input and 211,958 output tokens in 823.166
seconds, with complete provider accounting. It executed no project. Its
3,507-event history and 16 digest-bound generated-file checkpoints remain
intact. The original `BUDGET_EXHAUSTED` outcome has not been rewritten.

Inspection found a second error: the static input-use screen treated ordinary
string literals as evidence of file access. It rejected valid composed paths
in the saved workspace-preparation script. The corrected screen distinguishes
simple bindings from unresolved computed paths. It retains syntax, network,
and effect checks; it never certifies runtime input consumption or task
acceptance. All 34 focused checks pass. A path-only replay of the 16 generated
files and 13 selected input bindings receives an unresolved assessment instead
of the false rejection. This replay did not execute the generated code.

The candidate also needs two omitted package-marker input bindings before
execution. Static-screen admission does not repair those missing inputs or
qualify the candidate. Continuation should reuse the saved files, resolve the
bindings, and evaluate the result independently.

GitHub CI exposed older documentation failures. Question IDs were preserved
while correcting Markdown lists, and nine retired-term matches were corrected.
The local Markdown check covers 235 files with no issues. CI is still not
green: 187 high-severity audit findings across 37 paths require semantic review.
They are findings, not 187 confirmed defects. Neither the baseline nor the
allowlist was replaced to hide them.

The [continuation evidence](../evidence/kaggle-pilot-continuation-2026-09-05.json)
preserves the independent counterexamples, stopped-run identity, checkpoints,
offline verification, and remaining limits. The structured handoff is revision
2 of `session.kaggle-pilot-20260905`, written through the managed-record tool.
No competition data, submission, or Kaggle score was added by this follow-up.

The follow-up source suite passed 2,838/2,838 and the clean base wheel passed
2,793/2,793. Both conformance runs passed 27/27. All 475 runtime file bodies
matched source, wheel, sdist, and installation. These offline checks made no
provider calls and do not clear the separate CI audit findings.
