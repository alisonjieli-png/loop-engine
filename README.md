# Building with Loops

Loop Engine takes a task, performs real work in a confined workspace, verifies
the result, and saves an inspectable Run History.

The first supported solve path is intentionally bounded. It can build small
Python utilities, transform supplied local files, summarize documents, analyze
repositories, and repair small Python packages. Unsupported work returns an
honest `CAPABILITY_GAP`.

## Install

You need Python 3.10 or newer, Git, and Docker.

```bash
mkdir loop-engine-quickstart
cd loop-engine-quickstart

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install \
  "git+https://github.com/alisonjieli-png/loop-engine.git@main"

docker pull \
  python@sha256:2407c61b1a18067393fecd8a22cf6fceede893b6aaca817bf9fbfe65e33614a3

loop-engine doctor
```

The default install is lightweight. In a source checkout, install `.[data]`
for the larger ML, Kaggle, vector, and analytical adapters, or `.[all]` for
every first-party optional adapter.

## Configure one provider

The shortest hosted path uses Ollama Cloud:

```bash
export OLLAMA_API_KEY="your-key"
```

Check the exact route with one authorized call:

```bash
loop-engine models probe ollama_cloud \
  --model-route cloud.default \
  --model-id deepseek-v4-flash:0731 \
  --authorize-model-calls \
  --max-model-calls 1 \
  --max-total-tokens 70000
```

Do not continue if the probe reports authentication, rate-limit, output-limit,
or availability failure. A configured key is not proof that a provider works.

See [providers and keys](docs/guides/providers-and-keys.md) for OpenRouter,
Mistral, local Ollama, OpenCode Go, and custom endpoints.

## Solve a real task

```bash
loop-engine solve \
  --text "Create a small Python command-line program that reads a JSON file of expenses, totals spending by category, writes a Markdown report, and includes runnable verification." \
  --workspace ./workspace \
  --runs-dir ./runs \
  --interaction-mode autonomous \
  --model-route cloud.default \
  --model-id deepseek-v4-flash:0731 \
  --authorize-model-calls \
  --max-model-calls 16 \
  --max-total-tokens 1000000
```

A successful result has this shape:

```text
COMPLETED_VERIFIED
Expense report command and verified Markdown output.

Artifacts:
  .../workspace/attempt-1/expense_report.py (verified)
  .../workspace/attempt-1/report.md (verified)

Workspace: .../workspace/attempt-1
Verification: passed
Run History: .../runs/<run-id>
```

A generated-project solve writes only inside the selected workspace. Commands
run in the pinned Docker image with bounded resources and no network during
execute or verify steps. Dependency setup requires separate authority.

## Inspect the result

```bash
loop-engine --runs --runs-dir ./runs
loop-engine --report @last --runs-dir ./runs
loop-engine --studio --runs-dir ./runs --port 8765
```

Use JSON when another program consumes the result:

```bash
loop-engine solve \
  --file task.txt \
  --workspace ./workspace-from-file \
  --runs-dir ./runs-from-file \
  --interaction-mode autonomous \
  --model-route cloud.default \
  --model-id deepseek-v4-flash:0731 \
  --authorize-model-calls \
  --max-model-calls 16 \
  --max-total-tokens 1000000 \
  --format json
```

JSON mode emits one machine-readable solve result with the terminal code,
artifact records, verification, model usage, tool count, workspace, and Run
History location.

## Solve from a task file

```bash
cat > task.txt <<'EOF'
Create a Python command-line program that reads a JSON file, produces a
Markdown summary, and includes runnable verification.
EOF

loop-engine solve \
  --file task.txt \
  --workspace ./task-workspace \
  --runs-dir ./task-runs \
  --interaction-mode autonomous \
  --model-route cloud.default \
  --authorize-model-calls \
  --max-model-calls 16 \
  --max-total-tokens 1000000
```

## Use a local dataset or repository

Local source content is not sent to a model without a separate grant.

```bash
loop-engine solve \
  --dataset ./inventory.csv \
  --text "Normalize product names, mark quantities of five or lower as low stock, and write a cleaned CSV plus a summary." \
  --allow-source-to-model \
  --workspace ./inventory-workspace \
  --runs-dir ./inventory-runs \
  --interaction-mode autonomous \
  --model-route cloud.default \
  --authorize-model-calls \
  --max-model-calls 16 \
  --max-total-tokens 1000000
```

Use `--repository PATH --text "task"` for a document folder or small Python
package. Loop Engine accepts only bounded text source files, excludes common
dependency and version-control folders, and records exact input digests.

## What is supported now

| Area | Current behavior |
|---|---|
| Small Python utilities | Model proposes typed files and commands. Docker executes and verifies them. |
| Local data transforms | CSV, JSON, text, and related bounded inputs can be copied into the workspace. |
| Document and repository analysis | Bounded text files can be materialized with explicit source-to-model authority. |
| Small Python package repair | The run can reproduce a nonzero exit, apply a changed source artifact, and rerun verification. |
| Providers | Ollama Cloud, Mistral, OpenRouter, OpenCode Go, and typed custom endpoints. Availability must be probed. |
| Effects | Workspace writes and commands require configured sandbox authority and exact per-effect approval. |
| Unsupported work | Returns `CAPABILITY_GAP`, `AUTHORITY_REQUIRED`, `PROVIDER_UNAVAILABLE`, or another typed terminal result. |

Loop Engine does not yet claim arbitrary-domain execution, automatic
deployment, unrestricted shell access, broad repository repair, or guaranteed
model quality.

## Task build is not solve

```text
loop-engine task build
  -> understands and structures a task
  -> does not claim that requested artifacts exist

loop-engine solve
  -> performs permitted work
  -> verifies real artifacts or returns an honest blocker
```

## How it works

```text
Original task
└─ Starting Practitioner Loop
   ├─ orient and standardize
   ├─ select the next bounded action
   ├─ bind a registered capability
   ├─ run Solution Loops in a confined workspace
   ├─ inspect commands and artifacts
   └─ return one terminal result with Run History
```

Every executable graph position uses the same runtime type, `Loop`.
Practitioner, Intelligence, and Solution are roles. Deterministic, hybrid, and
non-deterministic are per-Loop modes. `LoopGraphDefinition` remains the one
executable graph authority.

Read [how Loop Engine works](docs/guides/how-it-works.md) after the quickstart.
The [Architecture Constitution](docs/architecture/CONSTITUTION.md) defines the
hard runtime, permission, evidence, and governance rules.

## Development

```bash
python -m pip install -e '.[all]'
PYTHONPATH=src python -m loop_engine --self-test
PYTHONPATH=src python -m loop_engine --conformance
python -m build
```

Offline fixtures test typed semantic obligations but do not prove live model
quality. Live-provider claims require a separately saved authorized result.

## License

MIT. See [LICENSE](LICENSE).
