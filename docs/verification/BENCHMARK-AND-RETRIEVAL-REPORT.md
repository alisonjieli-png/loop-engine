# Benchmark and retrieval verification report

Date: 2026-08-27

Audited branch and revision: `main` at
`6a26978c5e6cd2e3852818c4bb4b2dac23b0da76`, with concurrent uncommitted work
present.

## Verdict

Checkpoint 7 is `REQUIRED_NOT_IMPLEMENTED`.

The DS-1000 four-task tracked evidence is self-contained and verifies from a
clean archive. The current retrieval component checks also pass offline. The
checkpoint still lacks a reproducible frozen retrieval tournament, a matched
external-harness run, complete metric coverage, and a portable OpenML or
SciFact verifier.

```text
Benchmark and retrieval checkpoint
├── DS-1000 tracked four-task evidence: VERIFIED_WORKING
├── retrieval component checks: VERIFIED_WORKING, bounded fixture
├── external-harness contract fixtures: VERIFIED_WORKING, contract only
├── OpenML saved campaign recheck: REQUIRED_NOT_IMPLEMENTED in current state
├── SciFact rerun: EXACT_EXTERNAL_BLOCKER for source data
├── historical 170-record retrieval pilot: REQUIRED_NOT_IMPLEMENTED for replay
├── matched live external-harness arm: REQUIRED_NOT_IMPLEMENTED
└── frozen development and holdout tournament: REQUIRED_NOT_IMPLEMENTED
```

## DS-1000 tracked evidence

Command in the current worktree:

```bash
python3 benchmarks/ds1000/verify.py
```

Result: 288 of 288 checks passed. The verifier made zero provider calls and
zero fit or train calls. It verified eight compact Run History chains and the
exact recorded-output correction. The corrected evaluation passed 4 of 4
frozen tasks with zero new model calls. The original 2 of 4 evaluation remains
invalidated.

A `git archive HEAD` clean copy passed 280 of 280 checks. The difference is
the optional cross-check of ignored detailed local results in the working
copy. This establishes portable verification of the tracked compact evidence,
not performance on all DS-1000 tasks.

## OpenML saved campaign

Current-worktree command:

```bash
PYTHONPATH=src python3 benchmarks/openml_cc18/verify.py
```

Result: exit 1 with
`RunHistoryIntegrityError: saved event log does not match its manifest or digest chain`.

A clean `git archive HEAD` contains zero files under
`benchmarks/openml_cc18/data`. In that clean copy the same verifier exits 1
with `FileNotFoundError` for the first task dataset ARFF. The six required ARFF
files are ignored local data. The saved OpenML summary may be retained as
historical evidence, but it is not currently reverified or portable from the
repository alone.

## SciFact retrieval diagnostic

The checked-in `verified-result.json` describes a historical deterministic
diagnostic over 300 queries. The source dataset, final rankings, complete Run
History, and generated outputs are not tracked.

Current offline reproduction:

```bash
PYTHONPATH=src python3 benchmarks/beir_scifact/run.py \
  --data-root benchmarks/beir_scifact/data \
  --output-root /tmp/scifact-audit \
  --run-id audit-no-data
```

Result: exit 1 because
`benchmarks/beir_scifact/data/source-manifest.json` is absent. The runner
created no result files.

This subcheck has an `EXACT_EXTERNAL_BLOCKER`: the pinned BEIR source must be
downloaded with separate network authorization. The documented next commands
are:

```bash
python3 benchmarks/beir_scifact/download.py \
  --data-root benchmarks/beir_scifact/data
PYTHONPATH=src python3 benchmarks/beir_scifact/run.py \
  --data-root benchmarks/beir_scifact/data \
  --output-root benchmarks/beir_scifact/output \
  --run-id scifact-audit-rerun
```

No download was performed in this audit.

## Current retrieval component

Command:

```bash
PYTHONPATH=src HF_HUB_OFFLINE=1 python3 -c \
  'from loop_engine.core.retrieval import self_test; print(self_test())'
```

Result: 12 of 12 checks passed with network access disabled. The checks cover
SQLite FTS5 BM25, hashed character 3-grams, RRF output, SimHash cards, facet
filtering, deterministic ordering, backend handshakes, embedding-space
refusal, a cached local model2vec canary, and a small tournament run through a
Practitioner Loop.

This is component evidence. The model2vec weights were already present in the
host cache, so it is not a clean-install model-weight proof.

The historical retrieval tournament is labeled `PILOT` with 10 queries over
170 records. It is not replayable from the current repository because its
declared corpus, `src/loop_engine/strings/generated_candidates.jsonl`, is
absent and its recompute script exists only in a prior session scratchpad.
There is no `NgramSpaceDefinition` implementation. The current n-gram support
is a fixed hashed character 3-gram vector, not the requested versioned family
of character, word, code, graph, and trajectory materializations.

## External harness evidence

Offline contract commands returned 17 of 17 and 20 of 20 passing checks for
the generic harness boundary and optional SDK adapters. These checks use
injected runners and do not call a real harness.

```bash
PYTHONPATH=src python3 examples/16_compare_complex_harnesses/run.py
```

Result: exit 0. The evidence catalogs validated, but the exact comparison
count was 0. Neither Loop Engine benchmark had a published harness result with
the same population, model, effort, metric, evaluator, and environment.

No OpenCode, Codex CLI, Claude Code, Aider, Harbor, Terminal-Bench, SWE-bench,
MLE-bench, or PaperBench run was executed in this audit.

## Required checkpoint behaviors not present

- No tracked development and holdout retrieval judgments can be replayed.
- Precision at k, false merge, false split, incremental update, memory, and
  scope-leak metrics are not available as one current tournament result.
- No general versioned n-gram space contract exists.
- No matched external-harness arm exists.
- No route reports a Pareto view across matched quality, cost, latency, and
  resource conditions.
- OpenML cannot be rechecked from a clean checkout.

## Exact next gate

Keep the DS-1000 claim bounded to its four-task recorded-output evidence.
Repair OpenML verification and track or reconstruct its immutable source
inputs. Restore a tracked frozen retrieval population, development and holdout
queries, judgments, and runner. Only then run a matched external-harness arm
and report paired results. A historical JSON summary or an injected adapter
test cannot satisfy that gate.
