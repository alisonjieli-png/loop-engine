# OpenML-CC18 full Practitioner run

This standalone benchmark implements the three-task OpenML-CC18 track declared
in `docs/benchmarks/first-loop-engine-portfolio.yaml`.

The selected campaign uses one non-deterministic reference-nine-step
Practitioner per task. Each task searches and materializes the core seven-lens
Intelligence Portfolio, runs separate logistic and random-forest model-led
candidate spawned Loops, synthesizes one selection, compiles a typed Solution
Canvas, executes every official fold, grades predictions with an independent
accuracy evaluator, saves and verifies a Run History, then renders playback and
a report from the reloaded Run History. One evaluator-triggered repair call is
allowed per task.

Provider calls are pinned to Ollama Cloud model
`deepseek-v4-flash:0731`, with no failover and the source-backed maximum output
setting of 65,536 tokens. The maximum is a ceiling, not a requested response
length. Provider price is unknown and remains unknown.

Files:

- `openml_runtime.py` contains the real data, split, pipeline, fold,
  evaluator, Canvas compiler, and Canvas runner callables.
- `code_intelligence.py` registers those callables as the benchmark-local Code
  Intelligence pack with typed contracts, source digests, effects, versions,
  and the admission check.
- `run.py` performs source preflight or the full selected campaign.
- `verify.py` rechecks saved hashes, predictions, fold scores, intelligence
  consumption, call accounting, and Run History chains without fitting or
  making a model call.
- `verified-result.json` points to the completed selected campaign.

The completed campaign must not be rerun merely to inspect it. Verify it with:

```bash
python3 benchmarks/openml_cc18/verify.py
```

Downloaded OpenML ARFF files are under the ignored `data/` directory. Saved
Run Histories, prediction artifacts, Canvas views, reports, environment lock,
source snapshot, Code pack, and call accounting are under `artifacts/`.
