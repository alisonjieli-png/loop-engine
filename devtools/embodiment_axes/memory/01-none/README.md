# none

Nothing survives a run.

Family: `memory`  |  Status: measured

## How it works

- Start from an empty state.
- Keep nothing at the end.

## What it gives you

- Cannot be poisoned. There is nothing to write to.
- Every run is reproducible from its inputs alone.
- No storage, no keys, no eviction, no staleness.

## What it costs you

- Identical work is redone in full every time.
- A run that stops loses everything it had done.
- Nothing improves with experience.

## Pick this when

- Runs are cheap, or inputs never repeat.
- You need every run to be independently reproducible.

## Avoid it when

- Runs are expensive and inputs repeat.

## Run it

```bash
python3 memory/01-none/embodiment.py        # its own self-check
python3 registry.py run --family memory
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.
