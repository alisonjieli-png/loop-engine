# Quick start

## Install

Python 3.10 or newer, Git, and Docker are required.

```bash
mkdir -p ~/loop-engine-quickstart
cd ~/loop-engine-quickstart
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install \
  "git+https://github.com/alisonjieli-png/loop-engine.git@main"
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
loop-engine models probe ollama_cloud \
  --model-route cloud.default \
  --model-id deepseek-v4-flash:0731 \
  --authorize-model-calls \
  --max-model-calls 1 \
  --max-total-tokens 70000
```

Do not continue if the probe fails.

## Solve a task

Start with a [downloadable example task](../../examples/tasks/) or create your
own `task.txt`.

Create `task.txt`:

```text
Build a small Python package that reads a JSON file, emits a summary, includes
tests, runs those tests, and returns the verified package and test evidence.
```

```bash
loop-engine solve \
  --file task.txt \
  --interaction-mode autonomous \
  --workspace ./workspace \
  --runs-dir ./loop-engine-runs \
  --model-route cloud.default \
  --authorize-model-calls \
  --max-model-calls 16 \
  --max-total-tokens 1000000
```

For provider-backed work, configure a provider first. See
[Providers and keys](providers-and-keys.md).

## Read the result

```bash
loop-engine --runs --runs-dir ./loop-engine-runs
loop-engine --report @last --runs-dir ./loop-engine-runs
```

A successful solve returns `COMPLETED_VERIFIED`, real artifact paths, the
workspace, verification details, and the saved Run History. A blocked result
preserves the exact reason and recovery action.

`loop-engine task build` only structures a task. It does not perform the work.
