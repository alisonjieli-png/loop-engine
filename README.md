# Building with Loops

Loop Engine turns a plain-language task into structured work, then runs
supported work as a graph of `Loop` objects.

Every running unit is a `Loop`. Practitioner, Intelligence, and Solution are
roles that describe the work. They are not separate runtimes.

Loop Engine is alpha software. The local five-step demo runs from start to
finish. The modeling task below can be built and reviewed, but its four-model
Solution is not available yet.

## Get started on Linux

Python 3.10 or newer and Git are required. These commands create one folder
and one virtual environment under your home directory.

```bash
mkdir -p ~/loop-engine-quickstart
cd ~/loop-engine-quickstart
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --quiet \
  "git+https://github.com/alisonjieli-png/loop-engine.git@main"
python -m pip check
loop-engine doctor
```

The first installation can take several minutes because it includes the data,
modeling, storage, and integration packages used by the examples.

If `task build` is reported as an unrecognized command, the virtual environment
has an older copy of Loop Engine. Refresh only the Loop Engine package:

```bash
python -m pip install --quiet --force-reinstall --no-deps \
  "git+https://github.com/alisonjieli-png/loop-engine.git@main"
hash -r
loop-engine doctor
```

Use the separate [Windows guide](docs/guides/install-windows/) or
[macOS guide](docs/guides/install-macos/) on those systems.

## Build a modeling task

Create a text file for the request:

```bash
cat > flagship-modeling-task.txt <<'EOF'
Download an authorized public dataset.
Train a linear model, tree model, boosted-tree model, and MLP to predict the
target variable. Use identical validation folds for every model. Compare the
results honestly and produce verified PDF and HTML reports.
EOF
```

Build the task and ask Ollama Cloud to review how Loop Engine understood it:

```bash
loop-engine task build \
  --ollama-api-key 'YOUR_OLLAMA_API_KEY' \
  --interaction-mode autonomous \
  --file flagship-modeling-task.txt
```

The output starts with a short summary like this:

```text
Task build: READY
Task type: tabular model comparison
Task details: enough to continue
Main work: predict
Expected output: file or report
Choices the Solution may make: dataset source, target column
```

`READY` means Loop Engine has enough information for the next step. It does not
mean the requested modeling Solution ran. The model review adds its status,
provider, model, token use, and selected next action below this summary.

Build the same task without a model call:

```bash
loop-engine task build --file flagship-modeling-task.txt
```

Use `--text` instead of `--file` for a short request. See
[Providers and keys](docs/guides/providers-and-keys.md) for OpenRouter,
OpenCode Go, environment variables, custom endpoints, and advanced settings.

## Run a complete local Solution

The five-step demo builds a small task, runs its Solution, verifies the result,
saves Run History, and stages a learning candidate. It does not call a model.

```bash
loop-engine --demo five-step --runs-dir ./loop-engine-runs
```

Open the saved run in Studio:

```bash
loop-engine --studio --port 0 --runs-dir ./loop-engine-runs
```

Studio prints a local address and keeps running. Open that address in your
browser. Press `Ctrl+C` in the terminal to stop Studio.

## Loop modes

Mode belongs to each Loop. It does not describe GitHub Actions or the whole
application.

| Mode | Meaning |
|---|---|
| `deterministic` | Code, rules, calculations, or retrieval do the work. No language model is called. |
| `hybrid` | Code controls the work. A language model may handle one bounded step. |
| `non_deterministic` | A language model leads the semantic work. Loop Engine still controls permissions, tools, limits, records, and verification. |

A Loop can use a mode only when its definition permits it and a matching
executor is installed.

## Architecture in one view

```text
Task
└── Practitioner Loop
    ├── builds the structured work
    ├── queries Intelligence Loops when needed
    ├── selects a Solution Canvas
    └── runs one LoopGraphDefinition
        └── Solution Loops
            ├── produce a result
            ├── verify the result
            └── save Run History
```

`LoopGraphDefinition` is the executable graph. A Solution Canvas is a builder
and portable description for that graph. It is not another runtime.

The four persistent intelligence layers are:

```text
Intelligence
├── Context Intelligence
├── Code Intelligence
├── Runtime History and Solution Intelligence
└── User Feedback Intelligence
```

The three public capability groups are Intelligence Search and Retrieval, Web
Research, and Custom Plugins.

## More examples

Run installed examples:

```bash
loop-engine --example support-queue
loop-engine --example intelligence-layers
loop-engine --example context-seed
```

Browse [all examples](examples/README.md), including the
[five text task examples](examples/20_compile_text_tasks/).

## Contributor checks

These checks scan the installed package and can take about a minute. A progress
message appears every 10 seconds.

```bash
python -m loop_engine --self-test
python -m loop_engine --conformance
```

## Documentation

- [Architecture Constitution](docs/architecture/CONSTITUTION.md)
- [Contracts](docs/contracts/README.md)
- [Components](docs/components/README.md)
- [Providers and keys](docs/guides/providers-and-keys.md)
- [Reports and playback](docs/guides/reports.md)
- [Semantic identity dictionary](docs/architecture/SEMANTIC-IDENTITY-DICTIONARY.md)
- [Current limits](docs/verification/CORE-ENGINE-COMPLETION-REPORT.md)

Loop Engine requires Python 3.10 or newer and uses the MIT license. See
[LICENSE](LICENSE).
