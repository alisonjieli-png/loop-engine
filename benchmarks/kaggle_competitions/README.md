# Kaggle competition campaign

This directory supports a staged Kaggle campaign. The current saved evidence
covers metadata access for a frozen population of 120 competitions. It does
not show 120 competition solves.

The [September 5 live pilot](../../docs/verification/KAGGLE-LIVE-PILOT-2026-09-05.md)
records a real provider probe and a public-specification tool-building run.
Independent review found defects despite the tool's passing generated tests.
No Kaggle score is claimed. An explicit `--search` filter now binds a smaller
selected population to its preflight and qualification evidence.

```text
Kaggle campaign evidence
├── Metadata access preflight
│   └── Can the account list a competition and read its file metadata?
├── Source and evaluator qualification
│   └── Is the source frozen, usable, licensed, and independently gradable?
└── Product solve and score
    └── Did Loop Engine solve the task, verify the artifact, and receive a score?
```

These levels are cumulative. Metadata access is not source qualification.
Source qualification is not a solve or a score.

## Current 120 competition preflight

On 2026-09-04, the preflight froze 120 competitions entered by the configured
Kaggle account. A corrected, Loop-owned continuation reused 71 successful
metadata results and made 49 additional read requests. The resulting report
has a readable JSON list response for all 120 selected competitions. A total
of 117 responses contain at least one file row, while 3 are readable empty
lists. Of the nonempty listings, 49 included a next page token and may be
truncated at the 200-row CLI page size.

An earlier report classified the remaining 49 responses as 11 access
refusals, 33 rate limits, and 5 invalid responses. Those statuses were wrong.
The parser had tried to decode the Kaggle CLI's `Next Page Token` preamble as
JSON, then had treated digits inside the opaque token as status codes. The
corrected report supersedes those access results but preserves them as
diagnostic lineage.

The run downloaded no competition data, called no model, and submitted
nothing. The returned metadata describes at least 903,955,358,757 bytes of
files. This is a lower bound because 49 listings have another page. Source
acquisition therefore needs an explicit selection and storage plan.

The corrected continuation's canonical Run History contains 308 events. It
includes 49 Intelligence retrieval events, and its digest chain verifies as
intact. That saved run predates the stricter effect records now in the
preflight source, so it is partial ownership evidence rather than a complete
network-effect trace. The detailed
[preflight report](../../docs/verification/KAGGLE-120-ACCESS-PREFLIGHT-2026-09-04.md)
records the population digest, report digests, limitations, and exact evidence
boundaries.

The reports contain account-scoped competition membership and file metadata.
The superseded throttled diagnostic also retained opaque pagination cursors.
Local ignore rules and owner-only permissions keep these artifacts out of a
normal commit. They require privacy review before any publication.

## Hardened live canary

After the privacy and authority fixes, a fresh three-competition canary made
four read-only CLI requests: one population list and three file-list probes.
All four returned readable lists. The run recorded four exact network-effect
approvals, four tool successes, four Intelligence retrievals, a report-core
binding, and an intact 151-event Run History. It retained no raw pagination
cursor, authorization header, bearer value, or Kaggle key marker. It made zero
downloads, model calls, and submissions.

This canary proves the hardened metadata path at a denominator of three. The
larger 120-member result remains the composite campaign described above.

## Active-source qualification canary

The next read-only canary evaluated the three active candidates from the
frozen 120-member population. It made exactly three Kaggle page reads and
stored 27 page bodies as private, content-addressed artifacts. Its 1,227-event
Run History verifies as intact. It made no model call, data download, or
submission.

The results were 0 `QUALIFIED`, 2 `DEFERRED`, 1 `UNSUPPORTED`, and 0
`BLOCKED`. The two deferred sources have truncated 200-file listings. All
three still require authoritative data-use and independent evaluator review.
The preflight deadlines lack time-zone information, so the qualification path
left them unresolved.

This result proves the source-qualification mechanics on three live sources.
It does not qualify a source for acquisition or solving. The detailed
[verification report](../../docs/verification/KAGGLE-120-ACCESS-PREFLIGHT-2026-09-04.md)
records the exact digests and remaining gates.

## Run the offline checks

The fixture checks authority refusal, population freezing, digest stability,
failure accounting, resume behavior, Loop ownership, and Run History without
using the network:

```bash
PYTHONPATH=src:benchmarks/kaggle_competitions \
  python3 benchmarks/kaggle_competitions/preflight_checks.py
```

The current result is 25 of 25 checks passed, with zero network requests,
model calls, and submissions.

## Run a read-only metadata preflight

Use fresh campaign and output paths for a new run. Network reads must be
authorized explicitly. The Loop-owned path currently requires concurrency
one. Resume, output, and Run History paths must remain below the private
workspace root and must not overlap.

```bash
PYTHONPATH=src:benchmarks/kaggle_competitions \
  python3 benchmarks/kaggle_competitions/preflight.py \
  --campaign-id <campaign-id> \
  --workspace-root <private-workspace-root> \
  --target 120 \
  --maximum-pages 8 \
  --page-size 20 \
  --concurrency 1 \
  --timeout-seconds 60 \
  --probe-delay-seconds 1.25 \
  --authorize-network-reads \
  --runs-dir <runs-dir> \
  --output <report.json>
```

Pass `--resume-report <prior-report.json>` to reuse successful probes from an
exact, digest-valid frozen population. A resumed report keeps every selected
competition in the denominator.

## Qualify a competition before solving it

An accessible file listing is only a source candidate. Qualification should
freeze the source identity and digest, record rules and license constraints,
check storage and compute needs, and establish an independent evaluator. The
current `contract.py` grader supports only the file shapes it can derive from
train, prediction, and sample-submission files.

`contract.py` derives a target as the column present in the training file and
absent from the prediction file, confirmed against the sample submission. It
also records contract traps that the files establish, such as a target that
is not the last training column or a sample submission that asks for scores
rather than labels.

Qualification must reject or defer unsupported archives, modalities, table
layouts, and evaluation contracts. It must not silently reshape them into a
tabular benchmark.

The source-qualification implementation has a separate offline suite:

```bash
PYTHONPATH=src:benchmarks/kaggle_competitions \
  python3 benchmarks/kaggle_competitions/source_qualification_checks.py
```

The current result is 31 of 31 checks passed. The fixture makes no network
request, model call, download, or submission.

The current reader and executor now fail closed on multi-output submissions,
duplicate CSV headers, a target absent from training data, a target present in
test data, unexplained train-only columns, and preprocessing that leaves no
usable feature. Their offline checks pass 6 of 6 and 16 of 16 respectively.
This narrows the valid region. It does not expand the number of qualified
competitions.

## Run a qualified solve

### Generated source diagnostics

`fresh_shaped_cases.py` creates three benchmark-only cases and an independent
hidden-label grader. Its fixed generators describe the test population; they
are not runtime solver branches. The real product solver receives ordinary
task/source material and chooses its own implementation.
Publishing the deterministic generator makes A, B, and C public reproducible
fixtures. Later use must not count them as hidden or unseen holdouts.

```bash
PYTHONPATH=src:benchmarks/kaggle_competitions \
  python3 benchmarks/kaggle_competitions/fresh_shaped_cases.py self-test
```

The [new-task diagnostic report](../../docs/verification/UNSEEN-TASK-DIAGNOSTIC-AND-GENERALIZATION-2026-09-04.md)
records two real-provider attempts on one case, zero verified completions,
and an unresolved token-budget preflight gap. The other two cases remain
unattempted. These are not completed Kaggle competitions or an assisted/fresh
experiment. Private source data, labels, and live histories remain excluded
from Git. Do not regenerate or change the frozen helper while grading its
existing campaign; use a separately versioned population for later changes.

### Product solve after qualification

After downloading an authorized, qualified source, run the product path with
a real configured provider:

```bash
PYTHONPATH=src python3 -m loop_engine solve \
  --file <task-file> \
  --dataset <data-dir> \
  --workspace <workspace> \
  --runs-dir <runs> \
  --compile-provider <provider> \
  --provider-key-env <key-env-name> \
  --model-route <route> \
  --authorize-model-calls --allow-source-to-model --allow-local-execution \
  --max-passes 40 --format json
```

Then grade the produced artifact with an evaluator that did not read the
run's own conclusion. Record physical model calls, token-accounting
completeness, elapsed time, cost state, failures, exclusions, and the exact
denominator.

## What a valid result must distinguish

`compare.py` reports discovery separately from execution. A run that finds
the correct target but cannot execute is different from one that executes on
the wrong target.

A locally verified submission is still not a Kaggle score. Schema, row count,
column order, identifier coverage, and local validation establish useful but
different facts. Only a recorded Kaggle evaluation establishes a Kaggle
score.
