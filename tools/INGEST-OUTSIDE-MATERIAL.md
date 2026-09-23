# Ingest outside harness material as review-only candidates

`ingest_outside_material.py` reads harness material from outside this
repository through the source engines of the
[library ingestion component](../src/loop_engine/core/library_ingestion/README.md)
and stages it as candidates through the existing staging tool. It has three
commands. None of them approves, serves, publishes or installs anything, and
every staged row stays a candidate until an independent review approves its
exact bytes.

The first two real runs, of September 23, 2026, are recorded with their
counts in
[artifacts/library-ingestion-2026-09-23](../artifacts/library-ingestion-2026-09-23/README.md).

## Collect

`collect` reads the curated sources in
`src/loop_engine/core/library_ingestion/outside_sources.yaml`, runs the
ingestion pipeline and writes one new run folder. It refuses an existing
folder, so a run is never overwritten. Put run folders outside the
repository: they hold third-party bytes.

```bash
PYTHONPATH=src python tools/ingest_outside_material.py collect \
  --run-folder RUN_FOLDER --authorize-network-reads \
  --github-request-ceiling 4800 --https-request-ceiling 3000 \
  --maximum-pause-seconds 3700 --upstream-licence-lookups 3000 --package-checks \
  --skillspector-program PATH_TO_SKILLSPECTOR
```

| Option | Meaning |
|---|---|
| `--authorize-network-reads` | Required. Every request is a read-only GET: GitHub through the existing `gh` login, and HTTPS to the hosts the run declares. |
| `--source-id` | Read only the named sources; repeat for several. |
| `--github-request-ceiling`, `--https-request-ceiling` | The most requests of each kind the run may send. A request beyond a ceiling is refused before it is sent, and the source stops with a cursor. |
| `--maximum-pause-seconds` | The longest total wait for a provider's allowance. A longer wait stops the source cleanly instead of waiting without end. Every pause is recorded. |
| `--upstream-licence-lookups` | How many upstream code repositories of registry entries may have their licence read. Zero keeps every upstream licence unknown, never assumed. |
| `--package-checks` | Refuse a registry entry whose npm or PyPI package does not exist at its exact version. Any answer other than found or not found is marked for the reviewer, never read as a pass. |
| `--skillspector-program` | Adds the SkillSpector scanner. Without it the built-in rules scan alone, and the run records why SkillSpector was not chosen. |
| `--reuse-fetched-bytes-from` | An earlier run folder whose fetched bytes may be reused; repeat for several. A file at a pinned commit never changes, so a rerun takes it from that quarantine instead of asking GitHub again, but only after hashing it again against the blob the current tree names; the reused item keeps the provenance of the fetch that produced it. The run report counts the reuse. |
| `--authorize-model-calls`, `--outline-model`, `--model-call-ceiling` | Let the model outline engine write one sentence per outline through Ollama Cloud, stopping before the ceiling. Without all three the deterministic outline engine writes every outline. |

The optional engines need libraries that the base package does not carry:
datasketch, and skills-ref, which needs Python 3.11 or later. Install them in
an environment of your own, never in a shared one. When a library is
missing, its engine is recorded as ineligible with the reason
`dependency_missing` and the declared fallback runs.

The run folder holds:

| File | What it is |
|---|---|
| `quarantine/` | Every fetched byte, read-only, named by its SHA-256 digest. Nothing executes it. |
| `requests.jsonl` | One `library_network_request/v1` row per request, with its outcome and the provider's remaining allowance. No header, token or body is kept. |
| `batches/` | Each source engine's `library_candidate_batch/v1`. |
| `refusals.jsonl`, `outlines.jsonl`, `duplicates.jsonl`, `model-calls.jsonl` | Every refusal with its stage and reason, every outline, every duplicate link and every model call. |
| `engine-decisions.json` | The `library_engine_selection/v1` decision of every engine slot, made before any engine ran. |
| `populations/` | The `candidate_intelligence_specifications/v2` rows, at most fifty to a file. |
| `run-report.json` | `library_ingestion_run_report/v1`: the code revision and digest, each source's outcome, every count, the request and model call summaries and the limits. |

## Stage

`stage` stages a run folder's populations into an isolated candidate
database, one atomic batch of at most fifty rows at a time, through
`tools/stage_intelligence_candidates.py`.

```bash
PYTHONPATH=src python tools/ingest_outside_material.py stage \
  --run-folder RUN_FOLDER --database RUN_FOLDER/candidates.db \
  --namespace library.outside --authorize-isolated-staging
```

An identical rerun adds nothing. A population that was partly staged, or a
staged candidate that changed, stops the command: a changed candidate is a
new review subject and needs a decision. The staging report records how many
rows are in the namespace, that normal search returned none of them, and how
many title probes found their own row among the first three results.

## Curate

`curate` reads the head commit and the licence evidence of named
repositories for the person who maintains the source list. It changes
nothing. A repository enters `outside_sources.yaml` only at an exact commit,
after its licence was read through GitHub's licence interface and matched in
its licence file, and its note says why.

```bash
PYTHONPATH=src python tools/ingest_outside_material.py curate \
  --repository OWNER/NAME --authorize-network-reads
```

## What the counts mean

| Count | Meaning |
|---|---|
| `discovered` | Candidates the source engines returned, plus their refusals before a candidate existed (a symbolic link, an unreadable entry, a status other than active). |
| `by_licence_decision` | Candidates by what their licence evidence permits: verbatim, link only, outline only or refused. |
| `refused_by_reason` | Every refusal by stage and reason, from the closed vocabulary in `candidates.py`. |
| `restricted_copies` | Verbatim items refused because their text repeats a refused or outline-only file of the same run. |
| `exact_duplicates`, `near_duplicates` | Items merged into another row; their provenance travels in the kept row. |
| `outlines_written` | Outlines of sources without a permissive licence. |
| `staged_rows` | Rows written to the populations. These are candidates, not library items: a public library number counts approved, active packages only. |
