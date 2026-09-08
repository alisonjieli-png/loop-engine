# cross_run_cache

Remember the answer and serve it whenever the task matches.

Family: `memory`  |  Status: measured

## How it works

- Store the final answer under a task key.
- Serve it on a later match without any calls.

## What it gives you

- The largest possible saving: a repeat costs zero calls.
- Trivial to implement and to reason about.
- Latency on a hit is a lookup.

## What it costs you

- Anything that can write decides what later runs believe. An outsider's record was served unchanged and the run returned it as its answer.
- The margin it buys over a checkpoint store is one call out of seventeen, and it pays for that margin with total exposure.
- No provenance, no review, no re-derivation.
- A wrong answer, once written, is served forever and looks authoritative because it is fast.

## Pick this when

- The store is trusted end to end and answers are genuinely deterministic in the key.

## Avoid it when

- Anything other than the run can write, or the key does not fully determine the answer.

## Run it

```bash
python3 memory/03-cross-run-cache/embodiment.py        # its own self-check
python3 registry.py run --family memory
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.
