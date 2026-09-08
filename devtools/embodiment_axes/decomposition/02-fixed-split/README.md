# fixed_split

Cut the work into a fixed number of independent groups.

Family: `decomposition`  |  Status: measured

## How it works

- Slice the units into contiguous groups.
- Give each its own accumulator and its own pass.
- Merge the partial results at the end.

## What it gives you

- Serial depth falls by roughly the group count, which is what wall time follows when groups run at once.
- Groups are independent, so one failing costs that group and not the run.
- The group count is a direct handle on how many workers get used.
- Contiguous slices keep a group's identifiers adjacent, so a ledger reader can tell which slice a call belonged to.

## What it costs you

- More total calls, not fewer: every group pays its own final call.
- The right group count depends on the machine, not on the work, so it has to be set by someone who knows the machine.
- Needs a merge that is associative and gets the task's tie-breaks right, which is a real piece of code that can be wrong.
- This folder shipped a slicer that returned six groups when seven were asked for, which would have silently mis-sized a worker pool.

## Pick this when

- Units are independent and workers are available.
- You know how many workers you have.

## Avoid it when

- Units depend on each other, or the merge cannot be made associative.

## Run it

```bash
python3 decomposition/02-fixed-split/embodiment.py        # its own self-check
python3 registry.py run --family decomposition
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.
