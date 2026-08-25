# Loop Engine case studies

A case study is a completed full Loop Engine run on a real task with an
independent evaluator. This folder does not treat examples, component tests,
provider checks, or incomplete runs as case studies.

## Admission rule

```text
real task and frozen population
  -> Starting non-deterministic Practitioner
  -> reviewed Context and executable Code Intelligence
  -> bounded Spawned Practitioner Loops and Queried Intelligence Loops
  -> candidate comparison and verification
  -> compiled and executed Solution Canvas
  -> independent evaluator
  -> verified Run History, playback, and report
  -> case study or explicit failure
```

Every case study reports:

- task, source, version, population, and selection rule;
- Starting and Spawned Loops profiles;
- run modes and model thinking power;
- intelligence references consumed by each model-led spawned Loop;
- Solution Canvas and typed connections;
- evaluator, metric, score direction, and failure treatment;
- physical calls, input tokens, output tokens, elapsed time, and cost state;
- all failed and incomplete attempts;
- what the result does not establish.

## Current studies

- [OpenML-CC18 three-task run](openml-cc18-three-task-run.md): completed full
  non-deterministic Practitioner runs on three frozen tasks.
- [DS-1000 four-task recorded-output correction](ds1000-four-task-recorded-output-correction.md):
  the first 2 of 4 score is preserved but invalidated; a zero-model-call
  correction of the exact recorded outputs passed all 4 tasks.

The deterministic SciFact run is an excluded engineering diagnostic and is
not listed as performance evidence.

Use [the case-study template](TEMPLATE.md) for a completed run.
