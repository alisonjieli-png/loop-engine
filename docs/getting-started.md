# Getting started

Loop Engine takes a task, performs work in a confined Docker workspace,
verifies the result, and saves the product outcome with its Run History.

The [main README](../README.md) is the canonical onboarding path. This page
explains the same commands with a little more context.

## Install

Install Python 3.10 or newer and Docker first. Git is not required. Then run:

```bash
mkdir loop-engine-quickstart
cd loop-engine-quickstart
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install \
  "https://github.com/alisonjieli-png/loop-engine/archive/refs/heads/main.zip"
docker pull \
  python@sha256:2407c61b1a18067393fecd8a22cf6fceede893b6aaca817bf9fbfe65e33614a3
loop-engine doctor
```

Use the separate [Windows](guides/install-windows/) or
[macOS](guides/install-macos/) instructions when needed.

## Configure a provider

Set one supported key. Ollama Cloud is the preferred first route:

```bash
export OLLAMA_API_KEY="your-key"
loop-engine configure
```

`configure` inspects credential references without contacting a provider.
Make one explicit probe before solve:

```bash
loop-engine models probe ollama_cloud \
  --model-route cloud.default \
  --model-id deepseek-v4-flash:0731 \
  --authorize-model-calls \
  --max-model-calls 1 \
  --max-total-tokens 70000
```

Stop if the probe fails.

## Solve and verify a task

```bash
curl -LO \
  https://raw.githubusercontent.com/alisonjieli-png/loop-engine/main/examples/tasks/01-expense-report.txt

loop-engine solve --file 01-expense-report.txt --quickstart
```

The quickstart profile is explicit authority for the LLM-first onboarding run.
The LLM-first profile has no product-imposed pass, model-call, or token ceiling.
Explicit user, provider, cost, deadline, and deployment policies may still set
limits. Generated programs run without network access inside the pinned Docker
image.

A successful result returns `COMPLETED_VERIFIED`, artifact paths, the
workspace, verification details, and a saved Run History.

## Inspect the saved result

```bash
loop-engine runs
loop-engine report @last
loop-engine studio --port 0
```

The report and Studio read the same verified saved-run bundle. They show the
product terminal state, verification result, artifacts, workspace, Solution
Canvas, Loop activity, and model calls.

## Use Loop Engine as a library

The CLI is the shortest first experience. Library users can create the same
canonical runtime directly:

```python
from loop_engine import LoopLedger
from loop_engine.loop.encapsulate import as_practitioner_loop

ledger = LoopLedger()
result = as_practitioner_loop(
    "choose the highest severity ticket",
    lambda: max([
        {"id": "SUP-1042", "severity": 2},
        {"id": "SUP-1044", "severity": 3},
    ], key=lambda ticket: ticket["severity"]),
    ledger=ledger,
)

print(result["value"]["id"])
print(result["model_calls"])
```

Continue with [loops and modes](guides/loops-and-modes.md),
[providers and keys](guides/providers-and-keys.md), and
[reports](guides/reports.md).
