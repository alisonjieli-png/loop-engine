# Install Loop Engine on macOS

These commands create one folder under your home directory and one virtual
environment. Python 3.10 or newer and Git must already be available.

## Create the environment

Open Terminal:

```bash
mkdir -p ~/loop-engine-quickstart
cd ~/loop-engine-quickstart
python3 --version
git --version
python3 -m venv .venv
source .venv/bin/activate
```

## Install and run

```bash
python -m pip install --quiet \
  "git+https://github.com/alisonjieli-png/loop-engine.git@main"
python -m pip check
loop-engine doctor
loop-engine --demo five-step --runs-dir ./loop-engine-runs
loop-engine --studio --port 0 --runs-dir ./loop-engine-runs
```

Studio prints a free local address. Open it in a browser and press `Ctrl+C` to
stop the server.

## Compile a longer task

```bash
cat > flagship-modeling-task.txt <<'EOF'
Download an authorized public dataset.
Train a linear model, tree model, boosted-tree model, and MLP to predict the
target variable. Use identical validation folds for every model. Compare the
results honestly and produce verified PDF and HTML reports.
EOF

loop-engine task compile --file flagship-modeling-task.txt
```

Add one Ollama review without putting a key in the command:

```bash
loop-engine task compile \
  --ollama-api-key \
  --interaction-mode autonomous \
  --file flagship-modeling-task.txt
```

Loop Engine uses `OLLAMA_API_KEY` when it is already set. Otherwise, it asks
for the key through a hidden prompt.

For a disposable local test, pass the value directly:

```bash
loop-engine task compile \
  --ollama-api-key 'YOUR_OLLAMA_API_KEY' \
  --interaction-mode autonomous \
  --file flagship-modeling-task.txt
```

## Run the full contributor checks

The full self-test scans the installed package and can take about a minute.
It prints a progress message before the scan begins.

```bash
python -m loop_engine --self-test
python -m loop_engine --conformance
```

Run `deactivate` when finished.
