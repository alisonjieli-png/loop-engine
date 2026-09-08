# independent_recompute

A second implementation reads the world again and recomputes.

Family: `verification`  |  Status: measured

## How it works

- Read every unit again through the tool.
- Compute the answer with arithmetic written from the task text, not shared with the run.
- Compare, and refuse on any disagreement.

## What it gives you

- Caught all five faults, including the internally consistent one that the structural gate cannot see.
- Shares no work with the run, so a defect cannot propagate into its own check.
- Rejected nothing on the clean control.

## What it costs you

- Costs a full second pass over the world, one read per unit, and the harness records exactly that.
- Needs a second implementation, which is real work and can itself be wrong.
- Only applies where the answer can be recomputed at all.

## Pick this when

- Something acts on the answer automatically.
- The answer is cheap to recompute relative to its cost being wrong.

## Avoid it when

- Recomputation is as expensive as the original run and the answer is low stakes.

## Run it

```bash
python3 verification/03-independent-recompute/embodiment.py        # its own self-check
python3 registry.py run --family verification
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.
