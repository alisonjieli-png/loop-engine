# Install Loop Engine on Windows

These commands create one user-owned folder and one virtual environment.
Python 3.10 or newer and Git must already be available.

## Create the environment

Open PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path "$HOME\loop-engine-quickstart"
Set-Location "$HOME\loop-engine-quickstart"
py --version
git --version
py -m venv .venv
.venv\Scripts\Activate.ps1
```

If activation scripts are disabled, leave the environment unactivated and use
`.venv\Scripts\python.exe` and `.venv\Scripts\loop-engine.exe` in the commands
below.

## Install and run

With the environment activated:

```powershell
python -m pip install --quiet `
  "git+https://github.com/alisonjieli-png/loop-engine.git@main"
python -m pip check
loop-engine doctor
loop-engine --demo five-step --runs-dir .\loop-engine-runs
loop-engine --studio --port 0 --runs-dir .\loop-engine-runs
```

Studio prints a free local address. Open it in a browser and press `Ctrl+C` to
stop the server.

## Build a longer task

```powershell
@'
Download an authorized public dataset.
Train a linear model, tree model, boosted-tree model, and MLP to predict the
target variable. Use identical validation folds for every model. Compare the
results honestly and produce verified PDF and HTML reports.
'@ | Set-Content -Encoding utf8 flagship-modeling-task.txt

loop-engine task build --file flagship-modeling-task.txt
```

Add one Ollama review without putting a key in the command:

```powershell
loop-engine task build `
  --ollama-api-key `
  --interaction-mode autonomous `
  --file flagship-modeling-task.txt
```

Loop Engine uses `OLLAMA_API_KEY` when it is already set. Otherwise, it asks
for the key through a hidden prompt.

For a disposable local test, pass the value directly:

```powershell
loop-engine task build `
  --ollama-api-key "YOUR_OLLAMA_API_KEY" `
  --interaction-mode autonomous `
  --file flagship-modeling-task.txt
```

## Run the full contributor checks

The full self-test scans the installed package and can take about a minute.
It prints a progress message before the scan begins.

```powershell
python -m loop_engine --self-test
python -m loop_engine --conformance
```

Run `deactivate` when finished.
