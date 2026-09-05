# Kaggle 120 competition access preflight

Date: 2026-09-04

The campaign froze 120 competitions entered by the configured Kaggle account
and tested read-only access to their file metadata. The corrected report found
a readable JSON list response for all 120 competitions. A total of 117 lists
contain one or more file rows and 3 are empty. It did not download data, call
a model, solve a competition, or submit an artifact.

## Evidence boundary

```text
Kaggle campaign evidence
├── Metadata access preflight
│   ├── Frozen selection and exact denominator
│   ├── Read-only file-listing response
│   └── Request, failure, and Run History accounting
├── Source and evaluator qualification
│   ├── Exact source snapshot and digest
│   ├── Rules, license, privacy, format, and resource review
│   └── Independent metric and evaluator
└── Product solve and score
    ├── Starting Practitioner and bounded Loop graph
    ├── Model, tool, execution, and verification records
    └── Verified artifact and independent score
```

The metadata branch has evidence for all 120 selected competitions. The source
qualification branch now has a current-source mechanical canary for the three
active candidates in that population. None passed every qualification gate.
A successful metadata probe does not show that competition files were
acquired, understood, or solved.

## Frozen population

The initial request selected 120 unique competitions from the account's
entered competition list, ordered by the Kaggle CLI `prize` sort. The frozen
population digest is:

```text
066301403fc51993cd27f49f90ddcf242f62c1a4f3c36644d50898bb571bc8c0
```

All three saved reports use that same population and keep all 120 members in the
denominator.

## Results

| Observation | Initial diagnostic | Throttled diagnostic | Corrected primary result |
| --- | ---: | ---: | ---: |
| Selected denominator | 120 | 120 | 120 |
| Prior probe results reused | 0 | 39 | 71 |
| Physical CLI reads in this run | 126 | 81 | 49 |
| Readable file-list responses in resulting report | 39 | 71 | 120 |
| Responses with one or more file rows | 37 | 68 | 117 |
| Access refused in resulting report | 0 | 11 | 0 |
| Rate limited in resulting report | 55, recorded as `probe_failed` | 33 | 0 |
| Response rejected as invalid | 26 | 5 | 0 |
| Listings that may be truncated | Not recorded | Not recorded | 49 |
| Known returned metadata bytes | 429,300,071,449 | 531,545,989,626 | 903,955,358,757 |
| Elapsed seconds | 42.807 | 124.997 | 64.753 |
| Downloads | 0 | 0 | 0 |
| Model calls | 0 | 0 | 0 |
| Submissions | 0 | 0 | 0 |

The initial diagnostic made six list requests and 120 file-listing requests.
All 55 `probe_failed` results reported HTTP 429. Its other 26 failed probes
had a zero exit code but were rejected as unreadable JSON. The implementation
changed after this report, and the report has no implementation snapshot or
canonical Loop ownership. Treat it as a diagnostic acquisition record only.

The throttled continuation reused the 39 prior successes, serialized request
starts at 1.25 second intervals, and issued 81 new reads. It recognized 71
accessible listings. It classified the other 49 as 11 access refusals, 33 rate
limits, and 5 invalid responses.

Those 49 statuses were parser errors, not final access results. For listings
with more than 200 files, Kaggle CLI 2.2.3 writes a `Next Page Token` preamble
before the JSON array. The old parser tried to decode the entire output as
JSON. Its failure classifier then inspected the opaque token and could mistake
digits such as `403` or `429` for an HTTP status. The corrected parser removes
and validates the preamble before decoding the JSON. It does not infer a
status code from token text.

The corrected continuation reused the 71 recognized successes and read the
other 49 listings again. All 49 returned readable metadata. Each returned 200
rows and a next page token, so each is marked `may_be_truncated`. The corrected
report therefore records all 120 as `files_accessible`, while preserving the
earlier reports as diagnostic lineage. A later reader audit found that 3 of
the 120 responses contain zero file rows. Current source migrates those legacy
labels to `files_listing_empty` instead of claiming nonempty metadata.

The byte totals add known file sizes returned by accessible metadata. They are
not downloaded bytes, complete source sizes, or a storage allocation. The
corrected total of 903,955,358,757 bytes is a lower bound because 49 listings
have another page.

## Loop ownership and Run History

The corrected continuation used one Starting Practitioner with profile
`practitioner.research`. Each of its 49 physical Kaggle reads was owned by a
Context Intelligence retrieval Loop. The final report also reuses 71 results
from earlier reports. Its own Run History covers the 49 corrected reads, not
all 120 observations in one run.

The saved canonical Run History records:

- 308 total events;
- 49 `intelligence.context.retrieved` events;
- an intact digest chain with no reported break;
- head digest
  `f8b51644ca74be602fa4c7f49c881970396073198659d5f1830ec97a25839a09`.

The Run History path is
`artifacts/verification/kaggle_access_preflight_runs_corrected_20260904/kaggle-entered-access-corrected-20260904`.

This proves an intact Loop and event-accounting record for the metadata
continuation. It does not prove complete effect attribution. That run used an
older Context Intelligence wrapper whose contract did not declare its Kaggle
network subprocess. Current source adds an exact effect approval, a
network-effect Intelligence Loop contract, a sanitized transport receipt, and
separate tool success or failure events for every request. Those stronger
properties have offline fixture evidence only and need a new live run before
they become live campaign evidence for the 120-member population.

## Hardened live canary

A fresh current-source canary tested three selected competitions without
reusing prior results. It made one list request and three file-list requests.
All four responses were readable, and all three selected competitions returned
nonempty file lists.

The canary recorded:

- four exact `network_read` approvals;
- four network-effect Intelligence Loops;
- four tool starts and four tool successes;
- four `intelligence.context.retrieved` events;
- one report-core digest binding;
- 151 Run History events with an intact chain;
- zero downloads, model calls, and submissions.

The report digest is
`4a56a0d2eba50443f6b3a4bb32ae25440eaf9b150ecb02c4954dc7737c508ac5`.
Its source digest is
`db2a02e652384569e054a4f486a257d0444ee13be588d589d25cfc60a6f29109`,
and its Run History head is
`c8ce58c706163328d108ed735624d06a8e0d9055a194ecb70fb5b53f828234de`.
The report and Run History digests were recomputed after the run, the
report-core binding matched, and a bounded scan found no saved pagination
cursor, authorization header, bearer value, or Kaggle key marker.

This is live evidence for the hardened metadata path at a denominator of
three. It does not retroactively add the stronger effect receipts to the
composite 120-member run.

## Active-source qualification canary

The frozen 120-member report contained three active candidates selected for a
second read-only canary. The qualification path retrieved the rules,
evaluation, description, data-description, and related competition pages. It
stored page bodies in private content-addressed files and kept only sanitized
references in Run History.

| Competition | Source listing | Result | Main unresolved gates |
|---|---|---|---|
| `pokemon-tcg-ai-battle-challenge-strategy` | 8 files, complete first listing, 641,480,184 known bytes | `UNSUPPORTED` | Deadline, legal review, evaluator metric and direction, and independent evaluator review |
| `rsna-knee-abnormality-detection` | 200 returned files, truncated, 293,711,835 known bytes | `DEFERRED` | Complete source listing, deadline, legal review, and evaluator review |
| `biohub-cell-tracking-during-development` | 200 returned files, truncated, 986,997,631 known bytes | `DEFERRED` | Complete source listing, deadline, legal review, and evaluator review |

The source preflight stored deadline values without time-zone information.
The qualification path therefore marked them unreadable instead of guessing a
time zone. Mechanical extraction found rule and evaluation pages but could not
grant data-use authority or approve an evaluator.

The live canary recorded:

- 3 physical Kaggle page reads and 3 completed retrievals;
- 27 private page artifacts totaling 152,808 bytes;
- 1,227 Run History events with an intact digest chain;
- 0 model calls, downloads, submissions, or account mutations;
- 0 `QUALIFIED`, 2 `DEFERRED`, 1 `UNSUPPORTED`, and 0 `BLOCKED` results.

The campaign record digest is
`b5b85ea75a508acdb607160c25e8a3b18034d9597ea01535f54a4d7aed4984ff`.
Its file SHA-256 is
`dd4a5a641270971a07aa048ed53372163cc7648c4ed837b905dc852d9227394b`,
and its Run History head is
`a9a025553ffb79fed83a97fc70828c2374d76f2b779b8a2fc9449d91f8ba16bb`.
All page-artifact hashes were recomputed successfully. Files use mode `0600`
and private directories use mode `0700`.

This canary is evidence for page retrieval, private persistence, typed effect
approval, and fail-closed gate classification. It is not a legal review,
qualified evaluator, data download, product solve, or Kaggle score.

## Artifact identity

Initial direct diagnostic:

- report:
  `artifacts/verification/kaggle_access_preflight_20260904.json`;
- report digest:
  `bd41dfe1d7588ca835c8fe23e4bf250cd43353fa5a470ec90cc0ed72cb72e3a1`.

Throttled Loop-owned continuation:

- report:
  `artifacts/verification/kaggle_access_preflight_throttled_20260904.json`;
- report digest:
  `dd00d66aab9a981070f0cba34107d9f50dea384a3d3f6dae0a489f5ed7dce7c7`;
- repository revision recorded by the report:
  `22ee44052b027ba96ce50c37e4cc6a659e1b91c8`;
- preflight source digest recorded by the report:
  `d2a7869e8554e8d1d30f801e21e507a1aa8ed69a895dccf2e15d1f7b6dd56f60`;
- Python version `3.14.4` and Kaggle CLI version `2.2.3`.

Corrected Loop-owned continuation, which is the primary result:

- report:
  `artifacts/verification/kaggle_access_preflight_corrected_20260904.json`;
- report digest:
  `f80007278eb336c41cdb3be7906ccabb1eaf466f7328eb158d8ae81d8a1e47c1`;
- parent report digest:
  `dd00d66aab9a981070f0cba34107d9f50dea384a3d3f6dae0a489f5ed7dce7c7`;
- repository revision recorded by the report:
  `22ee44052b027ba96ce50c37e4cc6a659e1b91c8`;
- preflight source digest recorded by the report:
  `9c406c68f30ee584aad7e8ebd944ee33bdc328026976415eb454349da69103d7`;
- Python version `3.14.4` and Kaggle CLI version `2.2.3`.

All three report digest fields match a fresh SHA-256 calculation over their
canonical report bodies. The corrected report records that the worktree was
dirty, so the repository revision alone does not identify its implementation.
Its saved source digest and worktree status digest provide the additional
binding present at capture time.

## Privacy and publication

The reports contain account-scoped private metadata. In particular, they
record which competitions the configured account entered, plus file names,
sizes, dates, and competition metadata. The throttled diagnostic also retained
opaque Kaggle pagination cursors in failure previews even though its privacy
field said otherwise. Those cursors are not API credentials, but they are
sensitive operational values and must not be published.

Do not publish any report or Run History without reviewing the account
membership and file metadata. A source can be public while account membership
remains private. Local ignore rules now exclude these artifacts from Git, and
their files use owner-only permissions. Current source records only sanitized
response measurements and digests, not raw failure bodies or cursors.

## Offline verification

The exact offline command was:

```bash
PYTHONPATH=src:benchmarks/kaggle_competitions \
  python3 benchmarks/kaggle_competitions/preflight_checks.py
```

Observed result: 25 of 25 checks passed. The fixture made zero network
requests, model calls, and submissions. It checked explicit network authority,
population freezing and deduplication, digest stability, per-member probing,
status separation, pagination-preamble parsing, exact request accounting,
failure retention, secret and cursor redaction, empty-list migration, path
confinement, collision refusal, private evidence modes, exact effect approvals,
transport receipts, atomic report writing, resume behavior, Loop ownership,
report-core binding, and Run History integrity.

The command that produced the corrected primary result was:

```bash
PYTHONPATH=src:benchmarks/kaggle_competitions \
  python3 benchmarks/kaggle_competitions/preflight.py \
  --campaign-id kaggle-entered-access-corrected-20260904 \
  --target 120 \
  --maximum-pages 8 \
  --page-size 20 \
  --concurrency 1 \
  --timeout-seconds 60 \
  --probe-delay-seconds 1.25 \
  --resume-report \
    artifacts/verification/kaggle_access_preflight_throttled_20260904.json \
  --authorize-network-reads \
  --runs-dir \
    artifacts/verification/kaggle_access_preflight_runs_corrected_20260904 \
  --output \
    artifacts/verification/kaggle_access_preflight_corrected_20260904.json
```

That is the historical command, not the current safe invocation. Current
source also requires `--workspace-root`, refuses output and Run History
collisions before external reads, and keeps account-scoped evidence private.
The saved report's source digest preserves the distinction.

## What this establishes

The configured account returned an entered population of 120 unique
competition identifiers. The read-only campaign retained an exact frozen
population and corrected a concrete Kaggle CLI pagination-parser defect. The
corrected report has readable first-page responses for all 120 selected
competitions, including 117 nonempty file lists and 3 empty lists. The
corrected continuation executed its 49 external reads through classified Loops
and wrote an intact Run History. Its effect contracts and receipts remain the
older partial form described above.

## What this does not establish

This campaign provides no evidence for any of the following claims:

- 120 sources downloaded or locally frozen;
- any source contract or evaluator fully qualified;
- 120 tasks entered through the product solver;
- 120 models trained or artifacts verified;
- any Kaggle submission or score;
- model quality, generalization, cost, or latency for competition solving;
- a 100-competition solve campaign.

In the saved artifact, `files_accessible` means only that the CLI returned a
readable JSON list at that time. Three lists are empty. For 49 competitions,
only the first 200 rows were returned and a next page token shows that more
rows exist. Current source uses `files_listing_empty` for the empty case.

## Next evidence step

Resolve the three active-source canary gates before any data acquisition. For
each selected competition:

1. Record source identity, terms, license constraints, exact bytes, and file
   digests.
2. Qualify the input format and an evaluator that is independent of the
   solving run.
3. Run the task through a Starting Practitioner and preserve every Loop,
   physical call, action, failure, artifact, and verification record.
4. Report local validation separately from any Kaggle score.
5. Keep all attempted members in the denominator, including unsupported,
   blocked, failed, and excluded cases.

Only completed product runs with qualified sources and independent evaluation
can contribute to a future 100 or more competition solve claim.
