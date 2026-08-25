# DS-1000 full Practitioner smoke benchmark

This benchmark ran four frozen public DS-1000 tasks through the complete Loop
Engine path. It did not run a partial Canvas-only diagnostic as the selected
benchmark.

The population is fixed in [`population-v1.json`](population-v1.json): Pandas
problems 72 and 218, and Sklearn problems 838 and 896, from upstream commit
`b39aab71da6d23ef8d3cac59a7c5f834516ab334`.

## What ran

Each selected task used:

1. a Starting Practitioner with the `reference_nine_step` profile in
   `non_deterministic` mode;
2. pre-decision Context, Code, Previous Run, and User Feedback Intelligence search;
3. two model-led candidate spawned Loops with distinct canonical seven-lens
   portfolios;
4. one model-led synthesis spawned Loop that compared both candidates;
5. one repair spawned Loop only after a completed upstream evaluator failure;
6. an exact `LoopIntelligenceConsumption` binding on every model call;
7. a compiled typed code Solution Canvas;
8. network-disabled, non-root, read-only container execution;
9. the pinned upstream DS-1000 pass or fail evaluator; and
10. Run History save, hash-chain verification, playback, and report generation.

The model route was pinned to Ollama Cloud
`deepseek-v4-flash:0731`. Every call requested its source-backed maximum output
of 65,536 tokens. Provider failover and hidden retries were disabled.

The model prompt surface contained the public task prompt, the materialized
selected intelligence, the typed output contract, and generated candidate text.
Only a repair prompt received the upstream failure string. Reference solutions,
evaluator bodies, and upstream tests were kept outside model prompts.

## Result

The full selected run used 14 physical model calls. One earlier interrupted
diagnostic call was excluded from scoring but counted against the packet, for a
total of 15 calls under the 16-call ceiling. Provider-reported usage for the
selected run was 11,577 input tokens and 25,301 output tokens, or 36,878 total.
All four tasks completed the required full path.

The selected run first reported 2 of 4 passes. Falsification found that this
score was not valid: the first safe extractor called `strip()`, which removed
leading indentation required when DS-1000 inserts a completion inside a
function body. The immutable original run remains preserved with that failure.

A separate full reference-nine-step recorded-output regrade reused the exact
saved provider responses, preserved leading whitespace, and executed the same
compiled Canvas and locked upstream evaluator. It made zero new model calls.
All four tasks passed in that corrected evaluation.

Plain verdict: the exact recorded model outputs passed this four-task public
smoke population after the deterministic extractor was made conformant with
the upstream whitespace behavior. This does not establish performance on the
full DS-1000 suite or on broader AI, ML, experimentation, tuning, and data
engineering work.

The compact result is in
[`verified-result.json`](verified-result.json). The tracked
[`artifacts`](artifacts/) directory contains the normalized selected and
correction summaries, compact Run History chains, Canvas records, report
summaries, and full playback text needed to verify the result from a clean
checkout. Detailed local outputs remain under the ignored `results/` directory.

Check all tracked evidence without fitting or training anything and without a
provider call:

```bash
python3 benchmarks/ds1000/verify.py
```

## Reproduction

On a fresh result directory:

```bash
PYTHONPATH=src python3 benchmarks/ds1000/run.py preflight
PYTHONPATH=src python3 benchmarks/ds1000/run.py run
```

The preflight clones and verifies the pinned source, builds and identifies the
locked evaluator image, proves the sandbox controls, passes the focused Loop
Engine and intelligence gates, confirms all four upstream reference solutions,
and rejects an intentional negative candidate before any provider call.

`run.py` refuses a duplicate completed provider campaign for this frozen
population. `regrade.py` is the one-time deterministic correction utility for
the preserved 2026-08-25 run and also refuses to overwrite its existing output.

`materialize_evidence.py` created the tracked non-secret compact evidence from
the preserved detailed local results. It is not part of ordinary verification;
`verify.py` reads the already tracked artifacts directly.
