# Quick start

## Install

Python 3.10 or newer and Docker are required. Git is not required.

```bash
mkdir -p ~/loop-engine-quickstart
cd ~/loop-engine-quickstart
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install \
  "https://github.com/alisonjieli-png/loop-engine/archive/refs/heads/main.zip"
docker pull \
  python@sha256:2407c61b1a18067393fecd8a22cf6fceede893b6aaca817bf9fbfe65e33614a3
python -m pip check
loop-engine doctor
```

Use the separate [Windows](install-windows/) or [macOS](install-macos/) guide
when needed.

## Configure and probe Ollama Cloud

```bash
export OLLAMA_API_KEY="your-key"
loop-engine configure
loop-engine models probe ollama_cloud \
  --model-route cloud.default \
  --model-id deepseek-v4-flash:0731 \
  --authorize-model-calls \
  --max-model-calls 1 \
  --max-total-tokens 70000
```

Do not continue if the probe fails.

## Solve a task

Download the first [example task](../../examples/tasks/):

```bash
curl -LO \
  https://raw.githubusercontent.com/alisonjieli-png/loop-engine/main/examples/tasks/01-expense-report.txt

loop-engine solve --file 01-expense-report.txt --quickstart
```

For provider-backed work, configure a provider first. See
[Providers and keys](providers-and-keys.md).

## Read the result

```bash
loop-engine runs
loop-engine report @last
loop-engine studio --port 0
```

A successful solve returns `COMPLETED_VERIFIED`, real artifact paths, the
workspace, verification details, and the saved Run History. A blocked result
preserves the exact reason and recovery action.

`BLOCKED_MATERIAL_INPUT` includes answer slots. Rerun the same task with
`--task-feedback 'answer_slot=value'`; feedback remains separate from the
immutable original task.

`loop-engine task build` only structures a task. It does not perform the work.
