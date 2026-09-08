# single_pass

Do not decompose. One pass over everything.

Family: `decomposition`  |  Status: measured

## How it works

- One state, one cursor, one order.
- Every unit folds into the same accumulator.

## What it gives you

- Fewest total calls of any arm here, because nothing pays a per-group final call.
- No merge, so no chance of a merge being wrong.
- Nothing to size, nothing to tune, nothing to schedule.

## What it costs you

- Serial depth equals the work. Nothing can run at the same time as anything else.
- One failure is the whole run's failure; there are no independent domains.
- Cannot use more than one worker even when they are free.

## Pick this when

- Work is small, or strictly ordered, or you have one worker.
- You want the cheapest total and do not care about latency.

## Avoid it when

- Latency matters and workers are available.

## Run it

```bash
python3 decomposition/01-single-pass/embodiment.py        # its own self-check
python3 registry.py run --family decomposition
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.
