# Getting started

The first examples run without an API key.

## 1. Install

```bash
python -m pip install "git+https://github.com/alisonjieli-png/loop-engine.git"
```

Python 3.10 or newer.

Verify it:

```bash
loop-engine --self-test
```

If that exits 0, the installation passed its built-in test suite.
The default output is a short summary plus any failures. Run
`loop-engine --self-test-verbose` to inspect module demo output and the full
test record.

## 2. Your first loop

```python
from loop_engine import LoopLedger
from loop_engine.loop.encapsulate import as_practitioner_loop

ledger = LoopLedger()

result = as_practitioner_loop(
    "choose the next support ticket",
    lambda: max([
        {"id": "SUP-1042", "severity": 2},
        {"id": "SUP-1044", "severity": 3},
    ], key=lambda ticket: ticket["severity"]),
    ledger=ledger)

print(result["value"]["id"])       # SUP-1044
print(result["model_calls"])       # 0
print(len(ledger.events))          # 13: the run recorded itself
```

You got an answer and an event log from the same run. The answer is the task
result. The event log supports reports, inspection, and debugging.

`as_practitioner_loop()` is a compatibility entry point. It composes a
complete `LoopDefinition` and restricted `LoopRuntimeContext` before the Loop
starts. Use the [Loop object guide](components/loop-object/) for the low-level
typed start contract.

Runnable version:
[support queue example](../examples/01_prioritize_support_queue/)

## 3. Send it a real problem

```python
from loop_engine.code_nodes.smoke_ladder import run_smoke_loop

run_result = run_smoke_loop(
    "predict which customers renew",
    train_csv="train.csv",
    test_csv="test.csv",
    sample_csv="sample_submission.csv",
    out_csv="predictions.csv",
    ledger=ledger)

trace = run_result["trace"]
trace["estimator"]      # what it chose
trace["cv_score"]       # its honest local score
trace["model_calls"]    # []: nothing was sent to a model
```

The deterministic data workflow inspects the files, chooses an approach,
builds predictions, and validates the output. It makes no model call.

Runnable version, which generates its own dataset:
[`examples/02_predict_customer_renewal/`](../examples/02_predict_customer_renewal/)

## 4. See what it did

```bash
python3 examples/04_read_run_reports/run.py
```

The example prints the Loop graph and keeps Markdown, HTML, and JSON reports
under `example-output/incident-report/`.

Or in code, for a run you have in hand:

```python
from loop_engine.code_nodes.loop_report import report_from_ledger, render_text
print(render_text(report_from_ledger(ledger.events, run_id="my-run")))
```

More: [reports guide](guides/reports.md).

## 5. Add a model, when you want one

Nothing so far touched a provider. To permit one:

```python
from loop_engine import configure, advice_function

access = configure(openrouter_key="...")
print(access.explain())

advise = advice_function(access)     # None if nothing is reachable
```

`configure()` probes each configured provider with a real call. It reports the
available loop modes before a job starts. A capped or rejected key becomes a
setup error instead of a failure during the job.

More: [providers and keys](guides/providers-and-keys.md) ·
[custom endpoints](guides/custom-endpoints.md)

## Where to go next

| | |
|---|---|
| [Loops and modes](guides/loops-and-modes.md) | how nesting, exit conditions, and permissions work |
| [Providers and keys](guides/providers-and-keys.md) | discovery, failover, cost attribution |
| [Runtime settings and model tiers](guides/settings.md) | YAML defaults, search choices, providers, and bounded model escalation |
| [Custom endpoints](guides/custom-endpoints.md) | your own server or a third party's |
| [Reports](guides/reports.md) | reading and exporting a run |
| [Component guide](components/) | the Loop object, roles, Core Architecture, and intelligence layers |
| [Architecture](architecture/) | deeper implementation and visual guidance |
| [`examples/`](../examples/) | categorized example folders |
| [Customer import Canvas](../examples/10_validate_customer_import/) | a realistic compiled Solution Canvas with fallback |
