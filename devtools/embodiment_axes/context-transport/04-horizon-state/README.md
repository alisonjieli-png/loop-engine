# horizon_state

The same state fields, labelled long, medium and short horizon.

Family: `context-transport`  |  Status: measured

## How it works

- Carry exactly what state_patch carries.
- Render it in three labelled blocks: what holds for the whole run, what holds for this phase, and what just happened.
- Nothing else differs, which makes this the clean presentation test.

## What it gives you

- Costs 60 to 65 bytes more per prompt than state_patch at every horizon tried, so the price of the labels is known and small.
- The three blocks give a human reader a place to look.
- Differs from state_patch in presentation only, so a live run prices the labels against nothing else.

## What it costs you

- Against a perfect reader its correctness is identical by construction, so this harness can price the labels and cannot value them.
- Inherits the horizon-proportional fields from state_patch, and the same 10 kilobyte prompt at 1,024 shards.

## Pick this when

- A person reads the prompts and needs the structure.
- You are running the live A/B against state_patch.

## Avoid it when

- Bytes are the binding constraint and no one reads the prompts.

## Run it

```bash
python3 context-transport/04-horizon-state/embodiment.py        # its own self-check
python3 registry.py run --family context-transport
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.
