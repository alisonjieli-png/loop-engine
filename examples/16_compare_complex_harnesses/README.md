# Audit published harness benchmark evidence

This example validates the published harness catalog and the saved Loop Engine
benchmark catalog inside a deterministic Verifier Practitioner Loop. It then
looks for exact matches. It does not run an external harness or call a model.

## Why use this example

Harness comparisons often mix benchmark versions, models, populations, and
evaluators. This audit requires an exact match before it calls a comparison
fair.

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
python -m pip install "https://github.com/alisonjieli-png/loop-engine/archive/refs/heads/main.zip"
```

## Run it

From a repository checkout:

```bash
python examples/16_compare_complex_harnesses/run.py
```

The command starts from a complete `LoopDefinition`, `LoopStartRequest`,
`LoopRuntimeContext`, typed contract, exact definition digest, and restricted
capability bindings. It reads the installed published-harness catalog and the
installed Loop Engine evidence catalog. The report gives an exclusion reason
for every Loop Engine result that lacks a matching published harness run.

## Expected result

The Loop output reports the published records, two saved Loop Engine smoke
populations, and zero fair Loop Engine-to-harness matches. The result is zero
because no published harness record uses the same population, model, effort,
metric, evaluator, and environment. It does not produce a new benchmark score.

## Watch it live

This example performs one local Loop validation and exits. It has no live
view.

## Play it back

This example does not create a Run History.

## What this example does not prove

A valid catalog does not prove that Loop Engine is better. A comparison needs
the same benchmark version, population, model, effort, metric, evaluator, and
environment.

Read [Published harness benchmark evidence](../../docs/guides/complex-task-comparisons.md)
before adding a record.
