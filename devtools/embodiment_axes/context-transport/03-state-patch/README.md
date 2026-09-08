# state_patch

Send the procedure, one closed state record, and the latest observation.

Family: `context-transport`  |  Status: measured

## How it works

- Hold an accumulator with a fixed set of keys.
- Each step sends the procedure, the accumulator, and only the observation that just arrived.
- The reply may patch the accumulator; keys outside the schema are refused rather than merged.

## What it gives you

- Solves every horizon tried, up to 1,024 shards.
- The closed schema means a reply cannot widen what travels forward.
- History is not resent, so the per-step cost does not depend on how many steps came before.

## What it costs you

- Its state is not actually constant. Two fields are lists with one entry per shard, so the prompt goes from 950 bytes at 4 shards to 10,165 at 1,024. Ten times larger than the arm that fixed this.
- The word 'compact' in the design description was not true and reading the description would never have revealed it.
- One call per shard: 1,025 calls at 1,024 shards.

## Pick this when

- You want the standard SKILL.state shape and horizons are moderate.
- You need refusal of out-of-schema fields more than minimum bytes.

## Avoid it when

- The horizon is large. Audit the schema first, then use bounded_state.

## Run it

```bash
python3 context-transport/03-state-patch/embodiment.py        # its own self-check
python3 registry.py run --family context-transport
```

Generated from `manifest.json` by `registry.py catalog`. Edit the
manifest, not this file.
