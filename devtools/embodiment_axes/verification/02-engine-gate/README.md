# engine_gate

Structural gates that need no second pass over the world.

Family: `verification`  |  Status: measured

## How it works

- Check the answer has the promised keys and types.
- Check every referenced thing exists.
- Check the run actually finished its reading.
- Check the answer agrees with the state the run carried.

## What it gives you

- Costs no extra reads, so it is affordable on every run.
- Caught four of five faults, including two that a reader would expect to need recomputation: an answer that stopped early, and a total that disagreed with its own account breakdown.
- The agreement check is the cheap one people skip and it is the one that earns its place: an answer that contradicts its own run is wrong whatever it says.

## What it costs you

- Missed the one fault that agrees with itself at every level, where the total, the breakdown and the count were all moved together. No structural check can see that, by construction.
- Every gate is a rule someone wrote, so it only covers the failures that were imagined.
- Scores well enough against ordinary faults to give a false sense of coverage.

## Pick this when

- You want a default that is strictly better than free.
- Answers are structured and referential.

## Avoid it when

- Correctness of the arithmetic is the thing at stake.

## Run it

```bash
python3 verification/02-engine-gate/embodiment.py        # its own self-check
python3 registry.py run --family verification
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.
