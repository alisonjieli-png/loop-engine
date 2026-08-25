# Audit published harness benchmark evidence

This example validates the source-backed published-evidence catalog inside a
deterministic Verifier Practitioner Loop. It prints population accounting. It
does not run an external harness or call a model.

## Why use this example

Harness comparisons often mix benchmark versions, models, populations, tools,
and metrics. The catalog refuses that conflation. It groups records only when
the required comparison facts match.

## Run settings

| Setting | Value |
|---|---|
| Loop role | Practitioner |
| Role profile | `practitioner.verifier@1.0.0` |
| Run mode | Deterministic |
| Step profile | `adversarial_review` |
| Intelligence layers | None |
| Runtime Memory | Not used |
| Run History | Kept in the in-memory event log |
| Model calls | Zero |
| Network access | None |

## Install

```bash
python -m pip install "git+https://github.com/alisonjieli-png/loop-engine.git"
```

## Run it

From a repository checkout:

```bash
python examples/16_compare_complex_harnesses/run.py
```

The command starts from a complete `LoopDefinition`, `LoopStartRequest`,
`LoopRuntimeContext`, typed contract, exact definition digest, and restricted
capability bindings. It reads
`docs/benchmarks/published-harness-evidence.json`. It reports record counts by
evidence qualifier and the number of exact comparable groups.

## Expected result

The Loop output reports numeric records, qualitative findings, same-harness
configuration studies, and one exact cross-harness group from Artificial
Analysis Coding Agent Index v1.4. The example validates those source records. It
does not produce a new benchmark score.

## Watch it live

This example performs one local Loop validation and exits. It has no live
view.

## Play it back

This example does not create a Run History.

## What this example does not prove

A valid catalog schema does not prove harness performance. A comparison needs
source-reviewed published records on the same benchmark version, population,
tools, model, and metric.

Read [Published harness benchmark evidence](../../docs/guides/complex-task-comparisons.md)
before adding a record.
