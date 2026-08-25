# BEIR SciFact deterministic engineering diagnostic

This diagnostic asks Loop Engine to build and run a complete scientific
evidence retrieval solution. It does not call a language model.

This run is explicitly excluded from selected benchmark evidence. Selected
benchmarks require non-deterministic runs, while this diagnostic is fully
deterministic and makes zero model calls. It tests engineering integration. It
does not answer how Loop Engine performs on the selected non-deterministic
benchmark question. Do not compare these numbers with model-driven benchmark
results as though they were the same experiment.

The diagnostic score comes from the final Solution Canvas run over all 300
official SciFact test queries. Scores from candidate methods are internal
diagnostics used by the Practitioner.

## Official source

The download step uses the official BEIR archive:

`https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip`

The source is accepted only when both hashes match:

| Hash | Required value |
|---|---|
| MD5 | `5f7d1de60b170fc8027bb7898e2efca1` |
| SHA-256 | `536e14446a0ba56ed1398ab1055f39fe852686ecad24a6306c80c490fa8e0165` |

The verified test population has 5,183 corpus documents, 1,109 rows in the
query file, 300 queries with test relevance judgments, and 339 relevance
rows.

## Run it

Download and verify the source in a separate step:

```bash
python3 benchmarks/beir_scifact/download.py \
  --data-root benchmarks/beir_scifact/data
```

Then run the complete benchmark from the repository checkout:

```bash
PYTHONPATH=src python3 benchmarks/beir_scifact/run.py \
  --data-root benchmarks/beir_scifact/data \
  --output-root benchmarks/beir_scifact/output \
  --run-id scifact-local-001
```

The run command never downloads data. It verifies the archive and every
required extracted file before the Starting Practitioner begins.

Use a new run ID for each run. Saved run histories are immutable, so the
runner refuses to overwrite an existing run.

## Complete run shape

One Starting Practitioner uses the registered reference nine-step profile:

1. Orient: accept the task and run a spawned Loop that verifies and loads the source.
2. Reconcile: search the built-in intelligence library for experiment and independent
   review guidance.
3. Assess: run a spawned Loop that defines three distinct deterministic candidates.
4. Decide: freeze the population, metrics, candidates, and selection rule.
5. Determine how: verify that each candidate has a runnable search surface.
6. Act: run three spawned Loop experiments. Each spawned Loop evaluates all 300 queries.
7. Verify: calculate every candidate score through an independent metric path,
   then select by nDCG@10, Recall@10, MRR@10, and stable candidate id.
8. Integrate: create, validate, compile, and render a deterministic Solution
   Canvas for the selected method.
9. Route: run the Canvas as a Solution loop over all 300 queries, verify its
   metrics independently, produce playback and a report, then finish.

Every retrieval query crosses `search_as_loop`. The three experiments create
900 query loops. The final Canvas creates another 300 query loops. The final
run is rejected if a query bypasses its loop, a spawned Loop remains open, a model
call appears, the source changes, the evaluator paths disagree, the Canvas
does not execute, or the Run History chain fails.

## Completed engineering diagnostic

The verified local diagnostic on the frozen source completed the full
Practitioner and Canvas path:

| Final Canvas diagnostic metric | Score |
|---|---:|
| nDCG@10 | 0.6384475973 |
| Recall@10 | 0.7469444444 |
| MRR@10 | 0.6114695767 |

Run facts:

- 300 official test queries reached the final evaluator.
- 1,200 retrieval queries ran as loops across experiments and final execution.
- 1,211 real loop objects completed.
- 9,770 events were saved in a verified Run History chain.
- 0 model calls were made.
- All 21 end-to-end shape assertions passed.

The final diagnostic TREC ranking was also evaluated with `ir_measures` 0.4.3. Its
nDCG@10, Recall@10, and RR@10 values matched the two evaluator paths in this
benchmark within floating-point precision. The checked summary is in
[`verified-result.json`](verified-result.json).

Candidate diagnostics from the same run:

| Candidate | nDCG@10 | Recall@10 | MRR@10 |
|---|---:|---:|---:|
| Titles and abstracts | 0.6384475973 | 0.7469444444 | 0.6114695767 |
| Titles only | 0.3848215810 | 0.4901111111 | 0.3584788360 |
| Abstracts only | 0.6214482347 | 0.7296111111 | 0.5936335979 |

The runner writes a typed `result.json`, a self-contained HTML report, a text
playback, a Mermaid Solution Canvas, the final TREC-format ranking, and the
complete Run History directory.

## What this result does not show

This deterministic run is not selected benchmark evidence. It does not test a
non-deterministic model-driven Practitioner and must not be used to answer that
question. It is one scientific retrieval dataset and does not establish
general task quality. The three candidates use the same lexical engine and
are not an exhaustive method search. The diagnostic measures retrieval, not
whether a downstream system correctly verifies each scientific claim.
