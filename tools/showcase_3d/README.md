# 3D with and without Baltor

Kind: development comparison tool. It answers one question with numbers: does a harness pass more 3D modeling
tasks when material from Baltor is placed in it? It does not change the product.

The first comparison, on September 27, 2026, ran one run per task and condition and is recorded in
[the research record](../../docs/research/USER-JOURNEY-AND-3D-WITH-WITHOUT-2026-09-27.md). This tool repeats it
with at least five paired runs per task and condition, grading fixed before the first run, and a report that
lists every run.

## What one run is

```text
one run
├── a fresh project folder, configuration and session store, inside a sandbox that hides the home folder
├── condition
│   ├── without_baltor: the task text only
│   └── with_baltor: the runner first acts as the customer's client
│       ├── searches Baltor with the task text (frozen once per task before the first run)
│       ├── takes the top three skills of that search
│       ├── downloads every file of each package, with digest checks
│       └── places the files where OpenCode reads project skills (.opencode/skills/<name>/)
├── OpenCode starts once, with the same model, time budget and call ceiling in both conditions
├── every model call passes through the counting proxy (proxy.py)
└── the frozen checker grades the output file (checks.py)
```

No Baltor connection is open during a run, so model calls are spent on the task only. The prompt of the Baltor
condition adds one sentence that names where the material is (`tasks.BALTOR_NOTE`).

## Files

| File | What it holds |
|---|---|
| `tasks.py` | The five tasks, their acceptance numbers and a written definition of every check |
| `checks.py` | The deterministic checker; it refuses to report a check without a definition |
| `render_check.mjs` | The headless browser part of the three.js check |
| `controls.py` | Correct outputs that must pass and known-wrong outputs that must fail on a named check |
| `proxy.py` | The counting proxy in front of the model endpoint, with per-run and session ceilings |
| `rerun.py` | Schedule, freeze, selection, delivery, runs, sharing gate and report |

## How to run it

All machine paths live in a private configuration file (`showcase_3d_configuration/v1`), never in this folder.

```bash
python tools/showcase_3d/rerun.py freeze --config CONFIG.json [--extra-controls REAL-OUTPUTS.json]
python tools/showcase_3d/rerun.py select --config CONFIG.json
python tools/showcase_3d/rerun.py plan --config CONFIG.json --label rerun
python tools/showcase_3d/rerun.py run --config CONFIG.json --label rerun
python tools/showcase_3d/rerun.py report --config CONFIG.json --label rerun
```

- `freeze` refuses to record anything unless every control behaves as expected. A run refuses to start when a
  grading file changed after the freeze.
- `run` is resumable. Before every batch it waits while a daily library slot would overlap the batch, or while a
  process matching a configured busy pattern runs (the daily library job, candidate review, component
  qualification).
- `probe-installer` asks the first-party installer (`tools/install_selected_material.py`), in preview, whether it
  can place the selection natively. When it can, set `delivery_engine` to `first_party_installer`.

## What a run records

Task, condition, run number, pair and batch; model calls, with tokens as the server reported them (a total is
null when any call's usage is unknown); wall time; the harness version; every file Baltor delivered, with its
SHA-256 digest and its place; whether OpenCode listed each placed skill before the model started; pass or fail of
every check; and each failure (time budget, call ceiling, endpoint error, incomplete delivery, checker error).

The report gives the pass rate of each condition, overall and per task, with a Wilson 95 percent interval, the
pooled difference with a Newcombe interval, and one row for every run.

## Limits

- Five runs per cell can show only a large difference. The report states the intervals and makes no other claim.
- The selection is the service's own ranking for the task text. The report states the selected items for each task,
  whether they fit the task or not.
- The harness, the model endpoint and the machine are shared resources; wall times are affected by other load.
