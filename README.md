# Baltor

Harness and agent optimized operation.

Baltor makes coding harnesses and multi-agent systems as efficient as
possible. The aim is a frontier harness, multi-agent system or fabric that can
take on any unseen task in the most efficient way:

- the exact context each step needs, and no more;
- code that already exists is reused instead of written again;
- the right amount of intelligence and heuristics for each decision;
- small models doing much more, including work that runs overnight.

The task can be anything: a data pipeline, research, a data cleanup or a piece
of software. Turning a complex problem into a solution you can run again is
one benefit of this work. It is not the goal itself.

Baltor is the product and the website at <https://baltor.ai>. Loop Engine is
this repository: the open engine behind Baltor, the Python package
`loop-engine` and the `loop-engine` command.

## One harness for each step

A harness is the program that runs a coding agent, such as OpenCode, Codex,
Claude Code or Pi. Baltor is designed to start a fresh harness for every
step of a task. Each one holds only the context, skills, tools and code that
its small step needs, so no step carries the context rot of a long,
overloaded session.

```text
A task
├── Step 1: a fresh harness with the material step 1 selected
├── Step 2: a fresh harness with the material step 2 selected
├── Step 3: a fresh harness that reuses tested code instead of writing it
└── Check: an independent step accepts or rejects the result
```

Inside the engine, each step is a discrete cognitive or act step Loop node:
one independently governed instance of the Loop runtime, responsible for one
clearly defined cognitive step or action, with its own contracts, permissions
and history. Read the
[complete behavioral explanation](ASTRA.md#complete-behavioral-explanation)
before describing one.

## What Baltor gives your harness

Baltor Pro connects the harness you already run to a searchable library of
material that drops into a harness working directory:

- `AGENTS.md` and other context files;
- skills (`SKILL.md`);
- plugins and protocol server configurations;
- reusable, tested code.

Your harness searches the library, gets back short references (identity,
purpose, source, licence, exact version and digest) and downloads only the
item a step chose. Access is checked again at download, and every delivery is
recorded in your usage. Your models and your provider keys stay with you:
Baltor never asks for a provider key and never calls a model on your behalf.

The library is meant to be the one place that holds material scattered today
across many skill sites, plugin directories and repositories. Each item is
reviewed by someone other than its author before it is served, and retrieval
hands each step a small, exact result.

## Who it is for

- **Developers.** Leave a local model such as Gemma 4 running overnight on
  bounded steps, with a record of every step to read in the morning.
- **Teams.** Share one reviewed library and one way of breaking work into
  steps across the harnesses people already use.
- **Agentic systems.** An agent can call Baltor itself to give each of its
  steps the right context, so smaller and cheaper models can finish larger
  problems without context drift.

## The problems it answers

1. Too much context for a small task.
2. An expensive model for every decision.
3. Missing domain expertise.
4. Paying to rewrite code that already exists.
5. The same mistakes appearing again.
6. Large, multi-step, long-horizon problems that small and cheap models cannot
   finish alone.

The benefits we are working to prove are: finishing complex and long-horizon
work and producing reusable solutions; lower cost through cheaper models and
fewer tokens; work that finishes overnight; and optimization, including
turning work that needed a model into a deterministic solution. They are
drafts until the [benefit evidence guide](docs/guides/launch-benefits-and-evidence.md)
records a measured run for each one.

Use cases we are building demonstrations for, each with and without Baltor:

- a developer's tickets worked overnight on a local model;
- a data set cleaned without asking an expensive model to do simple
  transformations;
- a data science competition taken from task to submission.

## Status on September 25, 2026

Working on the live service today:

- public sign-up at <https://baltor.ai/get-started>: your email address, then
  the link we send you, then a password you choose. The first 10 accounts
  hold Baltor Pro free each month;
- Baltor Pro at $29 a month through Stripe checkout, cancelled from your
  account page;
- personal client keys, and ready connection entries for Claude Code, Codex,
  OpenCode, Pi (through a small Baltor extension) and the Baltor Harness (with
  one manual step);
- the Model Context Protocol endpoint, speaking protocol revisions
  `2025-11-25` and `2026-07-28`, with search that returns references and
  downloads that check access and bytes;
- a reviewed library in two labelled tiers, published without a redeploy.
  **Community** items were each approved by one model family that did not
  write them, with every automated check passing. **Verified** is for items
  approved by reviewers of at least two such families. Today's Verified items
  are the first catalogue of September 21, 2026, which predates that rule: its
  skills were written with Claude Code and approved by three reviewers that did
  not write them, and those reviews do not show two other model families, so
  they are reviewed again by two other families as soon as those reviewers are
  available. The service's `/api/v1/capabilities` record gives the live count
  and the published meaning of each tier;
- an Administration view where a superadmin sees every account and can grant
  or revoke free monthly Baltor Pro and switch an account off or on. Staff
  roles are fixed in code: superadmin, developer and analytics.

Not open yet:

- items with more than one file, placed as a package in your harness working
  directory;
- the engine starting a fresh standard harness for each step, and searching
  the library by itself.

The [current deployment](docs/architecture/MVP-CLIENT-SERVER.md#current-deployment)
section records the running release. The [development tracker](docs/roadmap/DEVELOPMENT-TRACKER.md)
lists what is being built now, next and later, generated from the
[roadmap](docs/roadmap/roadmap.yaml).

## How the library grows

Every item starts as a candidate, and a candidate is served only after an
independent review approves it:

```text
Library item
├── Sources
│   ├── original methods written by the first-party generation waves
│   ├── generation lanes on Ollama Cloud models and a Gemma 4 model server
│   └── outside projects, used only as inspiration unless their licence
│       allows copying
├── Deterministic pre-checks: layout, digests, secrets, network use, effects,
│   duplicates, and each package's own tests in a sandbox with no network
├── Review panel: three approvals from three model families that did not
│   write the item, and no rejection
└── Catalogue release: published to the running service without a redeploy,
    with the previous release kept for rollback
```

The candidate pool holds several thousand files across skills, instruction
files, subagents, commands, hooks, rules, plugin manifests, protocol server
configurations, permission settings, step packets and verifiers. None of them
is served until the review approves it. The library target is 10,000
approved items first and 100,000 after that.

## Connect your harness

1. Create your account at <https://baltor.ai/get-started>, then subscribe to
   Baltor Pro from your account page, unless your account already includes
   it.
2. Create a personal client key on your account page and put it in the
   environment variable `BALTOR_SERVICE_TOKEN`. A connection entry names that
   variable and never contains the key.
3. Add Baltor to your harness. The Get set up page on <https://baltor.ai/setup>
   gives the exact entry for Claude Code, Codex, OpenCode, Pi and the Baltor
   Harness, and [getting set up](docs/guides/service-getting-set-up.md)
   explains each one.

Revoking a key stops its next request. It does not recall files that were
already downloaded.

## Case studies

- [Data cleanup with and without Baltor](case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md)
  measures what library material did to a cheap model's cleanup work,
  including the cases where it cost more tokens or made the result worse.
- [Release 24 account journeys](artifacts/release-24-2026-09-24/README.md)
  record how sign-up was checked on the live site, including an attempt to
  take over an address through the identity provider's own sign-up.

## Components and engines

The architecture rule: every functional component sits behind a fixed, typed
and versioned edge, with one or more engines behind it. Swapping, adding or
retiring an engine changes that engine and its declaration, not the
components around it. The rule applies at the component level and above and
below it, and the folder structure is to follow the components and their
engines.

| Component | Engines that exist today | Being built |
|---|---|---|
| Search and retrieval | SQLite full-text search (the default), LanceDB, hashing and Model2Vec backends behind one handshake | a served relevance floor; self-learning and near-duplicate engines |
| Record storage | SQLite, DuckDB and an in-memory store | durable cloud records |
| Model calls | one gateway that resolves each call to a configured provider route with a source-backed output limit | a layer that decides between one model and several (voting, disagreement and resolution) |
| Decisions | the Jev, Circuit and System One decision engine profiles | logging each decision against its later outcome |
| Address parsing | standard library, usaddress and libpostal | more data-work engines |
| Configuration search | grid, random, vector warm start and Optuna | evidence-based ranking across runs |
| Step execution | the engine's own runtime and registered harness adapters | one fresh standard harness per step through the Agent Client Protocol, OpenCode first |

The shared engine framework is designed and not built yet. It will index
every slot, let a harness send engine preferences within its authority, and
choose among eligible engines by declared order and recorded evidence. The
[components index](docs/components/README.md) holds a guide for each
component.

## Intelligence

The library keeps four persistent intelligence layers: Context Intelligence,
Code Intelligence, Runtime History and Solution Intelligence, and User
Feedback Intelligence. Runtime Memory is separate, temporary and scoped to one
run.

Material is also organized by family, which says what it is built to follow:
harness intelligence (files a standard harness already reads, served first),
Loop-native intelligence and Open Knowledge Format intelligence. Imported and
generated material stays a candidate until an independent process approves
it. Nothing is promoted because it was retrieved, executed or scored well. The
[harness-first decision](docs/architecture/ADR-HARNESS-FIRST-SERVING-AND-EXECUTION.md)
explains what the main line serves today.

## Run the service on your own machine

You can run the same intelligence service locally without a cloud account.
Follow the [local intelligence service example](examples/29_intelligence_service/README.md).

## The local engine

The engine in this repository can also solve tasks on your machine with your
own provider. The built-in quickstart builds small Python projects. Other
applications supply their own operations and checks through the
[host integration API](docs/guides/embedding-loop-engine.md). This is not a
claim that arbitrary unseen tasks are already solved.

### Install

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
for the larger machine learning, Kaggle, vector and analytical adapters, or
`.[all]` for every first-party optional adapter.

### Configure one provider

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

Do not continue if the probe reports an authentication, rate-limit,
output-limit or availability failure. A configured key is not proof that a
provider works. See [providers and keys](docs/guides/providers-and-keys.md)
for OpenRouter, Mistral, local Ollama, OpenCode Go and custom endpoints.

### Solve a task

Download the first example task and run the quickstart profile:

```bash
curl -LO \
  https://raw.githubusercontent.com/alisonjieli-png/loop-engine/main/examples/tasks/01-expense-report.txt

loop-engine solve --file 01-expense-report.txt --quickstart
```

You can also [download ready-to-run task files](examples/tasks/) from GitHub.

`--quickstart` is an explicit authority profile. It selects one configured
provider, starts the model-led Practitioner, asks material questions when an
answer would improve the outcome, and permits the confined Docker workspace.
It does not authorize deployment, publication or network access from
generated code. Commands run in the pinned Docker image with bounded
resources and no network during the execute and verify steps.

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

A task that needs a capability the engine does not have returns a complete
best-available result with the exact `CAPABILITY_GAP`, the useful work
already done and the next actions. Read
[model-led universal solving](docs/guides/llm-first-universal-solver.md) for
the boundary between the model and the runtime.

### Inspect the result

```bash
loop-engine runs
loop-engine report @last
loop-engine studio --port 0
```

Studio picks a free local port and prints the address. The Result tab shows
artifacts and verification, Playback the event sequence, Tree the Loop
hierarchy and Calls the provider activity.

### Add providers and capabilities with files

The engine checks `.loop-engine/extensions` and
`~/.config/loop-engine/extensions` for provider routes, skills, plugin bundles
and plugin intelligence. Dropped code and intelligence remain candidates until
their admission and review requirements pass. See
[added-file extensions](docs/architecture/ADDED-FILE-EXTENSIONS.md) and the
[complete example](examples/23_drop_in_extensions/).

### Task build is not solve

```text
loop-engine task build
  -> understands and structures a task
  -> does not claim that requested artifacts exist

loop-engine solve
  -> performs permitted work
  -> verifies real artifacts or returns an honest blocker
```

## Repository map

```text
loop-engine
├── src/loop_engine       the engine, the Loop runtime and the hosted service
├── docs                  architecture, contracts, component guides, roadmap
├── examples              runnable examples, including the local service
├── tools                 development, release and checking commands
├── devtools              developer-only audits and qualification labs
├── embodiments           harness integration experiments
├── integrations          thin host packages over the command or the service
├── kaggle                single-cell notebooks that run the engine on Kaggle
├── benchmarks            frozen task populations and their records
├── case-studies          worked cases
├── artifacts             dated evidence and release records
├── checkpoints           dated snapshots of the whole system
└── showcase              the interactive architecture view
```

[Repository organization](docs/REPOSITORY-ORGANIZATION.md) gives the kind and
the rules of each folder.

## Develop and release

Start with [AGENTS.md](AGENTS.md): the rules, the north star and the
authority for commits, pushes and releases. Then read
[START-HERE](docs/context/START-HERE.md) and the
[Constitution](docs/architecture/CONSTITUTION.md).

```bash
python -m pip install -e '.[all]'
PYTHONPATH=src python -m loop_engine --self-test
PYTHONPATH=src python -m loop_engine --conformance
PYTHONPATH=src python -m loop_engine service smoke
python -m build
```

Releases come only from a committed revision whose continuous integration run
passed. They are deployed by image digest through the guarded workflow, the
previous image is kept for rollback, and every live hostname is checked after
the release. Offline fixtures test typed obligations; they do not prove live
model quality, and a live-provider claim needs a saved, authorized result.

## What is not claimed

- The engine does not yet execute arbitrary tasks in any domain, deploy
  automatically, or repair large repositories in general.
- No benefit above has a published measurement yet.
- A connected client, a downloaded file and a completed step are separate
  facts. Offered, fetched, loaded, used and verified are recorded separately.

## License

MIT. See [LICENSE](LICENSE). [CONTRIBUTING](CONTRIBUTING.md) and
[SECURITY](SECURITY.md) describe how to contribute and how to report a
security problem.
