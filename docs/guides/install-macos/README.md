# Install Loop Engine on macOS

These commands create one folder under your home directory and one virtual
environment. Install Python 3.10 or newer and Docker Desktop first.
Start Docker Desktop before the provider-backed solve.

## Create the environment

Open Terminal:

```bash
mkdir -p ~/loop-engine-quickstart
cd ~/loop-engine-quickstart
python3 --version
python3 -m venv .venv
source .venv/bin/activate
```

## Install and run

```bash
python -m pip install --quiet \
  "https://github.com/alisonjieli-png/loop-engine/archive/refs/heads/main.zip"
python -m pip check
docker pull \
  python@sha256:2407c61b1a18067393fecd8a22cf6fceede893b6aaca817bf9fbfe65e33614a3
loop-engine doctor
```

## Configure and solve

Set the Ollama Cloud key for this Terminal session:

```bash
export OLLAMA_API_KEY="your-key"
loop-engine configure
```

Make one bounded provider probe:

```bash
loop-engine models probe ollama_cloud \
  --model-route cloud.default \
  --model-id deepseek-v4-flash:0731 \
  --authorize-model-calls \
  --max-model-calls 1 \
  --max-total-tokens 70000
```

Stop if the probe fails. Then download and solve the first task:

```bash
curl -LO \
  https://raw.githubusercontent.com/alisonjieli-png/loop-engine/main/examples/tasks/01-expense-report.txt

loop-engine solve --file 01-expense-report.txt --quickstart
loop-engine runs
loop-engine report @last
loop-engine studio --port 0
```

Studio prints a local address. Open it in a browser. The Result tab shows the
terminal state, verification, workspace, and artifacts. Press `Ctrl+C` in
Terminal to stop Studio.

## Run the full contributor checks

The full self-test scans the installed package and can take about a minute.
It prints a progress message before the scan begins.

```bash
python -m loop_engine --self-test
python -m loop_engine --conformance
```

Run `deactivate` when finished.
