# Getting started

Fifteen minutes, no API key required.

## 1. Install

```bash
python -m pip install .
```

Python 3.10 or newer.

Verify it:

```bash
loop-engine --self-test
```

If that exits 0, the installation passed its built-in test suite.

## 2. Your first loop

```python
from loop_engine import LoopLedger
from loop_engine.loop.encapsulate import as_practitioner_loop

ledger = LoopLedger()

result = as_practitioner_loop(
    "estimate delivery time",
    lambda: 4,                     # any callable — ordinary Python
    ledger=ledger)

print(result["value"])             # 4
print(result["model_calls"])       # 0
print(len(ledger.events))          # 13 — the run recorded itself
```

Two things happened. You got an answer, and you got a record of how it was
produced. That pairing is the point: work and evidence are the same act, not
two.

Runnable version: [`examples/01_hello_loop.py`](../examples/01_hello_loop.py)

## 3. Send it a real problem

```python
from loop_engine.code_nodes.smoke_ladder import run_smoke_loop

receipt = run_smoke_loop(
    "predict which customers renew",
    train_csv="train.csv",
    test_csv="test.csv",
    sample_csv="sample_submission.csv",
    out_csv="predictions.csv",
    ledger=ledger)

trace = receipt["trace"]
trace["estimator"]      # what it chose
trace["cv_score"]       # its honest local score
trace["model_calls"]    # [] — nothing was sent to a model
```

The loop runs the nine-step practitioner cycle: orient on the data, research an
approach, decide, act, verify, commit. On the deterministic rail this costs
nothing but CPU.

Runnable version, which generates its own dataset:
[`examples/02_solve_a_problem.py`](../examples/02_solve_a_problem.py)

## 4. See what it did

```bash
loop-engine --report
```

```
LOOP REPORT — quarterly-plan
  5 loops, 34 events, max depth 2
  0 model calls, 0 tokens

loop1 — prepare a quarterly plan
    loop2 — gather last quarter's numbers
    loop3 — draft the objectives
    loop4 — review the draft
        loop5 — check one assumption
```

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

`configure()` probes every provider with a real call and tells you which loop
modes this installation can actually run — *before* you start a job, so a
capped or rejected key is a setup message rather than a failure twenty minutes
in.

More: [providers and keys](guides/providers-and-keys.md) ·
[custom endpoints](guides/custom-endpoints.md)

## Where to go next

| | |
|---|---|
| [Loops and modes](guides/loops-and-modes.md) | how nesting, stop conditions, and permissions work |
| [Providers and keys](guides/providers-and-keys.md) | discovery, failover, cost attribution |
| [Custom endpoints](guides/custom-endpoints.md) | your own server or a third party's |
| [Reports](guides/reports.md) | reading and exporting a run |
| [Architecture](architecture/) | the four abstractions |
| [`examples/`](../examples/) | four runnable programs |
