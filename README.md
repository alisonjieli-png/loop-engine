# Building with Loops

Loop Engine takes a plain-language task, works out what must happen, runs the
work it can support, and verifies the result. Every executable unit is the
same runtime type: `Loop`.

Practitioner, Intelligence, and Solution are roles. A role explains what a
Loop is doing. It does not create another runtime.

Loop Engine is alpha software. A run counts as successful only when the
requested result exists and passes verification. Orientation, a plan, or a
candidate project is not completion.

## Clean Linux install

Python 3.10 or newer and Git are required. The commands below create a new
folder and a virtual environment. They do not install system packages.

```bash
mkdir -p ~/loop-engine-quickstart
cd ~/loop-engine-quickstart

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install \
  "git+https://github.com/alisonjieli-png/loop-engine.git@main"

python -m pip check
loop-engine doctor
```

The first install is large because the package includes the data, modeling,
storage, and integration libraries used by its examples.

If `task build` is not recognized, refresh the Loop Engine package inside the
active virtual environment:

```bash
python -m pip install --force-reinstall --no-deps \
  "git+https://github.com/alisonjieli-png/loop-engine.git@main"
hash -r
loop-engine task build --help
```

Windows and macOS instructions are kept on separate pages:

- [Windows](docs/guides/install-windows/)
- [macOS](docs/guides/install-macos/)

## Build a solution from a text task

Put a longer request in a text file so the command stays readable:

```bash
cat > flagship-modeling-task.txt <<'EOF'
Download an authorized public dataset.
Train a linear model, tree model, boosted-tree model, and MLP to predict the
target variable. Use identical validation folds for every model. Compare the
results honestly and produce verified PDF and HTML reports.
EOF
```

Run the complete Practitioner with Ollama Cloud:

```bash
loop-engine task build \
  --ollama-api-key 'YOUR_OLLAMA_API_KEY' \
  --interaction-mode autonomous \
  --runs-dir ./loop-engine-runs \
  --file flagship-modeling-task.txt
```

This command does not stop after understanding the request. It repeats the
Practitioner cycle, chooses registered capabilities, researches sources when
needed, builds a candidate Solution Canvas, runs the selected graph, checks
the files, and repairs failed attempts while its budget remains.

Progress appears in the terminal. Each message names the active step and its
current objective. The final summary lists every Loop, its role, mode, input,
output, steps, and terminal state.

The command exits successfully only when it prints:

```text
Task build: VERIFIED WORKING
```

`NOT COMPLETED` or `FAILED` means the requested result was not produced and
verified. The summary still gives the saved Run History and full result path.
Use `--format json` when you want every typed orientation, action decision,
Canvas candidate, source record, project attempt, and verification result.

## Pass a provider key

An Ollama key can be passed directly, as shown above. It can also come from the
shell:

```bash
export OLLAMA_API_KEY='YOUR_OLLAMA_API_KEY'

loop-engine task build \
  --ollama-api-key \
  --interaction-mode autonomous \
  --file flagship-modeling-task.txt
```

OpenRouter and OpenCode Go use the same command shape:

```bash
loop-engine task build \
  --openrouter-api-key 'YOUR_OPENROUTER_API_KEY' \
  --interaction-mode autonomous \
  --file flagship-modeling-task.txt
```

```bash
loop-engine task build \
  --opencode-go-api-key 'YOUR_OPENCODE_GO_API_KEY' \
  --interaction-mode autonomous \
  --file flagship-modeling-task.txt
```

Ollama web search is available only when an Ollama key is present. A run using
another model provider sees only the capabilities it can actually use.

See [Providers and keys](docs/guides/providers-and-keys.md) for custom
endpoints, route selection, and settings files.

## Autonomous judgment and feedback

Autonomous mode does not ask the user to choose between ordinary acceptable
options. It records a delegated choice, selects one under the current
constraints, and continues.

It still stops when a missing value changes legality, authority, safety,
privacy, irreversible effects, cost limits, acceptance criteria, or whether
the result would be useful.

Feedback is optional. Add it when one choice matters to you:

```bash
loop-engine task build \
  --ollama-api-key 'YOUR_OLLAMA_API_KEY' \
  --interaction-mode autonomous \
  --task-feedback task.preference.dataset_source=openml:61 \
  --file flagship-modeling-task.txt
```

The feedback slot becomes part of the typed model context and the saved run.
Without feedback, the Practitioner uses its available capabilities and best
judgment within the recorded constraints.

## What the three modes mean

Mode belongs to each Loop. It does not describe GitHub Actions or the whole
application.

- `deterministic`: Exact parsers, registered procedures, calculations,
  retrieval, or tests do the work. No language model is called.

- `hybrid`: The deterministic attempt runs first. If it cannot continue, the
  model receives the original task, current state, complete deterministic
  trace, failures, capabilities, permissions, and required output contract.

- `non_deterministic`: The model leads orientation and next-action selection.
  Loop Engine still controls providers, tools, permissions, budgets, files,
  commands, Run History, and verification.

`task build` uses hybrid mode by default. To test only the exact deterministic
path, say so:

```bash
loop-engine task build \
  --practitioner-mode deterministic \
  --file flagship-modeling-task.txt
```

An unsupported deterministic task returns a typed capability gap with zero
model calls. It does not guess.

## Follow the run

Open saved runs in Studio:

```bash
loop-engine --studio --port 0 --runs-dir ./loop-engine-runs
```

Studio prints the local address it selected. Open that address in a browser.
Press `Ctrl+C` in the terminal to stop the server.

For a small model-free runtime smoke test, run:

```bash
loop-engine --demo five-step --runs-dir ./loop-engine-runs
```

That command checks a known local procedure. It is not proof that an
unfamiliar free-form task can be solved.

## Architecture in one view

```text
Task
└── Starting Practitioner Loop
    ├── preserves the original task
    ├── orients and builds typed state
    ├── queries Intelligence Loops
    ├── selects the next typed action
    ├── compares candidate Solution Canvases
    └── runs one LoopGraphDefinition
        └── Connected Solution Loops
            ├── produce artifacts
            ├── verify artifacts
            └── save Run History
```

`LoopGraphDefinition` is the executable graph contract. A Solution Canvas is a
candidate, builder, and portable view of that graph. It is not another
runtime.

The four persistent intelligence layers are Context Intelligence, Code
Intelligence, Runtime History and Solution Intelligence, and User Feedback
Intelligence.

## Examples and checks

The five text files in
[the task-intake example](examples/20_compile_text_tasks/) are input fixtures.
That example checks intake decisions. It does not claim that the five
solutions ran.

Run the complete offline suite and architecture checks:

```bash
python -m loop_engine --self-test
python -m loop_engine --conformance
```

The self-test prints progress every 10 seconds. It does not call a provider.

To inspect one component or state transition without running a full task, use
the independent qualification lab:

```bash
cd devtools/qualification_lab
python runner.py list
python runner.py render --case route-breakout
python runner.py audit-run --result /path/to/adaptive-result.json
python -m unittest -v test_runner.py
```

The lab does not import Loop Engine. It can be copied into a separate
repository and can use Ollama for one bounded review prompt at a time. Start
with component identity and atomic operations, then qualify interactions,
verification scope, routing, one complete pass, and finally multi-pass work.

Useful references:

- [Adaptive Practitioner architecture](docs/architecture/ADAPTIVE-WORK-APPROACH-ARCHITECTURE.md)
- [Ollama component qualification lab prompt](docs/prompts/OLLAMA-COMPONENT-QUALIFICATION-LAB.md)
- [Architecture Constitution](docs/architecture/CONSTITUTION.md)
- [Contracts](docs/contracts/README.md)
- [Components](docs/components/README.md)
- [Reports and playback](docs/guides/reports.md)
- [Current verification status](docs/verification/CORE-ENGINE-COMPLETION-REPORT.md)

Loop Engine uses the MIT license. See [LICENSE](LICENSE).
