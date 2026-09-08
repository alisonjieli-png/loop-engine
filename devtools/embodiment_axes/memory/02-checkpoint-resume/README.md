# checkpoint_resume

The position survives a stop. Conclusions never do.

Family: `memory`  |  Status: measured

## How it works

- Write the accumulator and the cursor when a run stops.
- A later run over the same task continues from there.
- No answer is ever stored.

## What it gives you

- A stopped run keeps its progress, which is the difference between a retry and a restart.
- Nearly all of the cache's saving without any of its exposure: a repeat cost 1 call against the cold run's 17, because the position is already at the end and the answer is re-derived from the state rather than served.
- The worst a corrupted checkpoint can do is start from a wrong subtotal, which recomputation catches. It cannot make a run report someone else's conclusion, and the poison scenario confirmed it.
- No review machinery needed, because nothing is ever believed.

## What it costs you

- One call short of the cache on a repeat, so it is not free where the cache is.
- Keyed on the task, so a changed input silently misses.
- A stale checkpoint against a changed world is a real hazard, and the position and the subtotal must be stored together or a resumed run counts the same work twice. This folder shipped that defect until a measurement found it.

## Pick this when

- Runs are long and interruption is normal.
- You want durability without opening a trust surface.

## Avoid it when

- The same task repeats often and you want the savings.

## Run it

```bash
python3 memory/02-checkpoint-resume/embodiment.py        # its own self-check
python3 registry.py run --family memory
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.
