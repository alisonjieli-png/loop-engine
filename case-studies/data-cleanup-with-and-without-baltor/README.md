# Data cleanup with and without Baltor material

A measured demonstration for roadmap steps D-07, D-08, S-6.37 and S-6.47.
A small or cheap model cleans data in a fresh Pi harness for each step, with
and without an approved item from the starter catalogue, and an independent
deterministic scorer checks every output file. It is not a full Loop Engine
case study; see [the design](DESIGN.md#data-cleanup-with-and-without-baltor-material-frozen-design).

## Layout

```text
data-cleanup-with-and-without-baltor/
├── DESIGN.md                 frozen design, written before the first model call
├── design.json               the same design as data the runner reads
├── design-freeze.json        SHA-256 of every frozen file and item
├── population/               generator, inputs, prompts, truth, known-wrong outputs
├── scorer/                   independent scorer and its tests
├── runner/                   harness runner, counting proxy, freeze tool, tests
├── trials/                   request ledger, one record, score and output per step
└── results/                  summaries built from the trial records
```

## Run it

From this folder, with Python 3.12 or later and no extra packages:

```bash
python population/generate_population.py --check
python runner/freeze.py --check
(cd scorer && python -m unittest test_score_step)
(cd runner && python -m unittest test_meter)
python runner/run_trials.py capture --run-folder /path/outside/the/repository
```

`capture` sends every request to a local stub with no model behind it and
reports what each arm would send. The `pilot`, `main` and `optional` phases
call models and need the model authority and budget recorded in the design.

## Status and result files

The pilot, the main plan and the optional arm ran on September 22 and 23,
2026, United States Eastern time, with 225 of the 400 allowed model requests.

- [results/tables.md](results/tables.md): scores for every family, arm and
  repetition, and the comparisons under the frozen claim rules.
- [results/summary.json](results/summary.json): the same with requests,
  tokens, time, loading checks and row types.
- [results/use-signals.json](results/use-signals.json): words that only the
  items introduce, found in the model's own text.
- [trials/requests.jsonl](trials/requests.jsonl): one line for every request
  sent or refused. `trials/request-bodies.tar.gz` holds every request and
  response body.
- [amendments.json](amendments.json): the one change after the pilot, which
  touched recording only, and the pilot findings.

Rebuild the summaries with `python runner/summarize.py`, and the signs of use
with `python runner/use_signals.py --bodies <folder>` after unpacking the
archive into that folder.

## Evidence boundary

The data is synthetic and disclosed as such. One harness and three models
were used. Cloud model cost is covered by a subscription and is not metered
for each request. Any public statement must stay within the claim rules in
the design and the dated report in this folder.
