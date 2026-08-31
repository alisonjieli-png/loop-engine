# Building with Loops

Loop Engine takes a task, performs real work in a confined workspace, verifies
the result, and saves an inspectable Run History.

Task interpretation is not limited to a fixed list or template. The current
effect capabilities can build small Python utilities, transform supplied local
files, summarize documents, analyze repositories, and repair small Python
packages. A task that needs another physical capability returns an honest
`CAPABILITY_GAP`.

## Install

You need [Python 3.10 or newer](https://www.python.org/downloads/) and
[Docker](https://docs.docker.com/get-docker/). Git is not required for the
quickstart. Starting from an empty computer? Use the
[Windows](docs/guides/install-windows/) or
[macOS](docs/guides/install-macos/) instructions first.

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

The default install is lightweight. In a source checkout, install `.[data]`
for the larger ML, Kaggle, vector, and analytical adapters, or `.[all]` for
every first-party optional adapter. The base self-test reports optional
adapters as not tested; it does not misreport a lightweight installation as
broken.

## Configure one provider

The shortest hosted path uses Ollama Cloud. Set the key, then inspect the
configuration without making a provider call:

```bash
export OLLAMA_API_KEY="your-key"
loop-engine configure
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

If you have an OpenRouter key and want a current zero-price route, export the
key and add `--openrouter-api-key` to `solve`. Loop Engine reads OpenRouter's
live catalog, selects an exact zero-price structured model with a declared
output maximum, and freezes that route for the run. `--opencode-zen-api-key`
does the same for current compatible OpenCode Zen zero-cost models.

## Add providers and capabilities with files

Loop Engine automatically checks these optional folders:

```text
.loop-engine/extensions
~/.config/loop-engine/extensions
```

They may contain provider routes, capability candidates, skills, plugin
bundles, and plugin intelligence. Inspect everything without a provider call:

```bash
loop-engine extensions discover
loop-engine extensions providers --format json
```

Zero-price routes and local routes activate automatically when their required
configuration exists. Free-plan allowances and paid routes require
`--allow-paid-extension-routes` because billing may begin after a quota.
Dropped code and intelligence remain candidates until their existing admission
and review requirements pass.

See [added-file extensions](docs/architecture/ADDED-FILE-EXTENSIONS.md) and the
[complete example](examples/23_drop_in_extensions/). The
[provider endpoint landscape](docs/guides/provider-endpoint-landscape.md)
lists the protocol and authentication families, including native cloud APIs
that still need a reviewed adapter.

## Solve a real task

Download the first example task and run the LLM-first quickstart profile:

```bash
curl -LO \
  https://raw.githubusercontent.com/alisonjieli-png/loop-engine/main/examples/tasks/01-expense-report.txt

loop-engine solve --file 01-expense-report.txt --quickstart
```

If the selected hosted model is temporarily unavailable, permit another exact
route for the same configured provider on the same solve path:

```bash
loop-engine solve --file 01-expense-report.txt --quickstart \
  --allow-model-failover
```

An explicitly selected `--model-id` remains pinned. Failover does not bypass
authentication, request, permission, effect, output, or verification checks.

`--quickstart` is an explicit authority profile. It selects one configured
provider, starts the LLM-first Practitioner, asks material
questions when needed, and permits the existing confined Docker workspace. It
does not impose a numeric pass, model-call, or token ceiling unless the user or
settings provide one. It does not authorize deployment, publication, or network
access from generated code.

Users do not choose deterministic, hybrid, or model-led execution during the
normal solve path. The runtime selects model-led reasoning when a model is
available. Use `--unattended` only when a run must abstain instead of returning
a material question.

Perspectives, question sets, templates, Intelligence refs, prior solutions,
and recovery strategies enter the prompt as candidates. The model selects
among them. Scores and step affinity help comparison but do not choose a task
meaning or solution.

After an accepted generated implementation, Loop Engine can emit a small
reuse opportunity and return the source result without waiting for packaging.
The asynchronous harvest path creates a Code Intelligence candidate. A future
task can use it only after independent qualification and explicit promotion.
An exact promoted match executes deterministically with zero model calls.

A versioned Loop contract may also execute without a dedicated conventional
implementation body. The exact semantic specification is bound into its
`LoopDefinition`. A qualified interpreter produces an untrusted candidate,
then independent verification and effect control decide whether anything may
enter trusted state. A later promoted deterministic realization can satisfy the
same contract with zero model calls for its declared input region. Read
[Transactional semantic runtime](docs/components/loop-object/SEMANTIC-RUNTIME.md).

If several known provider keys are present, quickstart prefers the dynamic
zero-price OpenRouter route, then the zero-cost OpenCode Zen route, before the
fixed Ollama Cloud, Mistral, and OpenCode Go routes. This chooses a candidate
route; it does not promise that the provider quota is currently available.

Read [LLM-first universal solving](docs/guides/llm-first-universal-solver.md)
for the model/runtime boundary. Read the
[Reusable Capability Flywheel](docs/components/intelligence-layers/REUSABLE-CAPABILITY-FLYWHEEL.md)
for candidate harvesting, promotion, search, and deterministic reuse.

A successful result has this shape:

```text
COMPLETED_VERIFIED
Expense report command and verified Markdown output.

Artifacts:
  .../workspace/attempt-1/expense_report.py (verified)
  .../workspace/attempt-1/report.md (verified)

Workspace: .../<run-id>-workspace/attempt-1
Verification: passed
Run ID: <run-id>
Run History: ~/.loop-engine/runs/<run-id>
```

A generated-project solve writes only inside the selected workspace. Commands
run in the pinned Docker image with bounded resources and no network during
execute or verify steps. Dependency setup requires separate authority.

If an answer can materially change the goal, authority, inputs, or acceptance,
the solve returns `BLOCKED_MATERIAL_INPUT` with a named answer slot instead of
guessing. Supply the answer separately and rerun the unchanged task:

```bash
loop-engine solve --file task.txt --quickstart \
  --task-feedback 'required_destination=./results/final-report.md'
```

## Inspect the result

```bash
loop-engine runs
loop-engine report @last
loop-engine studio --port 0
```

Studio selects an available local port and prints the address. Open the Result
tab for artifacts and verification, Playback for the event sequence, Tree for
the Loop hierarchy, and Calls for provider activity.

Use JSON when another program consumes the result:

```bash
loop-engine solve \
  --file task.txt \
  --quickstart \
  --format json
```

JSON mode emits one machine-readable solve result with the terminal code,
artifact records, verification, model usage, tool count, workspace, and Run
History location.

## Solve from a task file

You can also [download ready-to-run task files](examples/tasks/) from GitHub.

```bash
cat > task.txt <<'EOF'
Create a Python command-line program that reads a JSON file, produces a
Markdown summary, and includes runnable verification.
EOF

loop-engine solve --file task.txt --quickstart
```

## Use a local dataset or repository

Local source content is not sent to a model without a separate grant.

```bash
loop-engine solve \
  --dataset ./inventory.csv \
  --text "Normalize product names, mark quantities of five or lower as low stock, and write a cleaned CSV plus a summary." \
  --allow-source-to-model \
  --quickstart
```

Use `--repository PATH --text "task"` for a document folder or small Python
package. The Practitioner first sees an input manifest. The model selects the
text files it needs, then Loop Engine materializes those exact files, excludes
common dependency and version-control folders, and records input digests.

## What is supported now

| Area | Current behavior |
|---|---|
| Small Python utilities | Model proposes typed files and commands. Docker executes and verifies them. |
| Local data transforms | Selected CSV, JSON, text, and related inputs can be copied into the workspace. |
| Document and repository analysis | Model-selected text files can be materialized with explicit source-to-model authority. |
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
   ├─ select the next concrete action
   ├─ propose a registered capability or a new local implementation
   ├─ validate permissions and capability availability
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
