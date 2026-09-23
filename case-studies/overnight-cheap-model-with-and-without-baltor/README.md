# Overnight batch with a cheap model, with and without Baltor material

A measured demonstration for roadmap steps S-6.37, D-07 and D-08. A cheap
model, `gemma4:31b` on Ollama Cloud, works through a queue of 36 data cleanup
steps with nobody watching. Every step runs in a fresh Pi harness process,
with or without an approved item from the starter catalogue, and an
independent deterministic scorer checks every output file. The runner
survives a crash and resumes; a declared drill kills it once in the middle of
a step. It is not a full Loop Engine case study; see
[the design](DESIGN.md#overnight-batch-with-a-cheap-model-with-and-without-baltor-material-frozen-design).

## Layout

```text
overnight-cheap-model-with-and-without-baltor/
├── DESIGN.md                 frozen design, written before the first counted model call
├── design.json               the same design as data the runner reads
├── design-freeze.json        SHA-256 of every frozen file
├── material/                 the exact approved item bytes and their approval rows
├── probe/                    model metadata, the tool call probe and the capture check
├── population/               generator, inputs, prompts, truth, known-wrong outputs,
│                             and the item method reference with no model
├── scorer/                   independent scorer and its tests
├── runner/                   runner, supervisor, counting proxy, freeze tool, analysis, tests
├── trials/                   request ledger, one record, score and output per step attempt
└── results/                  summaries built from the step records
```

## Run it

From this folder, with Python 3.12 or later and no extra packages:

```bash
python population/generate_population.py --check
python runner/freeze.py --check --catalogue
(cd scorer && python -m unittest test_score_step)
(cd runner && python -m unittest test_meter test_runner)
python runner/run_trials.py capture --run-folder /path/outside/the/repository
```

`capture` sends every request to a local stub with no model behind it and
reports what each arm would send. The `probe`, `pilot` and `main` phases call
the provider and need the model authority and the key recorded in the
design. The unattended batch is started with
`runner/overnight.sh /path/outside/the/repository`, which restarts the runner
after a crash. The item method reference needs the repository source:
`PYTHONPATH=src python case-studies/overnight-cheap-model-with-and-without-baltor/runner/item_reference.py --check`
from the repository root.

## Status

The design is frozen. The pilot and the main plan have not run yet. A dated
report will be added beside this file with every number, failure and
limitation.

## Evidence boundary

The data is synthetic and disclosed as such. One harness, one model and one
provider are used. The model runs in the provider's cloud, so nothing here is
evidence about local hardware. Cloud model cost is covered by a subscription
and is not metered for each request. Any public statement must stay within
the claim rules in the design and the dated report in this folder.
